
import os
import secrets
import json
import logging
import copy
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, render_template, request, jsonify, session
from flask_session import Session
from dotenv import load_dotenv

# Import Project Logic
from chess_logic import ChessGame
from services import coach_agent, opponent_agent

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask App
app = Flask(__name__)

# --- Configuration ---
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(16))
app.config["SESSION_TYPE"] = "filesystem" 
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_USE_SIGNER"] = True
app.config["SESSION_FILE_DIR"] = "/tmp/flask_session"

# Initialize Session Extension
Session(app)

# Ensure Google Cloud Project is set
if 'GOOGLE_CLOUD_PROJECT' not in os.environ:
    logger.warning("GOOGLE_CLOUD_PROJECT not found in environment variables. Vertex AI calls may fail.")

# Helper for AI worker
def ai_worker(game_copy, skill_level):
    """
    Worker function to calculate AI move in a separate thread.
    This includes the expensive 'get_all_legal_moves_with_consequences' call.
    """
    # 1. Calculate the 'ground truth' for the AI (Move Consequence Mapping)
    enhanced_moves = game_copy.get_all_legal_moves_with_consequences(game_copy.turn)
    
    # 2. Calculate tactical threats (Dangers List)
    tactical_threats = game_copy.get_tactical_threats(game_copy.turn)
    
    # 3. Get simple list of legal moves for validation
    legal_moves_simple = [m['move'] for m in enhanced_moves]
    
    # 4. Call the Agent
    return opponent_agent.get_ai_move(
        json.dumps(enhanced_moves),
        json.dumps(tactical_threats),
        legal_moves_simple,
        skill_level
    )

# --- Routes ---

@app.route('/')
def index():
    """Renders the main game page."""
    return render_template('index.html')

@app.route('/health')
def health_check():
    return jsonify({"status": "healthy", "app": "RooChess Flask"})

# --- Game API ---

@app.route('/api/new_game', methods=['POST'])
def new_game():
    """Initializes a new game session."""
    game = ChessGame()
    session['chess_game'] = game
    
    data = request.json or {}
    session['player_color'] = data.get('player_color', 'white')
    session['user_skill_level'] = data.get('skill_level', 'beginner') # Default to beginner
    
    # Reset chat history logic if we were storing it in session, 
    # but the frontend seems to manage chat display. 
    # The Coach agent is stateless per request mostly (except for Q&A context).
    session['chat_context'] = [] 

    return jsonify({
        "status": "success", 
        "message": "New game started",
        "turn": game.turn,
        "fen": game._get_board_state_string()
    })

@app.route('/api/state', methods=['GET'])
def get_state():
    """Returns the current board state."""
    game = session.get('chess_game')
    if not game:
        return jsonify({"status": "error", "message": "No active game"}), 404
        
    # Build a simple grid representation for the frontend
    grid = []
    for r in range(8):
        row = []
        for c in range(8):
            piece = game.board.get_piece((r, c))
            if piece:
                row.append({
                    "type": piece.__class__.__name__.lower(), # e.g., "pawn", "king"
                    "color": piece.color,
                    "symbol": piece.symbol
                })
            else:
                row.append(None)
        grid.append(row)

    return jsonify({
        "status": "success",
        "turn": game.turn,
        "grid": grid,
        "history": game.move_history,
        "game_over": game.game_over,
        "in_check": game.is_in_check(game.turn),
        "winner": 'draw' if "draw" in game.status_message.lower() else ('white' if game.turn == 'black' else 'black') if game.game_over else None,
        "status_message": game.status_message
    })

@app.route('/api/process_move', methods=['POST'])
def process_move():
    """
    Orchestrates the turn:
    1. Pre-Move: Calculate context for Coach (dangers/options BEFORE move).
    2. Move: Apply Human Move.
    3. Parallel Analysis: Run Coach (analyzing the move) and Opponent (thinking).
    4. Return: Coach feedback and AI move.
    """
    game = session.get('chess_game')
    if not game:
        return jsonify({"status": "error", "message": "No active game"}), 404
        
    data = request.json
    start_pos = data.get('start') 
    end_pos = data.get('end')
    
    if not start_pos or not end_pos:
        return jsonify({"status": "error", "message": "Invalid coordinates"}), 400
        
    start_tuple = tuple(start_pos)
    end_tuple = tuple(end_pos)
    
    # --- 1. Pre-Move Context (For Coach) ---
    # The coach needs to know what the dangers were *before* the user moved.
    dangers_before = game.get_tactical_threats(game.turn)
    options_before = game.get_all_legal_moves_with_consequences(game.turn)
    
    # --- 2. Apply Human Move ---
    game.store_pre_move_state()
    success, message = game.make_move(start_tuple, end_tuple)
    
    if not success:
        return jsonify({"status": "invalid", "message": message}), 400
        
    # Get move data for the Coach (the move that was just made)
    last_move_data = game.game_data[-1] if game.game_data else {}
    
    # --- 3. Parallel Execution (Coach & Opponent) ---
    coach_feedback = {"response_type": "silent", "message": None}
    ai_move_packet = None
    ai_reasoning = ""
    
    user_skill = session.get('user_skill_level', 'beginner')
    player_color = session.get('player_color', 'white')

    with ThreadPoolExecutor() as executor:
        # Task A: Coach Agent
        # Analyzes the move just made, using the "before" context.
        future_coach = executor.submit(
            coach_agent.get_coaching_packet,
            last_move_data,
            json.dumps(dangers_before),
            json.dumps(options_before),
            user_skill,
            player_color
        )
        
        # Task B: Opponent Agent (AI)
        # Calculates the response move. only if game is not over.
        future_ai = None
        if not game.game_over:
            # We MUST pass a deepcopy because 'ai_worker' will modify the board 
            # (simulating moves) and we don't want to corrupt the session game state 
            # or cause race conditions if we were doing other things.
            game_copy = copy.deepcopy(game)
            
            future_ai = executor.submit(
                ai_worker,
                game_copy,
                user_skill
            )
            
        # Wait for results (Coach)
        try:
            coach_feedback = future_coach.result(timeout=15)
        except Exception as e:
            logger.error(f"Coach failed: {e}")
            coach_feedback = {"response_type": "silent", "message": None}
            
        # Wait for results (AI)
        if future_ai:
            try:
                ai_packet = future_ai.result(timeout=30) # AI might take longer
                if ai_packet:
                    ai_move_packet = ai_packet.get("move")
                    ai_reasoning = ai_packet.get("reasoning")
            except Exception as e:
                logger.error(f"AI failed: {e}")

    # --- 4. Handle Results ---
    
    # Store AI move in session for confirmation step
    session['pending_ai_move'] = ai_move_packet
    session['pending_ai_reasoning'] = ai_reasoning
    session['chess_game'] = game # Save state
    
    # Simplified feedback/intervention logic
    # The frontend expects {status, coach_feedback, ai_move, ...}
    
    return jsonify({
        "status": "success",
        "fen": game._get_board_state_string(),
        "game_over": game.game_over,
        "coach_feedback": {
            "type": coach_feedback.get("response_type", "silent"),
            "message": coach_feedback.get("message")
        },
        # If the coach intervenes ("blunder"), we do NOT show/execute the AI move yet.
        # The frontend will show the intervention modal.
        "ai_move": ai_move_packet if coach_feedback.get("response_type") != "intervention" else None,
        "ai_reasoning": ai_reasoning
    })

@app.route('/api/confirm_ai_move', methods=['POST'])
def confirm_ai_move():
    """Executes the pending AI move (used after intervention check)."""
    game = session.get('chess_game')
    ai_move_uci = session.get('pending_ai_move')
    
    if not game or not ai_move_uci:
        return jsonify({"status": "error", "message": "No pending AI move"}), 400
        
    # Helper to convert UCI-like "e2-e4" to coords
    def notation_to_coords(notation_str):
        if '-' not in notation_str: return None, None
        start_str, end_str = notation_str.split('-')
        
        def parse(sq):
            files = 'abcdefgh'
            c = files.index(sq[0])
            r = 8 - int(sq[1])
            return (r, c)
            
        return parse(start_str), parse(end_str)
        
    start, end = notation_to_coords(ai_move_uci)
    if start and end:
        success, msg = game.make_move(start, end)
        
        # Auto-promote (simplified for AI)
        if game.promotion_pending:
            game.promote_pawn("Queen") 
    
    session['pending_ai_move'] = None # Clear
    session['chess_game'] = game
    
    return jsonify({
        "status": "success", 
        "move": ai_move_uci,
        "fen": game._get_board_state_string()
    })

@app.route('/api/undo_move', methods=['POST'])
def undo_move():
    """Reverts the last move using the stored pre-move state."""
    game = session.get('chess_game')
    if game:
        game.revert_to_pre_move_state()
        session['chess_game'] = game
        return jsonify({"status": "success", "fen": game._get_board_state_string()})
        
    return jsonify({"status": "error"}), 400

@app.route('/api/legal_moves', methods=['POST'])
def get_legal_moves():
    """Returns legal moves for a specific piece."""
    game = session.get('chess_game')
    if not game:
        return jsonify({"status": "error", "message": "No active game"}), 404
        
    data = request.json
    start_pos = data.get('start') # Expected format: [row, col]
    
    if not start_pos:
        return jsonify({"status": "error", "message": "Invalid coordinates"}), 400
        
    r, c = start_pos
    piece = game.board.get_piece((r, c))
    
    if not piece or piece.color != game.turn:
        return jsonify({"status": "success", "moves": []})
        
    raw_moves = piece.get_valid_moves(game.board, game)
    legal_moves = []
    
    for move in raw_moves:
        # Check if move puts *own* king in check (illegal)
        if not game.move_puts_king_in_check((r, c), move):
            legal_moves.append(move)
            
    return jsonify({
        "status": "success",
        "moves": legal_moves 
    })

@app.route('/api/promote', methods=['POST'])
def promote_pawn():
    """Handles pawn promotion choice."""
    game = session.get('chess_game')
    if not game:
        return jsonify({"status": "error", "message": "No active game"}), 404
        
    data = request.json
    piece_choice = data.get('promotion') 
    
    if not piece_choice:
        return jsonify({"status": "error", "message": "Missing promotion choice"}), 400
        
    success, message = game.promote_pawn(piece_choice)
    
    if success:
        session['chess_game'] = game
        return jsonify({
            "status": "success",
            "message": message,
            "game_over": game.game_over
        })
    else:
        return jsonify({
            "status": "error",
            "message": message
        })

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handles Q&A with Coach."""
    game = session.get('chess_game')
    if not game:
         return jsonify({"status": "error", "response": "Start a game first!"})
         
    user_query = request.json.get('message')
    user_skill = session.get('user_skill_level', 'beginner')
    player_color = session.get('player_color', 'white')
    
    # Build context
    context = {
        "user_skill_level": user_skill,
        "player_color": player_color,
        "last_ai_reasoning": session.get('pending_ai_reasoning', ""), # Might be stale
        "current_turn": game.turn,
        # Live analysis for Q&A
        "dangers_list": json.dumps(game.get_tactical_threats(game.turn)),
        "options_list": json.dumps(game.get_all_legal_moves_with_consequences(game.turn))
    }
    
    response_packet = coach_agent.get_qa_response(user_query, json.dumps(context))
    response_text = response_packet.get("commentary", "I'm thinking...")
    
    return jsonify({"status": "success", "response": response_text})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
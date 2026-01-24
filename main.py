import os
import secrets
import json
from flask import Flask, render_template, request, jsonify, session
from flask_session import Session
from dotenv import load_dotenv

import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import Project Logic
from chess_logic import ChessGame
from services.coach_agent import coach_agent
from services.opponent_agent import opponent_agent

# Load environment variables
load_dotenv()

# Initialize Flask App
app = Flask(__name__)

# --- Configuration ---
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(16))
app.config["SESSION_TYPE"] = "filesystem" 
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_USE_SIGNER"] = True

# Initialize Session Extension
Session(app)

# Ensure Google API Key is present
if 'GOOGLE_API_KEY' not in os.environ:
    logger.warning("GOOGLE_API_KEY not found in environment variables.")

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
    
    return jsonify({
        "status": "success", 
        "message": "New game started",
        "turn": game.turn,
        "fen": game._get_board_state_string() # We might need a better serializer
    })

@app.route('/api/state', methods=['GET'])
def get_state():
    """Returns the current board state."""
    game = session.get('chess_game')
    if not game:
        return jsonify({"status": "error", "message": "No active game"}), 404
        
    # Build a simple grid representation for the frontend
    # (Or we can send FEN and let the frontend parse it, but grid is easier for custom UI)
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
        "in_check": game.is_in_check(game.turn), # ADDED
        "winner": 'draw' if "draw" in game.status_message.lower() else ('white' if game.turn == 'black' else 'black') if game.game_over else None, # ADDED simple winner logic
        "status_message": game.status_message
    })

@app.route('/api/move', methods=['POST'])
def make_move():
    """Handles a player move."""
    game = session.get('chess_game')
    if not game:
        return jsonify({"status": "error", "message": "No active game"}), 404
        
from concurrent.futures import ThreadPoolExecutor
import json

@app.route('/api/process_move', methods=['POST'])
def process_move():
    """
    Orchestrates the turn:
    1. Makes Human Move.
    2. Runs Agent Analysis & AI Move Search in Parallel.
    3. Returns Intervention status.
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
    
    # 1. Apply Human Move
    success, message = game.make_move(start_tuple, end_tuple)
    
    if not success:
        return jsonify({"status": "invalid", "message": message}), 400
        
    # Get last move info for analyis
    last_move_san = game.move_history[-1] if game.move_history else "Unknown"
    fen_after_move = game.fen
    
    # 2. Parallel Execution (Coach Analysis + Opponent Think)
    coach_result = {"type": "normal", "message": ""}
    ai_move_result = None
    ai_reasoning = ""
    
    if not game.game_over:
        with ThreadPoolExecutor() as executor:
            # We assume AI plays the opposite color of the human (who just moved)
            # So game.turn is now the AI's turn.
            
            # Task A: Coach checks for blunders in the HUMAN'S move (just made)
            # Note: We assess the move just made.
            future_coach = executor.submit(
                coach_agent.analyze_move, 
                fen_after_move, 
                str(game.move_history), 
                last_move_san
            )
            
            # Task B: Opponent calculate reponse
            future_ai = executor.submit(
                opponent_agent.get_move, 
                fen_after_move
            )
            
            # Wait for results
            try:
                coach_result = future_coach.result(timeout=10) # 10s timeout
            except Exception as e:
                logger.error(f"Coach failed: {e}")
                
            try:
                ai_move_result, ai_reasoning = future_ai.result(timeout=10)
            except Exception as e:
                logger.error(f"AI failed: {e}")

    # 3. Store AI move in session for confirmation
    logger.info(f"AI Move Result: {ai_move_result}, Coach Result: {coach_result}")
    
    session['pending_ai_move'] = ai_move_result
    session['pending_ai_reasoning'] = ai_reasoning
    session['chess_game'] = game # Save state
    
    return jsonify({
        "status": "success",
        "fen": game.fen,
        "game_over": game.game_over,
        "coach_feedback": coach_result,  # {type, message}
        "ai_move": ai_move_result if coach_result.get('type') != 'intervention' else None,
        "ai_reasoning": ai_reasoning
    })

@app.route('/api/confirm_ai_move', methods=['POST'])
def confirm_ai_move():
    """Executes the pending AI move (used after intervention check)."""
    game = session.get('chess_game')
    ai_move_uci = session.get('pending_ai_move')
    
    logger.info(f"Confirming AI Move: {ai_move_uci}")
    
    if not game or not ai_move_uci:
        logger.warning("Confirm AI Move failed: Missing game or move.")
        return jsonify({"status": "error", "message": "No pending AI move"}), 400
        
    # Helper to convert UCI to coords (duplicated logic, should serve refactor)
    def uci_to_coords(uci):
        files = 'abcdefgh'
        c1 = files.index(uci[0])
        r1 = 8 - int(uci[1])
        c2 = files.index(uci[2])
        r2 = 8 - int(uci[3])
        return (r1, c1), (r2, c2)
        
    start, end = uci_to_coords(ai_move_uci)
    success, msg = game.make_move(start, end)
    
    # Auto-promote
    if len(ai_move_uci) == 5:
        game.promote_pawn("Queen") # Simplified default
        
    session['pending_ai_move'] = None # Clear
    session['chess_game'] = game
    
    return jsonify({
        "status": "success", 
        "move": ai_move_uci,
        "fen": game.board.fen()
    })

@app.route('/api/undo_move', methods=['POST'])
def undo_move():
    """Reverts the last move."""
    game = session.get('chess_game')
    if game:
        # Assuming ChessGame has undo logic. From previous files, I recall distinct state methods.
        # Streamlit app used `game.revert_to_pre_move_state()` but that was for specific flow.
        # python-chess board.pop() works if history kept.
        # Let's try basic pop if available, or just reload game.
        try:
            game.board.pop() # Undo last move
            game.move_history.pop()
            game.turn = 'white' if game.turn == 'black' else 'black' # Toggle back
            session['chess_game'] = game
            return jsonify({"status": "success", "fen": game.board.fen()})
        except:
            return jsonify({"status": "error", "message": "Cannot undo"}), 400
    return jsonify({"status": "error"}), 404

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
        
    # Get all valid moves for the piece using existing logic
    # The existing get_valid_moves usually returns raw moves, but doesn't check for checkmate/checks on self
    # We need to filter by game.move_puts_king_in_check like the streamlit app did
    
    raw_moves = piece.get_valid_moves(game.board, game)
    legal_moves = []
    
    for move in raw_moves:
        if not game.move_puts_king_in_check((r, c), move):
            legal_moves.append(move)
            
    return jsonify({
        "status": "success",
        "moves": legal_moves # Returns list of [row, col]
    })

@app.route('/api/promote', methods=['POST'])
def promote_pawn():
    """Handles pawn promotion choice."""
    game = session.get('chess_game')
    if not game:
        return jsonify({"status": "error", "message": "No active game"}), 404
        
    data = request.json
    piece_choice = data.get('promotion') # e.g., 'Queen', 'Rook', etc.
    
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)

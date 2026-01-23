import os
import secrets
import json
from flask import Flask, render_template, request, jsonify, session
from flask_session import Session
from dotenv import load_dotenv

# Import Project Logic
from chess_logic import ChessGame

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
    print("WARNING: GOOGLE_API_KEY not found in environment variables.")

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
        
    data = request.json
    start_pos = data.get('start') # Expected format: [row, col]
    end_pos = data.get('end')     # Expected format: [row, col]
    
    if not start_pos or not end_pos:
        return jsonify({"status": "error", "message": "Invalid coordinates"}), 400
        
    # Convert list to tuple
    start_tuple = tuple(start_pos)
    end_tuple = tuple(end_pos)
    
    # Store pre-move state for coach (TODO)
    
    # Attempt move
    success, message = game.make_move(start_tuple, end_tuple)
    
    if success:
        # Save state back to session (important for filesystem sessions sometimes)
        session['chess_game'] = game
        return jsonify({
            "status": "success",
            "message": message,
            "game_over": game.game_over
        })
        return jsonify({
            "status": "invalid",
            "message": message
        })

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

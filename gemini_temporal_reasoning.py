# gemini_temporal_reasoning.py
# Track B: Temporal Reasoning + Stockfish eval + Gemini next move prediction + reply prediction

import time
import os
import io
import requests
import google.generativeai as genai
from PIL import Image
import chess  # python-chess library

# --- Gemini Setup ---
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

# --- Stockfish API (stockfish.online) ---
STOCKFISH_API = "https://stockfish.online/api/s/v2.php"

def query_stockfish(fen: str) -> dict:
    """
    Query Stockfish.online API with a FEN string.
    Returns eval (centipawns or mate), best move, and ponder (reply).
    """
    params = {"fen": fen, "depth": 15}
    try:
        resp = requests.get(STOCKFISH_API, params=params, timeout=10)
        data = resp.json()
        return {
            "stockfish_eval": data.get("evaluation", "N/A"),
            "stockfish_best_move": data.get("bestmove", "N/A"),
            "stockfish_ponder": data.get("ponder", "N/A")  # Stockfish reply
        }
    except Exception as e:
        return {
            "stockfish_eval": f"error: {e}",
            "stockfish_best_move": "N/A",
            "stockfish_ponder": "N/A"
        }

# --- Gemini Move Analyzer ---
def analyze_move_from_streamlit(file1, file2) -> dict:
    """Compare two chessboard frames uploaded via Streamlit."""
    frame1 = Image.open(io.BytesIO(file1.getbuffer()))
    frame2 = Image.open(io.BytesIO(file2.getbuffer()))

    prompt = (
        "Compare these two chessboard images. "
        "Identify the move in coordinate notation (e.g., e2-e4). "
        "If no move is detected, respond 'no move'."
    )

    start = time.time()
    response = model.generate_content([prompt, frame1, frame2])
    latency = round((time.time() - start) * 1000, 2)

    return {"move": response.text.strip(), "latency_ms": latency}

# --- Gemini Next Move Predictor ---
def predict_next_move_with_gemini(file_last) -> str:
    """Ask Gemini to predict the next most likely move from the final board frame."""
    frame = Image.open(io.BytesIO(file_last.getbuffer()))
    prompt = (
        "Look at this chessboard position. "
        "Predict the next most likely move in coordinate notation only (e.g., e7-e5). "
        "Do not explain, just give the move."
        "Do not add letters in front of the coordinate noation (e.g., Nb1-c3)."
    )
    response = model.generate_content([prompt, frame])
    return response.text.strip()

# --- Utility: Convert moves to FEN ---
def moves_to_fen(moves: list, start_fen: str = chess.STARTING_FEN) -> str:
    """Apply a sequence of moves to starting FEN."""
    board = chess.Board(start_fen)
    for move in moves:
        try:
            uci = move.lower().replace("to", "").replace("-", "").replace(" ", "")
            if len(uci) == 4:
                board.push_uci(uci)
            else:
                board.push_san(move)
        except Exception as e:
            print(f"Skipping invalid move {move}: {e}")
            continue
    return board.fen()

# --- Full Evaluation Pipeline ---
def evaluate_sequence(uploaded_files: list, ground_truth_moves: list) -> dict:
    """Run Gemini detection, evaluate accuracy, query Stockfish, and predict next move + reply."""
    detected_moves, latencies = [], []

    # Step 1: Gemini move detection
    for i in range(len(uploaded_files) - 1):
        result = analyze_move_from_streamlit(uploaded_files[i], uploaded_files[i+1])
        detected_moves.append(result["move"])
        latencies.append(result["latency_ms"])

    # Step 2: Accuracy metrics
    correct = 0
    for g, d in zip(ground_truth_moves, detected_moves):
        g_norm = g.lower().replace("-", "").replace(" ", "").replace("to", "")
        d_norm = d.lower().replace("-", "").replace(" ", "").replace("to", "")
        if g_norm == d_norm:
            correct += 1

    seq_accuracy = round((correct / len(ground_truth_moves)) * 100, 2) if ground_truth_moves else 0.0
    mae = abs(len(detected_moves) - len(ground_truth_moves))
    avg_latency = round(sum(latencies) / len(latencies), 2) if latencies else 0.0

    # Step 3: Convert moves to FEN
    final_fen = moves_to_fen(detected_moves)

    # Step 4: Stockfish eval of current position
    sf_final = query_stockfish(final_fen)

    # Step 5: Gemini predicts the next move
    gemini_best = predict_next_move_with_gemini(uploaded_files[-1])

    # Step 6: Apply Gemini’s move, then Stockfish evaluates that new position
    gemini_fen = moves_to_fen(detected_moves + [gemini_best])
    sf_after_gemini = query_stockfish(gemini_fen)

    return {
        "predicted_moves": detected_moves,
        "ground_truth": ground_truth_moves,
        "sequence_accuracy": seq_accuracy,
        "event_mae": mae,
        "avg_latency_ms": avg_latency,
        "final_fen": final_fen,
        "stockfish_eval": sf_final["stockfish_eval"],
        "stockfish_best_move": sf_final["stockfish_best_move"],
        "gemini_best_move": gemini_best,
        "gemini_eval": sf_after_gemini["stockfish_eval"],
        "stockfish_reply_to_gemini": sf_after_gemini["stockfish_best_move"]
    }

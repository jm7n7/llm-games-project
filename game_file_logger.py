# file: game_file_logger.py
import os
import csv
import re
import time
import requests
import re
from typing import Optional
import chess

STOCKFISH_API_URL = "https://stockfish.online/api/s/v2.php"
CSV_PATH = "game_metrics_extended.csv"



def _clean_move_notation(move: str) -> str:
    """Remove chess piece icons and normalize move notation."""
    if not move:
        return move
    # Remove unicode chess symbols
    move = re.sub(r"[♙♘♗♖♕♔♟♞♝♜♛♚]", "", move)
    # Remove captures text
    move = re.sub(r"\(.*?\)", "", move)
    # Normalize spacing and hyphens
    move = move.replace("-", "").replace("–", "").replace(" ", "").replace("to", "").strip().lower()
    cleaned = move
    return cleaned



def query_stockfish_eval(fen: str, depth: int = 12) -> dict:
    """Query Stockfish.online API for evaluation + best move."""
    try:
        r = requests.get(STOCKFISH_API_URL, params={"fen": fen, "depth": depth}, timeout=10)
        if r.status_code == 200 and r.text.strip().startswith("{"):
            data = r.json()
            return {
                "stockfish_eval": data.get("evaluation"),
                "bestmove": data.get("bestmove", "").replace("bestmove ", "").split()[0],
                "continuation": data.get("continuation"),
            }
    except Exception as e:
        print(f"[WARN] Stockfish eval failed: {e}")
    return {"stockfish_eval": None, "bestmove": None, "continuation": None}


def log_move(
    game_id: str,
    move_number: int,
    color: str,
    move: str,
    fen: str,
    stockfish_eval: Optional[float] = None,
    stockfish_best: Optional[str] = None,
    gemini_pred: Optional[str] = None,
    gemini_eval: Optional[float] = None,
    stockfish_reply: Optional[str] = None,
    latency: Optional[float] = None,
):
    """
    Append one move’s data (Gemini + Stockfish + FEN) into extended CSV log.
    """

    file_exists = os.path.isfile(CSV_PATH)

    with open(CSV_PATH, mode="a", newline="") as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow([
                "game_id","move_number","color","move","fen",
                "stockfish_eval","stockfish_best_move",
                "gemini_predicted_move","gemini_eval","stockfish_reply",
                "latency_seconds","timestamp"
            ])

        writer.writerow([
            game_id, move_number, color, move, fen,
            stockfish_eval, stockfish_best,
            gemini_pred, gemini_eval, stockfish_reply,
            latency, time.strftime("%Y-%m-%d %H:%M:%S")
        ])

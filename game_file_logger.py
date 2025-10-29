# file: game_file_logger.py
import os
import csv
import time
import requests
import re
from typing import Optional, Any

STOCKFISH_API_URL = "https://stockfish.online/api/s/v2.php"

def _clean_move_notation(move_str: str, color: str) -> str:
    """
    Convert annotated move like '♗ c1-h6 (captures ♝)' into UCI form 'c1h6'.
    Handles captures, castling, and promotions.
    Always returns 4–5 chars for Stockfish compatibility.
    """
    if not move_str:
        return move_str

    # --- Handle castling ---
    if "O-O-O" in move_str or "0-0-0" in move_str:
        return "e1c1" if color.lower() == "white" else "e8c8"
    if "O-O" in move_str or "0-0" in move_str:
        return "e1g1" if color.lower() == "white" else "e8g8"

    # --- Handle promotions ---
    promo_match = re.search(r"([a-h][1-8])[- ]?([a-h][1-8])=([QRNBqrbn])", move_str)
    if promo_match:
        from_sq, to_sq, promo = promo_match.groups()
        return f"{from_sq}{to_sq}{promo.lower()}"

    # --- Normal moves (remove icons + captures) ---
    cleaned = re.sub(r"[♙♘♗♖♕♔♟♞♝♜♛♚]", "", move_str)  # remove piece icons
    cleaned = re.sub(r"\(.*?\)", "", cleaned)            # remove "(captures …)"
    cleaned = cleaned.replace("-", "").replace("–", "").strip()

    tokens = cleaned.split()
    if len(tokens) >= 2:
        candidate = tokens[0] + tokens[1]
    else:
        candidate = cleaned

    # --- Final guard: must be 4–5 chars ---
    candidate = candidate.strip().lower()
    if len(candidate) in (4, 5):
        return candidate

    print(f"[WARN] Could not clean move properly: {move_str} → {candidate}")
    return candidate[:5]  # fallback


def log_move_data(
    game_id: str,
    move_number: int,
    color: str,
    move: str,
    fen: str,
    latency: Optional[float] = None,
    stockfish_eval: Optional[float] = None,
    bestmove: Optional[str] = None,
    continuation: Optional[str] = None,
):
    """Appends a single move’s data to the CSV log. No LLM metrics."""
    csv_path = "game_metrics.csv"
    file_exists = os.path.isfile(csv_path)

    # --- Clean move notation ---
    clean_move = _clean_move_notation(move, color)

    # --- If Stockfish eval not provided, fetch it now ---
    if stockfish_eval is None and fen:
        try:
            r = requests.get(STOCKFISH_API_URL, params={"fen": fen, "depth": 10}, timeout=10)
            if r.status_code == 200 and r.text.strip().startswith("{"):
                data = r.json()
                stockfish_eval = data.get("evaluation")
                bestmove = data.get("bestmove", "").replace("bestmove ", "").split()[0]
                continuation = data.get("continuation")
        except Exception as e:
            print(f"[WARN] Stockfish eval failed: {e}")

    # Compute absolute eval
    abs_eval = abs(stockfish_eval) if stockfish_eval is not None else None

    # --- Append to CSV ---
    with open(csv_path, mode="a", newline="") as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow([
                "game_id","move_number","color","move","fen",
                "stockfish_eval","absolute_eval","bestmove","continuation",
                "latency_seconds","timestamp"
            ])

        writer.writerow([
            game_id, move_number, color, clean_move, fen,
            stockfish_eval, abs_eval, bestmove, continuation,
            latency, time.strftime("%Y-%m-%d %H:%M:%S")
        ])

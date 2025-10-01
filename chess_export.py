#--- imports----------
import streamlit as st

# chess_export.py
import chess
import chess.pgn
import pandas as pd
import io
import os

# === Naming Rules Function ===
def piece_name(piece, square):
    """Return the correct name of a piece based on your rules."""
    file = chess.square_file(square)
    file_letter = chr(file + ord("a"))

    if piece.piece_type == chess.PAWN:
        return f"{file_letter}_pawn"
    elif piece.piece_type == chess.ROOK:
        return "Q_rook" if file_letter == "a" else "K_rook"
    elif piece.piece_type == chess.KNIGHT:
        return "Q_knight" if file_letter == "b" else "K_knight"
    elif piece.piece_type == chess.BISHOP:
        return "Q_bishop" if file_letter == "c" else "K_bishop"
    elif piece.piece_type == chess.QUEEN:
        return "Queen"
    elif piece.piece_type == chess.KING:
        return "King"
    return "Unknown"

# === PGN → CSV Conversion ===
def convert_pgn_to_csv(pgn_data, csv_path, start_game):
    """Convert PGN string to structured CSV rows and append to dataset."""
    games_data = []
    game_number = start_game

    # Treat PGN string like a file
    pgn_io = io.StringIO(pgn_data)

    while True:
        game = chess.pgn.read_game(pgn_io)
        if game is None:
            break

        board = game.board()
        game_id = f"chs-850-{str(game_number).zfill(4)}"
        turn = 1

        for move in game.mainline_moves():
            color = "white" if board.turn == chess.WHITE else "black"
            piece = board.piece_at(move.from_square)
            piece_moved = piece_name(piece, move.from_square)

            start_square = chess.square_name(move.from_square)
            end_square = chess.square_name(move.to_square)

            capture = int(board.is_capture(move))
            captured_piece = ""
            if capture:
                captured_piece_obj = board.piece_at(move.to_square)
                if captured_piece_obj:
                    captured_piece = piece_name(captured_piece_obj, move.to_square)

            board.push(move)
            check = int(board.is_check())
            checkmate = int(board.is_checkmate())

            games_data.append({
                "game_id": game_id,
                "turn": turn,
                "color": color,
                "piece_moved": piece_moved,
                "start_square": start_square,
                "end_square": end_square,
                "capture": capture,
                "captured_piece": captured_piece,
                "check": check,
                "checkmate": checkmate
            })

            turn += 1

        game_number += 1

    df = pd.DataFrame(games_data)

    # Append instead of overwrite
    if os.path.exists(csv_path):
        df.to_csv(csv_path, mode="a", index=False, header=False)
    else:
        df.to_csv(csv_path, index=False)

    print(f"Appended game(s) to {csv_path}")

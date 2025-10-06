import streamlit as st
import numpy as np
import random
import string

def play_letter_tile_game():
    """
    Sets up and runs the Letter-Tile-Game (Scrabble-like) UI and logic.
    """
    st.header("Letter-Tile-Game (Scrabble)")

    # --- GAME CONSTANTS AND SETUP ---
    BOARD_SIZE = 15
    TILE_SCORES = {"A": 1, "B": 3, "C": 3, "D": 2, "E": 1, "F": 4, "G": 2, "H": 4, "I": 1, "J": 8, "K": 5, "L": 1, "M": 3, "N": 1, "O": 1, "P": 3, "Q": 10, "R": 1, "S": 1, "T": 1, "U": 1, "V": 4, "W": 4, "X": 8, "Y": 4, "Z": 10}
    TILE_DISTRIBUTION = "A"*9 + "B"*2 + "C"*2 + "D"*4 + "E"*12 + "F"*2 + "G"*3 + "H"*2 + "I"*9 + "J"*1 + "K"*1 + "L"*4 + "M"*2 + "N"*6 + "O"*8 + "P"*2 + "Q"*1 + "R"*6 + "S"*4 + "T"*6 + "U"*4 + "V"*2 + "W"*2 + "X"*1 + "Y"*2 + "Z"*1
    VALID_WORDS = { "streamlit", "python", "code", "game", "play", "word", "tile", "board", "score", "win", "fun", "hello" } # A small dictionary for demo

    PREMIUM_SQUARES = {
        (0,0): "TW", (0,7): "TW", (0,14): "TW", (7,0): "TW", (7,14): "TW", (14,0): "TW", (14,7): "TW", (14,14): "TW",
        (1,1): "DW", (2,2): "DW", (3,3): "DW", (4,4): "DW", (1,13): "DW", (2,12): "DW", (3,11): "DW", (4,10): "DW",
        (10,4): "DW", (11,3): "DW", (12,2): "DW", (13,1): "DW", (10,10): "DW", (11,11): "DW", (12,12): "DW", (13,13): "DW", (7,7): "DW",
        (0,3): "DL", (0,11): "DL", (2,6): "DL", (2,8): "DL", (3,0): "DL", (3,7): "DL", (3,14): "DL", (6,2): "DL", (6,6): "DL", (6,8): "DL", (6,12): "DL",
        (7,3): "DL", (7,11): "DL", (8,2): "DL", (8,6): "DL", (8,8): "DL", (8,12): "DL", (11,0): "DL", (11,7): "DL", (11,14): "DL", (12,6): "DL", (12,8): "DL", (14,3): "DL", (14,11): "DL",
        (1,5): "TL", (1,9): "TL", (5,1): "TL", (5,5): "TL", (5,9): "TL", (5,13): "TL",
        (9,1): "TL", (9,5): "TL", (9,9): "TL", (9,13): "TL", (13,5): "TL", (13,9): "TL"
    }

    def initialize_game():
        st.session_state.scrabble_board = np.full((BOARD_SIZE, BOARD_SIZE), " ", dtype=str)
        st.session_state.tile_bag = list(TILE_DISTRIBUTION)
        random.shuffle(st.session_state.tile_bag)
        st.session_state.player_tiles = [st.session_state.tile_bag.pop() for _ in range(7)]
        st.session_state.player_score = 0
        st.session_state.scrabble_message = "First word must cover the center square (H8)."
        st.session_state.is_first_move = True

    if 'scrabble_board' not in st.session_state:
        initialize_game()

    def play_word(word, row, col, direction):
        word = word.upper()
        if word.lower() not in VALID_WORDS:
            st.session_state.scrabble_message = f"'{word}' is not a valid word."
            return

        temp_tiles = st.session_state.player_tiles.copy()
        word_score = 0
        word_multiplier = 1
        
        for i, letter in enumerate(word):
            r, c = (row, col + i) if direction == "Across" else (row + i, col)
            if not (0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE):
                st.session_state.scrabble_message = "Word goes off the board."
                return
            
            if st.session_state.scrabble_board[r,c] == " ":
                if letter not in temp_tiles:
                    st.session_state.scrabble_message = f"You don't have the tile: {letter}"
                    return
                temp_tiles.remove(letter)
                letter_score = TILE_SCORES[letter]
                square = PREMIUM_SQUARES.get((r,c))
                if square == "DL": letter_score *= 2
                if square == "TL": letter_score *= 3
                if square == "DW": word_multiplier *= 2
                if square == "TW": word_multiplier *= 3
                word_score += letter_score
            else:
                if st.session_state.scrabble_board[r,c] != letter:
                    st.session_state.scrabble_message = "Word conflicts with existing tiles."
                    return
                word_score += TILE_SCORES[letter]

        if st.session_state.is_first_move:
            center_covered = any((row, col + i) == (7, 7) if direction == "Across" else (row + i, col) == (7, 7) for i in range(len(word)))
            if not center_covered:
                st.session_state.scrabble_message = "First word must cover the center square (H8)."
                return
            st.session_state.is_first_move = False

        word_score *= word_multiplier
        st.session_state.player_score += word_score

        for i, letter in enumerate(word):
            r, c = (row, col + i) if direction == "Across" else (row + i, col)
            st.session_state.scrabble_board[r, c] = letter
        
        st.session_state.player_tiles = temp_tiles
        draw_count = 7 - len(st.session_state.player_tiles)
        for _ in range(draw_count):
            if st.session_state.tile_bag:
                st.session_state.player_tiles.append(st.session_state.tile_bag.pop())

        st.session_state.scrabble_message = f"You played '{word}' for {word_score} points!"

    # --- RENDER GAME UI ---
    st.info(st.session_state.scrabble_message)
    st.subheader(f"Score: {st.session_state.player_score}")

    # Display Board
    board_html = "<table style='border-collapse: collapse;'>"
    for r in range(BOARD_SIZE):
        board_html += "<tr>"
        for c in range(BOARD_SIZE):
            letter = st.session_state.scrabble_board[r, c]
            text = letter if letter != " " else ""
            color = "#F0EAD6"
            premium = PREMIUM_SQUARES.get((r,c))
            if premium == "TW": color = "#FF4B4B"
            elif premium == "DW": color = "#FFDDC1"
            elif premium == "TL": color = "#4B8BFF"
            elif premium == "DL": color = "#A2D2FF"
            if r==7 and c==7 and text=="": text = "★"
            board_html += f"<td style='border: 1px solid #ccc; width: 30px; height: 30px; text-align: center; background-color: {color}; font-weight: bold;'>{text}</td>"
        board_html += "</tr>"
    board_html += "</table>"
    st.markdown(board_html, unsafe_allow_html=True)

    # Player Hand
    st.subheader("Your Tiles:")
    tile_cols = st.columns(7)
    for i, tile in enumerate(st.session_state.player_tiles):
        tile_cols[i].markdown(f"<div style='border: 2px solid #555; padding: 10px; border-radius: 5px; text-align: center; font-size: 1.5em; background-color: #F0EAD6;'>{tile}</div>", unsafe_allow_html=True)

    with st.form("scrabble_move_form", clear_on_submit=True):
        word = st.text_input("Word:")
        row = st.selectbox("Row:", options=list(string.ascii_uppercase[:BOARD_SIZE]), format_func=lambda x: f"Row {x}")
        col = st.number_input("Column:", min_value=1, max_value=BOARD_SIZE, step=1)
        direction = st.radio("Direction:", ("Across", "Down"), horizontal=True)
        play_button = st.form_submit_button("Play Word")

    if play_button and word:
        row_idx = string.ascii_uppercase.index(row)
        col_idx = col - 1
        play_word(word, row_idx, col_idx, direction)
        st.rerun()

    if st.button("New Game"):
        initialize_game()
        st.rerun()

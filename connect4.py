import streamlit as st
import numpy as np

def play_four_in_a_row():
    """
    Sets up and runs the Four-in-a-row (Connect-4) game UI and logic.
    """
    st.header("Four-in-a-row (Connect-4)")

    # --- GAME LOGIC ---
    ROWS, COLS = 6, 7
    PLAYER_1, PLAYER_2 = 1, 2

    # Initialize game state
    if 'c4_board' not in st.session_state:
        st.session_state.c4_board = np.zeros((ROWS, COLS), dtype=int)
        st.session_state.c4_turn = PLAYER_1
        st.session_state.c4_winner = None

    def check_winner(board):
        # Check horizontal
        for r in range(ROWS):
            for c in range(COLS - 3):
                if board[r, c] == board[r, c+1] == board[r, c+2] == board[r, c+3] != 0:
                    return board[r, c]
        # Check vertical
        for c in range(COLS):
            for r in range(ROWS - 3):
                if board[r, c] == board[r+1, c] == board[r+2, c] == board[r+3, c] != 0:
                    return board[r, c]
        # Check diagonal (down-right)
        for r in range(ROWS - 3):
            for c in range(COLS - 3):
                if board[r, c] == board[r+1, c+1] == board[r+2, c+2] == board[r+3, c+3] != 0:
                    return board[r, c]
        # Check diagonal (up-right)
        for r in range(3, ROWS):
            for c in range(COLS - 3):
                if board[r, c] == board[r-1, c+1] == board[r-2, c+2] == board[r-3, c+3] != 0:
                    return board[r, c]
        # Check for draw
        if np.all(board != 0):
            return "Draw"
        return None

    def make_move(col):
        for r in range(ROWS - 1, -1, -1):
            if st.session_state.c4_board[r, col] == 0:
                st.session_state.c4_board[r, col] = st.session_state.c4_turn
                break
        winner = check_winner(st.session_state.c4_board)
        if winner:
            st.session_state.c4_winner = winner
        else:
            st.session_state.c4_turn = PLAYER_2 if st.session_state.c4_turn == PLAYER_1 else PLAYER_1

    # --- RENDER GAME BOARD ---
    if st.session_state.c4_winner:
        if st.session_state.c4_winner == "Draw":
            st.warning("It's a Draw!")
        else:
            st.success(f"Player {st.session_state.c4_winner} wins!")
    else:
        st.info(f"Player {st.session_state.c4_turn}'s turn")

    # Column buttons for making a move
    cols = st.columns(COLS)
    for i, col in enumerate(cols):
        with col:
            is_disabled = st.session_state.c4_board[0, i] != 0 or st.session_state.c4_winner is not None
            if st.button("↓", key=f"c4_col_{i}", use_container_width=True, disabled=is_disabled):
                make_move(i)
                st.rerun()

    # Visual representation of the board
    st.markdown("""<style>.c4-board { background-color: #007bff; border-radius: 10px; padding: 10px; display: grid; grid-template-columns: repeat(7, 1fr); grid-gap: 5px; } .c4-cell { width: 50px; height: 50px; border-radius: 50%; display: flex; justify-content: center; align-items: center; } </style>""", unsafe_allow_html=True)
    board_html = "<div class='c4-board'>"
    for r in range(ROWS):
        for c in range(COLS):
            player = st.session_state.c4_board[r, c]
            if player == PLAYER_1: color = "#ff4b4b"
            elif player == PLAYER_2: color = "#ffff00"
            else: color = "#ffffff"
            board_html += f"<div class='c4-cell' style='background-color: {color};'></div>"
    board_html += "</div>"
    st.markdown(board_html, unsafe_allow_html=True)

    if st.button("New Game"):
        st.session_state.c4_board = np.zeros((ROWS, COLS), dtype=int)
        st.session_state.c4_turn = PLAYER_1
        st.session_state.c4_winner = None
        st.rerun()

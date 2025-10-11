import streamlit as st

def play_mancala():
    """
    Sets up and runs the Mancala game UI and logic.
    """
    st.header("Mancala")

    # --- GAME LOGIC ---
    PLAYER_1, PLAYER_2 = "Player 1", "Player 2"
    P1_MANCALA, P2_MANCALA = 6, 13

    # Initialize game state
    if 'mancala_board' not in st.session_state:
        st.session_state.mancala_board = [4, 4, 4, 4, 4, 4, 0, 4, 4, 4, 4, 4, 4, 0]
        st.session_state.mancala_turn = PLAYER_1
        st.session_state.mancala_winner = None
        st.session_state.mancala_message = ""

    def make_move(pit_index):
        stones = st.session_state.mancala_board[pit_index]
        if stones == 0:
            st.session_state.mancala_message = "Cannot move from an empty pit."
            return

        st.session_state.mancala_board[pit_index] = 0
        current_pit = pit_index
        while stones > 0:
            current_pit = (current_pit + 1) % 14
            if (st.session_state.mancala_turn == PLAYER_1 and current_pit == P2_MANCALA) or \
               (st.session_state.mancala_turn == PLAYER_2 and current_pit == P1_MANCALA):
                continue
            st.session_state.mancala_board[current_pit] += 1
            stones -= 1

        # Capture rule
        is_p1_turn = st.session_state.mancala_turn == PLAYER_1
        is_p1_side = 0 <= current_pit <= 5
        is_p2_turn = st.session_state.mancala_turn == PLAYER_2
        is_p2_side = 7 <= current_pit <= 12
        
        if (is_p1_turn and is_p1_side) or (is_p2_turn and is_p2_side):
            if st.session_state.mancala_board[current_pit] == 1:
                opposite_pit = 12 - current_pit
                if st.session_state.mancala_board[opposite_pit] > 0:
                    captured_stones = st.session_state.mancala_board[opposite_pit] + 1
                    st.session_state.mancala_board[opposite_pit] = 0
                    st.session_state.mancala_board[current_pit] = 0
                    mancala_pit = P1_MANCALA if is_p1_turn else P2_MANCALA
                    st.session_state.mancala_board[mancala_pit] += captured_stones
                    st.session_state.mancala_message = f"{st.session_state.mancala_turn} captured {captured_stones} stones!"

        # Check for game end
        p1_pits_empty = all(s == 0 for s in st.session_state.mancala_board[0:6])
        p2_pits_empty = all(s == 0 for s in st.session_state.mancala_board[7:13])

        if p1_pits_empty or p2_pits_empty:
            st.session_state.mancala_board[P1_MANCALA] += sum(st.session_state.mancala_board[0:6])
            st.session_state.mancala_board[P2_MANCALA] += sum(st.session_state.mancala_board[7:13])
            for i in list(range(6)) + list(range(7, 13)): st.session_state.mancala_board[i] = 0
            
            p1_score = st.session_state.mancala_board[P1_MANCALA]
            p2_score = st.session_state.mancala_board[P2_MANCALA]
            if p1_score > p2_score: st.session_state.mancala_winner = PLAYER_1
            elif p2_score > p1_score: st.session_state.mancala_winner = PLAYER_2
            else: st.session_state.mancala_winner = "Draw"
            return

        # Switch turns unless last stone landed in own mancala
        if not ((is_p1_turn and current_pit == P1_MANCALA) or (is_p2_turn and current_pit == P2_MANCALA)):
            st.session_state.mancala_turn = PLAYER_2 if is_p1_turn else PLAYER_1
        else:
            st.session_state.mancala_message = f"{st.session_state.mancala_turn} gets another turn!"

    # --- RENDER GAME UI ---
    if st.session_state.mancala_winner:
        st.success(f"Game Over! The winner is {st.session_state.mancala_winner}!")
        st.write(f"Final Score: Player 1 ({st.session_state.mancala_board[P1_MANCALA]}) - Player 2 ({st.session_state.mancala_board[P2_MANCALA]})")
    else:
        st.info(f"It's **{st.session_state.mancala_turn}'s** turn.")
        if st.session_state.mancala_message:
            st.write(st.session_state.mancala_message)
            st.session_state.mancala_message = ""

    mancala_col, board_cols, mancala_col_2 = st.columns([2, 6, 2])

    with mancala_col:
        st.header("P2")
        st.markdown(f"<div style='border: 2px solid #444; padding: 10px; border-radius: 10px; text-align: center; height: 300px; display: flex; justify-content: center; align-items: center; font-size: 2em;'>{st.session_state.mancala_board[P2_MANCALA]}</div>", unsafe_allow_html=True)

    with board_cols:
        p2_cols = st.columns(6)
        for i, col in enumerate(p2_cols):
            with col:
                pit_index = 12 - i
                disabled = st.session_state.mancala_turn != PLAYER_2 or st.session_state.mancala_winner is not None
                if st.button(f"{st.session_state.mancala_board[pit_index]}", key=f"pit_{pit_index}", use_container_width=True, disabled=disabled):
                    make_move(pit_index)
                    st.rerun()

        st.markdown("<hr>", unsafe_allow_html=True)

        p1_cols = st.columns(6)
        for i, col in enumerate(p1_cols):
            with col:
                pit_index = i
                disabled = st.session_state.mancala_turn != PLAYER_1 or st.session_state.mancala_winner is not None
                if st.button(f"{st.session_state.mancala_board[pit_index]}", key=f"pit_{pit_index}", use_container_width=True, disabled=disabled):
                    make_move(pit_index)
                    st.rerun()

    with mancala_col_2:
        st.header("P1")
        st.markdown(f"<div style='border: 2px solid #444; padding: 10px; border-radius: 10px; text-align: center; height: 300px; display: flex; justify-content: center; align-items: center; font-size: 2em;'>{st.session_state.mancala_board[P1_MANCALA]}</div>", unsafe_allow_html=True)

    if st.button("New Game"):
        st.session_state.mancala_board = [4, 4, 4, 4, 4, 4, 0, 4, 4, 4, 4, 4, 4, 0]
        st.session_state.mancala_turn = PLAYER_1
        st.session_state.mancala_winner = None
        st.session_state.mancala_message = ""
        st.rerun()

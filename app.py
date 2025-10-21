#--- imports----------
import streamlit as st
import pandas as pd
from chess_logic import ChessGame 
import chess_llm_functions as ll_api
import json
from PIL import Image
from streamlit_image_coordinates import streamlit_image_coordinates
from chess_app_functions import *
import os
import time

#--- PAGE CONFIG --
st.set_page_config(
    page_title="Chess Coach",
    layout="wide"
)

#--- APP TITLE AND HEADER------
st.title("LLM Chess Coach")

#--- SIDEBAR (simplified) -------------
st.sidebar.header("About")
st.sidebar.info("This chess app uses three distinct LLMs to create a dynamic coaching experience. An Opponent LLM plays against you, while a Coach LLM analyzes your moves for key learning moments.")


#--- MAIN CONTENT AREA -----------------------------------------------
st.header("Chess")

# --- API KEY CHECK ---
if 'GOOGLE_API_KEY' not in os.environ:
    st.error("Your Google AI API key is not configured. Please set the GOOGLE_API_KEY environment variable to play.")
    st.stop()

# --- INITIALIZATION ---
if 'chess_game' not in st.session_state:
    st.session_state.chess_game = ChessGame()
    st.session_state.selected_square = None
    st.session_state.last_click = None
    st.session_state.chess_game_phase = 'color_selection'
    st.session_state.player_color = 'white'
    st.session_state.ai_color = 'black'
    st.session_state.coach_session = ll_api.initialize_coach_chat()
    st.session_state.opponent_session = ll_api.initialize_opponent_chat()
    st.session_state.chat_history = [{"role": "coach", "text": "Hi! I'm Coach Gemini. I'll be watching your game and offering feedback."}]
    st.session_state.pending_ai_move = None
    st.session_state.coach_stream_data = None

game = st.session_state.chess_game

# --- UI DRAWING FUNCTIONS ---
def render_chat():
    for msg in st.session_state.chat_history:
        with st.chat_message(name="coach", avatar="🤖"):
            st.write(msg['text'])

def draw_main_ui(is_board_disabled=False, chat_spinner=False):
    """Draws the main game UI, abstracting the layout."""
    col1, col2 = st.columns([2, 1])
    
    click_value = None
    with col1:
        board_image = draw_chess_board_pil(load_piece_images())
        click_value = streamlit_image_coordinates(board_image, key="chess_board")

    with col2:
        st.subheader("Game Info")
        status_container = st.container(border=True, height=150)
        
        with status_container:
            phase = st.session_state.chess_game_phase
            if phase == 'color_selection':
                st.write("Choose your color to begin.")
                if st.button("Play as White", use_container_width=True):
                    st.session_state.player_color = 'white'
                    st.session_state.ai_color = 'black'
                    st.session_state.chess_game_phase = 'playing'
                    st.rerun()
                if st.button("Play as Black", use_container_width=True):
                    st.session_state.player_color = 'black'
                    st.session_state.ai_color = 'white'
                    st.session_state.chess_game_phase = 'processing_ai_move'
                    st.rerun()
            elif phase == 'awaiting_user_decision':
                st.warning("Coach has a suggestion. What would you like to do?")
                btn_cols = st.columns(2)
                if btn_cols[0].button("Proceed Anyway", use_container_width=True):
                    game.clear_pre_move_state() # Finalize the move
                    st.session_state.chess_game_phase = 'processing_ai_move'
                    st.rerun()
                if btn_cols[1].button("Take Back Move", use_container_width=True):
                    game.revert_to_pre_move_state()
                    st.session_state.chat_history.append({"role": "coach", "text": "Okay, take another look. What's a better move?"})
                    st.session_state.pending_ai_move = None
                    st.session_state.last_click = None
                    st.session_state.chess_game_phase = 'playing'
                    st.rerun()
            elif game.promotion_pending:
                st.warning("Pawn Promotion!")
                st.write("Choose a piece:")
                promo_cols = st.columns(4)
                choices = ["Queen", "Rook", "Bishop", "Knight"]
                for i, choice in enumerate(choices):
                    if promo_cols[i].button(choice, key=f"promo_{choice}", use_container_width=True):
                        game.promote_pawn(choice)
                        st.session_state.chess_game_phase = 'processing_llms'
                        st.session_state.last_click = None
                        st.rerun()
            else:
                if game.game_over:
                     st.success(game.status_message)
                else:
                     st.info(game.status_message)

        if st.button("New Game", use_container_width=True, disabled=(phase != 'playing' and phase != 'awaiting_user_decision' and not game.game_over)):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

        st.subheader("Coach Gemini")
        chat_container = st.container(height=300, border=True)
        with chat_container:
            if chat_spinner:
                with st.spinner("Coach is thinking..."):
                    render_chat()
            else:
                render_chat()
        
        st.subheader("Move History")
        st.text_area("Moves", "\n".join(f"{i+1}. {move}" for i, move in enumerate(game.move_history)), height=150)
    
    return click_value if not is_board_disabled else None


# --- GAME PHASE ROUTER ---
phase = st.session_state.get('chess_game_phase')

if phase == 'color_selection':
    draw_main_ui(is_board_disabled=True)

elif phase in ['playing', 'awaiting_user_decision']:
    is_disabled = (game.turn != st.session_state.player_color or phase == 'awaiting_user_decision')
    value = draw_main_ui(is_board_disabled=is_disabled)
    
    if not is_disabled and value and value != st.session_state.get('last_click'):
        st.session_state.last_click = value
        pos = get_click_board_coords(value)
        if pos and (0 <= pos[0] < 8 and 0 <= pos[1] < 8):
            selected_piece = game.board.get_piece(st.session_state.selected_square) if st.session_state.selected_square else None
            clicked_piece = game.board.get_piece(pos)
            if selected_piece:
                game.store_pre_move_state()
                success, message = game.make_move(st.session_state.selected_square, pos)
                st.session_state.selected_square = None
                if success and message != "Promotion":
                    st.session_state.chess_game_phase = 'processing_llms'
                    st.rerun()
                elif not success:
                    game.revert_to_pre_move_state()
                    if clicked_piece and clicked_piece.color == game.turn:
                        st.session_state.selected_square = pos
                    st.rerun()
            elif clicked_piece and clicked_piece.color == game.turn:
                st.session_state.selected_square = pos
                st.rerun()

elif phase == 'processing_llms':
    draw_main_ui(is_board_disabled=True, chat_spinner=True)
    
    last_move_data = game.game_data[-1] if game.game_data else {}
    commentary = ll_api.get_move_commentary(last_move_data)
    history_str = json.dumps(game.game_data)
    legal_moves = game._get_all_legal_moves(st.session_state.ai_color)

    if legal_moves:
        ai_response = ll_api.get_ai_opponent_move(st.session_state.opponent_session, history_str, legal_moves)
        st.session_state.pending_ai_move = ai_response['move']
        st.session_state.coach_stream_data = ll_api.get_coach_analysis(st.session_state.coach_session, commentary, history_str)
        st.session_state.chess_game_phase = 'streaming_coach_response'
        st.rerun()
    else: 
        game.clear_pre_move_state()
        st.session_state.chess_game_phase = 'playing'
        st.rerun()

elif phase == 'streaming_coach_response':
    draw_main_ui(is_board_disabled=True)
    
    raw_text_accumulator = ""
    all_cols = st.columns([2, 1])
    chat_area_on_right = all_cols[1].container()
    with chat_area_on_right:
        st.subheader("Coach Gemini")
        chat_container = st.container(height=300, border=True)
        with chat_container:
            render_chat()
            with st.chat_message(name="coach", avatar="🤖"):
                stream_placeholder = st.empty()
                for chunk in st.session_state.coach_stream_data:
                    raw_text_accumulator += chunk.text
                    stream_placeholder.markdown(raw_text_accumulator + "▌")
                    time.sleep(0.02)
                stream_placeholder.markdown(raw_text_accumulator)

    try:
        parsed_json = json.loads(raw_text_accumulator)
        final_commentary = parsed_json.get('commentary', "Sorry, I lost my train of thought.")
    except json.JSONDecodeError:
        final_commentary = raw_text_accumulator if raw_text_accumulator else "My apologies, I had a connection issue."

    if final_commentary.startswith("[INTERVENTION]"):
        cleaned_commentary = final_commentary.replace("[INTERVENTION]", "").strip()
        st.session_state.chat_history.append({"role": "coach", "text": cleaned_commentary})
        st.session_state.chess_game_phase = 'awaiting_user_decision'
    else:
        game.clear_pre_move_state()
        st.session_state.chat_history.append({"role": "coach", "text": final_commentary})
        st.session_state.chess_game_phase = 'processing_ai_move'
    
    st.session_state.coach_stream_data = None
    st.rerun()

elif phase == 'processing_ai_move':
    with st.spinner("Opponent is moving..."):
        if not st.session_state.pending_ai_move:
             legal_moves = game._get_all_legal_moves(st.session_state.ai_color)
             history_str = json.dumps(game.game_data)
             ai_response = ll_api.get_ai_opponent_move(st.session_state.opponent_session, history_str, legal_moves)
             st.session_state.pending_ai_move = ai_response['move']

    move_str = st.session_state.pending_ai_move
    if move_str:
        start_pos = game._notation_to_pos_tuple(move_str.split('-')[0])
        end_pos = game._notation_to_pos_tuple(move_str.split('-')[1])
        game.make_move(start_pos, end_pos)
        if game.promotion_pending:
            game.promote_pawn("Queen")
        st.session_state.pending_ai_move = None
        st.session_state.last_click = None
        game.clear_pre_move_state()
        
    st.session_state.chess_game_phase = 'playing'
    st.rerun()


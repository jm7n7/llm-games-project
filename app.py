#--- imports----------
import streamlit as st
import pandas as pd
from chess_logic import ChessGame 

from PIL import Image, ImageDraw, ImageFont
from streamlit_image_coordinates import streamlit_image_coordinates
from chess_app_functions import *
import io
import os

#--- PAGE CONFIG --
st.set_page_config(
    page_title="Game Arcade",
    layout="wide"
)

#--- APP TITLE AND HEADER------
st.title("Game Arcade")

#--- SIDEBAR FOR GAME SELECTION-------------
st.sidebar.header("Choose a Game")
game_selection = st.sidebar.radio(
    "Select a game to play:",
    ("Home", "Chess", "Four-in-a-row", "Letter-Tile-Game", "Mancala")
)
#--- MAIN CONTENT AREA ROUTER -----------------------------------------------
if game_selection == "Home":
    st.header("Welcome to the Game Arcade!")
    st.info("Select a game from the sidebar on the left to start playing.")
    st.markdown("This app is a collection of classic board and word games built from scratch. Enjoy your stay!")

elif game_selection == "Chess":
    st.header("Chess")

    # --- API KEY CHECK ---
    if 'GOOGLE_API_KEY' not in os.environ:
        st.error("Your Google AI API key is not configured. Please set the GOOGLE_API_KEY environment variable to play against the AI.")
        st.stop()

    # --- INITIALIZATION ---
    if 'chess_game' not in st.session_state:
        st.session_state.chess_game = ChessGame()
        st.session_state.selected_square = None
        st.session_state.last_click = None
        st.session_state.chess_game_phase = 'color_selection'
        st.session_state.player_color = 'white'
        st.session_state.ai_color = 'black'

    game = st.session_state.chess_game

    # --- GAME PHASES ---
    if st.session_state.get('chess_game_phase') == 'color_selection':
        st.subheader("Choose Your Color")
        st.write("You will play against Coach Gemini.")
        c1, c2, c3 = st.columns([2,1,2])
        with c2:
            if st.button("Play as White", use_container_width=True):
                st.session_state.player_color = 'white'
                st.session_state.ai_color = 'black'
                st.session_state.chess_game_phase = 'playing'
                st.rerun()
            if st.button("Play as Black", use_container_width=True):
                st.session_state.player_color = 'black'
                st.session_state.ai_color = 'white'
                st.session_state.chess_game_phase = 'playing'
                st.rerun()

    elif st.session_state.get('chess_game_phase') == 'playing':
        # AI moves first if it's White
        if game.turn == st.session_state.ai_color and len(game.move_history) == 0:
            with st.spinner("Coach Gemini is thinking..."):
                game.request_ai_move()
            st.rerun()

        # --- Main game layout ---
        piece_images = load_piece_images()
        if piece_images is None or not piece_images:
            st.error("Could not find the `assets` folder or it is empty. Please create it and add the required chess piece images (e.g., 'w_king.png').")
            st.stop()
            
        col1, col2 = st.columns([2, 1])
        
        with col1:
            board_image = draw_chess_board_pil(piece_images)
            value = streamlit_image_coordinates(board_image, key="chess_board")
            
            # --- HUMAN TURN ---
            if value and value != st.session_state.get('last_click'):
                st.session_state.last_click = value
                if not game.promotion_pending and game.turn == st.session_state.player_color:
                    handle_chess_click(value)
                    
                    # --- AI TURN TRIGGER ---
                    if not game.game_over and game.turn == st.session_state.ai_color:
                        with st.spinner("Coach Gemini is thinking..."):
                            game.request_ai_move()
                    st.rerun()

        with col2:
            st.subheader("Game Info")

            if game.promotion_pending:
                st.warning("Pawn Promotion!")
                st.write("Choose a piece to promote your pawn to:")
                promo_cols = st.columns(4)
                choices = ["Queen", "Rook", "Bishop", "Knight"]
                for i, choice in enumerate(choices):
                    with promo_cols[i]:
                        if st.button(choice, key=f"promo_{choice}", use_container_width=True):
                            game.promote_pawn(choice)
                            # --- AI TURN TRIGGER AFTER PROMOTION ---
                            if not game.game_over and game.turn == st.session_state.ai_color:
                                with st.spinner("Coach Gemini is thinking..."):
                                    game.request_ai_move()
                            st.session_state.last_click = None
                            st.rerun()
            else:
                status_container = st.empty()
                if game.game_over:
                     status_container.success(game.status_message)
                else:
                     status_container.info(game.status_message)
            
                if st.button("New Game", use_container_width=True):
                    st.session_state.chess_game.reset_game()
                    st.session_state.selected_square = None
                    st.session_state.last_click = None
                    st.session_state.chess_game_phase = 'color_selection'
                    st.rerun()

            st.subheader("Move History")
            st.text_area(
                "Moves", 
                "\n".join(f"{i+1}. {move}" for i, move in enumerate(game.move_history)), 
                height=300,
                key="move_history"
            )

            if game.game_over and game.game_data:
                st.subheader("Game Data Log")
                df = pd.DataFrame(game.game_data)
                st.dataframe(df)


#--- ABOUT SECTION IN SIDEBAR-------------
st.sidebar.header("About")
st.sidebar.info("This is a collection of simple games built using Streamlit.")


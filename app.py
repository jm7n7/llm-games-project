#--- imports----------
import streamlit as st
import pandas as pd
from chess_logic import ChessGame 

from PIL import Image, ImageDraw, ImageFont
from streamlit_image_coordinates import streamlit_image_coordinates
from chess_app_functions import *
import os
import time
#This should look correct

#--- PAGE CONFIG --
st.set_page_config(
    page_title="Chess Coach",
    layout="wide"
)

#--- APP TITLE AND HEADER------
st.title("LLM Chess Coach")

#--- SIDEBAR FOR GAME SELECTION-------------
st.sidebar.header("Choose a Game")
game_selection = st.sidebar.radio(
    "Select a game to play:",
    ("Home", "Chess")
)
#--- MAIN CONTENT AREA ROUTER -----------------------------------------------
if game_selection == "Home":
    st.header("Welcome to the Game Arcade!")
    st.info("Select a game from the sidebar on the left to start playing.")
    st.markdown("This app is a collection of classic board and word games built from scratch. Enjoy your stay!")


#--- MAIN CONTENT AREA -----------------------------------------------
st.header("Chess")

# --- API KEY CHECK ---
# (Ensures all required API keys are set in the environment)
if 'GOOGLE_API_KEY' not in os.environ:
    st.error("Your Google AI API key is not configured. Please set the GOOGLE_API_KEY environment variable to play.")
    st.stop()
if 'AI_OPPONENT_KEY' not in os.environ:
    st.error("Your Google AI API key is not configured. Please set the AI_OPPONENT_KEY environment variable to play.")
    st.stop()
if 'COACH_KEY' not in os.environ:
    st.error("Your Google AI API key is not configured. Please set the COACH_KEY environment variable to play.")
    st.stop()
if 'COMMENTATOR_KEY' not in os.environ:
    st.error("Your Google AI API key is not configured. Please set the COMMENTATOR_KEY environment variable to play.")
    st.stop()

# --- INITIALIZATION ---
if 'chess_game' not in st.session_state:
    st.session_state.chess_game = ChessGame()
    st.session_state.selected_square = None
    st.session_state.last_click = None
    st.session_state.chess_game_phase = 'color_selection'
    st.session_state.player_color = 'white'
    st.session_state.ai_color = 'black'
    st.session_state.chat_history = [{"role": "coach", "text": "Hi! I'm Coach Gemini. I'll be watching your game and offering feedback."}]
    st.session_state.pending_ai_move = None
    st.session_state.coach_stream_data = None
    st.session_state.coach_chat_session = None # This will be initialized per-call

game = st.session_state.chess_game

# --- UI DRAWING FUNCTIONS (REFACTORED) ---

def render_chat():
    """Renders the chat history."""
    for msg in st.session_state.chat_history:
        with st.chat_message(name=msg["role"], avatar="🤖" if msg["role"] == "coach" else "🧑"):
            st.write(msg['text'])

def draw_board(is_opponent_thinking=False):
    """Draws the left column (board)."""
    # Load piece images (cached by Streamlit)
    piece_images = load_piece_images()
    if piece_images is None:
        st.error("Failed to load piece images from 'assets' folder.")
        return None
        
    board_image = draw_chess_board_pil(piece_images, is_opponent_thinking=is_opponent_thinking)
    click_value = streamlit_image_coordinates(board_image, key="chess_board")
    return click_value

def draw_right_panel(chat_spinner=False, stream_data=None, is_board_disabled=False):
    """Draws the right column (info, chat, moves) and returns user input."""
    
    # --- Game Info Panel ---
    st.subheader("Game Info")
    status_container = st.container(border=True, height=150)
    phase = st.session_state.chess_game_phase
    
    with status_container:
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
                st.session_state.chess_game_phase = 'processing_ai_move' # AI moves first
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
                st.session_state.selected_square = None
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
                    st.session_state.chess_game_phase = 'processing_llms' # Treat promotion as a move
                    st.session_state.last_click = None
                    st.rerun()
        else:
            if game.game_over:
                 st.success(game.status_message)
            else:
                 st.info(game.status_message)

    # --- New Game Button ---
    if st.button("New Game", use_container_width=True, disabled=(phase != 'playing' and phase != 'awaiting_user_decision' and not game.game_over)):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    # --- Coach Chat Panel ---
    st.subheader("Coach Gemini")
    chat_container = st.container(height=300, border=True)
    raw_text_accumulator = None
    
    with chat_container:
        if chat_spinner and not stream_data:
            # Spinner is shown while waiting for the *first* chunk
            with st.spinner("Coach is thinking..."):
                render_chat()
        else:
            # Chat is rendered normally
            render_chat()
        
        # Stream data is handled here, rendering the last message dynamically
        if stream_data:
            raw_text_accumulator = ""
            with st.chat_message(name="coach", avatar="🤖"):
                stream_placeholder = st.empty()
                for chunk in stream_data:
                    try:
                        raw_text_accumulator += chunk.text
                        stream_placeholder.markdown(raw_text_accumulator + "▌")
                        time.sleep(0.02) # Small delay for streaming effect
                    except ValueError:
                        pass # Ignore final, empty chunk
                stream_placeholder.markdown(raw_text_accumulator) # Final render
    
    user_prompt = st.chat_input("Ask Coach Gemini a question...", disabled=is_board_disabled)
    
    # --- Move History Panel ---
    st.subheader("Move History")
    st.text_area("Moves", "\n".join(f"{i+1}. {move}" for i, move in enumerate(game.move_history)), height=150)
    
    return user_prompt, raw_text_accumulator


# --- SINGLE-PASS UI DRAW ---
col1, col2 = st.columns([2, 1])
phase = st.session_state.get('chess_game_phase')

# 1. Determine UI state flags
is_board_disabled = (phase != 'playing' and phase != 'awaiting_user_decision')
is_opponent_thinking = (phase in ['processing_llms', 'processing_chat_message', 'streaming_coach_response', 'processing_ai_move'])
chat_spinner = (phase == 'processing_llms' or phase == 'processing_chat_message')
stream_data = st.session_state.coach_stream_data if phase == 'streaming_coach_response' else None

# 2. Draw UI
with col1:
    click_value = draw_board(is_opponent_thinking)

with col2:
    user_prompt, streamed_text = draw_right_panel(chat_spinner, stream_data, is_board_disabled)


# --- GAME PHASE LOGIC (No UI calls in this section) ---
# This is the main state machine for the application.

if phase == 'color_selection':
    # All logic is handled by the buttons in draw_right_panel()
    pass 

elif phase in ['playing', 'awaiting_user_decision']:
    # --- This phase handles all USER interactions (clicks or chat) ---
    
    if user_prompt:
        # User sent a chat message
        st.session_state.chat_history.append({"role": "user", "text": user_prompt})
        st.session_state.pending_user_query = user_prompt
        st.session_state.return_phase = phase # Remember where to return
        st.session_state.chess_game_phase = 'processing_chat_message'
        st.rerun()
    
    elif not is_board_disabled and click_value and click_value != st.session_state.get('last_click'):
        # User clicked the board
        st.session_state.last_click = click_value
        pos = get_click_board_coords(click_value)
        
        if pos and (0 <= pos[0] < 8 and 0 <= pos[1] < 8):
            selected_square = st.session_state.selected_square
            selected_piece = game.board.get_piece(selected_square) if selected_square else None
            clicked_piece = game.board.get_piece(pos)

            if selected_piece:
                # --- This is the SECOND click (making a move) ---
                if pos == selected_square:
                    # Clicked the same square, de-select
                    st.session_state.selected_square = None
                    st.rerun()
                else:
                    # Attempt to make the move
                    game.store_pre_move_state() # Store state in case of take-back
                    success, message = game.make_move(selected_square, pos)
                    st.session_state.selected_square = None
                    
                    if success and message != "Promotion":
                        # Move was successful, proceed to LLM analysis
                        st.session_state.chess_game_phase = 'processing_llms'
                        st.rerun()
                    elif not success:
                        # Move was invalid
                        game.revert_to_pre_move_state() # Revert to before move attempt
                        # If user clicked on *another* of their pieces, select it
                        if clicked_piece and clicked_piece.color == game.turn:
                            st.session_state.selected_square = pos
                        st.rerun()
            elif clicked_piece and clicked_piece.color == game.turn:
                # --- This is the FIRST click (selecting a piece) ---
                st.session_state.selected_square = pos
                st.rerun()

elif phase == 'processing_llms':
    # --- This phase runs after a *human* move is completed ---
    
    # 1. Get the last move's data
    last_move_data = game.game_data[-1]
    
    # 2. Call Commentator to get simple text
    last_move_commentary = ll_api.get_move_commentary(last_move_data)
    
    # 3. Get the 100% accurate Board State Narrative (FOR COACH)
    board_state_narrative = game.get_board_state_narrative()

    # 4. Call Coach for analysis (and get the stream)
    fresh_coach_session = ll_api.initialize_coach_chat()
    st.session_state.coach_stream_data = ll_api.get_coach_analysis(
        fresh_coach_session, 
        last_move_commentary,
        board_state_narrative  # Pass the new ground truth
    )
    
    # 5. Move to streaming phase
    st.session_state.stream_type = 'analysis' # To handle interventions
    st.session_state.chess_game_phase = 'streaming_coach_response'
    st.rerun()

elif phase == 'processing_chat_message':
    # --- This phase runs when the user asks a Q&A question ---
    
    # 1. Get context
    user_query = st.session_state.pending_user_query
    
    # 2. Get the 100% accurate Board State Narrative
    board_state_narrative = game.get_board_state_narrative()
    
    # 3. Call Coach for Q&A (and get the stream)
    fresh_coach_session = ll_api.initialize_coach_chat()
    st.session_state.coach_stream_data = ll_api.get_coach_qa_response(
        fresh_coach_session, 
        user_query, 
        board_state_narrative # Pass the new ground truth
    )
    
    # 4. Move to streaming phase
    st.session_state.pending_user_query = None
    st.session_state.stream_type = 'chat' # To handle return phase
    st.session_state.chess_game_phase = 'streaming_coach_response'
    st.rerun()

elif phase == 'streaming_coach_response':
    # --- This phase handles the *output* of the coach's stream ---
    
    final_commentary = ""
    try:
        if not streamed_text:
            raise ValueError("Streamed text is empty")
        
        # Clean the text (remove markdown, etc.)
        clean_text = streamed_text.strip().replace("```json", "").replace("```", "").strip()
        
        # Print for debugging
        print("--- COACH RESPONSE (RAW) ---")
        print(clean_text)
        print("------------------------------")
        
        parsed_json = json.loads(clean_text)
        final_commentary = parsed_json.get('commentary', "Sorry, I lost my train of thought.")
            
    except Exception as e: 
        print(f"Could not parse JSON, falling back to raw text. Error: {e}\nRaw text: {streamed_text}")
        final_commentary = streamed_text if streamed_text else "My apologies, I had a connection issue."

#--- ABOUT SECTION IN SIDEBAR-------------
st.sidebar.header("About")
st.sidebar.info("This is a collection of simple games built using Streamlit.")


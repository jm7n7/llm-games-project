#--- imports----------
import streamlit as st
from dotenv import load_dotenv # (FIX) Import dotenv
load_dotenv() # (FIX) Load the .env file at the very start

import pandas as pd
from chess_logic import ChessGame 
import chess_llm_functions as ll_api
import coach_agent
import ai_opponent_agent
import json
from PIL import Image
from streamlit_image_coordinates import streamlit_image_coordinates
from chess_app_functions import *
import os
import time
from concurrent.futures import ThreadPoolExecutor # FOR PARALLEL CALLS
#This should look correct

#--- PAGE CONFIG --
st.set_page_config(
    page_title="Chess Coach",
    layout="wide"
)

#--- APP TITLE AND HEADER------
st.title("LLM Chess Coach")

#--- SIDEBAR (simplified) -------------
st.sidebar.header("About")
st.sidebar.info("This chess app uses an agent-based Generative AI system to play chess against you, scale to your skill level, and provide real-time coaching.")


#--- MAIN CONTENT AREA -----------------------------------------------
st.header("Chess")

# --- API KEY CHECK ---
# (Ensures all required API keys are set in the environment)
if 'GOOGLE_API_KEY' not in os.environ:
    st.error("Your Google AI API key is not configured. Please set the GOOGLE_API_KEY environment variable to play.")
    st.stop()

# --- INITIALIZATION ---
# Initialize session state keys if they don't exist
if 'user_skill_level' not in st.session_state:
    st.session_state.user_skill_level = 'beginner'

if 'chess_game' not in st.session_state:
    # This block runs only once when the app is first loaded
    st.session_state.chess_game = ChessGame()
    st.session_state.selected_square = None
    st.session_state.last_click = None
    st.session_state.chess_game_phase = 'color_selection'
    st.session_state.player_color = 'white'
    st.session_state.ai_color = 'black'
    st.session_state.chat_history = [{"role": "coach", "text": "Hi! I'm Coach Gemini. Select your skill level and color to begin."}]
    st.session_state.pending_ai_move_packet = None
    st.session_state.coach_packet = None
    st.session_state.coach_stream_data = None
    st.session_state.pending_user_query = None
    st.session_state.return_phase = None
    # NEW state for opponent UI and post-game summary
    st.session_state.last_ai_reasoning = None
    st.session_state.last_ai_move_type = None
    st.session_state.post_game_summary_shown = False
    
game = st.session_state.chess_game

def reset_game_state():
    """Resets all game-related state, preserving user skill."""
    print("--- RESETTING GAME ---")
    st.session_state.chess_game = ChessGame()
    st.session_state.selected_square = None
    st.session_state.last_click = None
    st.session_state.chess_game_phase = 'color_selection'
    st.session_state.player_color = 'white'
    st.session_state.ai_color = 'black'
    st.session_state.chat_history = [{"role": "coach", "text": f"New game! Your skill level is set to {st.session_state.user_skill_level}. Choose your color to begin."}]
    st.session_state.pending_ai_move_packet = None
    st.session_state.coach_packet = None
    st.session_state.coach_stream_data = None
    st.session_state.pending_user_query = None
    st.session_state.return_phase = None
    st.session_state.last_ai_reasoning = None
    st.session_state.last_ai_move_type = None
    st.session_state.post_game_summary_shown = False


# --- UI DRAWING FUNCTIONS ---

def render_chat():
    """Renders the chat history."""
    for msg in st.session_state.chat_history:
        with st.chat_message(name=msg["role"], avatar="🤖" if msg["role"] == "coach" else "🧑"):
            st.write(msg['text'])

def draw_opponent_panel():
    """
    (NEW) Draws the Opponent's "chat bubble" above the board
    if the opponent has reasoning from its last move.
    """
    if st.session_state.last_ai_reasoning:
        faces = {
            "blunder": "😥",
            "human": "🙂",
            "best": "🧐",
            "default": "🤖"
        }
        avatar = faces.get(st.session_state.last_ai_move_type, faces["default"])
        
        with st.chat_message(name=st.session_state.ai_color.capitalize(), avatar=avatar):
            st.write(st.session_state.last_ai_reasoning)

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
    status_container = st.container(border=True, height=200) # Increased height
    phase = st.session_state.chess_game_phase
    
    with status_container:
        st.selectbox(
            "Select Skill Level",
            ("beginner", "intermediate", "advanced"),
            key="user_skill_level",
            disabled=(is_board_disabled and phase != 'color_selection') # Allow change only before game
        )
        
        st.write(f"Player: {st.session_state.player_color.capitalize()}")
        st.write(f"Opponent: {st.session_state.ai_color.capitalize()}")
        
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
                st.session_state.pending_ai_move_packet = None # Clear the pre-calced move
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
    if st.button("New Game", use_container_width=True):
        reset_game_state()
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
    draw_opponent_panel() # (NEW) Draw opponent's bubble
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
        
        # (NEW) Clear the opponent's last message on any valid user click
        st.session_state.last_ai_reasoning = None
        st.session_state.last_ai_move_type = None
        
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
    # This phase calls BOTH agents in parallel.
    
    # 1. Get the last move's data
    last_move_data = game.game_data[-1]
    
    # 2. Get the 100% accurate Board State Narrative
    board_state_narrative = game.get_board_state_narrative()
    
    # 3. Get context for agents
    user_skill_level = st.session_state.user_skill_level
    player_color = st.session_state.player_color
    legal_moves = game._get_all_legal_moves(st.session_state.ai_color)

    # 4. Run both agents concurrently using a ThreadPoolExecutor
    instruction_packet = None
    ai_move_packet = None

    with ThreadPoolExecutor() as executor:
        # Submit Coach Agent
        coach_future = executor.submit(
            coach_agent.get_coaching_packet,
            last_move_data,
            board_state_narrative,
            user_skill_level,
            player_color # (FIXED) Pass player color
        )
        
        # (NEW) Only submit AI Agent if the game is NOT over
        ai_future = None
        if not game.game_over and legal_moves:
            ai_future = executor.submit(
                ai_opponent_agent.get_ai_move,
                board_state_narrative,
                legal_moves,
                user_skill_level
            )
        
        # Wait for both futures to complete and get their results
        instruction_packet = coach_future.result()
        if ai_future:
            ai_move_packet = ai_future.result()

    # 5. Store packets and move to packet processing phase
    st.session_state.coach_packet = instruction_packet
    st.session_state.pending_ai_move_packet = ai_move_packet # Store the generated AI move
    st.session_state.chess_game_phase = 'processing_coach_packet'
    st.rerun()

elif phase == 'processing_coach_packet':
    # --- This phase handles the *output* of the coach's packet ---
    
    packet = st.session_state.coach_packet
    st.session_state.coach_packet = None # Clear the packet
    
    if not packet:
        print("!!! CRITICAL: Coach packet was None. Failing silently.")
        packet = {"response_type": "silent", "message": None}
        
    response_type = packet.get("response_type", "silent")
    message = packet.get("message")

    if message: # Add any non-silent message to chat
        st.session_state.chat_history.append({"role": "coach", "text": message})

    if response_type == "intervention":
        # Coach wants to stop the game
        st.session_state.chess_game_phase = 'awaiting_user_decision'
    else:
        # Normal analysis, proceed to AI move (or end game)
        game.clear_pre_move_state() # Finalize the human's move
        
        # (NEW) Check for game over and run post-game summary
        if game.game_over and not st.session_state.get('post_game_summary_shown'):
            st.session_state.post_game_summary_shown = True # Mark as shown
            
            # Call the summary tool
            game_data_json = json.dumps(game.game_data)
            summary_packet = coach_agent.get_post_game_summary(game_data_json, st.session_state.player_color)
            
            if summary_packet and summary_packet.get('message'):
                st.session_state.chat_history.append({"role": "coach", "text": summary_packet['message']})
            
            st.session_state.chess_game_phase = 'playing' # End state
            
        elif game.game_over:
            st.session_state.chess_game_phase = 'playing' # Game already over, do nothing
        
        else:
            st.session_state.chess_game_phase = 'processing_ai_move'

    st.rerun()

elif phase == 'processing_chat_message':
    # --- This phase runs when the user asks a Q&A question ---
    
    # 1. Get context
    user_query = st.session_state.pending_user_query
    
    # 2. Get the 100% accurate Board State Narrative
    board_state_narrative = game.get_board_state_narrative()
    
    # 3. Call Coach for Q&A (and get the stream)
    st.session_state.coach_stream_data = ll_api.get_coach_qa_response(
        user_query, 
        board_state_narrative,
        st.session_state.player_color # (NEW) Pass player color
    )
    
    # 4. Move to streaming phase
    st.session_state.pending_user_query = None
    st.session_state.stream_type = 'chat' # To handle return phase
    st.session_state.chess_game_phase = 'streaming_coach_response'
    st.rerun()

elif phase == 'streaming_coach_response':
    # --- This phase handles the *output* of the coach's stream (Q&A ONLY) ---
    
    final_commentary = ""
    try:
        if not streamed_text:
            raise ValueError("Streamed text is empty")
        
        # (FIXED) Handle streaming JSON
        clean_text = streamed_text.strip().replace("```json", "").replace("```", "").strip()
        if not clean_text:
            raise ValueError("Streamed text was empty after cleaning")

        parsed_json = json.loads(clean_text)
        final_commentary = parsed_json.get('commentary', "Sorry, I lost my train of thought.")
            
    except Exception as e: 
        print(f"Could not parse Q&A JSON, falling back to raw text. Error: {e}\nRaw text: {streamed_text}")
        final_commentary = streamed_text if (streamed_text and "{" not in streamed_text) else "My apologies, I had a connection issue."

    stream_type = st.session_state.get('stream_type', 'chat')
    st.session_state.stream_type = None # Clear stream type

    if stream_type == 'chat':
        # This was a Q&A response
        st.session_state.chat_history.append({"role": "coach", "text": final_commentary})
        st.session_state.chess_game_phase = st.session_state.get('return_phase', 'playing')
        st.session_state.return_phase = None
    
    st.session_state.coach_stream_data = None # Clear the stream data
    st.rerun()

elif phase == 'processing_ai_move':
    # --- This phase runs after the Coach approves the human move (or intervention) ---
    
    # 1. Get the pre-calculated AI move packet
    ai_move_packet = st.session_state.pending_ai_move_packet
    st.session_state.pending_ai_move_packet = None # Clear the packet

    if not ai_move_packet:
        # No legal moves, game is over (checkmate/stalemate) or an error occurred
        # This can happen if AI moved first and player chose black
        if game.game_over:
             st.session_state.chess_game_phase = 'playing'
             st.rerun()
        
        # This is the "AI moves first" scenario
        print("[APP] No AI move packet found. Assuming AI moves first.")
        legal_moves = game._get_all_legal_moves(st.session_state.ai_color)
        if not legal_moves:
            st.session_state.chess_game_phase = 'playing'
            st.rerun()
            
        ai_move_packet = ai_opponent_agent.get_ai_move(
            game.get_board_state_narrative(),
            legal_moves,
            st.session_state.user_skill_level
        )
        if not ai_move_packet:
             st.session_state.chess_game_phase = 'playing'
             st.rerun() # Critical error, just stop
    
    # 2. Get move data from the packet
    move_str = ai_move_packet.get('move')
    
    # (NEW) Store reasoning and move type for the UI
    st.session_state.last_ai_reasoning = ai_move_packet.get('reasoning', "...")
    st.session_state.last_ai_move_type = ai_move_packet.get('move_type', "default")

    # 3. Make the AI's move on the board
    if move_str:
        start_pos = game._notation_to_pos_tuple(move_str.split('-')[0])
        end_pos = game._notation_to_pos_tuple(move_str.split('-')[1])
        game.make_move(start_pos, end_pos)
        
        # Auto-promote to Queen if AI gets a promotion
        if game.promotion_pending:
            game.promote_pawn("Queen")
        
        # (NEW) Check for post-move game over (AI delivered checkmate)
        if game.game_over and not st.session_state.get('post_game_summary_shown'):
            st.session_state.post_game_summary_shown = True # Mark as shown
            
            # Call the summary tool
            game_data_json = json.dumps(game.game_data)
            summary_packet = coach_agent.get_post_game_summary(game_data_json, st.session_state.player_color)
            
            if summary_packet and summary_packet.get('message'):
                st.session_state.chat_history.append({"role": "coach", "text": summary_packet['message']})
    
    # 4. Set state to playing
    st.session_state.chess_game_phase = 'playing'
    st.session_state.selected_square = None
    game.clear_pre_move_state()
    st.rerun()



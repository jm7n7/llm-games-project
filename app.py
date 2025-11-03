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
st.sidebar.info("This chess app uses a team of specialized LLM agents to create a dynamic coaching experience. An Opponent Agent plays against you, while a Coach Agent analyzes your moves for key learning moments.")


#--- MAIN CONTENT AREA -----------------------------------------------
st.header("Chess")

# --- API KEY CHECK ---
if 'GOOGLE_API_KEY' not in os.environ or not os.environ['GOOGLE_API_KEY']:
    st.error("Your Google AI API key is not configured. Please set the GOOGLE_API_KEY environment variable to play.")
    st.stop()

# --- (MODIFIED) INITIALIZATION ---
# Initialize persistent state *outside* the 'New Game' block
if 'user_skill_level' not in st.session_state:
    st.session_state.user_skill_level = "beginner"
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = [{"role": "coach", "text": "Hi! I'm Coach Gemini. I'll be watching your game and offering feedback."}]

# Initialize game-specific state
def init_game():
    """Resets all game-specific session state variables."""
    st.session_state.chess_game = ChessGame()
    st.session_state.selected_square = None
    st.session_state.last_click = None
    st.session_state.chess_game_phase = 'color_selection'
    st.session_state.player_color = 'white'
    st.session_state.ai_color = 'black'
    
    # AI agent state
    st.session_state.pending_ai_packet = None
    st.session_state.last_ai_reasoning = None
    st.session_state.last_ai_move_type = "default"
    
    # Coach agent state
    st.session_state.pending_coach_packet = None
    st.session_state.pending_user_query = None
    st.session_state.streaming_coach_data = None
    
    # (NEW) Post-game summary state
    st.session_state.post_game_summary_done = False
    
    # (NEW) Pre-move context for Coach 2.0
    st.session_state.human_context_packet = None

# Check if a game needs to be initialized
if 'chess_game' not in st.session_state:
    init_game()

game = st.session_state.chess_game

# --- (NEW) UI DRAWING FUNCTIONS (Refactored) ---

def render_chat():
    """Renders the chat history."""
    for msg in st.session_state.chat_history:
        with st.chat_message(name=msg["role"], avatar="🤖" if msg["role"] == "coach" else "🧑"):
            st.write(msg['text'])

def draw_opponent_panel():
    """
    (NEW) Draws the opponent's "thinking" panel above the board.
    """
    reasoning = st.session_state.last_ai_reasoning
    move_type = st.session_state.last_ai_move_type
    
    # Define avatars
    faces = {
        "blunder": "😥",
        "human": "🙂",
        "best": "🧐",
        "default": "🤖"
    }
    
    avatar = faces.get(move_type, "🤖")
    
    if reasoning:
        with st.chat_message(name="opponent", avatar=avatar):
            st.markdown(f"**Opponent's thoughts:**\n\n{reasoning}")

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
                st.session_state.pending_coach_packet = None
                st.session_state.pending_ai_packet = None
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

        # (FIX) Skill Level Selector - Moved outside 'color_selection'
        # It is now always visible, but disabled during AI thinking
        st.radio(
            "Select Skill Level",
            ["beginner", "intermediate", "advanced"],
            key="user_skill_level",
            horizontal=True,
            disabled=(phase != 'playing' and phase != 'awaiting_user_decision' and phase != 'color_selection' and not game.game_over)
        )


    # --- New Game Button ---
    if st.button("New Game", use_container_width=True, disabled=(phase == 'processing_llms' or phase == 'processing_chat_message')):
        # (MODIFIED) Only reset game state, not chat history or skill level
        init_game() 
        # Add a fresh "Hi" message from the coach
        st.session_state.chat_history.append({"role": "coach", "text": "Starting a new game! Good luck."})
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
                        # (MODIFIED) Handle new streaming JSON
                        clean_chunk = chunk.text.strip().replace("```json", "").replace("```", "").strip()
                        if clean_chunk:
                            # Try to parse incremental JSON
                            try:
                                # Find the start of the JSON
                                json_start = clean_chunk.find('{')
                                if json_start != -1:
                                    json_text = clean_chunk[json_start:]
                                    # This is a brittle way to handle streaming JSON
                                    # We assume the commentary field is last
                                    commentary_start = json_text.find('"commentary": "')
                                    if commentary_start != -1:
                                        commentary_text = json_text[commentary_start + len('"commentary": "'):-2] # Strip "}}
                                        raw_text_accumulator = commentary_text
                                        stream_placeholder.markdown(raw_text_accumulator + "▌")
                            except Exception as e:
                                pass # Ignore parsing errors on partial streams
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
stream_data = st.session_state.streaming_coach_data if phase == 'streaming_coach_response' else None

# 2. Draw UI
with col1:
    # (NEW) Draw opponent panel above board
    draw_opponent_panel() 
    click_value = draw_board(is_opponent_thinking)

with col2:
    user_prompt, streamed_text = draw_right_panel(chat_spinner, stream_data, is_board_disabled)


# --- (NEW) GAME PHASE LOGIC (Agent-based) ---
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
                    # (NEW) Capture "Coach 2.0" context *before* the move
                    human_context_packet = {
                        "dangers_before": game.get_tactical_threats(game.turn),
                        "options_before": game.get_all_legal_moves_with_consequences(game.turn)
                    }
                    st.session_state.human_context_packet = human_context_packet

                    # Attempt to make the move
                    game.store_pre_move_state() # Store state in case of take-back
                    success, message = game.make_move(selected_square, pos)
                    st.session_state.selected_square = None
                    
                    if success:
                        # Move was successful, proceed to LLM analysis
                        st.session_state.chess_game_phase = 'processing_llms'
                        st.rerun()
                    elif not success:
                        # Move was invalid
                        game.revert_to_pre_move_state() # Revert to before move attempt
                        st.session_state.human_context_packet = None # Clear context
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
    
    # 1. Get data for the Coach Agent (Coach 2.0)
    last_move_data = game.game_data[-1]
    human_context = st.session_state.human_context_packet
    
    # (NEW) Print the ground truth narrative for debugging
    print("\n" + "="*50)
    print("--- [GROUND TRUTH] COACH 2.0 CONTEXT ---")
    print(f"Dangers: {json.dumps(human_context['dangers_before'], indent=2)}")
    print(f"Options: {len(human_context['options_before'])} legal moves found")
    print(f"Chosen Move: {json.dumps(last_move_data, indent=2)}")
    print("="*50 + "\n")
    
    # 2. Get data for the Opponent Agent
    user_skill_level = st.session_state.user_skill_level
    player_color = st.session_state.player_color
    
    # (NEW) Generate the "Move Consequence Mapping" for the opponent
    opponent_enhanced_moves = game.get_all_legal_moves_with_consequences(st.session_state.ai_color)
    # (NEW) Generate the "Dangers List" for the opponent
    opponent_tactical_threats = game.get_tactical_threats(st.session_state.ai_color)
    opponent_legal_moves_simple = [m['move'] for m in opponent_enhanced_moves] # For validation
    
    # 3. Call both agents in parallel
    instruction_packet = None
    ai_move_packet = None

    with ThreadPoolExecutor() as executor:
        # Submit Coach Agent (Coach 2.0)
        coach_future = executor.submit(
            coach_agent.get_coaching_packet,
            last_move_data,
            json.dumps(human_context['dangers_before']),
            json.dumps(human_context['options_before']),
            user_skill_level,
            player_color
        )
        
        # Submit Opponent Agent (only if game isn't over)
        ai_future = None
        if not game.game_over:
            ai_future = executor.submit(
                ai_opponent_agent.get_ai_move,
                json.dumps(opponent_enhanced_moves),  # (MODIFIED) Pass as JSON
                json.dumps(opponent_tactical_threats), # (NEW) Pass as JSON
                opponent_legal_moves_simple,
                user_skill_level
            )

        # Wait for both futures to complete and get their results
        instruction_packet = coach_future.result()
        if ai_future:
            ai_move_packet = ai_future.result()
        
    # 4. Store packets in session state and move to next phase
    st.session_state.pending_coach_packet = instruction_packet
    st.session_state.pending_ai_packet = ai_move_packet
    st.session_state.human_context_packet = None # Clear context packet
    st.session_state.chess_game_phase = 'processing_coach_packet'
    st.rerun()


elif phase == 'processing_coach_packet':
    # --- This phase handles the *output* of the Coach Agent ---
    
    packet = st.session_state.pending_coach_packet
    st.session_state.pending_coach_packet = None # Clear packet
    
    if not packet:
        # This should not happen, but as a fallback, move to AI move
        st.session_state.chess_game_phase = 'processing_ai_move'
        st.rerun()

    response_type = packet.get("response_type", "silent")
    message = packet.get("message")

    # (NEW) Post-Game Summary Logic
    if game.game_over and not st.session_state.post_game_summary_done:
        st.session_state.post_game_summary_done = True
        
        # Add the final move analysis (e.g., "Checkmate!")
        if message:
            st.session_state.chat_history.append({"role": "coach", "text": message})
        
        # Call the Post-Game tool
        print("[APP] Game over. Calling Post-Game Summary Tool...")
        summary_packet = coach_agent.get_post_game_summary(
            json.dumps(game.game_data),
            st.session_state.player_color
        )
        summary_message = summary_packet.get("message", "Game over. Well played!")
        st.session_state.chat_history.append({"role": "coach", "text": summary_message})
        
        # End the turn (don't proceed to AI move)
        st.session_state.chess_game_phase = 'playing'
        st.rerun()

    # (NEW) Standard Packet-Handling Logic
    if response_type == "intervention":
        # Coach wants to stop the game
        st.session_state.chat_history.append({"role": "coach", "text": message})
        st.session_state.chess_game_phase = 'awaiting_user_decision'
    
    elif response_type in ["praise", "encouragement"]:
        # Normal analysis, proceed to AI move
        game.clear_pre_move_state() # Finalize the human's move
        st.session_state.chat_history.append({"role": "coach", "text": message})
        st.session_state.chess_game_phase = 'processing_ai_move'
        
    elif response_type == "silent":
        # No message, just proceed
        game.clear_pre_move_state()
        st.session_state.chess_game_phase = 'processing_ai_move'

    st.rerun()


elif phase == 'processing_chat_message':
    # --- This phase runs when the user asks a Q&A question ---
    
    user_query = st.session_state.pending_user_query
    st.session_state.pending_user_query = None
    
    # Get context for the Q&A tool (it still uses the simple narrative)
    board_state_narrative = game.get_board_state_narrative()
    player_color = st.session_state.player_color
    
    # Call the Q&A tool (streaming)
    st.session_state.streaming_coach_data = ll_api.get_coach_qa_response(
        user_query, 
        board_state_narrative,
        player_color
    )
    
    st.session_state.chess_game_phase = 'streaming_coach_response'
    st.rerun()


elif phase == 'streaming_coach_response':
    # --- This phase handles the *output* of the Q&A stream ---
    
    final_commentary = ""
    try:
        if not streamed_text:
            raise ValueError("Streamed text is empty")
        
        # The streamed_text is now the *raw* commentary,
        # as the draw function already parsed the JSON
        final_commentary = streamed_text
            
    except Exception as e: 
        print(f"Could not parse stream, falling back. Error: {e}")
        final_commentary = streamed_text if streamed_text else "My apologies, I had a connection issue."

    # This was a Q&A response, so add it to chat and return
    st.session_state.chat_history.append({"role": "coach", "text": final_commentary})
    st.session_state.chess_game_phase = st.session_state.get('return_phase', 'playing')
    st.session_state.return_phase = None
    
    st.session_state.streaming_coach_data = None # Clear the stream data
    st.rerun()


elif phase == 'processing_ai_move':
    # --- This phase runs after the Coach packet is cleared ---
    # The AI's move has *already been decided* in parallel.
    
    if game.game_over:
        st.session_state.chess_game_phase = 'playing'
        st.rerun()
        
    ai_packet = st.session_state.pending_ai_packet
    st.session_state.pending_ai_packet = None # Clear packet
    
    if not ai_packet:
        # This can happen if it's AI's turn first
        print("[APP] No AI packet found, generating one now...")
        
        # (NEW) Generate the "Move Consequence Mapping" for the opponent
        opponent_enhanced_moves = game.get_all_legal_moves_with_consequences(st.session_state.ai_color)
        # (NEW) Generate the "Dangers List" for the opponent
        opponent_tactical_threats = game.get_tactical_threats(st.session_state.ai_color)
        opponent_legal_moves_simple = [m['move'] for m in opponent_enhanced_moves] # For validation
        
        if not opponent_legal_moves_simple:
            st.session_state.chess_game_phase = 'playing' # Game is over (stalemate/checkmate)
            st.rerun()
            
        ai_packet = ai_opponent_agent.get_ai_move(
            json.dumps(opponent_enhanced_moves),  # (MODIFIED) Pass as JSON
            json.dumps(opponent_tactical_threats), # (NEW) Pass as JSON
            opponent_legal_moves_simple,
            st.session_state.user_skill_level
        )

    # 4. Make the AI's move on the board
    move_str = ai_packet.get("move")
    if move_str:
        start_pos = game._notation_to_pos_tuple(move_str.split('-')[0])
        end_pos = game._notation_to_pos_tuple(move_str.split('-')[1])
        game.make_move(start_pos, end_pos)
        
        # Auto-promote to Queen if AI gets a promotion
        if game.promotion_pending:
            game.promote_pawn("Queen")
        
        # (NEW) Store the AI's reasoning and move type for the UI
        st.session_state.last_ai_reasoning = ai_packet.get("reasoning")
        st.session_state.last_ai_move_type = ai_packet.get("move_type")
        
        # 5. Get context for the Coach's *acknowledgment*
        # (We no longer need this, the AI reasoning is shown)
        
        # 6. Set state back to playing
        st.session_state.chess_game_phase = 'playing'
        st.session_state.selected_square = None
        game.clear_pre_move_state()
        st.rerun()
    
    st.session_state.chess_game_phase = 'playing'
    st.rerun()


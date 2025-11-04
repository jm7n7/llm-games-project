#--- imports----------
import streamlit as st
from dotenv import load_dotenv
load_dotenv()

import os
import json
import coach_agent
import pandas as pd
import ai_opponent_agent
import chess_llm_functions as ll_api

from PIL import Image
from chess_app_functions import *
from chess_logic import ChessGame
from concurrent.futures import ThreadPoolExecutor # FOR PARALLEL CALLS
from streamlit_image_coordinates import streamlit_image_coordinates

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

# --- INITIALIZATION ---
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
    st.session_state.last_ai_reasoning = "The game has just begun. Good luck!"
    st.session_state.last_ai_move_type = "default"
    
    # Coach agent state
    st.session_state.pending_coach_packet = None
    st.session_state.pending_user_query = None
    
    # Post-game summary state
    st.session_state.post_game_summary_done = False
    
    # Pre-move context for Coach
    st.session_state.human_context_packet = None

# Check if a game needs to be initialized
if 'chess_game' not in st.session_state:
    init_game()

game = st.session_state.chess_game

# --- UI DRAWING FUNCTIONS ---

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

def draw_right_panel(chat_spinner=False, is_board_disabled=False):
    """
    Draws the right column (info, chat, moves) and returns user input.
    """
    
    # --- Game Info Panel ---
    st.subheader("Game Info")
    status_container = st.container(border=True, height=200)
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

        # Skill Level Selector - Moved outside 'color_selection'
        st.radio(
            "Select Skill Level",
            ["beginner", "intermediate", "advanced"],
            key="user_skill_level",
            horizontal=True,
            disabled=(phase != 'playing' and phase != 'awaiting_user_decision' and phase != 'color_selection' and not game.game_over)
        )


    # --- New Game Button ---
    if st.button("New Game", use_container_width=True, disabled=(phase == 'processing_llms' or phase == 'processing_chat_message')):
        # Only reset game state, not chat history or skill level
        init_game() 
        # Add a fresh "Hi" message from the coach
        st.session_state.chat_history.append({"role": "coach", "text": "Starting a new game! Good luck."})
        st.rerun()

    # --- Coach Chat Panel ---
    st.subheader("Coach Joey")
    chat_container = st.container(height=300, border=True)
    
    with chat_container:
        if chat_spinner:
            # Spinner is shown while waiting for the *first* chunk
            with st.spinner("Coach Joey is thinking..."):
                render_chat()
        else:
            # Chat is rendered normally
            render_chat()
    
    user_prompt = st.chat_input("Ask Coach Joey a question...", disabled=is_board_disabled)
    
    # --- Move History Panel ---
    st.subheader("Move History")
    st.text_area("Moves", "\n".join(f"{i+1}. {move}" for i, move in enumerate(game.move_history)), height=150)
    
    return user_prompt


# --- SINGLE-PASS UI DRAW ---
col1, col2 = st.columns([2, 1])
phase = st.session_state.get('chess_game_phase')

# 1. Determine UI state flags
is_board_disabled = (phase != 'playing' and phase != 'awaiting_user_decision')
is_opponent_thinking = (phase in ['processing_llms', 'processing_chat_message', 'processing_ai_move'])
chat_spinner = (phase == 'processing_llms' or phase == 'processing_chat_message')

# 2. Draw UI
with col1:
    # Draw opponent panel above board
    draw_opponent_panel() 
    click_value = draw_board(is_opponent_thinking)

with col2:
    user_prompt = draw_right_panel(chat_spinner, is_board_disabled)


# --- GAME PHASE LOGIC (Agent-based) ---
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
                    # Capture "Coach" context *before* the move
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
    
    # 1. Get data for the Coach Agent (Coach)
    last_move_data = game.game_data[-1]
    human_context = st.session_state.human_context_packet
    
    # Print the ground truth for debugging
    print("\n" + "="*50)
    print("--- [GROUND TRUTH] COACH CONTEXT ---")
    print(f"Dangers: {json.dumps(human_context['dangers_before'], indent=2)}")
    print(f"Options: {len(human_context['options_before'])} legal moves found")
    print(f"Chosen Move: {json.dumps(last_move_data, indent=2)}")
    print("="*50 + "\n")
    
    # 2. Get data for the Opponent Agent
    user_skill_level = st.session_state.user_skill_level
    player_color = st.session_state.player_color
    
    # Generate the "Move Consequence Mapping" for the opponent
    opponent_enhanced_moves = game.get_all_legal_moves_with_consequences(st.session_state.ai_color)
    # Generate the "Dangers List" for the opponent
    opponent_tactical_threats = game.get_tactical_threats(st.session_state.ai_color)
    opponent_legal_moves_simple = [m['move'] for m in opponent_enhanced_moves] # For validation
    
    # 3. Call both agents in parallel
    instruction_packet = None
    ai_move_packet = None

    with ThreadPoolExecutor() as executor:
        # Submit Coach Agent
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
                json.dumps(opponent_enhanced_moves),  # Pass as JSON
                json.dumps(opponent_tactical_threats), # Pass as JSON
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

    # Post-Game Summary Logic
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

    # Standard Packet-Handling Logic
    # The new coach is conversational and *always* provides feedback
    # (even if just acknowledgment) unless silent on failure.
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
    # --- This phase runs the new Q&A Router Agent ---
    
    user_query = st.session_state.pending_user_query
    st.session_state.pending_user_query = None
    
    # 1. Build the full game context for the Q&A agent
    # Get last coach message (but not if it was the user)
    last_coach_message = None
    if st.session_state.chat_history:
        for msg in reversed(st.session_state.chat_history):
            if msg['role'] == 'coach':
                last_coach_message = msg['text']
                break
                
    game_context = {
        "user_skill_level": st.session_state.user_skill_level,
        "player_color": st.session_state.player_color,
        "last_ai_reasoning": st.session_state.last_ai_reasoning,
        "last_coach_message": last_coach_message,
        "current_turn": game.turn,
        # Provide live, ground-truth data for the 'analyze_board' specialist
        "dangers_list": json.dumps(game.get_tactical_threats(game.turn)),
        "options_list": json.dumps(game.get_all_legal_moves_with_consequences(game.turn))
    }
    game_context_json = json.dumps(game_context)
    
    # 2. Call the Q&A Agent (non-streaming)
    # This single call runs the entire "Router -> Specialist" pipeline
    qa_packet = coach_agent.get_qa_response(user_query, game_context_json)
    
    # 3. Add the response and return to the game
    response_text = qa_packet.get("commentary", "My apologies, I had a connection issue.")
    st.session_state.chat_history.append({"role": "coach", "text": response_text})
    
    # 4. Return to the previous phase
    st.session_state.chess_game_phase = st.session_state.get('return_phase', 'playing')
    st.session_state.return_phase = None
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
        
        # Generate the "Move Consequence Mapping" for the opponent
        opponent_enhanced_moves = game.get_all_legal_moves_with_consequences(st.session_state.ai_color)
        # Generate the "Dangers List" for the opponent
        opponent_tactical_threats = game.get_tactical_threats(st.session_state.ai_color)
        opponent_legal_moves_simple = [m['move'] for m in opponent_enhanced_moves] # For validation
        
        if not opponent_legal_moves_simple:
            st.session_state.chess_game_phase = 'playing' # Game is over (stalemate/checkmate)
            st.rerun()
            
        ai_packet = ai_opponent_agent.get_ai_move(
            json.dumps(opponent_enhanced_moves),  # Pass as JSON
            json.dumps(opponent_tactical_threats), # Pass as JSON
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
        
        # Store the AI's reasoning and move type for the UI
        st.session_state.last_ai_reasoning = ai_packet.get("reasoning")
        st.session_state.last_ai_move_type = ai_packet.get("move_type")
        
        # 6. Set state back to playing
        st.session_state.chess_game_phase = 'playing'
        st.session_state.selected_square = None
        game.clear_pre_move_state()
        st.rerun()
    
    st.session_state.chess_game_phase = 'playing'
    st.rerun()
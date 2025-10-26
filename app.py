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
st.sidebar.info("This chess app uses three distinct LLMs to create a dynamic coaching experience. A Commentator translates moves, an Opponent plays against you, and a Coach analyzes the game.")


#--- MAIN CONTENT AREA -----------------------------------------------
st.header("Chess")

# --- API KEY CHECK ---
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
    
    # --- State for new LLM flow ---
    st.session_state.pending_ai_move = None
    st.session_state.coach_stream_data = None
    # st.session_state.opponent_chat_session = None # No longer needed
    st.session_state.opponent_context = None      # Stores (game_history_json, legal_moves)

game = st.session_state.chess_game

# --- UI DRAWING FUNCTIONS (REFACTORED) ---

def render_chat():
    """Renders the chat history."""
    for msg in st.session_state.chat_history:
        with st.chat_message(name=msg["role"], avatar="🤖" if msg["role"] == "coach" else "🧑"):
            st.write(msg['text'])

def draw_board(is_opponent_thinking=False):
    """Draws the left column (board)."""
    board_image = draw_chess_board_pil(load_piece_images(), is_opponent_thinking=is_opponent_thinking)
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
                # Opponent needs to move first.
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
                # Clear pending AI state
                st.session_state.pending_ai_move = None
                # st.session_state.opponent_chat_session = None # No longer needed
                st.session_state.opponent_context = None
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
                    st.session_state.chess_game_phase = 'processing_llms' # Human move is now complete
                    st.session_state.last_click = None
                    st.rerun()
        else:
            if game.game_over:
                 st.success(game.status_message)
            else:
                 st.info(game.status_message)

    # --- New Game Button ---
    if st.button("New Game", use_container_width=True, disabled=(phase != 'playing' and phase != 'awaiting_user_decision' and not game.game_over)):
        # This loop clears all keys, including new ones
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    # --- Coach Chat Panel ---
    st.subheader("Coach Gemini")
    chat_container = st.container(height=300, border=True)
    raw_text_accumulator = None
    
    with chat_container:
        # Show spinner only when processing, not streaming
        if chat_spinner and not stream_data:
            with st.spinner("Coach is thinking..."):
                render_chat()
        else:
            render_chat()
        
        # Handle the streaming text display
        if stream_data:
            raw_text_accumulator = ""
            with st.chat_message(name="coach", avatar="🤖"):
                stream_placeholder = st.empty()
                for chunk in stream_data:
                    try:
                        raw_text_accumulator += chunk.text
                        # Render markdown with a cursor effect
                        stream_placeholder.markdown(raw_text_accumulator + "▌")
                        time.sleep(0.02) # Small delay for streaming effect
                    except ValueError:
                        pass # Ignore final, empty chunk
                # Show final, complete text
                stream_placeholder.markdown(raw_text_accumulator)
    
    # Chat input is disabled during any processing state
    user_prompt = st.chat_input("Ask Coach Gemini a question...", disabled=is_board_disabled)
    
    # --- Move History Panel ---
    st.subheader("Move History")
    # This just displays the simple algebraic notation from game_logic
    st.text_area("Moves", "\n".join(f"{i+1}. {move}" for i, move in enumerate(game.move_history)), height=150)
    
    return user_prompt, raw_text_accumulator


# --- SINGLE-PASS UI DRAW ---
col1, col2 = st.columns([2, 1])
phase = st.session_state.get('chess_game_phase')

# 1. Determine UI state flags
is_board_disabled = (phase != 'playing' and phase != 'awaiting_user_decision')
# is_opponent_thinking covers all non-interactive phases
is_opponent_thinking = (phase in ['processing_llms', 'processing_chat_message', 'streaming_coach_response', 'processing_ai_move'])
chat_spinner = (phase == 'processing_llms' or phase == 'processing_chat_message')
# stream_data is only populated during the streaming phase
stream_data = st.session_state.coach_stream_data if phase == 'streaming_coach_response' else None

# 2. Draw UI
with col1:
    click_value = draw_board(is_opponent_thinking)

with col2:
    # Get user input and the final text from the stream (if any)
    user_prompt, streamed_text = draw_right_panel(chat_spinner, stream_data, is_board_disabled)


# --- GAME PHASE LOGIC (No UI calls in this section) ---
if phase == 'color_selection':
    pass # UI handles this state completely

elif phase in ['playing', 'awaiting_user_decision']:
    # --- Handle User Q&A ---
    if user_prompt:
        st.session_state.chat_history.append({"role": "user", "text": user_prompt})
        st.session_state.pending_user_query = user_prompt
        st.session_state.return_phase = phase # Remember where to return
        st.session_state.chess_game_phase = 'processing_chat_message'
        st.rerun()
    
    # --- Handle Board Clicks ---
    elif not is_board_disabled and click_value and click_value != st.session_state.get('last_click'):
        st.session_state.last_click = click_value
        pos = get_click_board_coords(click_value)
        
        # Check for valid click coordinate
        if pos and (0 <= pos[0] < 8 and 0 <= pos[1] < 8):
            selected_square = st.session_state.selected_square
            selected_piece = game.board.get_piece(selected_square) if selected_square else None
            clicked_piece = game.board.get_piece(pos)

            if selected_piece: # A piece was already selected
                if pos == selected_square:
                    # Deselect
                    st.session_state.selected_square = None
                    st.rerun()
                else:
                    # Attempt to make a move
                    game.store_pre_move_state() # Store state for take-back
                    success, message = game.make_move(selected_square, pos)
                    st.session_state.selected_square = None
                    
                    if success and message != "Promotion":
                        # Move was successful, proceed to LLM processing
                        st.session_state.chess_game_phase = 'processing_llms'
                        st.rerun()
                    elif not success:
                        # Move failed (e.g., illegal, into check)
                        game.revert_to_pre_move_state()
                        # If user clicked another of their pieces, select it
                        if clicked_piece and clicked_piece.color == game.turn:
                            st.session_state.selected_square = pos
                        st.rerun()
            elif clicked_piece and clicked_piece.color == game.turn:
                # No piece was selected, so select this one
                st.session_state.selected_square = pos
                st.rerun()

elif phase == 'processing_llms':
    # --- This phase runs after a *human* move is completed ---
    
    # 1. Get the last move data (dict)
    last_move_data = game.game_data[-1]
    
    # 2. Call Commentator to get simple text
    last_move_commentary = ll_api.get_move_commentary(last_move_data)
    
    # 3. Get full game history for both LLMs
    game_history_json_str = json.dumps(game.game_data)
    
    # 4. Get legal moves for the AI
    legal_moves = game._get_all_legal_moves(st.session_state.ai_color)

    if legal_moves:
        # 5. Call Coach for analysis (and get the stream)
        fresh_coach_session = ll_api.initialize_coach_chat()
        st.session_state.coach_stream_data = ll_api.get_coach_analysis(
            fresh_coach_session, game_history_json_str, last_move_commentary
        )
        
        # 6. Prepare Opponent context (but do not call yet)
        # fresh_opponent_session = ll_api.initialize_opponent_chat() # No longer needed
        # st.session_state.opponent_chat_session = fresh_opponent_session # No longer needed
        st.session_state.opponent_context = (game_history_json_str, legal_moves)
        
        # 7. Move to streaming phase
        st.session_state.stream_type = 'analysis'
        st.session_state.chess_game_phase = 'streaming_coach_response'
        st.rerun()
    else: 
        # No legal moves, game is over
        game.clear_pre_move_state()
        st.session_state.chess_game_phase = 'playing'
        st.rerun()

elif phase == 'processing_chat_message':
    # --- This phase runs when the user asks a Q&A question ---
    
    # 1. Get context
    game_history_json_str = json.dumps(game.game_data)
    user_query = st.session_state.pending_user_query
    
    # 2. Call Coach for Q&A (and get the stream)
    fresh_coach_session = ll_api.initialize_coach_chat()
    st.session_state.coach_stream_data = ll_api.get_coach_qa_response(
        fresh_coach_session, user_query, game_history_json_str
    )
    
    # 3. Move to streaming phase
    st.session_state.pending_user_query = None
    st.session_state.stream_type = 'chat'
    st.session_state.chess_game_phase = 'streaming_coach_response'
    st.rerun()

elif phase == 'streaming_coach_response':
    # --- This phase handles the *result* of the coach's streamed text ---
    final_commentary = ""
    try:
        if not streamed_text:
            raise ValueError("Streamed text is empty")
        
        # Clean the final streamed text to get the JSON
        clean_text = streamed_text.strip().replace("```json", "").replace("```", "").strip()
        parsed_json = json.loads(clean_text)
        final_commentary = parsed_json.get('commentary', "Sorry, I lost my train of thought.")
            
    except Exception as e: 
        # Fallback if JSON parsing fails
        print(f"Could not parse JSON, falling back to raw text. Error: {e}\nRaw text: {streamed_text}")
        final_commentary = streamed_text if streamed_text else "My apologies, I had a connection issue."

    stream_type = st.session_state.get('stream_type', 'analysis')
    st.session_state.stream_type = None # Consume the type

    if stream_type == 'analysis': # Response to human move
        if final_commentary.startswith("[INTERVENTION]"):
            cleaned_commentary = final_commentary.replace("[INTERVENTION]", "").strip()
            st.session_state.chat_history.append({"role": "coach", "text": cleaned_commentary})
            st.session_state.chess_game_phase = 'awaiting_user_decision'
        else:
            game.clear_pre_move_state() # Finalize move
            st.session_state.chat_history.append({"role": "coach", "text": final_commentary})
            st.session_state.chess_game_phase = 'processing_ai_move'
            
    elif stream_type == 'ai_analysis': # Response to AI move
        if final_commentary and final_commentary != "...":
            st.session_state.chat_history.append({"role": "coach", "text": final_commentary})
        st.session_state.chess_game_phase = 'playing' # NOW the user can play
        
    elif stream_type == 'chat': # Response to Q&A
        st.session_state.chat_history.append({"role": "coach", "text": final_commentary})
        st.session_state.chess_game_phase = st.session_state.get('return_phase', 'playing')
        st.session_state.return_phase = None
    
    st.session_state.coach_stream_data = None # Clear stream data
    st.rerun()

elif phase == 'processing_ai_move':
    # This phase now has two parts:
    # 1. If pending_ai_move is None: Fetch it from the LLM.
    # 2. If pending_ai_move is set: Apply it, then call Commentator & Coach.

    if st.session_state.pending_ai_move:
        # --- PART 2: Apply move and get Coach acknowledgment ---
        move_str = st.session_state.pending_ai_move
        start_pos = game._notation_to_pos_tuple(move_str.split('-')[0])
        end_pos = game._notation_to_pos_tuple(move_str.split('-')[1])
        
        # Make the AI move
        game.make_move(start_pos, end_pos)
        if game.promotion_pending:
            game.promote_pawn("Queen") # AI always promotes to Queen
        
        # Get AI move commentary
        ai_move_data = game.game_data[-1]
        ai_move_commentary = ll_api.get_move_commentary(ai_move_data)
        
        # Get full history
        game_history_json_str = json.dumps(game.game_data)
        
        # Call Coach for acknowledgment
        fresh_coach_session = ll_api.initialize_coach_chat()
        st.session_state.coach_stream_data = ll_api.get_coach_ai_analysis(
            fresh_coach_session, game_history_json_str, ai_move_commentary
        )
        
        # Set state for streaming coach's reply
        st.session_state.stream_type = 'ai_analysis'
        st.session_state.chess_game_phase = 'streaming_coach_response'
        
        # Clear all pending AI contexts
        st.session_state.pending_ai_move = None
        # st.session_state.opponent_chat_session = None # No longer needed
        st.session_state.opponent_context = None
        st.session_state.selected_square = None
        game.clear_pre_move_state()
        st.rerun()

    else:
        # --- PART 1: Fetch the AI move ---
        # chat_session = st.session_state.opponent_chat_session # No longer needed
        context = st.session_state.opponent_context
        
        game_history_json_str = None
        legal_moves_list = None

        if context: # Modified (was if chat_session and context)
            # This is the normal flow after a human move
            game_history_json_str, legal_moves_list = context
        else:
            # This is the fallback for "Play as Black" (AI moves first)
            game_history_json_str = json.dumps(game.game_data)
            legal_moves_list = game._get_all_legal_moves(st.session_state.ai_color)
            # chat_session = ll_api.initialize_opponent_chat() # No longer needed

        if legal_moves_list:
            # Call Opponent LLM
            ai_response = ll_api.get_ai_opponent_move(
                # chat_session, # Removed
                game_history_json_str, 
                legal_moves_list
            )
            # Store the move. The rerun will trigger PART 2 of this phase.
            st.session_state.pending_ai_move = ai_response['move']
        else:
            # No legal moves, game is over.
            st.session_state.chess_game_phase = 'playing'
        
        st.rerun()


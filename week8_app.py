#--- imports----------
import io
import os
import streamlit as st
import pandas as pd
import json
import sys
from PIL import Image
from streamlit_image_coordinates import streamlit_image_coordinates
from streamlit_mic_recorder import mic_recorder # For audio recording

# Add the 'week6' directory to the system path to resolve module imports
# within that directory, which is necessary when running from the parent folder.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'week6')))

# --- User's actual game and retriever modules ---
from chess_logic import ChessGame
from chess_app_functions import *
import chess_llm_functions as llm_api
from speech_functions import transcribe_audio, text_to_speech
from visualization_generator import create_win_probability_chart, create_material_advantage_chart

# --- The following imports are from your existing project structure ---
# These are placeholders; ensure the paths are correct for your setup.
try:
    from week6.graph_retriever import GraphRetriever
    from week6.multi_hop_retriever import MultiHopRetriever
    from week6.generate_corpus import generate_game_analysis
    from week6.extract_entities import extract_graph_data
    from week6.build_graph import build_knowledge_graph, visualize_graph
except ImportError:
    st.error("Could not import modules from the 'week6' directory. Please ensure the path is correct.")
    # Define dummy functions to prevent crashes if imports fail
    def GraphRetriever(*args, **kwargs): return None
    def MultiHopRetriever(*args, **kwargs): return None
    def generate_game_analysis(*args, **kwargs): return ""
    def extract_graph_data(*args, **kwargs): return {}
    def build_knowledge_graph(*args, **kwargs): return None
    def visualize_graph(*args, **kwargs): pass


#--- RAG DATA PIPELINE ---
def run_full_rag_pipeline(dataframe, game_id):
    """
    Runs the complete data processing pipeline from game dataframe to knowledge graph.
    """
    st.info("Starting RAG pipeline...")
    progress_bar = st.progress(0)

    try:
        # 1. Generate Corpus
        st.write("Step 1: Generating game analysis corpus...")
        move_list = []
        for _, row in dataframe.iterrows():
            move_text = f"{row['turn']}. {row['piece_moved']} from {row['start_square']} to {row['end_square']}"
            if row['capture'] == 1:
                move_text += f" (captures {row['captured_piece']})"
            if row['check'] == 1:
                move_text += " (check)"
            if row['checkmate'] == 1:
                move_text += " (checkmate)"
            move_list.append(move_text)
        game_moves_str = "\n".join(move_list)

        analysis_text = generate_game_analysis(game_moves_str)
        if not analysis_text:
            st.error("Corpus generation failed.")
            return None, None
        with open(f"{game_id}_analysis.txt", "w", encoding='utf-8') as f:
            f.write(analysis_text)
        progress_bar.progress(25)

        # 2. Extract Entities
        st.write("Step 2: Extracting entities and relationships...")
        graph_data = extract_graph_data(analysis_text)
        if not graph_data:
            st.error("Entity extraction failed.")
            return None, None
        with open(f"{game_id}_graph_data.json", 'w', encoding='utf-8') as f:
            json.dump(graph_data, f, indent=4)
        progress_bar.progress(50)

        # 3. Build Graph
        st.write("Step 3: Building knowledge graph...")
        knowledge_graph = build_knowledge_graph(graph_data)
        import pickle
        graph_filename = f"{game_id}.graph"
        with open(graph_filename, 'wb') as f:
            pickle.dump(knowledge_graph, f)
        progress_bar.progress(75)

        # 4. Visualize Graph
        st.write("Step 4: Creating graph visualization...")
        visualize_graph(knowledge_graph, game_id)
        image_filename = f"{game_id}_knowledge_graph.png"
        progress_bar.progress(100)
        
        st.success(f"Analysis pipeline complete for game {game_id}!")
        return graph_filename, image_filename

    except Exception as e:
        st.error(f"An error occurred during the RAG pipeline: {e}")
        return None, None


# --- PAGE VIEW FUNCTIONS ---

def show_home_page():
    st.header("Welcome to the Game Arcade!")
    st.info("Select a page from the sidebar on the left to start playing or analyzing.")
    st.markdown("This app combines a playable chess game with a powerful Graph-RAG analysis tool.")

def show_chess_game_page():
    st.header("Play Chess vs. Coach Gemini")

    if 'GOOGLE_API_KEY' not in os.environ:
        st.error("Your Google AI API key is not configured. Please set the GOOGLE_API_KEY environment variable to play against the AI.")
        st.stop()

    if 'chess_game' not in st.session_state:
        st.session_state.chess_game = ChessGame()
        st.session_state.selected_square = None
        st.session_state.last_click = None
        st.session_state.chess_game_phase = 'color_selection'
        st.session_state.commentary_audio = None
        st.session_state.win_prob_chart = None
        st.session_state.material_chart = None
    
    game = st.session_state.chess_game

    # --- AUTOPLAY COMMENTARY AUDIO ---
    if st.session_state.get('commentary_audio'):
        st.audio(st.session_state.commentary_audio, autoplay=True)
        st.session_state.commentary_audio = None # Clear after playing

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
                # If player is black, AI makes the first move
                with st.spinner("Coach Gemini is thinking..."):
                    game.request_ai_move()
                st.rerun()

    elif st.session_state.get('chess_game_phase') == 'playing':
        piece_images = load_piece_images()
        if not piece_images:
            st.error("Could not find the `assets` folder or it is empty.")
            st.stop()
            
        col1, col2 = st.columns([2, 1])
        
        with col1:
            board_image = draw_chess_board_pil(piece_images)
            value = streamlit_image_coordinates(board_image, key="chess_board")
            
            # --- UPDATED CLICK HANDLING LOGIC ---
            if value and value != st.session_state.get('last_click'):
                st.session_state.last_click = value
                if not game.promotion_pending and game.turn == st.session_state.player_color:
                    
                    # Calculate clicked square from coordinates
                    SQUARE_SIZE, BORDER_SIZE = 80, 25
                    draw_c = (value['x'] - BORDER_SIZE) // SQUARE_SIZE
                    draw_r = (value['y'] - BORDER_SIZE) // SQUARE_SIZE
                    player_color = st.session_state.get('player_color', 'white')

                    if player_color == 'black':
                        r, c = 7 - draw_r, 7 - draw_c
                    else:
                        r, c = draw_r, draw_c
                    
                    clicked_pos = (r, c)
                    
                    if 0 <= r < 8 and 0 <= c < 8:
                        selected_square = st.session_state.selected_square
                        clicked_piece = game.board.get_piece(clicked_pos)

                        if selected_square:
                            # A piece was already selected, so this click is the destination square
                            start_notation = game.pos_to_notation(selected_square)
                            end_notation = game.pos_to_notation(clicked_pos)
                            move_str = f"{start_notation}-{end_notation}"

                            # This function makes the move AND triggers the AI response
                            success, message = game.make_move_from_notation(move_str)
                            st.session_state.selected_square = None # Deselect after move attempt

                            if success:
                                if not game.game_over:
                                    commentary = game.last_coach_commentary
                                    if commentary:
                                        st.session_state.commentary_audio = text_to_speech(commentary)
                                st.rerun()
                            else:
                                # If move failed, check if user clicked another of their pieces to select it instead
                                if clicked_piece and clicked_piece.color == game.turn:
                                    st.session_state.selected_square = clicked_pos
                                else:
                                    st.toast(message, icon="⚠️")
                                st.rerun()

                        elif clicked_piece and clicked_piece.color == game.turn:
                            # No piece was selected, so this click selects a piece
                            st.session_state.selected_square = clicked_pos
                            st.rerun()
                        else:
                            # Clicking on empty square or opponent piece does nothing
                            st.session_state.selected_square = None
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
                            # After promotion, capture AI commentary
                            if not game.game_over and game.turn == st.session_state.ai_color:
                                commentary = game.last_coach_commentary
                                if commentary:
                                    st.session_state.commentary_audio = text_to_speech(commentary)
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
                    st.session_state.pop('analysis_game_id', None)
                    st.session_state.chess_game_phase = 'color_selection'
                    st.session_state.win_prob_chart = None
                    st.session_state.material_chart = None
                    st.rerun()

            st.subheader("Move History")
            st.text_area(
                "Moves", 
                "\n".join(f"{i+1}. {move}" for i, move in enumerate(game.move_history)), 
                height=200, key="move_history"
            )

            # --- VOICE COMMAND SECTION ---
            st.subheader("Vocalize Your Move")
            if game.turn == st.session_state.player_color and not game.game_over:
                audio = mic_recorder(
                    start_prompt="🎤 Start Recording",
                    stop_prompt="⏹️ Stop Recording",
                    key='recorder'
                )

                if audio and audio['bytes']:
                    audio_bytes = audio['bytes']
                    with st.spinner("Processing your move..."):
                        move_text = transcribe_audio(audio_bytes)
                        if move_text:
                            st.info(f"Heard: '{move_text}'")
                            legal_moves = game._get_all_legal_moves(game.turn)
                            parsed_move = llm_api.parse_spoken_move(move_text, legal_moves)

                            if parsed_move and parsed_move in legal_moves:
                                game.make_move_from_notation(parsed_move)
                                commentary = game.last_coach_commentary
                                if commentary:
                                    st.session_state.commentary_audio = text_to_speech(commentary)
                                st.rerun()
                            else:
                                st.error("Could not understand that move or it was illegal. Try again.")
                        else:
                            st.error("Could not hear you clearly. Please speak closer to the microphone.")
            else:
                st.write("It's not your turn to speak a move.")

            # --- POST-GAME ANALYSIS SECTION ---
            if game.game_over and game.game_data:
                st.subheader("Post-Game Analysis")
                df = pd.DataFrame(game.game_data)
                
                if st.button("Analyze Game with RAG", use_container_width=True):
                    game_id = f"game_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}"
                    df.to_csv(f"{game_id}.csv", index=False)
                    graph_file, image_file = run_full_rag_pipeline(df, game_id)
                    if graph_file and image_file:
                        st.session_state.analysis_game_id = game_id
                        st.session_state.active_page = "Chess Analyzer"
                        st.rerun()
                
                if st.button("Generate Win Probability Chart", use_container_width=True):
                    game_id = game.game_id
                    with st.spinner("Analyzing game and generating chart..."):
                        chart_path = create_win_probability_chart(df, game_id)
                        if chart_path:
                            st.session_state.win_prob_chart = chart_path
                        else:
                            st.error("Failed to generate the win probability chart.")
                    st.rerun()
                
                if st.button("Generate Material Advantage Chart", use_container_width=True):
                    game_id = game.game_id
                    with st.spinner("Calculating material and generating chart..."):
                        chart_path = create_material_advantage_chart(df, game_id)
                        if chart_path:
                            st.session_state.material_chart = chart_path
                        else:
                            st.error("Failed to generate the material advantage chart.")
                    st.rerun()
        
        # Display the generated charts if they exist
        win_chart = st.session_state.get('win_prob_chart')
        mat_chart = st.session_state.get('material_chart')

        if win_chart or mat_chart:
            st.markdown("---") # Visual separator
            st.subheader("Game Visualizations")
        
        if win_chart and mat_chart:
            chart_col1, chart_col2 = st.columns(2)
            with chart_col1:
                st.image(win_chart, caption="Win Probability Chart")
            with chart_col2:
                st.image(mat_chart, caption="Material Advantage Chart")
        elif win_chart:
            st.image(win_chart, caption="Win Probability Chart")
        elif mat_chart:
            st.image(mat_chart, caption="Material Advantage Chart")


@st.cache_resource
def load_retriever(game_id):
    """Loads the retriever for a specific game_id."""
    graph_filename = f"{game_id}.graph"
    if not os.path.exists(graph_filename):
        st.error(f"Graph file for '{game_id}' not found. Please play a game and click 'Analyze This Game' first.")
        return None
    try:
        graph_retriever = GraphRetriever(graph_path=graph_filename)
        multi_hop_retriever = MultiHopRetriever(graph_retriever)
        return multi_hop_retriever
    except Exception as e:
        st.error(f"An error occurred while loading the system: {e}")
        return None

def show_analyzer_page():
    st.header("♟️ Chess Game RAG Analyzer")
    
    if 'analysis_game_id' not in st.session_state:
        st.info("Play a chess game to completion and click 'Analyze This Game' to use this feature.")
        if st.button("Go to Chess Game"):
            st.session_state.active_page = "Play Chess"
            st.rerun()
        return

    game_id = st.session_state.analysis_game_id
    st.subheader(f"Analyzing Game: `{game_id}`")
    
    retriever = load_retriever(game_id)
    
    if retriever:
        if "messages" not in st.session_state or st.session_state.get('last_analyzed_id') != game_id:
            st.session_state.messages = []
            st.session_state.last_analyzed_id = game_id

        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"], unsafe_allow_html=True)

        if prompt := st.chat_input("Ask a question about the chess game..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Analyzing the game..."):
                    final_answer, reasoning_trace = retriever.retrieve(prompt)
                    
                    st.markdown(final_answer)

                    with st.expander("Show Reasoning Trace and Knowledge Graph"):
                        st.text_area("Trace", reasoning_trace, height=200)
                        image_path = f"{game_id}_knowledge_graph.png"
                        if os.path.exists(image_path):
                            image = Image.open(image_path)
                            st.image(image, caption="Knowledge Graph Visualization")

                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": final_answer
                    })
    else:
        st.warning("Retriever could not be loaded. Ensure the data pipeline ran successfully.")


#--- MAIN APP LOGIC ---
st.set_page_config(page_title="Game Arcade & Analyzer", layout="wide")
st.title("Game Arcade & Analyzer")

st.sidebar.header("Navigation")
if 'active_page' not in st.session_state:
    st.session_state.active_page = "Home"

PAGES = ["Home", "Play Chess", "Chess Analyzer"]
st.session_state.active_page = st.sidebar.radio(
    "Select a page:", PAGES,
    index=PAGES.index(st.session_state.active_page)
)

if st.session_state.active_page == "Home":
    show_home_page()
elif st.session_state.active_page == "Play Chess":
    show_chess_game_page()
elif st.session_state.active_page == "Chess Analyzer":
    show_analyzer_page()

st.sidebar.header("About")
st.sidebar.info("Play a game of chess against an AI, then use a GraphRAG pipeline to ask complex questions about the match.")


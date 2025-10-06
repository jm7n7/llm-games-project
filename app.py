#--- imports----------
import streamlit as st
from chess_logic import ChessGame 
from connect4 import play_four_in_a_row
from scrabble import play_letter_tile_game
from mancala import play_mancala
from PIL import Image, ImageDraw, ImageFont
from streamlit_image_coordinates import streamlit_image_coordinates
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

# --- CHESS HELPER FUNCTIONS ---
@st.cache_data
def load_piece_images():
    """Loads all piece images from the assets folder."""
    images = {}
    for filename in os.listdir("assets"):
        if filename.endswith(".png"):
            # Use the filename (e.g., "w_king.png") as the key
            images[filename] = Image.open(os.path.join("assets", filename)).convert("RGBA")
    return images

def draw_chess_board_pil(piece_images):
    """Renders the chessboard using the Pillow library and piece images."""
    board = st.session_state.chess_game.board
    game = st.session_state.chess_game
    player_color = st.session_state.get('player_color', 'white')

    # --- Constants ---
    SQUARE_SIZE = 80
    BOARD_SIZE = 8 * SQUARE_SIZE
    BORDER_SIZE = 25
    IMG_SIZE = BOARD_SIZE + 2 * BORDER_SIZE
    
    # --- Colors (RGBA tuples for transparency) ---
    COLOR_LIGHT = "#F0D9B5"
    COLOR_DARK = "#4A4A4A"
    COLOR_BORDER = "#3C3A38"
    COLOR_COORD = "#E2E1E1"
    COLOR_SELECTED = (100, 149, 237, 178) 
    COLOR_VALID_MOVE = (144, 238, 144, 153)
    COLOR_CHECK = (255, 0, 0, 178)

    img = Image.new("RGBA", (IMG_SIZE, IMG_SIZE), COLOR_BORDER)
    draw = ImageDraw.Draw(img)

    try:
        coord_font = ImageFont.truetype("DejaVuSans.ttf", 14)
    except IOError:
        coord_font = ImageFont.load_default()

    # --- Draw squares and pieces from player's perspective ---
    for draw_r in range(8):
        for draw_c in range(8):
            board_r = 7 - draw_r if player_color == 'black' else draw_r
            board_c = 7 - draw_c if player_color == 'black' else draw_c
            
            x0 = BORDER_SIZE + draw_c * SQUARE_SIZE
            y0 = BORDER_SIZE + draw_r * SQUARE_SIZE
            color = COLOR_LIGHT if (draw_r + draw_c) % 2 == 0 else COLOR_DARK
            draw.rectangle([x0, y0, x0 + SQUARE_SIZE, y0 + SQUARE_SIZE], fill=color)

            piece = board.get_piece((board_r, board_c))
            if piece:
                piece_img = piece_images.get(piece.image_name)
                if piece_img:
                    resized_img = piece_img.resize((SQUARE_SIZE, SQUARE_SIZE), Image.Resampling.LANCZOS)
                    img.paste(resized_img, (x0, y0), resized_img)

    # --- Overlay for highlights (coordinates must be converted) ---
    overlay = Image.new("RGBA", img.size, (0,0,0,0))
    draw_overlay = ImageDraw.Draw(overlay)

    king_pos = game.board.find_king(game.turn)
    if king_pos and game.is_in_check(game.turn):
        board_r, board_c = king_pos
        draw_r = 7 - board_r if player_color == 'black' else board_r
        draw_c = 7 - board_c if player_color == 'black' else board_c
        x0 = BORDER_SIZE + draw_c * SQUARE_SIZE
        y0 = BORDER_SIZE + draw_r * SQUARE_SIZE
        draw_overlay.rectangle([x0, y0, x0 + SQUARE_SIZE, y0 + SQUARE_SIZE], fill=COLOR_CHECK)

    if st.session_state.selected_square:
        board_r, board_c = st.session_state.selected_square
        draw_r = 7 - board_r if player_color == 'black' else board_r
        draw_c = 7 - board_c if player_color == 'black' else board_c
        x0 = BORDER_SIZE + draw_c * SQUARE_SIZE
        y0 = BORDER_SIZE + draw_r * SQUARE_SIZE
        draw_overlay.rectangle([x0, y0, x0 + SQUARE_SIZE, y0 + SQUARE_SIZE], fill=COLOR_SELECTED)
        
        selected_piece = board.get_piece(st.session_state.selected_square)
        if selected_piece and selected_piece.color == game.turn:
            valid_moves = [m for m in selected_piece.get_valid_moves(board) if not game.move_puts_king_in_check(st.session_state.selected_square, m)]
            for move_br, move_bc in valid_moves:
                move_dr = 7 - move_br if player_color == 'black' else move_br
                move_dc = 7 - move_bc if player_color == 'black' else move_bc
                mx = BORDER_SIZE + move_dc * SQUARE_SIZE
                my = BORDER_SIZE + move_dr * SQUARE_SIZE
                draw_overlay.ellipse([mx+25, my+25, mx+SQUARE_SIZE-25, my+SQUARE_SIZE-25], fill=COLOR_VALID_MOVE)
    
    img = Image.alpha_composite(img, overlay)

    # --- Draw coordinates from player's perspective ---
    final_draw = ImageDraw.Draw(img)
    files = "abcdefgh"
    for i in range(8):
        file_char = files[i] if player_color == 'white' else files[7-i]
        rank_char = str(8 - i) if player_color == 'white' else str(i + 1)

        final_draw.text((BORDER_SIZE + i * SQUARE_SIZE + SQUARE_SIZE / 2, IMG_SIZE - BORDER_SIZE + 12), file_char, font=coord_font, fill=COLOR_COORD, anchor="ms")
        final_draw.text((BORDER_SIZE - 15, BORDER_SIZE + i * SQUARE_SIZE + SQUARE_SIZE / 2), rank_char, font=coord_font, fill=COLOR_COORD, anchor="rm")
        
    return img

def handle_chess_click(coords):
    SQUARE_SIZE, BORDER_SIZE = 80, 25
    draw_c = (coords['x'] - BORDER_SIZE) // SQUARE_SIZE
    draw_r = (coords['y'] - BORDER_SIZE) // SQUARE_SIZE

    player_color = st.session_state.get('player_color', 'white')

    # Convert screen coordinates to board coordinates based on player perspective
    if player_color == 'black':
        r = 7 - draw_r
        c = 7 - draw_c
    else:
        r = draw_r
        c = draw_c
    
    pos = (r, c)

    if not (0 <= r < 8 and 0 <= c < 8) or st.session_state.chess_game.game_over:
        return

    game = st.session_state.chess_game
    selected_piece = game.board.get_piece(st.session_state.selected_square) if st.session_state.selected_square else None
    clicked_piece = game.board.get_piece(pos)

    if selected_piece:
        success, message = game.make_move(st.session_state.selected_square, pos)
        st.session_state.selected_square = None 
        if not success:
             if clicked_piece and clicked_piece.color == game.turn:
                 st.session_state.selected_square = pos
             elif message != "Invalid move for this piece.":
                 st.toast(message, icon="⚠️")
    elif clicked_piece and clicked_piece.color == game.turn:
        st.session_state.selected_square = pos
    else:
        st.session_state.selected_square = None

#--- MAIN CONTENT AREA ROUTER -----------------------------------------------
if game_selection == "Home":
    st.header("Welcome to the Game Arcade!")
    st.info("Select a game from the sidebar on the left to start playing.")
    st.markdown("This app is a collection of classic board and word games built from scratch. Enjoy your stay!")

elif game_selection == "Chess":
    st.header("Chess")

    if 'chess_game' not in st.session_state:
        st.session_state.chess_game = ChessGame()
        st.session_state.selected_square = None
        st.session_state.last_click = None
        st.session_state.chess_game_phase = 'color_selection'
        st.session_state.player_color = 'white' # Default

    # --- COLOR SELECTION PHASE ---
    if st.session_state.get('chess_game_phase') == 'color_selection':
        st.subheader("Choose Your Color")
        c1, c2, c3 = st.columns([2,1,2])
        with c2:
            if st.button("Play as White", use_container_width=True):
                st.session_state.player_color = 'white'
                st.session_state.chess_game_phase = 'playing'
                st.rerun()
            if st.button("Play as Black", use_container_width=True):
                st.session_state.player_color = 'black'
                st.session_state.chess_game_phase = 'playing'
                st.rerun()

    # --- PLAYING PHASE ---
    elif st.session_state.get('chess_game_phase') == 'playing':
        try:
            piece_images = load_piece_images()
            if not piece_images:
                 st.error("The `assets` folder is empty or does not exist. Please create it and add the required piece images.")
                 st.stop()
        except FileNotFoundError:
            st.error("Could not find the `assets` folder. Please create it and add the piece images.")
            st.stop()

        game = st.session_state.chess_game
        col1, col2 = st.columns([2, 1])
        
        with col1:
            board_image = draw_chess_board_pil(piece_images)
            value = streamlit_image_coordinates(board_image, key="chess_board")
            
            if value and value != st.session_state.get('last_click'):
                st.session_state.last_click = value
                handle_chess_click(value)
                st.rerun()

        with col2:
            st.subheader("Game Info")
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
                height=400,
                key="move_history"
            )

elif game_selection == "Four-in-a-row":
    play_four_in_a_row()

elif game_selection == "Letter-Tile-Game":
    play_letter_tile_game()

elif game_selection == "Mancala":
    play_mancala()

#--- ABOUT SECTION IN SIDEBAR-------------
st.sidebar.header("About")
st.sidebar.info("This is a collection of simple games built using Streamlit.")


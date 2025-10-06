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
    
    # --- Constants ---
    SQUARE_SIZE = 80
    BOARD_SIZE = 8 * SQUARE_SIZE
    BORDER_SIZE = 25
    IMG_SIZE = BOARD_SIZE + 2 * BORDER_SIZE
    
    # --- Colors (RGBA tuples for transparency) ---
    COLOR_LIGHT = "#F0D9B5"
    COLOR_DARK = "#B58863"
    COLOR_BORDER = "#3C3A38"
    COLOR_COORD = "#E2E1E1"
    COLOR_SELECTED = (100, 149, 237, 178) 
    COLOR_VALID_MOVE = (144, 238, 144, 153)
    COLOR_CHECK = (255, 0, 0, 178)

    # --- Create a new image in RGBA mode to support transparency ---
    img = Image.new("RGBA", (IMG_SIZE, IMG_SIZE), COLOR_BORDER)
    draw = ImageDraw.Draw(img)

    try:
        coord_font = ImageFont.truetype("DejaVuSans.ttf", 14)
    except IOError:
        coord_font = ImageFont.load_default()

    # --- Draw squares and pieces ---
    for r in range(8):
        for c in range(8):
            x0, y0 = BORDER_SIZE + c * SQUARE_SIZE, BORDER_SIZE + r * SQUARE_SIZE
            color = COLOR_LIGHT if (r + c) % 2 == 0 else COLOR_DARK
            draw.rectangle([x0, y0, x0 + SQUARE_SIZE, y0 + SQUARE_SIZE], fill=color)

            piece = board.get_piece((r, c))
            if piece:
                piece_img = piece_images.get(piece.image_name)
                if piece_img:
                    # Resize image to fit square
                    resized_img = piece_img.resize((SQUARE_SIZE, SQUARE_SIZE), Image.Resampling.LANCZOS)
                    # Paste with transparency mask
                    img.paste(resized_img, (x0, y0), resized_img)

    # --- Overlay for highlights ---
    overlay = Image.new("RGBA", img.size, (0,0,0,0))
    draw_overlay = ImageDraw.Draw(overlay)

    # Highlight king in check
    king_pos = game.board.find_king(game.turn)
    if king_pos and game.is_in_check(game.turn):
        r, c = king_pos
        x0, y0 = BORDER_SIZE + c * SQUARE_SIZE, BORDER_SIZE + r * SQUARE_SIZE
        draw_overlay.rectangle([x0, y0, x0 + SQUARE_SIZE, y0 + SQUARE_SIZE], fill=COLOR_CHECK)

    # Highlight selected square and valid moves
    if st.session_state.selected_square:
        r, c = st.session_state.selected_square
        x0, y0 = BORDER_SIZE + c * SQUARE_SIZE, BORDER_SIZE + r * SQUARE_SIZE
        draw_overlay.rectangle([x0, y0, x0 + SQUARE_SIZE, y0 + SQUARE_SIZE], fill=COLOR_SELECTED)
        
        selected_piece = board.get_piece(st.session_state.selected_square)
        if selected_piece and selected_piece.color == game.turn:
            valid_moves = [m for m in selected_piece.get_valid_moves(board) if not game.move_puts_king_in_check(st.session_state.selected_square, m)]
            for move_r, move_c in valid_moves:
                mx, my = BORDER_SIZE + move_c * SQUARE_SIZE, BORDER_SIZE + move_r * SQUARE_SIZE
                draw_overlay.ellipse([mx+25, my+25, mx+SQUARE_SIZE-25, my+SQUARE_SIZE-25], fill=COLOR_VALID_MOVE)
    
    # Composite the overlay onto the main image
    img = Image.alpha_composite(img, overlay)

    # --- Draw coordinates ---
    final_draw = ImageDraw.Draw(img)
    files = "abcdefgh"
    for i in range(8):
        final_draw.text((BORDER_SIZE + i * SQUARE_SIZE + SQUARE_SIZE / 2, IMG_SIZE - BORDER_SIZE + 5), files[i], font=coord_font, fill=COLOR_COORD, anchor="ms")
        final_draw.text((BORDER_SIZE - 10, BORDER_SIZE + i * SQUARE_SIZE + SQUARE_SIZE / 2), str(8 - i), font=coord_font, fill=COLOR_COORD, anchor="rm")
        
    return img

def handle_chess_click(coords):
    SQUARE_SIZE, BORDER_SIZE = 80, 25
    c = (coords['x'] - BORDER_SIZE) // SQUARE_SIZE
    r = (coords['y'] - BORDER_SIZE) // SQUARE_SIZE
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

    try:
        piece_images = load_piece_images()
        if not piece_images:
             st.error("The `assets` folder is empty or does not exist. Please create it and add the required piece images.")
             st.stop()
    except FileNotFoundError:
        st.error("Could not find the `assets` folder. Please create it and add the piece images.")
        st.stop()


    if 'chess_game' not in st.session_state:
        st.session_state.chess_game = ChessGame()
        st.session_state.selected_square = None
        st.session_state.last_click = None

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


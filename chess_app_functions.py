import os
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from streamlit_image_coordinates import streamlit_image_coordinates
import time # Added for potential future pulsing, though not used for static color

def load_piece_images():
    """Loads all piece images from the assets folder."""
    images = {}
    # A simple check for the assets folder
    if not os.path.exists("assets"):
        return None
    for filename in os.listdir("assets"):
        if filename.endswith(".png"):
            images[filename] = Image.open(os.path.join("assets", filename)).convert("RGBA")
    return images

def draw_chess_board_pil(piece_images, is_opponent_thinking=False):
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
    
    # --- Modified Border ---
    COLOR_BORDER_DEFAULT = "#3C3A38"
    COLOR_BORDER_THINKING = "#EBD453" # Bright "thinking" yellow
    COLOR_BORDER = COLOR_BORDER_THINKING if is_opponent_thinking else COLOR_BORDER_DEFAULT
    
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
            if piece and piece.image_name in piece_images:
                # --- FIX: Changed 'filename' to 'piece.image_name' ---
                piece_img = piece_images[piece.image_name].resize((SQUARE_SIZE, SQUARE_SIZE), Image.Resampling.LANCZOS)
                img.paste(piece_img, (x0, y0), piece_img)

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
            # Pass the 'game' object to get_valid_moves to check for en passant
            valid_moves = [m for m in selected_piece.get_valid_moves(board, game) if not game.move_puts_king_in_check(st.session_state.selected_square, m)]
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

def get_click_board_coords(coords):
    """Helper function to convert x,y click to board (r, c)"""
    SQUARE_SIZE, BORDER_SIZE = 80, 25
    if not coords:
        return None
        
    draw_c = (coords['x'] - BORDER_SIZE) // SQUARE_SIZE
    draw_r = (coords['y'] - BORDER_SIZE) // SQUARE_SIZE

    player_color = st.session_state.get('player_color', 'white')

    # Convert screen coordinates to board coordinates
    if player_color == 'black':
        r = 7 - draw_r
        c = 7 - draw_c
    else:
        r = draw_r
        c = draw_c
    
    return (r, c)


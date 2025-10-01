#--- imports----------
import streamlit as st
import chess
import chess.pgn
import chess.svg
import numpy as np
import random
import string

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

#--- MAIN CONTENT AREA ----------------------------------------------------
if game_selection == "Home":
    st.header("Welcome to the Game Arcade!")
    st.info("Select a game from the sidebar on the left to start playing.")
    st.markdown("""
    This app is a collection of classic board and word games.
    Enjoy your stay!
    """)

elif game_selection == "Chess":
    st.header("Chess")

    # Initialize chess game state if it doesn't exist
    if 'chess_game_phase' not in st.session_state:
        st.session_state.chess_game_phase = 'color_selection'
        st.session_state.board = chess.Board()
        st.session_state.player_color = chess.WHITE

    # --- COLOR SELECTION PHASE ---
    if st.session_state.chess_game_phase == 'color_selection':
        st.subheader("Choose Your Color")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Play as White", use_container_width=True):
                st.session_state.player_color = chess.WHITE
                st.session_state.chess_game_phase = 'playing'
                st.session_state.board.reset() # Reset board to start
                st.rerun()
        with col2:
            if st.button("Play as Black", use_container_width=True):
                st.session_state.player_color = chess.BLACK
                st.session_state.chess_game_phase = 'playing'
                st.session_state.board.reset() # Reset board to start
                st.rerun()

    # --- PLAYING PHASE ---
    elif st.session_state.chess_game_phase == 'playing':
        # Display the current board state as an SVG image, oriented to the player's color.
        board_svg = chess.svg.board(st.session_state.board, orientation=st.session_state.player_color)
        st.image(board_svg)

        # Get legal moves for the current player
        legal_moves = list(st.session_state.board.legal_moves)

        # Check if the game is over to avoid showing the move selection
        if not st.session_state.board.is_game_over():
            # Convert moves to Standard Algebraic Notation (SAN) for the dropdown
            san_moves = [st.session_state.board.san(move) for move in legal_moves]

            with st.form("move_form", clear_on_submit=True):
                selected_san_move = st.selectbox("Choose your move:", options=san_moves)
                submitted = st.form_submit_button("Make Move")

            if submitted and selected_san_move:
                # Find the original move object from the selected SAN string
                move_to_make = legal_moves[san_moves.index(selected_san_move)]
                st.session_state.board.push(move_to_make)
                st.rerun()

        # Display game status
        st.subheader("Game Status")
        if st.session_state.board.is_checkmate():
            st.success(f"Checkmate! Winner is {'White' if st.session_state.board.turn == chess.BLACK else 'Black'}.")
        elif st.session_state.board.is_stalemate():
            st.warning("Stalemate!")
        elif st.session_state.board.is_insufficient_material():
            st.info("Draw by insufficient material.")
        elif st.session_state.board.is_seventyfive_moves():
            st.info("Draw by 75-move rule.")
        elif st.session_state.board.is_fivefold_repetition():
            st.info("Draw by fivefold repetition.")
        else:
            turn = "White" if st.session_state.board.turn == chess.WHITE else "Black"
            st.write(f"It's **{turn}'s** turn to move.")

        # Add a button to reset the game
        if st.button("New Game"):
            st.session_state.chess_game_phase = 'color_selection'
            st.rerun()

        # Display the move history in PGN format
        st.subheader("Move History (PGN)")
        pgn = chess.pgn.Game.from_board(st.session_state.board)
        st.text_area("PGN", str(pgn), height=150)


elif game_selection == "Four-in-a-row":
    st.header("Four-in-a-row (Connect-4)")

    # --- CONNECT 4 GAME LOGIC ---
    ROWS, COLS = 6, 7
    PLAYER_1, PLAYER_2 = 1, 2

    # Initialize game state
    if 'c4_board' not in st.session_state:
        st.session_state.c4_board = np.zeros((ROWS, COLS), dtype=int)
        st.session_state.c4_turn = PLAYER_1
        st.session_state.c4_winner = None

    def check_c4_winner(board):
        # Check horizontal
        for r in range(ROWS):
            for c in range(COLS - 3):
                if board[r, c] == board[r, c+1] == board[r, c+2] == board[r, c+3] != 0:
                    return board[r, c]
        # Check vertical
        for c in range(COLS):
            for r in range(ROWS - 3):
                if board[r, c] == board[r+1, c] == board[r+2, c] == board[r+3, c] != 0:
                    return board[r, c]
        # Check diagonal (down-right)
        for r in range(ROWS - 3):
            for c in range(COLS - 3):
                if board[r, c] == board[r+1, c+1] == board[r+2, c+2] == board[r+3, c+3] != 0:
                    return board[r, c]
        # Check diagonal (up-right)
        for r in range(3, ROWS):
            for c in range(COLS - 3):
                if board[r, c] == board[r-1, c+1] == board[r-2, c+2] == board[r-3, c+3] != 0:
                    return board[r, c]
        # Check for draw
        if np.all(board != 0):
            return "Draw"
        return None

    def make_c4_move(col):
        for r in range(ROWS - 1, -1, -1):
            if st.session_state.c4_board[r, col] == 0:
                st.session_state.c4_board[r, col] = st.session_state.c4_turn
                break
        winner = check_c4_winner(st.session_state.c4_board)
        if winner:
            st.session_state.c4_winner = winner
        else:
            st.session_state.c4_turn = PLAYER_2 if st.session_state.c4_turn == PLAYER_1 else PLAYER_1

    # --- RENDER CONNECT 4 BOARD ---
    if st.session_state.c4_winner:
        if st.session_state.c4_winner == "Draw":
            st.warning("It's a Draw!")
        else:
            st.success(f"Player {st.session_state.c4_winner} wins!")
    else:
        st.info(f"Player {st.session_state.c4_turn}'s turn")

    # Column buttons for making a move
    cols = st.columns(COLS)
    for i, col in enumerate(cols):
        with col:
            # Disable button if the column is full
            is_disabled = st.session_state.c4_board[0, i] != 0 or st.session_state.c4_winner is not None
            if st.button("↓", key=f"c4_col_{i}", use_container_width=True, disabled=is_disabled):
                make_c4_move(i)
                st.rerun()

    # Visual representation of the board
    st.markdown("""<style>.c4-board { background-color: #007bff; border-radius: 10px; padding: 10px; display: grid; grid-template-columns: repeat(7, 1fr); grid-gap: 5px; } .c4-cell { width: 50px; height: 50px; border-radius: 50%; display: flex; justify-content: center; align-items: center; } </style>""", unsafe_allow_html=True)
    board_html = "<div class='c4-board'>"
    for r in range(ROWS):
        for c in range(COLS):
            player = st.session_state.c4_board[r, c]
            if player == PLAYER_1: color = "#ff4b4b"  # Red
            elif player == PLAYER_2: color = "#ffff00" # Yellow
            else: color = "#ffffff" # White
            board_html += f"<div class='c4-cell' style='background-color: {color};'></div>"
    board_html += "</div>"
    st.markdown(board_html, unsafe_allow_html=True)


    if st.button("New Game"):
        st.session_state.c4_board = np.zeros((ROWS, COLS), dtype=int)
        st.session_state.c4_turn = PLAYER_1
        st.session_state.c4_winner = None
        st.rerun()

elif game_selection == "Letter-Tile-Game":
    st.header("Letter-Tile-Game (Scrabble)")

    # --- SCRABBLE CONSTANTS AND SETUP ---
    BOARD_SIZE = 15
    TILE_SCORES = {"A": 1, "B": 3, "C": 3, "D": 2, "E": 1, "F": 4, "G": 2, "H": 4, "I": 1, "J": 8, "K": 5, "L": 1, "M": 3, "N": 1, "O": 1, "P": 3, "Q": 10, "R": 1, "S": 1, "T": 1, "U": 1, "V": 4, "W": 4, "X": 8, "Y": 4, "Z": 10}
    TILE_DISTRIBUTION = "A"*9 + "B"*2 + "C"*2 + "D"*4 + "E"*12 + "F"*2 + "G"*3 + "H"*2 + "I"*9 + "J"*1 + "K"*1 + "L"*4 + "M"*2 + "N"*6 + "O"*8 + "P"*2 + "Q"*1 + "R"*6 + "S"*4 + "T"*6 + "U"*4 + "V"*2 + "W"*2 + "X"*1 + "Y"*2 + "Z"*1
    # Expanded dictionary for validation
    VALID_WORDS = {
        "streamlit", "python", "code", "game", "play", "word", "tile", "board", "score", "win", "fun", "hello",
        "apple", "banana", "cherry", "date", "fig", "grape", "kiwi", "lemon", "mango", "orange", "peach",
        "pear", "plum", "cat", "dog", "house", "tree", "sun", "moon", "star", "earth", "water", "fire", "air",
        "love", "hate", "happy", "sad", "big", "small", "fast", "slow", "hot", "cold", "red", "blue", "green",
        "yellow", "purple", "black", "white", "brown", "pink", "run", "walk", "jump", "swim", "fly", "eat",
        "drink", "sleep", "dream", "think", "learn", "teach", "read", "write", "listen", "speak", "sing",
        "dance", "work", "rest", "slide", "ace", "ape", "art", "bag", "bat", "bed", "bee", "box", "boy", "bun",
        "bus", "can", "cap", "car", "cow", "cup", "cut", "day", "die", "dig", "dot", "dry", "due", "ear", "egg",
        "fan", "far", "fat", "fee", "fin", "fit", "fix", "fly", "fog", "for", "fox", "fun", "fur", "gap", "gas",
        "gem", "get", "god", "gum", "gun", "guy", "hat", "hen", "hip", "hit", "hot", "how", "hug", "hum", "hut",
        "ice", "ill", "ink", "jar", "jaw", "jet", "job", "joy", "jug", "key", "kid", "kin", "kit", "lab", "lap",
        "law", "leg", "let", "lid", "lip", "log", "lot", "low", "mad", "man", "map", "mat", "men", "mix", "mom",
        "mud", "mug", "nap", "net", "new", "nod", "not", "now", "nun", "nut", "oak", "oar", "odd", "off", "oil",
        "old", "one", "our", "out", "owl", "own", "pad", "pal", "pan", "pat", "pay", "pea", "peg", "pen", "pet",
        "pie", "pig", "pin", "pit", "pod", "pop", "pot", "pro", "put", "rag", "ram", "ran", "rat", "raw", "ray",
        "red", "rib", "rid", "rig", "rim", "rip", "rob", "rod", "rot", "row", "rub", "rug", "rum", "run", "rye",
        "sad", "sag", "sap", "sat", "saw", "say", "sea", "see", "set", "sew", "she", "shy", "sin", "sip", "sir",
        "sit", "six", "ski", "sky", "sly", "sob", "sod", "son", "sow", "soy", "spa", "spy", "sub", "sue", "sum",
        "sun", "tab", "tag", "tan", "tap", "tar", "tax", "tea", "ten", "the", "tie", "tin", "tip", "toe", "ton",
        "top", "toy", "try", "tub", "tug", "two", "use", "van", "vat", "vet", "war", "was", "wax", "way", "web",
        "wed", "wet", "who", "why", "wig", "win", "wit", "woe", "won", "wow", "yak", "yam", "yap", "yaw", "yes",
        "yet", "you", "zap", "zen", "zig", "zip", "zoo"
    }

    PREMIUM_SQUARES = {
        (0,0): "TW", (0,7): "TW", (0,14): "TW", (7,0): "TW", (7,14): "TW", (14,0): "TW", (14,7): "TW", (14,14): "TW",
        (1,1): "DW", (2,2): "DW", (3,3): "DW", (4,4): "DW", (1,13): "DW", (2,12): "DW", (3,11): "DW", (4,10): "DW",
        (10,4): "DW", (11,3): "DW", (12,2): "DW", (13,1): "DW", (10,10): "DW", (11,11): "DW", (12,12): "DW", (13,13): "DW", (7,7): "DW",
        (0,3): "DL", (0,11): "DL", (2,6): "DL", (2,8): "DL", (3,0): "DL", (3,7): "DL", (3,14): "DL", (6,2): "DL", (6,6): "DL", (6,8): "DL", (6,12): "DL",
        (7,3): "DL", (7,11): "DL", (8,2): "DL", (8,6): "DL", (8,8): "DL", (8,12): "DL", (11,0): "DL", (11,7): "DL", (11,14): "DL", (12,6): "DL", (12,8): "DL", (14,3): "DL", (14,11): "DL",
        (1,5): "TL", (1,9): "TL", (5,1): "TL", (5,5): "TL", (5,9): "TL", (5,13): "TL",
        (9,1): "TL", (9,5): "TL", (9,9): "TL", (9,13): "TL", (13,5): "TL", (13,9): "TL"
    }

    def initialize_scrabble():
        st.session_state.scrabble_board = np.full((BOARD_SIZE, BOARD_SIZE), " ", dtype=str)
        st.session_state.tile_bag = list(TILE_DISTRIBUTION)
        random.shuffle(st.session_state.tile_bag)
        st.session_state.player_tiles = [st.session_state.tile_bag.pop() for _ in range(7)]
        st.session_state.player_score = 0
        st.session_state.scrabble_message = "First word must cover the center square (H8)."
        st.session_state.is_first_move = True

    if 'scrabble_board' not in st.session_state:
        initialize_scrabble()


    def play_word(word, row, col, direction):
        # Basic validation
        word = word.upper()
        if word.lower() not in VALID_WORDS:
            st.session_state.scrabble_message = f"'{word}' is not in our dictionary."
            return

        temp_tiles = st.session_state.player_tiles.copy()
        word_score = 0
        word_multiplier = 1
        
        # Check if player has the tiles and calculate score
        for i, letter in enumerate(word):
            r, c = (row, col + i) if direction == "Across" else (row + i, col)
            if not (0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE):
                st.session_state.scrabble_message = "Word goes off the board."
                return
            
            if st.session_state.scrabble_board[r,c] == " ": # If square is empty
                if letter not in temp_tiles:
                    st.session_state.scrabble_message = f"You do not have the tile: {letter}"
                    return
                
                temp_tiles.remove(letter)
                letter_score = TILE_SCORES[letter]
                square = PREMIUM_SQUARES.get((r,c))
                if square == "DL": letter_score *= 2
                if square == "TL": letter_score *= 3
                if square == "DW": word_multiplier *= 2
                if square == "TW": word_multiplier *= 3
                word_score += letter_score
            else: # Square is not empty, must match letter
                if st.session_state.scrabble_board[r,c] != letter:
                    st.session_state.scrabble_message = "Word placement conflicts with existing tiles."
                    return
                word_score += TILE_SCORES[letter] # Add score of existing tile

        # First move check
        if st.session_state.is_first_move:
            center_covered = False
            for i in range(len(word)):
                r, c = (row, col + i) if direction == "Across" else (row + i, col)
                if r == 7 and c == 7:
                    center_covered = True
                    break
            if not center_covered:
                st.session_state.scrabble_message = "First word must cover the center square (H8)."
                return
            st.session_state.is_first_move = False

        word_score *= word_multiplier
        st.session_state.player_score += word_score

        # Place word on board
        for i, letter in enumerate(word):
            r, c = (row, col + i) if direction == "Across" else (row + i, col)
            st.session_state.scrabble_board[r, c] = letter
        
        # Update player tiles
        st.session_state.player_tiles = temp_tiles
        draw_count = 7 - len(st.session_state.player_tiles)
        for _ in range(draw_count):
            if st.session_state.tile_bag:
                st.session_state.player_tiles.append(st.session_state.tile_bag.pop())

        st.session_state.scrabble_message = f"You played '{word}' for {word_score} points!"

    # --- RENDER SCRABBLE GAME ---
    st.info(st.session_state.scrabble_message)
    st.subheader(f"Score: {st.session_state.player_score}")

    # Display Board
    board_html = "<table style='border-collapse: collapse;'>"
    for r in range(BOARD_SIZE):
        board_html += "<tr>"
        for c in range(BOARD_SIZE):
            letter = st.session_state.scrabble_board[r, c]
            text = letter if letter != " " else ""
            color = "#F0EAD6" # Beige for normal squares
            premium = PREMIUM_SQUARES.get((r,c))
            if premium == "TW": color = "#FF4B4B" # Red
            elif premium == "DW": color = "#FFDDC1" # Pink
            elif premium == "TL": color = "#4B8BFF" # Blue
            elif premium == "DL": color = "#A2D2FF" # Light Blue
            if r==7 and c==7 and text=="": text = "★" # Center Star

            board_html += f"<td style='border: 1px solid #ccc; width: 30px; height: 30px; text-align: center; background-color: {color}; font-weight: bold;'>{text}</td>"
        board_html += "</tr>"
    board_html += "</table>"
    st.markdown(board_html, unsafe_allow_html=True)

    # Player Hand
    st.subheader("Your Tiles:")
    tile_cols = st.columns(7)
    for i, tile in enumerate(st.session_state.player_tiles):
        tile_cols[i].markdown(f"<div style='border: 2px solid #555; padding: 10px; border-radius: 5px; text-align: center; font-size: 1.5em; background-color: #F0EAD6;'>{tile}</div>", unsafe_allow_html=True)

    # Move Submission Form
    with st.form("scrabble_move_form", clear_on_submit=True):
        word = st.text_input("Word:")
        row = st.selectbox("Row:", options=list(string.ascii_uppercase[:BOARD_SIZE]), format_func=lambda x: f"Row {x}")
        col = st.number_input("Column:", min_value=1, max_value=BOARD_SIZE, step=1)
        direction = st.radio("Direction:", ("Across", "Down"), horizontal=True)
        play_button = st.form_submit_button("Play Word")

    if play_button and word:
        row_idx = string.ascii_uppercase.index(row)
        col_idx = col - 1
        play_word(word, row_idx, col_idx, direction)
        st.rerun()

    if st.button("New Game"):
        initialize_scrabble()
        st.rerun()


elif game_selection == "Mancala":
    st.header("Mancala")

    # --- MANCALA GAME LOGIC ---
    PLAYER_1, PLAYER_2 = "Player 1", "Player 2"
    P1_MANCALA, P2_MANCALA = 6, 13

    # Initialize game state
    if 'mancala_board' not in st.session_state:
        st.session_state.mancala_board = [4, 4, 4, 4, 4, 4, 0, 4, 4, 4, 4, 4, 4, 0]
        st.session_state.mancala_turn = PLAYER_1
        st.session_state.mancala_winner = None
        st.session_state.mancala_message = ""

    def make_mancala_move(pit_index):
        stones = st.session_state.mancala_board[pit_index]
        if stones == 0:
            st.session_state.mancala_message = "Cannot move from an empty pit."
            return

        st.session_state.mancala_board[pit_index] = 0
        current_pit = pit_index
        while stones > 0:
            current_pit = (current_pit + 1) % 14
            # Skip opponent's mancala
            if (st.session_state.mancala_turn == PLAYER_1 and current_pit == P2_MANCALA) or \
               (st.session_state.mancala_turn == PLAYER_2 and current_pit == P1_MANCALA):
                continue
            st.session_state.mancala_board[current_pit] += 1
            stones -= 1

        # Capture rule
        if (st.session_state.mancala_turn == PLAYER_1 and 0 <= current_pit <= 5 and st.session_state.mancala_board[current_pit] == 1):
            opposite_pit = 12 - current_pit
            if st.session_state.mancala_board[opposite_pit] > 0:
                captured_stones = st.session_state.mancala_board[opposite_pit] + 1
                st.session_state.mancala_board[opposite_pit] = 0
                st.session_state.mancala_board[current_pit] = 0
                st.session_state.mancala_board[P1_MANCALA] += captured_stones
                st.session_state.mancala_message = f"Player 1 captured {captured_stones} stones!"

        if (st.session_state.mancala_turn == PLAYER_2 and 7 <= current_pit <= 12 and st.session_state.mancala_board[current_pit] == 1):
            opposite_pit = 12 - current_pit
            if st.session_state.mancala_board[opposite_pit] > 0:
                captured_stones = st.session_state.mancala_board[opposite_pit] + 1
                st.session_state.mancala_board[opposite_pit] = 0
                st.session_state.mancala_board[current_pit] = 0
                st.session_state.mancala_board[P2_MANCALA] += captured_stones
                st.session_state.mancala_message = f"Player 2 captured {captured_stones} stones!"


        # Check for game end
        p1_pits_empty = all(s == 0 for s in st.session_state.mancala_board[0:6])
        p2_pits_empty = all(s == 0 for s in st.session_state.mancala_board[7:13])

        if p1_pits_empty or p2_pits_empty:
            # Collect remaining stones
            st.session_state.mancala_board[P1_MANCALA] += sum(st.session_state.mancala_board[0:6])
            st.session_state.mancala_board[P2_MANCALA] += sum(st.session_state.mancala_board[7:13])
            for i in range(6): st.session_state.mancala_board[i] = 0
            for i in range(7, 13): st.session_state.mancala_board[i] = 0

            # Determine winner
            p1_score = st.session_state.mancala_board[P1_MANCALA]
            p2_score = st.session_state.mancala_board[P2_MANCALA]
            if p1_score > p2_score: st.session_state.mancala_winner = PLAYER_1
            elif p2_score > p1_score: st.session_state.mancala_winner = PLAYER_2
            else: st.session_state.mancala_winner = "Draw"
            return # End turn logic

        # Switch turns unless last stone landed in own mancala
        if not ((st.session_state.mancala_turn == PLAYER_1 and current_pit == P1_MANCALA) or \
                (st.session_state.mancala_turn == PLAYER_2 and current_pit == P2_MANCALA)):
            st.session_state.mancala_turn = PLAYER_2 if st.session_state.mancala_turn == PLAYER_1 else PLAYER_1
        else:
            st.session_state.mancala_message = f"{st.session_state.mancala_turn} gets another turn!"


    # --- RENDER MANCALA BOARD ---
    if st.session_state.mancala_winner:
        st.success(f"Game Over! The winner is {st.session_state.mancala_winner}!")
        st.write(f"Final Score: Player 1 ({st.session_state.mancala_board[P1_MANCALA]}) - Player 2 ({st.session_state.mancala_board[P2_MANCALA]})")
    else:
        st.info(f"It's **{st.session_state.mancala_turn}'s** turn.")
        if st.session_state.mancala_message:
            st.write(st.session_state.mancala_message)
            st.session_state.mancala_message = "" # Clear message after displaying

    mancala_col, board_cols, mancala_col_2 = st.columns([2, 6, 2])

    with mancala_col: # Player 2 Mancala
        st.header("P2")
        st.markdown(f"<div style='border: 2px solid #444; padding: 10px; border-radius: 10px; text-align: center; height: 300px; display: flex; justify-content: center; align-items: center; font-size: 2em;'>{st.session_state.mancala_board[P2_MANCALA]}</div>", unsafe_allow_html=True)

    with board_cols:
        # Player 2 Pits (top row)
        p2_cols = st.columns(6)
        for i, col in enumerate(p2_cols):
            with col:
                pit_index = 12 - i
                disabled = st.session_state.mancala_turn != PLAYER_2 or st.session_state.mancala_winner is not None
                if st.button(f"{st.session_state.mancala_board[pit_index]}", key=f"pit_{pit_index}", use_container_width=True, disabled=disabled):
                    make_mancala_move(pit_index)
                    st.rerun()

        st.markdown("<hr>", unsafe_allow_html=True)

        # Player 1 Pits (bottom row)
        p1_cols = st.columns(6)
        for i, col in enumerate(p1_cols):
            with col:
                pit_index = i
                disabled = st.session_state.mancala_turn != PLAYER_1 or st.session_state.mancala_winner is not None
                if st.button(f"{st.session_state.mancala_board[pit_index]}", key=f"pit_{pit_index}", use_container_width=True, disabled=disabled):
                    make_mancala_move(pit_index)
                    st.rerun()

    with mancala_col_2: # Player 1 Mancala
        st.header("P1")
        st.markdown(f"<div style='border: 2px solid #444; padding: 10px; border-radius: 10px; text-align: center; height: 300px; display: flex; justify-content: center; align-items: center; font-size: 2em;'>{st.session_state.mancala_board[P1_MANCALA]}</div>", unsafe_allow_html=True)


    if st.button("New Game"):
        st.session_state.mancala_board = [4, 4, 4, 4, 4, 4, 0, 4, 4, 4, 4, 4, 4, 0]
        st.session_state.mancala_turn = PLAYER_1
        st.session_state.mancala_winner = None
        st.session_state.mancala_message = ""
        st.rerun()


#--- ABOUT SECTION IN SIDEBAR-------------
st.sidebar.header("About")
st.sidebar.info(
    "This is a collection of simple games built using Streamlit."
)
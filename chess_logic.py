import uuid
import chess_llm_functions as llm_api

class Piece:
    """Base class for all chess pieces."""
    def __init__(self, color, position, name=None):
        self.color = color
        self.position = position
        self.has_moved = False
        self.symbol = 'X' # Fallback symbol
        self.name = name if name else self.__class__.__name__
        self.image_name = f"{self.color[0]}_{self.__class__.__name__.lower()}.png"

    def get_valid_moves(self, board, game=None):
        """Returns a list of valid moves for the piece."""
        raise NotImplementedError

    def get_attack_squares(self, board):
        """Returns squares this piece is attacking. For most pieces, this is the same as valid moves."""
        return self.get_valid_moves(board, None) # Pass None to avoid recursion in king's castling

    def _is_valid_and_capturable(self, pos, board):
        """Helper to check if a position is on the board and can be moved to."""
        r, c = pos
        if not (0 <= r < 8 and 0 <= c < 8):
            return False, False
        
        piece = board.get_piece(pos)
        if piece is None:
            return True, False # Empty square
        if piece.color != self.color:
            return True, True  # Can capture opponent's piece
        return False, False # Blocked by own piece

class King(Piece):
    def __init__(self, color, position, name=None):
        super().__init__(color, position, name or "King")
        self.symbol = '♔' if color == 'white' else '♚'

    def _get_castling_moves(self, board, game):
        """Returns valid castling moves for the king."""
        castling_moves = []
        if self.has_moved or game.is_in_check(self.color):
            return []

        king_row, _ = self.position
        
        # Kingside castling
        rook_k = board.get_piece((king_row, 7))
        if isinstance(rook_k, Rook) and not rook_k.has_moved:
            if board.get_piece((king_row, 5)) is None and \
               board.get_piece((king_row, 6)) is None:
                if not game.is_square_attacked((king_row, 5), 'black' if self.color == 'white' else 'white') and \
                   not game.is_square_attacked((king_row, 6), 'black' if self.color == 'white' else 'white'):
                    castling_moves.append((king_row, 6))

        # Queenside castling
        rook_q = board.get_piece((king_row, 0))
        if isinstance(rook_q, Rook) and not rook_q.has_moved:
            if board.get_piece((king_row, 1)) is None and \
               board.get_piece((king_row, 2)) is None and \
               board.get_piece((king_row, 3)) is None:
                if not game.is_square_attacked((king_row, 2), 'black' if self.color == 'white' else 'white') and \
                   not game.is_square_attacked((king_row, 3), 'black' if self.color == 'white' else 'white'):
                    castling_moves.append((king_row, 2))
        
        return castling_moves

    def get_valid_moves(self, board, game=None):
        moves = []
        r, c = self.position
        # Standard moves
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:
                    continue
                new_pos = (r + dr, c + dc)
                is_valid, _ = self._is_valid_and_capturable(new_pos, board)
                if is_valid:
                    moves.append(new_pos)
        
        # Castling moves
        if game:
            moves.extend(self._get_castling_moves(board, game))
            
        return moves
    
    def get_attack_squares(self, board):
        """For the King, attack squares do not include castling."""
        moves = []
        r, c = self.position
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:
                    continue
                new_pos = (r + dr, c + dc)
                is_valid, _ = self._is_valid_and_capturable(new_pos, board)
                if is_valid:
                    moves.append(new_pos)
        return moves


class Queen(Piece):
    def __init__(self, color, position, name=None):
        super().__init__(color, position, name or "Queen")
        self.symbol = '♕' if color == 'white' else '♛'

    def get_valid_moves(self, board, game=None):
        moves = []
        r, c = self.position
        directions = [(-1, -1), (-1, 1), (1, -1), (1, 1), (-1, 0), (1, 0), (0, -1), (0, 1)]
        for dr, dc in directions:
            for i in range(1, 8):
                new_pos = (r + i * dr, c + i * dc)
                is_valid, can_capture = self._is_valid_and_capturable(new_pos, board)
                if is_valid:
                    moves.append(new_pos)
                    if can_capture:
                        break
                else:
                    break
        return moves

class Rook(Piece):
    def __init__(self, color, position, name=None):
        super().__init__(color, position, name)
        self.symbol = '♖' if color == 'white' else '♜'

    def get_valid_moves(self, board, game=None):
        moves = []
        r, c = self.position
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        for dr, dc in directions:
            for i in range(1, 8):
                new_pos = (r + i * dr, c + i * dc)
                is_valid, can_capture = self._is_valid_and_capturable(new_pos, board)
                if is_valid:
                    moves.append(new_pos)
                    if can_capture:
                        break
                else:
                    break
        return moves

class Bishop(Piece):
    def __init__(self, color, position, name=None):
        super().__init__(color, position, name)
        self.symbol = '♗' if color == 'white' else '♝'

    def get_valid_moves(self, board, game=None):
        moves = []
        r, c = self.position
        directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        for dr, dc in directions:
            for i in range(1, 8):
                new_pos = (r + i * dr, c + i * dc)
                is_valid, can_capture = self._is_valid_and_capturable(new_pos, board)
                if is_valid:
                    moves.append(new_pos)
                    if can_capture:
                        break
                else:
                    break
        return moves

class Knight(Piece):
    def __init__(self, color, position, name=None):
        super().__init__(color, position, name)
        self.symbol = '♘' if color == 'white' else '♞'

    def get_valid_moves(self, board, game=None):
        moves = []
        r, c = self.position
        potential_moves = [
            (r-2, c-1), (r-2, c+1), (r+2, c-1), (r+2, c+1),
            (r-1, c-2), (r-1, c+2), (r+1, c-2), (r+1, c+2)
        ]
        for move in potential_moves:
            is_valid, _ = self._is_valid_and_capturable(move, board)
            if is_valid:
                moves.append(move)
        return moves

class Pawn(Piece):
    def __init__(self, color, position, name=None):
        super().__init__(color, position, name)
        self.symbol = '♙' if color == 'white' else '♟'

    def get_valid_moves(self, board, game=None):
        moves = []
        r, c = self.position
        direction = -1 if self.color == 'white' else 1

        one_step = (r + direction, c)
        if 0 <= one_step[0] < 8 and board.get_piece(one_step) is None:
            moves.append(one_step)
            if not self.has_moved:
                two_steps = (r + 2 * direction, c)
                if 0 <= two_steps[0] < 8 and board.get_piece(two_steps) is None:
                    moves.append(two_steps)
        
        for dc in [-1, 1]:
            capture_pos = (r + direction, c + dc)
            if 0 <= capture_pos[0] < 8 and 0 <= capture_pos[1] < 8:
                target_piece = board.get_piece(capture_pos)
                if target_piece and target_piece.color != self.color:
                    moves.append(capture_pos)
        
        if game and game.en_passant_target and (game.en_passant_target == (r + direction, c - 1) or \
           game.en_passant_target == (r + direction, c + 1)):
            moves.append(game.en_passant_target)
        return moves

    def get_attack_squares(self, board):
        """For Pawns, attack squares are only the diagonal captures."""
        moves = []
        r, c = self.position
        direction = -1 if self.color == 'white' else 1
        for dc in [-1, 1]:
            capture_pos = (r + direction, c + dc)
            if 0 <= capture_pos[0] < 8 and 0 <= capture_pos[1] < 8:
                moves.append(capture_pos)
        return moves


class Board:
    """Represents the chessboard and its pieces."""
    def __init__(self):
        self.grid = [[None for _ in range(8)] for _ in range(8)]
        self.setup_pieces()

    def get_piece(self, pos):
        r, c = pos
        if 0 <= r < 8 and 0 <= c < 8:
            return self.grid[r][c]
        return None

    def set_piece(self, pos, piece):
        r, c = pos
        self.grid[r][c] = piece
        if piece:
            piece.position = pos

    def move_piece(self, start_pos, end_pos):
        piece = self.get_piece(start_pos)
        if piece:
            captured_piece = self.get_piece(end_pos)
            self.set_piece(end_pos, piece)
            self.set_piece(start_pos, None)
            piece.has_moved = True
            return captured_piece
        return None
    
    def find_king(self, color):
        for r in range(8):
            for c in range(8):
                piece = self.get_piece((r, c))
                if isinstance(piece, King) and piece.color == color:
                    return (r, c)
        return None

    def setup_pieces(self):
        # Place major pieces with specific names
        for r, color in [(0, 'black'), (7, 'white')]:
            self.set_piece((r, 0), Rook(color, (r, 0), name="Q_rook"))
            self.set_piece((r, 7), Rook(color, (r, 7), name="K_rook"))
            self.set_piece((r, 1), Knight(color, (r, 1), name="Q_knight"))
            self.set_piece((r, 6), Knight(color, (r, 6), name="K_knight"))
            self.set_piece((r, 2), Bishop(color, (r, 2), name="Q_bishop"))
            self.set_piece((r, 5), Bishop(color, (r, 5), name="K_bishop"))
            self.set_piece((r, 3), Queen(color, (r, 3)))
            self.set_piece((r, 4), King(color, (r, 4)))
        
        # Place pawns with specific names
        files = "abcdefgh"
        for c in range(8):
            self.set_piece((1, c), Pawn('black', (1, c), name=f"{files[c]}_pawn"))
            self.set_piece((6, c), Pawn('white', (6, c), name=f"{files[c]}_pawn"))


class ChessGame:
    """Manages the state and logic of a chess game."""
    def __init__(self):
        self.reset_game()

    def reset_game(self):
        self.board = Board()
        self.turn = 'white'
        self.game_over = False
        self.status_message = "White's turn."
        self.move_history = []
        self.promotion_pending = None
        self.en_passant_target = None
        self.position_history = {}
        self.game_id = f"chs-{uuid.uuid4()}"
        self.game_data = []
        self._record_position()
        # --- ATTRIBUTES FOR AI COACH ---
        self.coach_chat_session = llm_api.initialize_coach_chat()
        self.last_coach_commentary = ""

    def pos_to_notation(self, pos):
        r, c = pos
        return f"{'abcdefgh'[c]}{8-r}"

    def _get_board_state_string(self):
        """Generates a unique string for the current board state."""
        state_parts = []
        for r in range(8):
            empty_count = 0
            for c in range(8):
                piece = self.board.get_piece((r, c))
                if piece:
                    if empty_count > 0:
                        state_parts.append(str(empty_count))
                        empty_count = 0
                    state_parts.append(piece.symbol)
                else:
                    empty_count += 1
            if empty_count > 0:
                state_parts.append(str(empty_count))
            state_parts.append('/')
        
        state_string = "".join(state_parts)
        state_string += f" {self.turn[0]}"
        state_string += f" {self.en_passant_target if self.en_passant_target else '-'}"
        return state_string
    
    def _record_position(self):
        """Records the current board state for repetition checks."""
        state_key = self._get_board_state_string()
        self.position_history[state_key] = self.position_history.get(state_key, 0) + 1

    def _record_move_data(self, piece, start_pos, end_pos, captured_piece, promoted_into=None):
        """Records the details of a single move into the game_data list."""
        opponent_color = 'black' if piece.color == 'white' else 'white'
        move_data = {
            'game_id': self.game_id,
            'turn': len(self.game_data) + 1,
            'color': piece.color,
            'piece_moved': piece.name,
            'start_square': self.pos_to_notation(start_pos),
            'end_square': self.pos_to_notation(end_pos),
            'capture': 1 if captured_piece else 0,
            'captured_piece': captured_piece.name if captured_piece else 'NA',
            'check': 1 if self.is_in_check(opponent_color) else 0,
            'checkmate': 1 if self.is_checkmate(opponent_color) else 0,
            'promoted': 1 if promoted_into else 0,
            'promoted_into': promoted_into if promoted_into else 'NA',
            'draw': 1 if "draw" in self.status_message.lower() else 0,
        }
        self.game_data.append(move_data)

    def _check_insufficient_material(self):
        """Checks for draw conditions due to insufficient material."""
        pieces = [p for row in self.board.grid for p in row if p]
        
        if len(pieces) == 2: return True # King vs King
        if len(pieces) == 3 and any(isinstance(p, (Knight, Bishop)) for p in pieces):
            return True # King & Knight vs King OR King & Bishop vs King
        if len(pieces) == 4:
            bishops = [p for p in pieces if isinstance(p, Bishop)]
            if len(bishops) == 2:
                b1_r, b1_c = bishops[0].position
                b2_r, b2_c = bishops[1].position
                if (b1_r + b1_c) % 2 == (b2_r + b2_c) % 2:
                    return True # King & Bishop vs King & Bishop on same color
        return False

    def _update_game_status(self):
        """Internal method to update the game status after a move."""
        if self.is_checkmate(self.turn):
            self.game_over = True
            winner = 'White' if self.turn == 'black' else 'Black'
            self.status_message = f"Checkmate! {winner} wins."
        elif self.is_stalemate(self.turn):
            self.game_over = True
            self.status_message = "Stalemate! The game is a draw."
        elif self.position_history.get(self._get_board_state_string(), 0) >= 5:
            self.game_over = True
            self.status_message = "Draw by fivefold repetition."
        elif self._check_insufficient_material():
            self.game_over = True
            self.status_message = "Draw by insufficient material."
        elif self.is_in_check(self.turn):
             self.status_message = f"{self.turn.capitalize()}'s turn (in check)."
        else:
            self.status_message = f"{self.turn.capitalize()}'s turn."

    def is_square_attacked(self, pos, attacker_color):
        """Checks if a given square is under attack by any of the opponent's pieces."""
        for r in range(8):
            for c in range(8):
                piece = self.board.get_piece((r, c))
                if piece and piece.color == attacker_color:
                    if pos in piece.get_attack_squares(self.board):
                        return True
        return False

    def _get_all_legal_moves(self, color):
        """Generates a list of all legal moves for a given color in notation format."""
        all_moves = []
        for r in range(8):
            for c in range(8):
                piece = self.board.get_piece((r, c))
                if piece and piece.color == color:
                    start_pos = (r, c)
                    valid_moves = piece.get_valid_moves(self.board, self)
                    for end_pos in valid_moves:
                        if not self.move_puts_king_in_check(start_pos, end_pos):
                            all_moves.append(f"{self.pos_to_notation(start_pos)}-{self.pos_to_notation(end_pos)}")
        return all_moves

    def _notation_to_pos_tuple(self, notation):
        """Converts algebraic notation (e.g., 'e4') to a (row, col) tuple."""
        if not isinstance(notation, str) or len(notation) != 2: return None
        files, rank = "abcdefgh", notation[1]
        if notation[0] not in files or not rank.isdigit(): return None
        return (8 - int(rank), files.index(notation[0]))

    def request_ai_move(self):
        """Orchestrates the two-LLM pipeline to get and make the AI's move."""
        if self.game_over: return

        # 1. Get Commentary on Player's Last Move (optional step, for now just for debug)
        if self.game_data:
            commentary = llm_api.get_move_commentary(self.game_data[-1])
            print(f"Commentator: {commentary}")
        
        # 2. Prepare data for the Coach LLM
        game_history_str = "\n".join([str(move) for move in self.game_data])
        legal_moves = self._get_all_legal_moves(self.turn)

        if not legal_moves: return 

        # 3. Call the Coach LLM
        coach_response = llm_api.get_coach_move_and_commentary(
            self.coach_chat_session, game_history_str, legal_moves)

        print(f"Coach: {coach_response}")

        # 4. Parse and Execute the Move
        if coach_response and 'move' in coach_response and 'commentary' in coach_response:
            self.last_coach_commentary = coach_response['commentary']
            move_str = coach_response['move']
            
            # Use the new helper function to make the move
            success, message = self.make_move_from_notation(move_str, is_ai_move=True)
            if not success:
                print(f"Error: AI returned an illegal move: {move_str}. Making a default move.")
                self.make_move_from_notation(legal_moves[0], is_ai_move=True)
        else:
            # Fallback if the response is not as expected
            print("Error: AI response was not in the correct format. Making a default move.")
            self.make_move_from_notation(legal_moves[0], is_ai_move=True)


    def make_move(self, start_pos, end_pos):
        piece = self.board.get_piece(start_pos)
        if not piece or piece.color != self.turn or self.game_over:
            return False, "Not your turn or no piece selected."

        valid_moves = piece.get_valid_moves(self.board, self)
        if end_pos not in valid_moves:
            return False, "Invalid move for this piece."

        if self.move_puts_king_in_check(start_pos, end_pos):
            return False, "You cannot move into check."

        # --- CASTLING LOGIC ---
        if isinstance(piece, King) and abs(start_pos[1] - end_pos[1]) == 2:
            is_kingside = end_pos[1] > start_pos[1]
            rook_start_col = 7 if is_kingside else 0
            rook_end_col = 5 if is_kingside else 3
            rook_start = (start_pos[0], rook_start_col)
            rook_end = (start_pos[0], rook_end_col)

            # Record the move before piece positions change
            self._record_move_data(piece, start_pos, end_pos, captured_piece=None)

            # Move pieces
            self.board.move_piece(start_pos, end_pos) # Move King
            self.board.move_piece(rook_start, rook_end) # Move Rook
            
            move_notation = "O-O" if is_kingside else "O-O-O"
            self.move_history.append(move_notation)

            self.turn = 'black' if self.turn == 'white' else 'white'
            self._record_position()
            self._update_game_status()
            
            return True, "Castle successful."

        if isinstance(piece, Pawn) and end_pos[0] in [0, 7]:
            captured_piece = self.board.get_piece(end_pos)
            self.promotion_pending = (start_pos, end_pos, captured_piece, piece) # Pass the pawn object
            self.status_message = f"{self.turn.capitalize()} to promote pawn. Choose a piece."
            return True, "Promotion"

        is_en_passant = isinstance(piece, Pawn) and end_pos == self.en_passant_target
        captured_piece = None
        
        if is_en_passant:
            pawn_dir = -1 if piece.color == 'white' else 1
            captured_pawn_pos = (end_pos[0] - pawn_dir, end_pos[1])
            captured_piece = self.board.get_piece(captured_pawn_pos)
            self.board.set_piece(captured_pawn_pos, None)
            self.board.move_piece(start_pos, end_pos)
        else:
            captured_piece = self.board.move_piece(start_pos, end_pos)

        if isinstance(piece, Pawn) and abs(start_pos[0] - end_pos[0]) == 2:
            self.en_passant_target = ((start_pos[0] + end_pos[0]) // 2, start_pos[1])
        else:
            self.en_passant_target = None
        
        move_notation = f"{piece.symbol} {self.pos_to_notation(start_pos)}-{self.pos_to_notation(end_pos)}"
        if captured_piece:
             move_notation += f" (captures {captured_piece.symbol})"
        if is_en_passant:
            move_notation += " e.p."
        self.move_history.append(move_notation)

        self.turn = 'black' if self.turn == 'white' else 'white'
        self._record_position()
        self._update_game_status()
        self._record_move_data(piece, start_pos, end_pos, captured_piece)

        return True, self.status_message
        
    def make_move_from_notation(self, move_str, is_ai_move=False):
        """
        Helper function to make a move using notation like 'e2-e4'.
        This simplifies handling moves from the AI and spoken commands.
        """
        if '-' not in move_str:
            return False, "Invalid move format."
        
        start_notation, end_notation = move_str.split('-')
        start_pos = self._notation_to_pos_tuple(start_notation)
        end_pos = self._notation_to_pos_tuple(end_notation)

        if not start_pos or not end_pos:
            return False, "Invalid notation."
            
        success, message = self.make_move(start_pos, end_pos)
        
        # If the move was successful and it was NOT the AI's turn,
        # it must have been the player's turn, so we request the AI move.
        # We check `is_ai_move` to prevent an infinite loop of AI vs AI.
        if success and not is_ai_move and not self.game_over:
            self.request_ai_move()
            
        return success, message


    def promote_pawn(self, piece_choice_str):
        if not self.promotion_pending:
            return False, "No pawn is pending promotion."

        start_pos, end_pos, captured_piece, original_pawn = self.promotion_pending
        pawn_color = self.turn
        
        piece_map = {'Queen': Queen, 'Rook': Rook, 'Bishop': Bishop, 'Knight': Knight}
        new_piece_class = piece_map.get(piece_choice_str)
        
        if not new_piece_class:
            return False, "Invalid piece choice."
            
        new_piece = new_piece_class(pawn_color, end_pos)
        self.board.set_piece(start_pos, None)
        self.board.set_piece(end_pos, new_piece)

        self.promotion_pending = None
        move_notation = f"{self.pos_to_notation(end_pos)}={new_piece.symbol}"
        self.move_history.append(move_notation)

        self.turn = 'black' if self.turn == 'white' else 'white'
        self._record_position()
        self._update_game_status()
        
        self._record_move_data(original_pawn, start_pos, end_pos, captured_piece, promoted_into=piece_choice_str)

        # After promotion, if it's now the AI's turn, request its move.
        if not self.game_over and self.turn != pawn_color:
            self.request_ai_move()

        return True, "Pawn promoted successfully."


    def is_in_check(self, color):
        """Determines if the specified player is in check."""
        king_pos = self.board.find_king(color)
        if not king_pos: return False # Should not happen
        return self.is_square_attacked(king_pos, 'black' if color == 'white' else 'white')

    def move_puts_king_in_check(self, start_pos, end_pos):
        original_piece = self.board.get_piece(start_pos)
        if not original_piece: return False
        
        captured_piece = self.board.get_piece(end_pos)
        original_start_pos = original_piece.position
        
        is_en_passant = isinstance(original_piece, Pawn) and end_pos == self.en_passant_target
        captured_pawn_pos, en_passant_captured_piece = None, None

        if is_en_passant:
            pawn_dir = -1 if original_piece.color == 'white' else 1
            captured_pawn_pos = (end_pos[0] - pawn_dir, end_pos[1])
            en_passant_captured_piece = self.board.get_piece(captured_pawn_pos)
            self.board.set_piece(captured_pawn_pos, None)

        self.board.set_piece(end_pos, original_piece)
        self.board.set_piece(start_pos, None)

        in_check = self.is_in_check(original_piece.color)
        
        self.board.set_piece(start_pos, original_piece)
        self.board.set_piece(end_pos, captured_piece)
        original_piece.position = original_start_pos

        if is_en_passant and captured_pawn_pos:
            self.board.set_piece(captured_pawn_pos, en_passant_captured_piece)

        return in_check

    def has_legal_moves(self, color):
        for r in range(8):
            for c in range(8):
                piece = self.board.get_piece((r, c))
                if piece and piece.color == color:
                    for move in piece.get_valid_moves(self.board, self):
                        if not self.move_puts_king_in_check((r, c), move):
                            return True
        return False
    
    def is_checkmate(self, color):
        return self.is_in_check(color) and not self.has_legal_moves(color)

    def is_stalemate(self, color):
        return not self.is_in_check(color) and not self.has_legal_moves(color)

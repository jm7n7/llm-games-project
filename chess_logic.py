class Piece:
    """Base class for all chess pieces."""
    def __init__(self, color, position):
        self.color = color
        self.position = position
        self.has_moved = False
        self.symbol = 'X' # Fallback symbol
        self.image_name = f"{self.color[0]}_{self.__class__.__name__.lower()}.png"

    def get_valid_moves(self, board, game=None):
        """Returns a list of valid moves for the piece."""
        raise NotImplementedError

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
    def __init__(self, color, position):
        super().__init__(color, position)
        self.symbol = '♔' if color == 'white' else '♚'

    def get_valid_moves(self, board, game=None):
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
    def __init__(self, color, position):
        super().__init__(color, position)
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
    def __init__(self, color, position):
        super().__init__(color, position)
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
    def __init__(self, color, position):
        super().__init__(color, position)
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
    def __init__(self, color, position):
        super().__init__(color, position)
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
    def __init__(self, color, position):
        super().__init__(color, position)
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
        
        if game and game.en_passant_target and game.en_passant_target == (r + direction, c - 1) or \
           game and game.en_passant_target and game.en_passant_target == (r + direction, c + 1):
            moves.append(game.en_passant_target)
        return moves

class Board:
    """Represents the chessboard and its pieces."""
    def __init__(self):
        self.grid = [[None for _ in range(8)] for _ in range(8)]
        self.setup_pieces()

    def get_piece(self, pos):
        r, c = pos
        return self.grid[r][c]

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
        for r, color in [(0, 'black'), (7, 'white')]:
            for c, P in [(0, Rook), (1, Knight), (2, Bishop), (3, Queen), (4, King), (5, Bishop), (6, Knight), (7, Rook)]:
                self.set_piece((r, c), P(color, (r, c)))
        for c in range(8):
            self.set_piece((1, c), Pawn('black', (1, c)))
            self.set_piece((6, c), Pawn('white', (6, c)))

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
        self._record_position()

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

    def _check_insufficient_material(self):
        """Checks for draw conditions due to insufficient material."""
        pieces = [p for row in self.board.grid for p in row if p]
        
        # King vs King
        if len(pieces) == 2: return True

        # King and Knight vs King OR King and Bishop vs King
        if len(pieces) == 3:
            if any(isinstance(p, (Knight, Bishop)) for p in pieces):
                return True

        # King and Bishop vs King and Bishop (bishops on same color squares)
        if len(pieces) == 4:
            bishops = [p for p in pieces if isinstance(p, Bishop)]
            if len(bishops) == 2:
                b1_r, b1_c = bishops[0].position
                b2_r, b2_c = bishops[1].position
                if (b1_r + b1_c) % 2 == (b2_r + b2_c) % 2:
                    return True
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

    def make_move(self, start_pos, end_pos):
        piece = self.board.get_piece(start_pos)
        if not piece or piece.color != self.turn or self.game_over:
            return False, "Not your turn or no piece selected."

        valid_moves = piece.get_valid_moves(self.board, self)
        if end_pos not in valid_moves:
            return False, "Invalid move for this piece."

        if self.move_puts_king_in_check(start_pos, end_pos):
            return False, "You cannot move into check."

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
        
        if isinstance(piece, Pawn) and end_pos[0] in [0, 7]:
            self.promotion_pending = (start_pos, end_pos)
            self.status_message = f"{self.turn.capitalize()} to promote pawn. Choose a piece."
            return True, "Promotion"
        
        move_notation = f"{piece.symbol} {self.pos_to_notation(start_pos)}-{self.pos_to_notation(end_pos)}"
        if captured_piece:
             move_notation += f" (captures {captured_piece.symbol})"
        if is_en_passant:
            move_notation += " e.p."
        self.move_history.append(move_notation)

        self.turn = 'black' if self.turn == 'white' else 'white'
        self._record_position()
        self._update_game_status()

        return True, self.status_message

    def promote_pawn(self, piece_choice_str):
        if not self.promotion_pending:
            return False, "No pawn is pending promotion."

        _, end_pos = self.promotion_pending
        pawn_color = self.turn
        
        piece_map = {'Queen': Queen, 'Rook': Rook, 'Bishop': Bishop, 'Knight': Knight}
        new_piece_class = piece_map.get(piece_choice_str)
        
        if not new_piece_class:
            return False, "Invalid piece choice."
            
        new_piece = new_piece_class(pawn_color, end_pos)
        self.board.set_piece(end_pos, new_piece)

        self.promotion_pending = None
        move_notation = f"{self.pos_to_notation(end_pos)}={new_piece.symbol}"
        self.move_history.append(move_notation)

        self.turn = 'black' if self.turn == 'white' else 'white'
        self._record_position()
        self._update_game_status()
        return True, "Pawn promoted successfully."


    def is_in_check(self, color):
        king_pos = self.board.find_king(color)
        if not king_pos: return False

        opponent_color = 'black' if color == 'white' else 'white'
        for r in range(8):
            for c in range(8):
                piece = self.board.get_piece((r, c))
                if piece and piece.color == opponent_color:
                    if king_pos in piece.get_valid_moves(self.board, self):
                        return True
        return False

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


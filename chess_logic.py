class Piece:
    """Base class for all chess pieces."""
    def __init__(self, color, position):
        self.color = color
        self.position = position
        self.has_moved = False
        self.symbol = 'X' # Fallback symbol
        # Generates filenames like 'w_king.png' or 'b_pawn.png'
        self.image_name = f"{self.color[0]}_{self.__class__.__name__.lower()}.png"

    def get_valid_moves(self, board):
        """Returns a list of valid moves for the piece."""
        raise NotImplementedError

    def _is_valid_and_capturable(self, pos, board):
        """
        Helper to check if a position is on the board and can be moved to.
        Returns (on_board, can_capture).
        """
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

    def get_valid_moves(self, board):
        moves = []
        r, c = self.position
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:
                    continue
                
                new_pos = (r + dr, c + dc)
                is_valid, can_capture = self._is_valid_and_capturable(new_pos, board)
                if is_valid:
                    moves.append(new_pos)
        return moves

class Queen(Piece):
    def __init__(self, color, position):
        super().__init__(color, position)
        self.symbol = '♕' if color == 'white' else '♛'

    def get_valid_moves(self, board):
        # Combines Rook and Bishop logic
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
                        break # Stop after capturing
                else:
                    break # Stop if blocked or off-board
        return moves

class Rook(Piece):
    def __init__(self, color, position):
        super().__init__(color, position)
        self.symbol = '♖' if color == 'white' else '♜'

    def get_valid_moves(self, board):
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

    def get_valid_moves(self, board):
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

    def get_valid_moves(self, board):
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

    def get_valid_moves(self, board):
        moves = []
        r, c = self.position
        direction = -1 if self.color == 'white' else 1

        # 1. Standard one-step move
        one_step = (r + direction, c)
        if 0 <= one_step[0] < 8 and board.get_piece(one_step) is None:
            moves.append(one_step)

            # 2. Initial two-step move
            if not self.has_moved:
                two_steps = (r + 2 * direction, c)
                if 0 <= two_steps[0] < 8 and board.get_piece(two_steps) is None:
                    moves.append(two_steps)
        
        # 3. Captures
        for dc in [-1, 1]:
            capture_pos = (r + direction, c + dc)
            if 0 <= capture_pos[0] < 8 and 0 <= capture_pos[1] < 8:
                target_piece = board.get_piece(capture_pos)
                if target_piece and target_piece.color != self.color:
                    moves.append(capture_pos)
        
        # TODO: En passant and promotion
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
            # Handle capture
            captured_piece = self.get_piece(end_pos)
            
            self.set_piece(end_pos, piece)
            self.set_piece(start_pos, None)
            piece.has_moved = True
            return captured_piece
        return None
    
    def find_king(self, color):
        """Finds the position of the king for a given color."""
        for r in range(8):
            for c in range(8):
                piece = self.get_piece((r, c))
                if isinstance(piece, King) and piece.color == color:
                    return (r, c)
        return None

    def setup_pieces(self):
        # Place major pieces
        for r, color in [(0, 'black'), (7, 'white')]:
            self.set_piece((r, 0), Rook(color, (r, 0)))
            self.set_piece((r, 7), Rook(color, (r, 7)))
            self.set_piece((r, 1), Knight(color, (r, 1)))
            self.set_piece((r, 6), Knight(color, (r, 6)))
            self.set_piece((r, 2), Bishop(color, (r, 2)))
            self.set_piece((r, 5), Bishop(color, (r, 5)))
            self.set_piece((r, 3), Queen(color, (r, 3)))
            self.set_piece((r, 4), King(color, (r, 4)))
        
        # Place pawns
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
    
    def pos_to_notation(self, pos):
        r, c = pos
        return f"{'abcdefgh'[c]}{8-r}"

    def make_move(self, start_pos, end_pos):
        piece = self.board.get_piece(start_pos)
        if not piece or piece.color != self.turn or self.game_over:
            return False, "Not your turn or no piece selected."

        valid_moves = piece.get_valid_moves(self.board)
        if end_pos not in valid_moves:
            return False, "Invalid move for this piece."

        if self.move_puts_king_in_check(start_pos, end_pos):
            return False, "You cannot move into check."
        
        captured_piece = self.board.move_piece(start_pos, end_pos)

        # Log move
        move_notation = f"{piece.symbol} {self.pos_to_notation(start_pos)}-{self.pos_to_notation(end_pos)}"
        if captured_piece:
             move_notation += f" (captures {captured_piece.symbol})"
        self.move_history.append(move_notation)

        # Switch turns
        self.turn = 'black' if self.turn == 'white' else 'white'
        
        # Update game status
        if self.is_checkmate(self.turn):
            self.game_over = True
            winner = 'White' if self.turn == 'black' else 'Black'
            self.status_message = f"Checkmate! {winner} wins."
        elif self.is_stalemate(self.turn):
            self.game_over = True
            self.status_message = "Stalemate! The game is a draw."
        elif self.is_in_check(self.turn):
             self.status_message = f"{self.turn.capitalize()}'s turn (in check)."
        else:
            self.status_message = f"{self.turn.capitalize()}'s turn."

        return True, self.status_message

    def is_in_check(self, color):
        king_pos = self.board.find_king(color)
        if not king_pos: return False

        opponent_color = 'black' if color == 'white' else 'white'
        for r in range(8):
            for c in range(8):
                piece = self.board.get_piece((r, c))
                if piece and piece.color == opponent_color:
                    # Need to check valid moves from the opponent's perspective
                    # A simple 'in' check is not sufficient for pawns
                    if king_pos in piece.get_valid_moves(self.board):
                        return True
        return False

    def move_puts_king_in_check(self, start_pos, end_pos):
        """Simulates a move and checks if it results in the king being in check."""
        original_piece = self.board.get_piece(start_pos)
        if not original_piece: return False
        
        # Temporarily make the move
        captured_piece = self.board.get_piece(end_pos)
        
        # Special handling for piece's internal position state
        original_start_pos = original_piece.position
        
        self.board.set_piece(end_pos, original_piece)
        self.board.set_piece(start_pos, None)

        # Check for check
        in_check = self.is_in_check(original_piece.color)
        
        # Undo the move
        self.board.set_piece(start_pos, original_piece)
        self.board.set_piece(end_pos, captured_piece)
        
        # Restore piece's internal position state
        original_piece.position = original_start_pos

        return in_check

    def has_legal_moves(self, color):
        """Checks if a player has any legal moves."""
        for r in range(8):
            for c in range(8):
                piece = self.board.get_piece((r, c))
                if piece and piece.color == color:
                    for move in piece.get_valid_moves(self.board):
                        if not self.move_puts_king_in_check((r, c), move):
                            return True
        return False
    
    def is_checkmate(self, color):
        return self.is_in_check(color) and not self.has_legal_moves(color)

    def is_stalemate(self, color):
        return not self.is_in_check(color) and not self.has_legal_moves(color)



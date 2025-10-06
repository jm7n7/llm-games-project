import copy

class Piece:
    """
    Base class for a chess piece.
    """
    def __init__(self, color, position):
        self.color = color
        self.position = position
        self.symbol = None

    def __repr__(self):
        return self.symbol

    def get_valid_moves(self, board):
        """Returns a list of valid moves for the piece."""
        raise NotImplementedError("This method should be implemented by subclasses.")

    def is_valid_move(self, board, end_pos):
        """Checks if a move to end_pos is valid."""
        # A piece cannot capture a piece of the same color
        target_piece = board.get_piece(end_pos)
        if target_piece and target_piece.color == self.color:
            return False
        return True

class Pawn(Piece):
    def __init__(self, color, position):
        super().__init__(color, position)
        self.symbol = '♙' if color == 'white' else '♟'
        self.has_moved = False

    def get_valid_moves(self, board):
        moves = []
        r, c = self.position
        direction = -1 if self.color == 'white' else 1

        # Standard one-square move
        if board.is_on_board((r + direction, c)) and not board.get_piece((r + direction, c)):
            moves.append((r + direction, c))

        # Two-square initial move
        if not self.has_moved and not board.get_piece((r + direction, c)) and not board.get_piece((r + 2 * direction, c)):
            moves.append((r + 2 * direction, c))

        # Captures
        for dc in [-1, 1]:
            target_pos = (r + direction, c + dc)
            if board.is_on_board(target_pos):
                target_piece = board.get_piece(target_pos)
                if target_piece and target_piece.color != self.color:
                    moves.append(target_pos)
        
        # TODO: Implement En Passant logic
        
        return moves

class Rook(Piece):
    def __init__(self, color, position):
        super().__init__(color, position)
        self.symbol = '♖' if color == 'white' else '♜'

    def get_valid_moves(self, board):
        return board.get_straight_moves(self.position)

class Knight(Piece):
    def __init__(self, color, position):
        super().__init__(color, position)
        self.symbol = '♘' if color == 'white' else '♞'

    def get_valid_moves(self, board):
        moves = []
        r, c = self.position
        potential_moves = [
            (r-2, c-1), (r-2, c+1), (r-1, c-2), (r-1, c+2),
            (r+1, c-2), (r+1, c+2), (r+2, c-1), (r+2, c+1)
        ]
        for move in potential_moves:
            if board.is_on_board(move) and self.is_valid_move(board, move):
                moves.append(move)
        return moves


class Bishop(Piece):
    def __init__(self, color, position):
        super().__init__(color, position)
        self.symbol = '♗' if color == 'white' else '♝'

    def get_valid_moves(self, board):
        return board.get_diagonal_moves(self.position)

class Queen(Piece):
    def __init__(self, color, position):
        super().__init__(color, position)
        self.symbol = '♕' if color == 'white' else '♛'

    def get_valid_moves(self, board):
        moves = board.get_straight_moves(self.position)
        moves.extend(board.get_diagonal_moves(self.position))
        return moves

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
                target_pos = (r + dr, c + dc)
                if board.is_on_board(target_pos) and self.is_valid_move(board, target_pos):
                    moves.append(target_pos)
        # TODO: Implement Castling
        return moves

class Board:
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
            if isinstance(piece, Pawn) and not piece.has_moved:
                piece.has_moved = True

            # Handle capture
            captured_piece = self.get_piece(end_pos)
            
            self.set_piece(end_pos, piece)
            self.set_piece(start_pos, None)
            return captured_piece
        return None

    def setup_pieces(self):
        # Pawns
        for c in range(8):
            self.set_piece((1, c), Pawn('black', (1, c)))
            self.set_piece((6, c), Pawn('white', (6, c)))

        # Rooks
        self.set_piece((0, 0), Rook('black', (0, 0)))
        self.set_piece((0, 7), Rook('black', (0, 7)))
        self.set_piece((7, 0), Rook('white', (7, 0)))
        self.set_piece((7, 7), Rook('white', (7, 7)))

        # Knights
        self.set_piece((0, 1), Knight('black', (0, 1)))
        self.set_piece((0, 6), Knight('black', (0, 6)))
        self.set_piece((7, 1), Knight('white', (7, 1)))
        self.set_piece((7, 6), Knight('white', (7, 6)))

        # Bishops
        self.set_piece((0, 2), Bishop('black', (0, 2)))
        self.set_piece((0, 5), Bishop('black', (0, 5)))
        self.set_piece((7, 2), Bishop('white', (7, 2)))
        self.set_piece((7, 5), Bishop('white', (7, 5)))

        # Queens
        self.set_piece((0, 3), Queen('black', (0, 3)))
        self.set_piece((7, 3), Queen('white', (7, 3)))

        # Kings
        self.set_piece((0, 4), King('black', (0, 4)))
        self.set_piece((7, 4), King('white', (7, 4)))

    def is_on_board(self, pos):
        r, c = pos
        return 0 <= r < 8 and 0 <= c < 8

    def get_line_moves(self, start_pos, directions):
        moves = []
        piece = self.get_piece(start_pos)
        
        for dr, dc in directions:
            r, c = start_pos
            while True:
                r, c = r + dr, c + dc
                if not self.is_on_board((r, c)):
                    break
                target_piece = self.get_piece((r, c))
                if target_piece:
                    if target_piece.color != piece.color:
                        moves.append((r, c))
                    break
                moves.append((r, c))
        return moves
        
    def get_straight_moves(self, start_pos):
        return self.get_line_moves(start_pos, [(-1, 0), (1, 0), (0, -1), (0, 1)])

    def get_diagonal_moves(self, start_pos):
        return self.get_line_moves(start_pos, [(-1, -1), (-1, 1), (1, -1), (1, 1)])

    def find_king(self, color):
        for r in range(8):
            for c in range(8):
                piece = self.get_piece((r, c))
                if isinstance(piece, King) and piece.color == color:
                    return (r, c)
        return None


class ChessGame:
    def __init__(self):
        self.reset_game()

    def reset_game(self):
        self.board = Board()
        self.turn = 'white'
        self.move_history = []
        self.game_over = False
        self.winner = None
        self.status_message = "White's turn to move."

    def make_move(self, start_pos, end_pos):
        piece = self.board.get_piece(start_pos)

        # 1. Check if there is a piece at the start position
        if not piece:
            return False, "No piece at the selected square."
            
        # 2. Check if it's the correct player's turn
        if piece.color != self.turn:
            return False, f"It's {self.turn}'s turn."

        # 3. Check if the end position is a valid move for that piece
        valid_moves = piece.get_valid_moves(self.board)
        if end_pos not in valid_moves:
            return False, "Invalid move for this piece."

        # 4. Check if the move would put the current player's king in check
        if self.move_puts_king_in_check(start_pos, end_pos):
            return False, "You cannot make a move that leaves your king in check."

        # If all checks pass, make the move
        self.board.move_piece(start_pos, end_pos)
        self.add_move_to_history(piece, start_pos, end_pos)
        
        # Switch turns
        self.turn = 'black' if self.turn == 'white' else 'white'

        # Check for game-ending conditions for the new player
        if self.is_checkmate(self.turn):
            self.game_over = True
            self.winner = 'white' if self.turn == 'black' else 'black'
            self.status_message = f"Checkmate! {self.winner.capitalize()} wins."
        elif self.is_stalemate(self.turn):
            self.game_over = True
            self.winner = "Draw"
            self.status_message = "Stalemate! The game is a draw."
        elif self.is_in_check(self.turn):
            self.status_message = f"{self.turn.capitalize()}'s turn. King is in check!"
        else:
            self.status_message = f"{self.turn.capitalize()}'s turn to move."
        
        return True, self.status_message
    
    def add_move_to_history(self, piece, start_pos, end_pos):
        start_alg = self.get_algebraic_notation(start_pos)
        end_alg = self.get_algebraic_notation(end_pos)
        self.move_history.append(f"{piece.symbol} {start_alg} to {end_alg}")

    def get_algebraic_notation(self, pos):
        r, c = pos
        return f"{chr(ord('a') + c)}{8 - r}"

    def get_all_possible_moves(self, color):
        """Returns all possible moves for a given color."""
        all_moves = []
        for r in range(8):
            for c in range(8):
                piece = self.board.get_piece((r, c))
                if piece and piece.color == color:
                    moves = piece.get_valid_moves(self.board)
                    for move in moves:
                        # We must check if this move is truly legal (doesn't result in check)
                        if not self.move_puts_king_in_check((r,c), move):
                            all_moves.append(((r,c), move))
        return all_moves

    def is_in_check(self, king_color, board_state=None):
        """Checks if the king of a specific color is in check."""
        board = board_state if board_state else self.board
        king_pos = board.find_king(king_color)
        if not king_pos: return False # Should not happen in a real game

        opponent_color = 'black' if king_color == 'white' else 'white'
        
        for r in range(8):
            for c in range(8):
                piece = board.get_piece((r, c))
                if piece and piece.color == opponent_color:
                    # Check if any opponent piece can attack the king
                    if king_pos in piece.get_valid_moves(board):
                        return True
        return False
        
    def move_puts_king_in_check(self, start_pos, end_pos):
        """
        Simulates a move and checks if it results in the current player's
        king being in check.
        """
        piece = self.board.get_piece(start_pos)
        king_color = piece.color
        
        # Create a deep copy of the board to simulate the move
        temp_board = copy.deepcopy(self.board)
        temp_board.move_piece(start_pos, end_pos)
        
        return self.is_in_check(king_color, board_state=temp_board)

    def is_checkmate(self, color):
        """Checks if the player of a given color is in checkmate."""
        if not self.is_in_check(color):
            return False
        # If in check, check if there are any legal moves
        if not self.get_all_possible_moves(color):
            return True
        return False

    def is_stalemate(self, color):
        """Checks if the player of a given color is in stalemate."""
        if self.is_in_check(color):
            return False
        # If not in check, check if there are any legal moves
        if not self.get_all_possible_moves(color):
            return True
        return False


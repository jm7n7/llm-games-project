import uuid
import copy
import json # (NEW) For dumping game data

class Piece:
    """Base class for all chess pieces."""
    def __init__(self, color, position, name=None):
        self.color = color
        self.position = position
        self.has_moved = False
        self.move_count = 0 # (NEW) For tempo tracking
        self.symbol = 'X' # Fallback symbol
        self.name = name if name else self.__class__.__name__
        self.image_name = f"{self.color[0]}_{self.__class__.__name__.lower()}.png"
        self.value = 0 # (NEW) Base value

    def get_valid_moves(self, board, game=None):
        """Returns a list of valid moves for the piece."""
        raise NotImplementedError

    def get_attack_squares(self, board):
        """
        (FIXED) Returns squares this piece is attacking,
        including through/at friendly pieces (for defense/x-ray).
        """
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
    def __init__(self, color, position, name=None):
        super().__init__(color, position, name or "King")
        self.symbol = '♔' if color == 'white' else '♚'
        self.value = 1000 # (NEW) Invaluable

    def _get_castling_moves(self, board, game):
        castling_moves = []
        if self.has_moved or game.is_in_check(self.color):
            return []
        king_row, _ = self.position
        # Kingside
        rook_k = board.get_piece((king_row, 7))
        if isinstance(rook_k, Rook) and not rook_k.has_moved and all(board.get_piece((king_row, c)) is None for c in [5, 6]):
            if not game.is_square_attacked((king_row, 5), 'black' if self.color == 'white' else 'white') and \
               not game.is_square_attacked((king_row, 6), 'black' if self.color == 'white' else 'white'):
                castling_moves.append((king_row, 6))
        # Queenside
        rook_q = board.get_piece((king_row, 0))
        if isinstance(rook_q, Rook) and not rook_q.has_moved and all(board.get_piece((king_row, c)) is None for c in [1, 2, 3]):
            if not game.is_square_attacked((king_row, 2), 'black' if self.color == 'white' else 'white') and \
               not game.is_square_attacked((king_row, 3), 'black' if self.color == 'white' else 'white'):
                castling_moves.append((king_row, 2))
        return castling_moves

    def get_valid_moves(self, board, game=None):
        """Gets valid moves, including castling."""
        moves = []
        r, c = self.position
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0: continue
                new_pos = (r + dr, c + dc)
                if self._is_valid_and_capturable(new_pos, board)[0]:
                    moves.append(new_pos)
        if game: moves.extend(self._get_castling_moves(board, game))
        return moves
    
    def get_attack_squares(self, board):
        """(FIXED) Calculates all squares this King attacks (for check/defense)."""
        moves = []
        r, c = self.position
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0: continue
                new_pos = (r + dr, c + dc)
                nr, nc = new_pos
                # Only check if it's on the board
                if 0 <= nr < 8 and 0 <= nc < 8:
                    moves.append(new_pos)
        return moves

class Queen(Piece):
    def __init__(self, color, position, name=None):
        super().__init__(color, position, name or "Queen")
        self.symbol = '♕' if color == 'white' else '♛'
        self.value = 9 # (NEW)
        self.directions = [(-1, -1), (-1, 1), (1, -1), (1, 1), (-1, 0), (1, 0), (0, -1), (0, 1)] # (NEW)

    def get_valid_moves(self, board, game=None):
        moves = []
        r, c = self.position
        for dr, dc in self.directions: # (MODIFIED)
            for i in range(1, 8):
                new_pos = (r + i * dr, c + i * dc)
                is_valid, can_capture = self._is_valid_and_capturable(new_pos, board)
                if is_valid:
                    moves.append(new_pos)
                    if can_capture: break
                else: break
        return moves

    def get_attack_squares(self, board):
        """(FIXED) Calculates attack squares, including X-Ray defense."""
        moves = []
        r, c = self.position
        for dr, dc in self.directions: # (MODIFIED)
            for i in range(1, 8):
                new_pos = (r + i * dr, c + i * dc)
                nr, nc = new_pos
                if not (0 <= nr < 8 and 0 <= nc < 8):
                    break # Off board
                moves.append(new_pos)
                if board.get_piece(new_pos) is not None:
                    break # Stop after hitting *any* piece
        return moves

class Rook(Piece):
    def __init__(self, color, position, name=None):
        super().__init__(color, position, name)
        self.symbol = '♖' if color == 'white' else '♜'
        self.value = 5 # (NEW)
        self.directions = [(-1, 0), (1, 0), (0, -1), (0, 1)] # (NEW)

    def get_valid_moves(self, board, game=None):
        moves = []
        r, c = self.position
        for dr, dc in self.directions: # (MODIFIED)
            for i in range(1, 8):
                new_pos = (r + i * dr, c + i * dc)
                is_valid, can_capture = self._is_valid_and_capturable(new_pos, board)
                if is_valid:
                    moves.append(new_pos)
                    if can_capture: break
                else: break
        return moves

    def get_attack_squares(self, board):
        """(FIXED) Calculates attack squares, including X-Ray defense."""
        moves = []
        r, c = self.position
        for dr, dc in self.directions: # (MODIFIED)
            for i in range(1, 8):
                new_pos = (r + i * dr, c + i * dc)
                nr, nc = new_pos
                if not (0 <= nr < 8 and 0 <= nc < 8):
                    break # Off board
                moves.append(new_pos)
                if board.get_piece(new_pos) is not None:
                    break # Stop after hitting *any* piece
        return moves

class Bishop(Piece):
    def __init__(self, color, position, name=None):
        super().__init__(color, position, name)
        self.symbol = '♗' if color == 'white' else '♝'
        self.value = 3 # (NEW)
        self.directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)] # (NEW)

    def get_valid_moves(self, board, game=None):
        moves = []
        r, c = self.position
        for dr, dc in self.directions: # (MODIFIED)
            for i in range(1, 8):
                new_pos = (r + i * dr, c + i * dc)
                is_valid, can_capture = self._is_valid_and_capturable(new_pos, board)
                if is_valid:
                    moves.append(new_pos)
                    if can_capture: break
                else: break
        return moves

    def get_attack_squares(self, board):
        """(FIXED) Calculates attack squares, including X-Ray defense."""
        moves = []
        r, c = self.position
        for dr, dc in self.directions: # (MODIFIED)
            for i in range(1, 8):
                new_pos = (r + i * dr, c + i * dc)
                nr, nc = new_pos
                if not (0 <= nr < 8 and 0 <= nc < 8):
                    break # Off board
                moves.append(new_pos)
                if board.get_piece(new_pos) is not None:
                    break # Stop after hitting *any* piece
        return moves

class Knight(Piece):
    def __init__(self, color, position, name=None):
        super().__init__(color, position, name)
        self.symbol = '♘' if color == 'white' else '♞'
        self.value = 3 # (NEW)

    def get_valid_moves(self, board, game=None):
        moves = []
        r, c = self.position
        potential_moves = [(r-2, c-1), (r-2, c+1), (r+2, c-1), (r+2, c+1), (r-1, c-2), (r-1, c+2), (r+1, c-2), (r+1, c+2)]
        for move in potential_moves:
            if self._is_valid_and_capturable(move, board)[0]:
                moves.append(move)
        return moves

    def get_attack_squares(self, board):
        """(FIXED) Calculates all squares this Knight attacks (for check/defense)."""
        moves = []
        r, c = self.position
        potential_moves = [(r-2, c-1), (r-2, c+1), (r+2, c-1), (r+2, c+1), (r-1, c-2), (r-1, c+2), (r+1, c-2), (r+1, c+2)]
        for move in potential_moves:
            nr, nc = move
            # Only check if it's on the board
            if 0 <= nr < 8 and 0 <= nc < 8:
                moves.append(move)
        return moves

class Pawn(Piece):
    def __init__(self, color, position, name=None):
        super().__init__(color, position, name)
        self.symbol = '♙' if color == 'white' else '♟'
        self.value = 1 # (NEW)

    def get_valid_moves(self, board, game=None):
        moves = []
        r, c = self.position
        direction = -1 if self.color == 'white' else 1
        # 1. Forward moves
        one_step = (r + direction, c)
        if 0 <= one_step[0] < 8 and board.get_piece(one_step) is None:
            moves.append(one_step)
            # 2. Two-step initial move
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
        # 4. En Passant
        if game and game.en_passant_target and (game.en_passant_target == (r + direction, c - 1) or game.en_passant_target == (r + direction, c + 1)):
            moves.append(game.en_passant_target)
        return moves

    def get_attack_squares(self, board):
        """(FIXED) Calculates all squares this Pawn attacks (for check/defense)."""
        moves = []
        r, c = self.position
        direction = -1 if self.color == 'white' else 1
        for dc in [-1, 1]:
            capture_pos = (r + direction, c + dc)
            # Only check if it's on the board
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
        return self.grid[r][c] if 0 <= r < 8 and 0 <= c < 8 else None

    def set_piece(self, pos, piece):
        r, c = pos
        self.grid[r][c] = piece
        if piece: piece.position = pos

    def move_piece(self, start_pos, end_pos):
        piece = self.get_piece(start_pos)
        if piece:
            captured_piece = self.get_piece(end_pos)
            self.set_piece(end_pos, piece)
            self.set_piece(start_pos, None)
            piece.has_moved = True
            piece.move_count += 1 # (NEW) Increment move count
            return captured_piece
        return None
    
    def find_king(self, color):
        for r in range(8):
            for c in range(8):
                piece = self.get_piece((r, c))
                if isinstance(piece, King) and piece.color == color: return (r, c)
        return None

    def setup_pieces(self):
        for r, color in [(0, 'black'), (7, 'white')]:
            self.set_piece((r, 0), Rook(color, (r, 0), name="Q_rook"))
            self.set_piece((r, 7), Rook(color, (r, 7), name="K_rook"))
            self.set_piece((r, 1), Knight(color, (r, 1), name="Q_knight"))
            self.set_piece((r, 6), Knight(color, (r, 6), name="K_knight"))
            self.set_piece((r, 2), Bishop(color, (r, 2), name="Q_bishop"))
            self.set_piece((r, 5), Bishop(color, (r, 5), name="K_bishop"))
            self.set_piece((r, 3), Queen(color, (r, 3)))
            self.set_piece((r, 4), King(color, (r, 4)))
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
        self.position_history = {} # For 50-move rule, threefold rep
        self.game_id = f"chs-{uuid.uuid4()}"
        self.game_data = [] # Structured log of all moves
        self._record_position()
        self._pre_move_state = None # For "take back" functionality

    def pos_to_notation(self, pos):
        r, c = pos
        return f"{'abcdefgh'[c]}{8-r}"

    def _get_board_state_string(self):
        """Generates a FEN-like string for position history tracking."""
        state_parts = []
        for r in range(8):
            empty_count = 0
            for c in range(8):
                piece = self.board.get_piece((r,c))
                if piece:
                    if empty_count > 0:
                        state_parts.append(str(empty_count))
                        empty_count = 0
                    state_parts.append(piece.symbol)
                else:
                    empty_count += 1
            if empty_count > 0:
                state_parts.append(str(empty_count))
            if r < 7:
                state_parts.append('/')
        
        # Add turn
        state_parts.append(f" {self.turn[0]} ")
        
        # --- FIXED Castling Rights Logic ---
        castling_rights = ""
        
        # White King
        white_king = self.board.get_piece((7,4))
        if white_king and isinstance(white_king, King) and not white_king.has_moved:
            # White Kingside Rook
            white_rook_k = self.board.get_piece((7,7))
            if white_rook_k and isinstance(white_rook_k, Rook) and not white_rook_k.has_moved:
                castling_rights += "K"
            # White Queenside Rook
            white_rook_q = self.board.get_piece((7,0))
            if white_rook_q and isinstance(white_rook_q, Rook) and not white_rook_q.has_moved:
                castling_rights += "Q"

        # Black King
        black_king = self.board.get_piece((0,4))
        if black_king and isinstance(black_king, King) and not black_king.has_moved:
            # Black Kingside Rook
            black_rook_k = self.board.get_piece((0,7))
            if black_rook_k and isinstance(black_rook_k, Rook) and not black_rook_k.has_moved:
                castling_rights += "k"
            # Black Queenside Rook
            black_rook_q = self.board.get_piece((0,0))
            if black_rook_q and isinstance(black_rook_q, Rook) and not black_rook_q.has_moved:
                castling_rights += "q"
                
        state_parts.append(f"{castling_rights if castling_rights else '-'} ")
        # --- END Fixed Logic ---

        # Add en passant
        state_parts.append(f"{self.pos_to_notation(self.en_passant_target) if self.en_passant_target else '-'}")
        
        return "".join(state_parts)

    def get_board_state_narrative(self):
        """
        Generates a 100% accurate, human-readable narrative of the
        current board state for the (old) COACH LLM Q&A tool.
        """
        narrative = []
        pieces = {'white': [], 'black': []}
        
        for r in range(8):
            for c in range(8):
                piece = self.board.get_piece((r, c))
                if piece:
                    pos_str = self.pos_to_notation((r, c))
                    attack_squares = [self.pos_to_notation(pos) for pos in piece.get_attack_squares(self.board)]
                    attack_str = f" (Attacking: {', '.join(attack_squares)})" if attack_squares else ""
                    pieces[piece.color].append(f"{piece.name} on {pos_str}{attack_str}")

        narrative.append("Board State:\n")
        narrative.append("White Pieces:")
        narrative.extend([f"- {p}" for p in pieces['white']])
        narrative.append("\nBlack Pieces:")
        narrative.extend([f"- {p}" for p in pieces['black']])
        
        narrative.append("\nGame Status:")
        narrative.append(f"- It is {self.turn.capitalize()}'s turn to move.")
        
        king_pos = self.board.find_king(self.turn)
        if king_pos and self.is_in_check(self.turn):
            narrative.append(f"- The {self.turn.capitalize()} King is in check.")
        
        # Build castling rights string
        castling_rights = []
        king_w, king_b = self.board.get_piece((7,4)), self.board.get_piece((0,4))
        rook_wk, rook_wq = self.board.get_piece((7,7)), self.board.get_piece((7,0))
        rook_bk, rook_bq = self.board.get_piece((0,7)), self.board.get_piece((0,0))

        if king_w and not king_w.has_moved:
            if rook_wk and not rook_wk.has_moved: castling_rights.append("White Kingside")
            if rook_wq and not rook_wq.has_moved: castling_rights.append("White Queenside")
        if king_b and not king_b.has_moved:
            if rook_bk and not rook_bk.has_moved: castling_rights.append("Black Kingside")
            if rook_bq and not rook_bq.has_moved: castling_rights.append("Black Queenside")
            
        if castling_rights:
            narrative.append(f"- Castling is available for: {', '.join(castling_rights)}.")
        else:
            narrative.append("- Castling is no longer available for either side.")

        if self.en_passant_target:
            narrative.append(f"- The en passant target square is {self.pos_to_notation(self.en_passant_target)}.")
        else:
            narrative.append("- There is no en passant target square.")
            
        return "\n".join(narrative)

    def _record_position(self):
        """Records the FEN-like string for repetition tracking."""
        state_key = self._get_board_state_string()
        self.position_history[state_key] = self.position_history.get(state_key, 0) + 1

    def _record_move_data(self, piece, start_pos, end_pos, captured_piece, promoted_into=None):
        """Records a detailed log of the move in self.game_data."""
        opponent_color = 'black' if piece.color == 'white' else 'white'
        is_check = self.is_in_check(opponent_color)
        is_checkmate = is_check and self.is_checkmate(opponent_color)
        
        move_data = {
            'game_id': self.game_id, 'turn': len(self.game_data) + 1, 'color': piece.color,
            'piece_moved': piece.name, 'start_square': self.pos_to_notation(start_pos),
            'end_square': self.pos_to_notation(end_pos), 'capture': 1 if captured_piece else 0,
            'captured_piece': captured_piece.name if captured_piece else 'NA',
            'check': 1 if is_check else 0,
            'checkmate': 1 if is_checkmate else 0,
            'promoted': 1 if promoted_into else 0, 'promoted_into': promoted_into if promoted_into else 'NA',
            'draw': 0, # This will be updated by _update_game_status if true
            'move_notation': f"{self.pos_to_notation(start_pos)}-{self.pos_to_notation(end_pos)}" # (NEW) For Coach 2.0
        }
        self.game_data.append(move_data)

    def _check_insufficient_material(self):
        """Checks for draw by insufficient material."""
        pieces = [p for row in self.board.grid for p in row if p]
        
        # King vs King
        if len(pieces) == 2: return True
        
        # King vs King + (Knight or Bishop)
        if len(pieces) == 3 and any(isinstance(p, (Knight, Bishop)) for p in pieces): return True
        
        # TODO: Add more complex rules (e.g., two knights vs king is a draw)
        return False

    def _update_game_status(self):
        """Updates the game status message based on the current board state."""
        # Note: This is called *after* a move, so self.turn is the *next* player
        if self.is_checkmate(self.turn):
            self.game_over = True
            self.status_message = f"Checkmate! {'White' if self.turn == 'black' else 'Black'} wins."
        elif self.is_stalemate(self.turn):
            self.game_over = True
            self.status_message = "Stalemate! The game is a draw."
        elif self.position_history.get(self._get_board_state_string(), 0) >= 5:
            # FIDE rule: 5-fold repetition is an automatic draw
            self.game_over = True
            self.status_message = "Draw by fivefold repetition."
        elif self._check_insufficient_material():
            self.game_over = True
            self.status_message = "Draw by insufficient material."
        else:
            self.status_message = f"{self.turn.capitalize()}'s turn"
            if self.is_in_check(self.turn): self.status_message += " (in check)."
            
        if self.game_over and "draw" in self.status_message.lower():
             if self.game_data: self.game_data[-1]['draw'] = 1

    def is_square_attacked(self, pos, attacker_color):
        """Checks if a specific square is attacked by any piece of the attacker's color."""
        for r in range(8):
            for c in range(8):
                piece = self.board.get_piece((r, c))
                if piece and piece.color == attacker_color:
                    if pos in piece.get_attack_squares(self.board):
                        return True
        return False

    def _get_attackers_of_square(self, pos, attacker_color):
        """(NEW) Helper function to get a list of all pieces attacking a square."""
        attackers = []
        for r in range(8):
            for c in range(8):
                piece = self.board.get_piece((r, c))
                if piece and piece.color == attacker_color:
                    if pos in piece.get_attack_squares(self.board):
                        attackers.append(piece)
        return attackers

    def _get_all_legal_moves_tuples(self, color):
        """
        (NEW) Internal helper to get all legal moves as (start, end, piece) tuples.
        This is the new source of truth for all move generation.
        """
        for r in range(8):
            for c in range(8):
                piece = self.board.get_piece((r, c))
                if piece and piece.color == color:
                    start_pos = (r, c)
                    for end_pos in piece.get_valid_moves(self.board, self):
                        if not self.move_puts_king_in_check(start_pos, end_pos):
                            yield (start_pos, end_pos, piece) # Yield a generator

    def _get_all_legal_moves(self, color):
        """
        Gets all legal moves (in 'e2-e4' format) for a given color.
        (MODIFIED) Uses the new tuple generator.
        """
        all_moves = []
        for start_pos, end_pos, _ in self._get_all_legal_moves_tuples(color):
            all_moves.append(f"{self.pos_to_notation(start_pos)}-{self.pos_to_notation(end_pos)}")
        return all_moves
        
    def get_tactical_threats(self, color_being_threatened):
        """
        (NEW) This is the "Dangers List" / "Smart Triage List" generator.
        It scans the *current* board for threats against the given color,
        including simple threats and pins.
        """
        tactical_threats = []
        opponent_color = 'black' if color_being_threatened == 'white' else 'white'
        
        for r in range(8):
            for c in range(8):
                threatened_piece = self.board.get_piece((r, c))
                
                # 1. Is this one of our pieces?
                if not threatened_piece or threatened_piece.color != color_being_threatened:
                    continue
                    
                pos = (r, c)
                
                # 2. Is this piece attacked?
                attackers = self._get_attackers_of_square(pos, opponent_color)
                if not attackers:
                    continue # Not attacked, not a threat.
                    
                # 3. This piece is attacked. Now check for pins.
                is_pin = False
                pinned_to_piece_data = None
                
                for attacker in attackers:
                    # Pins only apply to sliding pieces (Queen, Rook, Bishop)
                    if not hasattr(attacker, 'directions'):
                        continue
                        
                    # Calculate direction from attacker to our piece
                    dr = pos[0] - attacker.position[0]
                    dc = pos[1] - attacker.position[1]
                    
                    # Normalize direction
                    unit_dr = 0 if dr == 0 else dr // abs(dr)
                    unit_dc = 0 if dc == 0 else dc // abs(dc)
                    
                    # If this direction isn't in the attacker's moveset, it's not a pin
                    if (unit_dr, unit_dc) not in attacker.directions:
                        continue
                        
                    # 4. Scan *past* our piece along the same line
                    for i in range(1, 8):
                        scan_pos = (pos[0] + i * unit_dr, pos[1] + i * unit_dc)
                        
                        if not (0 <= scan_pos[0] < 8 and 0 <= scan_pos[1] < 8):
                            break # Off board
                            
                        scanned_piece = self.board.get_piece(scan_pos)
                        
                        if scanned_piece:
                            # We hit another piece.
                            if scanned_piece.color == color_being_threatened:
                                # It's a friendly piece. This is a PIN!
                                is_pin = True
                                pinned_to_piece_data = {
                                    "name": scanned_piece.name,
                                    "position": self.pos_to_notation(scan_pos),
                                    "value": scanned_piece.value
                                }
                            # If it's an enemy piece, it blocks the pin.
                            # In either case, the scan along this line stops.
                            break 
                            
                    if is_pin:
                        break # Found a pin, no need to check other attackers

                # 5. Build the JSON packet for this single threat
                tactical_threats.append({
                    "threatened_piece": {
                        "name": threatened_piece.name,
                        "position": self.pos_to_notation(pos),
                        "value": threatened_piece.value
                    },
                    "attacking_pieces": [
                        {"name": p.name, "position": self.pos_to_notation(p.position), "value": p.value} 
                        for p in attackers
                    ],
                    "is_pin": is_pin,
                    "pinned_to_piece": pinned_to_piece_data
                })
                
        return tactical_threats

    def get_all_legal_moves_with_consequences(self, color):
        """
        (MODIFIED) This is the new "Move Consequence Mapping" function.
        It simulates every legal move to see what its results are
        (captures, checks, attacks) AND checks for retaliation.
        This is the "predictive" ground truth for the AI Opponent Agent.
        """
        enhanced_moves_list = []
        opponent_color = 'black' if color == 'white' else 'white'

        # Use the new tuple generator to get all legal moves
        for start_pos, end_pos, piece in self._get_all_legal_moves_tuples(color):
            
            move_notation = f"{self.pos_to_notation(start_pos)}-{self.pos_to_notation(end_pos)}"
            
            # --- (NEW) Define the packet structure ---
            captured_piece_on_square = self.board.get_piece(end_pos)
            packet = {
                "move": move_notation,
                "moving_piece": {
                    "name": piece.name,
                    "value": piece.value,
                    "previous_move_count": piece.move_count # (NEW) Add tempo data
                },
                "captured_piece": None,
                "consequences": [],
                "retaliation": [], # (NEW) For the 2-ply check
                "defenders": [], # (NEW) For the defense check
                "creates_pin": None, # (NEW) For offensive pin check
                "is_fork": False # (NEW) For offensive fork check
            }

            # --- Simulate Move ---
            original_piece_has_moved = piece.has_moved # Store pre-move state
            original_move_count = piece.move_count # (NEW) Store pre-move state
            
            self.board.set_piece(end_pos, piece)
            self.board.set_piece(start_pos, None)
            piece.has_moved = True # Temporarily set
            piece.move_count += 1 # (NEW) Temporarily set
            
            # --- Analyze Consequences of the *simulated* board state ---
            
            # 1. Was it a capture?
            if captured_piece_on_square:
                packet["consequences"].append(f"Captures {captured_piece_on_square.name} on {self.pos_to_notation(end_pos)}")
                packet["captured_piece"] = {"name": captured_piece_on_square.name, "value": captured_piece_on_square.value}
            
            # 2. Does the moved piece now attack anything?
            attacked_high_value_pieces = []
            for attack_pos in piece.get_attack_squares(self.board):
                target = self.board.get_piece(attack_pos)
                if target and target.color == opponent_color:
                    packet["consequences"].append(f"Attacks {target.name} on {self.pos_to_notation(attack_pos)}")
                    # (NEW) Track high-value attacks for fork detection
                    if target.value >= 3: # Knight, Bishop, Rook, Queen
                        attacked_high_value_pieces.append(target)
            
            # (NEW) 2a. Check for Forks
            if len(attacked_high_value_pieces) >= 2:
                packet["is_fork"] = True
                
            # 3. Does this move deliver check?
            is_check = self.is_in_check(opponent_color)
            if is_check:
                packet["consequences"].append("Delivers check!")
                # (NEW) Check if the check is *also* a high-value attack (a fork)
                king_pos = self.board.find_king(opponent_color)
                # Avoid double-counting if king is already in the list
                if king_pos and king_pos not in [p.position for p in attacked_high_value_pieces]:
                    attacked_high_value_pieces.append(self.board.get_piece(king_pos))
            
            # (NEW) Re-check for forks including the King
            if len(attacked_high_value_pieces) >= 2:
                packet["is_fork"] = True
                
            # 4. (NEW) Retaliation Check
            # Is the square the piece *landed on* attacked by the opponent?
            if self.is_square_attacked(end_pos, opponent_color):
                # Find all pieces that are attacking that square
                for r in range(8):
                    for c in range(8):
                        attacker_piece = self.board.get_piece((r, c))
                        if attacker_piece and attacker_piece.color == opponent_color:
                            if end_pos in attacker_piece.get_attack_squares(self.board):
                                packet["retaliation"].append({
                                    "name": attacker_piece.name,
                                    "value": attacker_piece.value,
                                    "position": self.pos_to_notation((r,c))
                                })

            # 4b. (NEW) Defender Check
            # Is the square the piece *landed on* defended by its *own* team?
            for r in range(8):
                for c in range(8):
                    defender_piece = self.board.get_piece((r, c))
                    # Check if it's a friendly piece AND *not* the piece that just moved
                    if defender_piece and defender_piece.color == color and defender_piece.position != end_pos:
                        if end_pos in defender_piece.get_attack_squares(self.board):
                            packet["defenders"].append({
                                "name": defender_piece.name,
                                "value": defender_piece.value,
                                "position": self.pos_to_notation((r,c))
                            })

            # (NEW) 5. Check if this move *creates* a pin (Offensive Pin)
            if hasattr(piece, 'directions'): # Only sliding pieces can pin
                for dr, dc in piece.directions:
                    # Scan along this direction from the piece's new position
                    first_opponent_piece = None
                    for i in range(1, 8):
                        scan_pos = (end_pos[0] + i * dr, end_pos[1] + i * dc)
                        
                        if not (0 <= scan_pos[0] < 8 and 0 <= scan_pos[1] < 8):
                            break # Off board
                            
                        scanned_piece = self.board.get_piece(scan_pos)
                        
                        if scanned_piece:
                            if scanned_piece.color == opponent_color:
                                if not first_opponent_piece:
                                    first_opponent_piece = scanned_piece
                                else:
                                    # This is the *second* opponent piece on the line
                                    # We have created a pin!
                                    packet["creates_pin"] = {
                                        "pinned_piece": {
                                            "name": first_opponent_piece.name,
                                            "position": self.pos_to_notation(first_opponent_piece.position),
                                            "value": first_opponent_piece.value
                                        },
                                        "pinned_to_piece": {
                                            "name": scanned_piece.name,
                                            "position": self.pos_to_notation(scanned_piece.position),
                                            "value": scanned_piece.value
                                        }
                                    }
                                    break # Pin found, stop scanning this line
                            else:
                                # Hit a friendly piece, blocks the pin
                                break
                    if packet["creates_pin"]:
                        break # Pin found, stop checking directions

            # --- Undo Move ---
            self.board.set_piece(start_pos, piece)
            self.board.set_piece(end_pos, captured_piece_on_square)
            piece.has_moved = original_piece_has_moved # Restore
            piece.move_count = original_move_count # (NEW) Restore
            
            # --- Store Result ---
            if not packet["consequences"]:
                packet["consequences"].append("Positional move")
                
            enhanced_moves_list.append(packet)
            
        return enhanced_moves_list


    def _notation_to_pos_tuple(self, notation):
        """Converts 'e4' to (4, 4)."""
        files, rank = "abcdefgh", notation[1]
        return (8 - int(rank), files.index(notation[0]))

    def store_pre_move_state(self):
        """Saves the game state before a move for the 'take back' feature."""
        self._pre_move_state = {
            'board': copy.deepcopy(self.board), 'turn': self.turn,
            'status_message': self.status_message, 'move_history': list(self.move_history),
            'promotion_pending': self.promotion_pending, 'en_passant_target': self.en_passant_target,
            'position_history': dict(self.position_history), 'game_data': list(self.game_data)
        }
        
    def revert_to_pre_move_state(self):
        """Restores the game state from the saved pre-move state."""
        if self._pre_move_state:
            for key, value in self._pre_move_state.items():
                setattr(self, key, value)
            self._pre_move_state = None
            return True
        return False
        
    def clear_pre_move_state(self):
        """Clears the pre-move state, "finalizing" the move."""
        self._pre_move_state = None

    def make_move(self, start_pos, end_pos):
        """
        Attempts to make a move on the board.
        Returns (True, "Message") on success or (False, "Error") on failure.
        """
        piece = self.board.get_piece(start_pos)
        
        # --- Validation ---
        if not piece: return False, "No piece at start square."
        if piece.color != self.turn: return False, "Not your turn."
        if self.game_over: return False, "The game is over."
        if end_pos not in [m[0] for m in piece.get_valid_moves(self.board, self)]:
             # Check if the move is in the list of valid move tuples
             # This is a fallback check in case get_valid_moves is just returning tuples
             # A cleaner way would be to ensure get_valid_moves always returns (r,c)
             
             # Let's assume get_valid_moves *does* return (r,c) tuples
             # and check the original logic
             valid_moves_list = piece.get_valid_moves(self.board, self)
             if end_pos not in valid_moves_list:
                 return False, "Invalid move for this piece."
                 
        if self.move_puts_king_in_check(start_pos, end_pos): return False, "Cannot move into check."
        
        # --- Handle Castling ---
        if isinstance(piece, King) and abs(start_pos[1] - end_pos[1]) == 2:
            is_kingside = end_pos[1] > start_pos[1]
            rook_start = (start_pos[0], 7 if is_kingside else 0)
            rook_end = (start_pos[0], 5 if is_kingside else 3)
            self.board.move_piece(start_pos, end_pos) # Move King
            self.board.move_piece(rook_start, rook_end) # Move Rook
            self.move_history.append("O-O" if is_kingside else "O-O-O")
            self._record_move_data(piece, start_pos, end_pos, None)
        else:
            # --- Handle Standard Moves ---
            
            # Check for promotion
            if isinstance(piece, Pawn) and end_pos[0] in [0, 7]:
                captured_piece = self.board.get_piece(end_pos)
                self.promotion_pending = (start_pos, end_pos, captured_piece, piece)
                self.status_message = f"{self.turn.capitalize()} to promote pawn."
                return True, "Promotion" # Special status for UI
            
            # Check for en passant
            is_en_passant = isinstance(piece, Pawn) and end_pos == self.en_passant_target
            captured_piece = None
            
            if is_en_passant:
                pawn_dir = -1 if piece.color == 'white' else 1
                captured_pawn_pos = (end_pos[0] - pawn_dir, end_pos[1])
                captured_piece = self.board.get_piece(captured_pawn_pos)
                self.board.set_piece(captured_pawn_pos, None) # Remove captured pawn
                self.board.move_piece(start_pos, end_pos) # Move attacking pawn
            else:
                captured_piece = self.board.move_piece(start_pos, end_pos) # Standard move
            
            # Set new en passant target if this was a 2-step pawn move
            self.en_passant_target = ((start_pos[0] + end_pos[0]) // 2, start_pos[1]) if isinstance(piece, Pawn) and abs(start_pos[0] - end_pos[0]) == 2 else None
            
            move_notation = f"{piece.symbol} {self.pos_to_notation(start_pos)}-{self.pos_to_notation(end_pos)}"
            if captured_piece: move_notation += f" (captures {captured_piece.symbol})"
            self.move_history.append(move_notation)
            self._record_move_data(piece, start_pos, end_pos, captured_piece)

        # --- Post-Move Updates ---
        self.turn = 'black' if self.turn == 'white' else 'white'
        self._record_position()
        self._update_game_status()
        return True, self.status_message

    def promote_pawn(self, piece_choice_str):
        """Finalizes a pawn promotion move."""
        if not self.promotion_pending: return False, "No promotion pending."
        
        start_pos, end_pos, captured_piece, original_pawn = self.promotion_pending
        
        piece_map = {'Queen': Queen, 'Rook': Rook, 'Bishop': Bishop, 'Knight': Knight}
        new_piece = piece_map[piece_choice_str](self.turn, end_pos) # Use self.turn (which is still pre-switch)
        
        self.board.set_piece(start_pos, None)
        self.board.set_piece(end_pos, new_piece)
        
        self.promotion_pending = None
        self.move_history.append(f"{self.pos_to_notation(end_pos)}={new_piece.symbol}")
        
        # Record the move data *after* all pieces are in place
        self._record_move_data(original_pawn, start_pos, end_pos, captured_piece, promoted_into=piece_choice_str)
        
        # Now, switch turns and update status
        self.turn = 'black' if self.turn == 'white' else 'white'
        self._record_position()
        self._update_game_status()
        return True, "Pawn promoted."

    def is_in_check(self, color):
        """Checks if the king of the given color is in check."""
        king_pos = self.board.find_king(color)
        if not king_pos: return False # Should not happen
        return self.is_square_attacked(king_pos, 'black' if color == 'white' else 'white')

    def move_puts_king_in_check(self, start_pos, end_pos):
        """
        Simulates a move and checks if it results in the
        moving player's king being in check.
        """
        original_piece = self.board.get_piece(start_pos)
        captured_piece = self.board.get_piece(end_pos)
        original_has_moved = original_piece.has_moved
        original_move_count = original_piece.move_count # (NEW) Store move count
        
        # Simulate move
        self.board.set_piece(end_pos, original_piece)
        self.board.set_piece(start_pos, None)
        
        in_check = self.is_in_check(original_piece.color)
        
        # Undo move
        self.board.set_piece(start_pos, original_piece)
        self.board.set_piece(end_pos, captured_piece)
        original_piece.has_moved = original_has_moved # (FIX) Restore has_moved state
        original_piece.move_count = original_move_count # (NEW) Restore move count
        
        return in_check

    def has_legal_moves(self, color):
        """
        Checks if the given color has any legal moves.
        (MODIFIED) Uses the new tuple generator.
        """
        try:
            # Get the first item from the generator.
            # If it exists, we have a legal move.
            next(self._get_all_legal_moves_tuples(color))
            return True
        except StopIteration:
            # The generator was empty, no legal moves.
            return False
    
    def is_checkmate(self, color):
        """Checks if the given color is in checkmate."""
        return self.is_in_check(color) and not self.has_legal_moves(color)

    def is_stalemate(self, color):
        """Checks if the given color is in stalemate."""
        return not self.is_in_check(color) and not self.has_legal_moves(color)


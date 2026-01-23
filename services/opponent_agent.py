from services.llm_service import llm_service
import chess

class OpponentAgent:
    def __init__(self):
        self.system_prompt = """
        You are a Chess Grandmaster AI.
        Your goal is to play high-quality chess moves.
        """

    def get_move(self, fen: str, difficulty="hard"):
        """
        Gets a move from the LLM, verifies legality, and returns it.
        """
        board = chess.Board(fen)
        legal_moves = [move.uci() for move in board.legal_moves]
        move_history = [] # TODO: Pass history if needed for context
        color = "White" if board.turn == chess.WHITE else "Black"
        
        # Call LLM
        response = llm_service.get_move_recommendation(
            fen=fen,
            legal_moves=str(legal_moves),
            move_history=str(move_history),
            color=color
        )
        
        if not response:
            return None, "Thinking failed."
            
        # Parse response: Expected "Reasoning: ... || Move: <SAN/UCI>"
        # We need to be robust.
        try:
            # Simple parsing strategy
            if "|| Move:" in response:
                parts = response.split("|| Move:")
                reasoning = parts[0].replace("Reasoning:", "").strip()
                move_str = parts[1].strip()
            elif "Move:" in response:
                parts = response.split("Move:")
                reasoning = "I chose this move based on the position."
                move_str = parts[1].strip()
            else:
                # Fallback: try to find a valid move in the text
                move_str = response.strip()
                reasoning = "Strategic choice."

            # Verify legality (Sanitization)
            # LLM might output SAN (e.g. Nf3) or UCI (e.g. g1f3)
            # python-chess push_san handles SAN. push_uci handles UCI.
            
            try:
                move = board.parse_san(move_str)
            except:
                try:
                    move = board.parse_uci(move_str)
                except:
                    print(f"Invalid move format from LLM: {move_str}")
                    return None, f"I tried to play {move_str} but it was illegal."

            if move in board.legal_moves:
                return move.uci(), reasoning
            else:
                return None, f"Illegal move suggested: {move_str}"

        except Exception as e:
            print(f"Error parsing opponent move: {e}")
            return None, "Error processing move."

# Singleton
opponent_agent = OpponentAgent()

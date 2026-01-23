from services.llm_service import llm_service

class CoachAgent:
    def __init__(self):
        self.system_prompt = """
        You are Coach Joey, a friendly and energetic kangaroo chess coach! 🦘
        Your goal is to help beginners learn chess in a fun way. 
        
        - Be encouraging and use chess emojis occasionally.
        - If the user asks for a hint, look at the provided board state (FEN) and give a general strategic tip, but don't give away the exact best move unless asked effectively.
        - Avoid long lectures. Keep responses concise and conversational.
        - You are playing the role of a coach, not the opponent.
        """

    def get_response(self, user_message, fen, move_history):
        context_str = f"Current Board FEN: {fen}\nMove History: {move_history}"
        # Combine system prompt with dynamic context
        full_system = f"{self.system_prompt}\n\nContext:\n{context_str}"
        
        return llm_service.get_chat_response(
            system_instruction=full_system,
            user_message=user_message
        )

# Singleton
coach_agent = CoachAgent()

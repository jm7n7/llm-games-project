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
        # Q&A Router Logic (Simplified for now, or we can port the full router)
        # Using Flash for speed as requested
        model = "gemini-2.5-flash"
        
        context_str = f"Current Board FEN: {fen}\nMove History: {move_history}"
        full_system = f"{self.system_prompt}\n\nContext:\n{context_str}"
        
        return llm_service.get_chat_response(
            system_instruction=full_system,
            user_message=user_message,
            model=model
        )

    def analyze_move(self, fen, move_history, last_move_san):
        """
        Analyzes the user's recent move using the Triage -> Conversational pipeline.
        Uses gemini-2.5-flash.
        """
        model = "gemini-2.5-flash"
        
        # 1. Triage Analyst (The Logic)
        triage_prompt = f"""
        You are a Chess Triage Analyst. Analyze the user's move: {last_move_san}
        FEN: {fen}
        
        Determine if this was a BLUNDER (hangs piece), GREAT move, or NORMAL.
        Output JSON: {{ "verdict": "blunder"|"good"|"normal"|"great", "justification": "..." }}
        """
        
        triage_json = llm_service.get_chat_response(
            system_instruction="You are a strict chess engine analyst. Output JSON only.",
            user_message=triage_prompt,
            model=model
        )
        
        # 2. Conversational Coach (The Voice)
        coach_prompt = f"""
        You are Coach Joey. Your internal analyst just said this about the user's move ({last_move_san}):
        {triage_json}
        
        Create a friendly, single-sentence response for the user.
        If verdict is 'blunder', format as: {{ "type": "intervention", "message": "..." }}
        Else: {{ "type": "normal", "message": "..." }}
        """
        
        response_text = llm_service.get_chat_response(
            system_instruction="You are a friendly chess coach. Output JSON only.",
            user_message=coach_prompt,
            model=model
        )
        
        # Parse result
        import json
        import re
        try:
            clean = re.sub(r'```json|```', '', response_text).strip()
            data = json.loads(clean)
            return data
        except:
            return {"type": "normal", "message": response_text}

# Singleton
coach_agent = CoachAgent()

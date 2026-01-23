import os
import logging
from google import genai
from google.genai import types

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        """Initializes the Vertex AI client using Application Default Credentials."""
        try:
            # Initialize the client. 
            # 'vertexai=True' enables the Vertex AI backend (vs. Google AI Studio).
            # It automatically uses ADC from the environment (Cloud Run or local 'gcloud auth').
            # Location can be customized, 'us-central1' is a safe default for Vertex.
            self.client = genai.Client(vertexai=True, location='us-central1')
            self.model_name = "gemini-2.0-flash-exp" # Or "gemini-1.5-pro" based on availability
            logger.info(f"LLMService initialized with model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize LLMService: {e}")
            self.client = None

    def get_chat_response(self, system_instruction: str, user_message: str, history: list = None) -> str:
        """
        Generates a chat response from the LLM.
        
        Args:
            system_instruction: The persona/rules for the agent.
            user_message: The latest input from the user.
            history: Optional list of previous turn objects (managed by frontend or session).
                     Expected format compatible with the SDK's history if using stateful chat,
                     or we can just append to prompt.
                     
        Returns:
            The text response from the model.
        """
        if not self.client:
            return "Error: LLM Service not available."

        try:
            # Construct a simple content list for stateless call or maintain chat session
            # For simplicity in this architecture, we'll treat it as a single turn with history context if provided
            # But the SDK supports a chat session.
            
            # config = types.GenerateContentConfig(
            #     system_instruction=system_instruction,
            #     temperature=0.7,
            # )
            
            # For now, let's just do a direct generate_content with the system prompt included or config
            # usage: client.models.generate_content(model='...', contents='...', config=...)
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=user_message,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.7
                )
            )
            
            if response.text:
                return response.text
            return "I'm not sure what to say."

        except Exception as e:
            logger.error(f"Error generating chat response: {e}")
            return "I encountered an error while thinking."

    def get_move_recommendation(self, fen: str, legal_moves: list, move_history: list, color: str) -> str:
        """
        Asks the LLM for a chess move.
        """
        if not self.client:
            return None

        prompt = f"""
        You are a Chess Grandmaster engine. 
        Current FEN: {fen}
        Your Color: {color}
        Legal Moves: {legal_moves}
        Move History: {move_history}
        
        Analyze the position and select the best move from the Legal Moves list.
        Explain your reasoning briefly in one sentence, then output the move in SAN format.
        Format your response EXACTLY as: "Reasoning: <text> || Move: <SAN>"
        """
        
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3 # Lower temp for logic
                )
            )
            return response.text
        except Exception as e:
            logger.error(f"Error generating move: {e}")
            return None
            
# Singleton instance
llm_service = LLMService()

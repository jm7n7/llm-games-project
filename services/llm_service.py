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
            self.model_name = "gemini-2.5-flash" # Or "gemini-1.5-pro" based on availability
            logger.info(f"LLMService initialized with model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize LLMService: {e}")
            self.client = None

    
    def get_chat_response(self, system_instruction: str, user_message: str, history: list = None, model: str = None, tools: list = None) -> str:
        """
        Generates a chat response from the LLM.
        """
        if not self.client:
            return "Error: LLM Service not available."

        target_model = model if model else self.model_name

        try:
            config_args = {
                "system_instruction": system_instruction,
                "temperature": 0.7,
            }
            if tools:
                config_args["tools"] = tools

            response = self.client.models.generate_content(
                model=target_model,
                contents=user_message,
                config=types.GenerateContentConfig(**config_args)
            )
            
            # TODO: Handle function calls if tools are used (not fully implemented in this wrapper yet)
            # For now, we assume text response or simple tool usage.
            
            if response.text:
                return response.text
            return "I'm not sure what to say."

        except Exception as e:
            logger.error(f"Error generating chat response: {e}")
            return "I encountered an error while thinking."

    def get_move_recommendation(self, fen: str, legal_moves: list, move_history: list, color: str, model: str = None) -> str:
        """
        Asks the LLM for a chess move.
        """
        if not self.client:
            return None

        target_model = model if model else self.model_name

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
                model=target_model,
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

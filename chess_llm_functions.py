import google.generativeai as genai
import json
import os
import random
from dotenv import load_dotenv
load_dotenv()

# --- API KEY CONFIG ---
# Ensure these are set in your environment or .env file
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
AI_OPPONENT_KEY = os.environ.get("AI_OPPONENT_KEY")
COACH_KEY = os.environ.get("COACH_KEY")
COMMENTATOR_KEY = os.environ.get("COMMENTATOR_KEY")

# --- MODEL INITIALIZATION ---
# Using specific models as requested by the architecture
commentator_model = genai.GenerativeModel('gemini-2.5-flash')
coach_model = genai.GenerativeModel('gemini-2.5-pro')
opponent_model = genai.GenerativeModel('gemini-2.5-flash')

# --- COMMENTATOR FUNCTION (NOW ACTIVELY USED) ---
def get_move_commentary(move_data_dict):
    """
    Uses the Commentator LLM to turn a single move's data (a dictionary)
    into a single, natural language sentence.
    """
    try:
        genai.configure(api_key=COMMENTATOR_KEY)
        prompt = f"""
        You are a chess commentator. Your task is to describe the following chess move,
        provided in a Python dictionary format, in a single, natural-language sentence.
        Do not add any preamble or explanation. Just the sentence.
        
        Example: "White's queen captures the black knight on f6."
        
        Move Data: {json.dumps(move_data_dict)}
        """
        # --- FIX: Added the missing API call and return ---
        response = commentator_model.generate_content(prompt)
        return response.text.strip()
    # --- FIX: Added the missing except block ---
    except Exception as e:
        print(f"Error calling Commentator LLM: {e}")
        # Provide a fallback commentary that still works
        return f"Move: {move_data_dict.get('piece_moved')} from {move_data_dict.get('start_square')} to {move_data_dict.get('end_square')}."

# --- AI OPPONENT FUNCTIONS (MODIFIED) ---

# This function is no longer needed with a stateless model
# def initialize_opponent_chat():
#     ...

def get_ai_opponent_move(game_data_history_str, legal_moves_list): # Removed chat_session
    """
    Sends the full game history (JSON) to the Opponent LLM and gets its next move
    using a stateless generate_content call.
    """
    
    # Persona and history setup
    persona_prompt = """
    You are an AI Chess Opponent. Your sole purpose is to play chess. 
    You will be given the entire game history as a JSON log and a list of legal moves.
    
    Your response MUST be a valid JSON object with one key: "move".
    - The "move" value must be one of the legal moves provided.
    
    Your goal is to win by playing a strong, challenging, and human-like game.
    """
    
    dynamic_prompt = f"""
    Here is the game history so far in a list of dictionaries format (JSON):
    {game_data_history_str}

    Here is the list of your available legal moves:
    {", ".join(legal_moves_list)}

    Based on this history, provide your response in the required JSON format.
    """

    # Construct the full contents for the one-shot call
    # This mimics the old chat history but in a single request
    contents = [
        {'role': 'user', 'parts': [persona_prompt]},
        {'role': 'model', 'parts': ['{"move": "Understood. I will select a move from the legal moves list and provide it in the required JSON format."}']},
        {'role': 'user', 'parts': [dynamic_prompt]}
    ]

    try:
        genai.configure(api_key=AI_OPPONENT_KEY)
        
        # Use generate_content instead of chat_session.send_message
        response = opponent_model.generate_content(contents) 
        
        # Clean the response to extract only the JSON part
        json_str = response.text.strip().replace("```json", "").replace("```", "").strip()
        parsed_json = json.loads(json_str)
        
        # Validate move
        if 'move' in parsed_json and parsed_json['move'] in legal_moves_list:
            return parsed_json
        else:
            # Fallback if LLM provides an invalid move
            raise ValueError(f"LLM returned invalid move: {parsed_json.get('move')}")
            
    except Exception as e:
        print(f"Error calling Opponent LLM or parsing JSON: {e}")
        # Fallback move if the LLM fails
        return {"move": random.choice(legal_moves_list)}


# --- COACH FUNCTIONS (MODIFIED FOR NEW CONTEXT) ---

class _MockChunk:
    """Mocks a stream chunk object with a .text attribute for fallback."""
    def __init__(self, text):
        self.text = text

def initialize_coach_chat():
    """
    Initializes and returns a new chat session with the Coach LLM,
    including the *updated* system persona prompt.
    """
    persona_prompt = """
    You are 'Coach Gemini,' a grandmaster-level chess player and expert coach.
    You excel at explaining complex ideas simply.
    Your sole purpose is to provide helpful, turn-by-turn feedback to a student
    to help them improve. YOU DO NOT PLAY THE GAME.

    You will be given the full `GAME_HISTORY_JSON` and the `LAST_MOVE_COMMENTARY`
    (a simple English sentence describing the move).
    Your response MUST be a valid JSON object with one key: "commentary".

    There are three types of tasks:
    1.  **Move Analysis (Human Player):** - You will be given the history and the human's last move commentary.
        - First, determine if this is a "key learning moment" (a major blunder,
          missed tactic, or critical strategic error).
        - If it IS a key moment, your commentary *MUST* start with the exact
          tag "[INTERVENTION]" (e.g., {"commentary": "[INTERVENTION] That move
          hangs your queen! Are you sure you want to play that?"}).
        - If it is NOT a key moment, just provide brief, encouraging feedback
          (e.g., {"commentary": "Good, solid developing move."}).

    2.  **AI Move Acknowledgment (AI Player):** - You will be given the history and the AI's last move commentary.
        - Your task is to provide a *brief*, one-sentence acknowledgment of
          the AI's move (e.g., {"commentary": "Okay, the AI develops its knight."}).
          This is just to let the student know you saw the AI's move.

    3.  **User Chat (Q&A):** - You will be given a direct question from the user and the game history.
        - Use the game history as context to provide a direct, helpful,
          natural language answer in the commentary field.
    """
    chat = coach_model.start_chat(history=[
        {'role': 'user', 'parts': [persona_prompt]},
        {'role': 'model', 'parts': ['{"commentary": "Understood. I am Coach Gemini. I will analyze the game history and last move commentary, and provide my feedback in the requested JSON format."}']}
    ])
    return chat

def get_coach_analysis(chat_session, game_history_json_str, last_move_commentary):
    """
    Sends the full game history and last move commentary to the Coach LLM
    to get analysis on the *human's* last move.
    """
    prompt = f"""
    CONTEXT: The human player just made a move.
    
    TASK: Analyze this last move. Is this a "key learning moment"?
    Provide your response in the required JSON format.
    
    GAME_HISTORY_JSON:
    {game_history_json_str}
    
    LAST_MOVE_COMMENTARY:
    "{last_move_commentary}"
    """
    try:
        genai.configure(api_key=COACH_KEY)
        response_stream = chat_session.send_message(
            prompt,
            stream=True
        )
        return response_stream
    except Exception as e:
        print(f"Error calling Coach LLM: {e}")
        fallback_json = {"commentary": f"Sorry, an error occurred: {e}"}
        
        def fallback_stream():
            yield _MockChunk(json.dumps(fallback_json))
        
        return fallback_stream()

def get_coach_ai_analysis(chat_session, game_history_json_str, last_move_commentary):
    """
    Sends the AI's last move (as commentary) to the Coach for brief,
    non-intervention acknowledgment.
    """
    prompt = f"""
    CONTEXT: The AI opponent just made a move.
    
    TASK: Provide a *brief* (one-sentence) acknowledgment of the AI's move
    for the student's benefit. Do NOT use the [INTERVENTION] tag.
    
    GAME_HISTORY_JSON:
    {game_history_json_str}
    
    LAST_MOVE_COMMENTARY:
    "{last_move_commentary}"
    
    Provide your brief analysis in the required JSON format.
    """
    try:
        genai.configure(api_key=COACH_KEY)
        response_stream = chat_session.send_message(
            prompt,
            stream=True
        )
        return response_stream
    except Exception as e:
        print(f"Error calling Coach LLM for AI analysis: {e}")
        fallback_json = {"commentary": "..."} # Fail silently
        
        def fallback_stream():
            yield _MockChunk(json.dumps(fallback_json))
        
        return fallback_stream()

def get_coach_qa_response(chat_session, user_query, game_history_json_str):
    """
    Sends a direct user question and game history to the Coach LLM.
    """
    try:
        genai.configure(api_key=COACH_KEY)
        prompt = f"""
        CONTEXT: The human player is asking a direct question: "{user_query}"
        
        TASK: Based on the current game history, provide a direct, helpful,
        natural language answer.
        
        GAME_HISTORY_JSON:
        {game_history_json_str}
        
        Provide your answer in the required JSON format.
        """
        response_stream = chat_session.send_message(
            prompt,
            stream=True
        )
        return response_stream
    except Exception as e:
        print(f"Error calling Coach LLM for Q&A: {e}")
        fallback_json = {"commentary": f"Sorry, an error occurred while answering: {e}"}
        
        def fallback_stream():
            yield _MockChunk(json.dumps(fallback_json))
        
        return fallback_stream()


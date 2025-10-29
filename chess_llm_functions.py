import google.generativeai as genai
import json
import os
import time
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
commentator_model = genai.GenerativeModel('gemini-2.5-flash-lite-preview-09-2025') # use 2.5 flash for the final
coach_model = genai.GenerativeModel('gemini-2.5-flash-lite') # use 2.5 pro for the final
opponent_model = genai.GenerativeModel('gemini-2.5-flash') # use 2.5 flash for the final

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
        # Using generate_content for a non-streaming, simple response
        response = commentator_model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Error calling Commentator LLM: {e}")
        # Provide a fallback commentary that still works
        return f"Move: {move_data_dict.get('piece_moved')} from {move_data_dict.get('start_square')} to {move_data_dict.get('end_square')}."

# --- AI OPPONENT FUNCTIONS (Unchanged) ---
# These functions already accept the full game history JSON,
# which aligns with the new architecture.
def initialize_opponent_chat():
    """
    Initializes and returns a new chat session with the AI Opponent LLM.
    """
    persona_prompt = """
    You are an AI Chess Opponent. Your sole purpose is to play chess. 
    You will be given the entire game history as a JSON log and a list of legal moves.
    
    Your response MUST be a valid JSON object with one key: "move".
    - The "move" value must be one of the legal moves provided.
    
    Your goal is to play a strong, challenging, and human-like game.
    """
    chat = opponent_model.start_chat(history=[
        {'role': 'user', 'parts': [persona_prompt]},
        {'role': 'model', 'parts': ['{"move": "Understood. I will select a move from the legal moves list and provide it in the required JSON format."}']}
    ])
    return chat

def get_ai_opponent_move(chat_session, game_data_history_str, legal_moves_list):
    """
    Sends the full game history (JSON) to the Opponent LLM and gets its next move.
    """
    try:
        genai.configure(api_key=AI_OPPONENT_KEY)
        legal_moves_str = ", ".join(legal_moves_list)
        prompt = f"""
        Here is the game history so far in a list of dictionaries format (JSON):
        {game_data_history_str}

        Here is the list of your available legal moves:
        {legal_moves_str}

        Based on this history, provide your response in the required JSON format.
        """
        response = chat_session.send_message(prompt)
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



def get_ai_opponent_move_with_metrics(chat_session, game_data_history_str, legal_moves_list):
    """
    Wraps the existing get_ai_opponent_move to return both the parsed move and an llm_metrics dict.
    """
    start = time.time()
    try:
        parsed = get_ai_opponent_move(chat_session, game_data_history_str, legal_moves_list)
        end = time.time()
        latency = end - start

        # Try to extract token usage if the SDK/response provides it.
        # This depends on your genai SDK response object structure. Example attempt:
        llm_info = {}
        try:
            last_resp = chat_session._last_response  # <-- if SDK exposes it; fallback below
            usage = getattr(last_resp, "usage", None)
            if usage:
                llm_info["prompt_tokens"] = usage.get("prompt_tokens")
                llm_info["response_tokens"] = usage.get("completion_tokens") or usage.get("response_tokens")
                llm_info["total_tokens"] = usage.get("total_tokens")
        except Exception:
            pass

        # Build metrics dict we expect log_move_data to consume
        llm_metrics = {
            "role": "opponent",
            "model": getattr(opponent_model, "name", "opponent_model"),
            "latency": latency,
            "prompt_tokens": llm_info.get("prompt_tokens"),
            "response_tokens": llm_info.get("response_tokens"),
            "total_tokens": llm_info.get("total_tokens"),
            "raw_response": None
        }

        # If parsed is a dict with raw text or chat_session has a last response text, include it
        try:
            llm_metrics["raw_response"] = parsed.get("_raw_text") if isinstance(parsed, dict) else None
        except Exception:
            pass

        return parsed, llm_metrics

    except Exception as e:
        end = time.time()
        return {"move": random.choice(legal_moves_list)}, {
            "role":"opponent","model":"opponent_model","latency":end-start,
            "prompt_tokens":None,"response_tokens":None,"total_tokens":None,"raw_response":f"error:{e}"
        }





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

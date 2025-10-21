import google.generativeai as genai
import json
import os
import random
from dotenv import load_dotenv
load_dotenv()

# --- IMPORTANT ---
# The application expects your Google AI API key to be set as an environment
# variable or in Streamlit's secrets management (st.secrets).
if 'GOOGLE_API_KEY' not in os.environ:
    print("API KEY NOT FOUND. Please set the GOOGLE_API_KEY environment variable.")
else:
    genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))

# --- MODEL INITIALIZATION ---
commentator_model = genai.GenerativeModel('gemini-2.5-flash')
coach_model = genai.GenerativeModel('gemini-2.5-flash')
opponent_model = genai.GenerativeModel('gemini-2.5-flash')

# --- COMMENTATOR FUNCTION ---
def get_move_commentary(move_data_dict):
    """
    Uses the Commentator LLM to turn a single move's data into a 
    natural language sentence.
    """
    prompt = f"""
    You are a chess commentator. Your task is to describe the following chess move,
    provided in a Python dictionary format, in a single, natural-language sentence.
    Do not add any preamble or explanation. Just the sentence.
    
    Example: "White's queen captures the black knight on f6."
    
    Move Data: {json.dumps(move_data_dict)}
    """
    try:
        response = commentator_model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Error calling Commentator LLM: {e}")
        return "The commentator is speechless."

# --- AI OPPONENT FUNCTIONS ---
def initialize_opponent_chat():
    """
    Initializes and returns a new chat session with the AI Opponent LLM.
    """
    persona_prompt = """
    You are an AI Chess Opponent. Your sole purpose is to play chess. 
    You will be given the entire game history and a list of legal moves.
    
    Your response MUST be a valid JSON object with one key: "move".
    - The "move" value must be one of the legal moves provided.
    
    Crucially, you must adapt your playing strength. You are not a grandmaster.
    Analyze the player's history. If they make blunders, do not play the
    absolute best engine move. Your goal is to be a challenging but
    beatable opponent that plays at a human-like, scalable level.
    If the user plays well, increase your strength. If they play poorly,
    make a few non-obvious mistakes.
    """
    chat = opponent_model.start_chat(history=[
        {'role': 'user', 'parts': [persona_prompt]},
        {'role': 'model', 'parts': ['{"move": "d2-d4"}']}
    ])
    return chat

def get_ai_opponent_move(chat_session, game_data_history_str, legal_moves_list):
    """
    Sends the full game history to the Opponent LLM and gets its next move.
    """
    legal_moves_str = ", ".join(legal_moves_list)
    prompt = f"""
    Here is the game history so far in a list of dictionaries format:
    {game_data_history_str}

    Here is the list of your available legal moves:
    {legal_moves_str}

    Based on this history, provide your response in the required JSON format.
    """
    try:
        response = chat_session.send_message(prompt)
        json_str = response.text.strip().replace("```json", "").replace("```", "").strip()
        parsed_json = json.loads(json_str)
        if 'move' in parsed_json and parsed_json['move'] in legal_moves_list:
            return parsed_json
        else:
            raise ValueError(f"LLM returned invalid move: {parsed_json.get('move')}")
    except Exception as e:
        print(f"Error calling Opponent LLM or parsing JSON: {e}")
        return {"move": random.choice(legal_moves_list)}

# --- COACH FUNCTIONS (MODIFIED) ---
def initialize_coach_chat():
    """
    Initializes and returns a new chat session with the Coach LLM.
    """
    persona_prompt = """
    You are 'Coach Gemini,' an adaptive chess AI. Your sole purpose is to
    provide helpful, turn-by-turn feedback to a student.
    YOU DO NOT PLAY THE GAME. You only analyze the *student's* moves.

    Your task is to analyze the student's last move in the context of the game.
    Ask yourself: Is this a "key learning moment"? (e.g., a major blunder, a missed
    tactic, or a critical strategic error).

    Your response MUST be a valid JSON object with ONE key: "commentary".

    - If you identify a "key learning moment," you MUST begin your commentary
      string with the exact tag "[INTERVENTION]". For example:
      "[INTERVENTION] That move puts your queen in immediate danger. Are you
      sure you want to play that?"

    - If it is NOT a key learning moment, just provide brief, encouraging
      feedback without the tag. For example:
      "Good, solid developing move!" or "This is a standard response in the
      Ruy Lopez opening."
    """
    chat = coach_model.start_chat(history=[
        {'role': 'user', 'parts': [persona_prompt]},
        {'role': 'model', 'parts': ['{"commentary": "Understood. I will analyze the student\'s moves and provide my feedback, using the [INTERVENTION] tag for key moments."}']}
    ])
    return chat

def get_coach_analysis(chat_session, last_move_commentary, game_data_history_str):
    """
    Sends the last move and history to the Coach LLM for analysis (streaming).
    """
    prompt = f"""
    The student's last move was: "{last_move_commentary}"
    
    Here is the full game history:
    {game_data_history_str}
    
    Provide your analysis in the required JSON format. Remember to use the
    [INTERVENTION] tag at the start of your commentary if it's a key moment.
    """
    try:
        response_stream = chat_session.send_message(prompt, stream=True)
        return response_stream
    except Exception as e:
        print(f"Error calling Coach LLM: {e}")
        fallback_json = {"commentary": "I seem to be having a moment of processor-induced confusion. Just... carry on for now."}
        
        def fallback_stream():
            yield json.dumps(fallback_json)
        
        return fallback_stream()


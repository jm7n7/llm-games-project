import google.generativeai as genai
import json
import os
import random
from dotenv import load_dotenv
load_dotenv()

# --- IMPORTANT ---
# The application expects your Google AI API key to be set as an environment
# variable or in Streamlit's secrets management (st.secrets).
# For local testing, you can uncomment and set the line below:
# os.environ['GOOGLE_API_KEY'] = "YOUR_API_KEY"

# Ensure the API key is configured
if 'GOOGLE_API_KEY' not in os.environ:
    # This is a fallback for environments where the key is not set.
    # The app will show an error if it tries to run without a key.
    print("API KEY NOT FOUND. Please set the GOOGLE_API_KEY environment variable.")
else:
    genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))

# Initialize the generative models
commentator_model = genai.GenerativeModel('gemini-2.5-flash')
coach_model = genai.GenerativeModel('gemini-2.5-flash')
parser_model = genai.GenerativeModel('gemini-2.5-flash')
visualizer_model = genai.GenerativeModel('gemini-2.5-flash') # New model for visualization data

def get_move_commentary(move_data_dict):
    """
    Uses the Commentator LLM to turn a single move's data into a 
    natural language sentence.
    """
    prompt = f"""
    You are a chess commentator. Your task is to describe the following chess move,
    provided in a Python dictionary format, in a single, natural-language sentence.
    Do not add any preamble or explanation.
    
    Move Data: {json.dumps(move_data_dict)}
    """
    try:
        response = commentator_model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Error calling Commentator LLM: {e}")
        return "The commentator is speechless."

def initialize_coach_chat():
    """
    Initializes and returns a new chat session with the Coach LLM,
    including the system persona prompt.
    """
    persona_prompt = """
    You are 'Coach Gemini,' an adaptive chess AI. Your dual purpose is to play 
    against a student and provide helpful, turn-by-turn feedback to help them 
    improve. You will be given the entire game history.

    Your final response MUST be a valid JSON object with two keys: "move" and "commentary".
    - The "move" value must be one of the legal moves provided.
    - The "commentary" value should be your coaching advice for the player.

    Crucially, you must adapt your playing strength based on the player's history. 
    Analyze their moves for blunders or inaccuracies and adjust your own move 
    selection to provide a challenging but fair game. Do not always play the 
    absolute best engine move. Your goal is to teach, not to crush the opponent.
    """
    chat = coach_model.start_chat(history=[{'role': 'user', 'parts': [persona_prompt]},
                                           {'role': 'model', 'parts': ["Understood. I am Coach Gemini. I will analyze the game and provide my move and commentary in the requested JSON format."]}])
    return chat

def get_coach_move_and_commentary(chat_session, game_data_history_str, legal_moves_list):
    """
    Sends the full game history to the Coach LLM and gets its next move and commentary.
    """
    legal_moves_str = ", ".join(legal_moves_list)
    prompt = f"""
    Here is the game history so far in a list of dictionaries format:
    {game_data_history_str}

    Here is the list of your available legal moves:
    {legal_moves_str}

    Based on this history, and your goal of adapting to the player's skill level,
    provide your response in the required JSON format.
    """
    try:
        response = chat_session.send_message(prompt)
        # Clean the response to extract only the JSON part
        json_str = response.text.strip().replace("```json", "").replace("```", "").strip()
        parsed_json = json.loads(json_str)
        return parsed_json
    except Exception as e:
        print(f"Error calling Coach LLM or parsing JSON: {e}")
        # Fallback move if the LLM fails
        return {"move": random.choice(legal_moves_list), "commentary": "I seem to be having a moment of processor-induced confusion. I'll just make a default move while I reboot my chess circuits."}

def parse_spoken_move(spoken_text, legal_moves_list):
    """
    Uses an LLM to parse a spoken command and match it to a legal chess move.
    """
    legal_moves_str = ", ".join(legal_moves_list)
    prompt = f"""
    You are a chess notation expert. Your task is to interpret a player's spoken command
    and determine which of the available legal moves they intended to make.

    Spoken command: "{spoken_text}"

    List of legal moves: {legal_moves_str}

    Analyze the command and identify the single best matching move from the list.
    Your response should be only the move in standard algebraic notation (e.g., "e2-e4"),
    and nothing else. If no move is a clear match, respond with "None".
    """
    try:
        response = parser_model.generate_content(prompt)
        move = response.text.strip()
        if move in legal_moves_list:
            return move
        return None
    except Exception as e:
        print(f"Error calling move parsing LLM: {e}")
        return None

def get_win_probability_data(game_data_str):
    """
    Asks an LLM to analyze a full game and return turn-by-turn win probabilities.
    """
    prompt = f"""
    You are a chess grandmaster and data analyst. Your task is to analyze the following
    chess game, provided as a JSON string of moves. For each turn, estimate the win
    probability for both White and Black based on the board state at that time.

    Game Data:
    {game_data_str}

    Your response MUST be a single valid JSON object. This object should contain one key,
    "probabilities", which is a list of objects. Each object in the list should
    represent a single turn and have three keys: "turn", "white_win_prob", and "black_win_prob".
    Probabilities should be floats between 0.0 and 1.0. The sum of probabilities for each turn
    should be 1.0.

    Example format:
    {{
      "probabilities": [
        {{"turn": 1, "white_win_prob": 0.5, "black_win_prob": 0.5}},
        {{"turn": 2, "white_win_prob": 0.52, "black_win_prob": 0.48}}
      ]
    }}
    """
    try:
        response = visualizer_model.generate_content(prompt)
        # Clean the response to ensure it's valid JSON
        json_str = response.text.strip().replace("```json", "").replace("```", "").strip()
        return json_str
    except Exception as e:
        print(f"Error calling visualization LLM: {e}")
        return None

def get_material_advantage_data(game_data_str):
    """
    Asks an LLM to analyze a full game and return turn-by-turn material scores.
    """
    prompt = f"""
    You are a chess engine and data analyst. Your task is to calculate the total material score for
    both White and Black after each turn of the following chess game. The game is provided as a JSON
    string of moves.

    Use the standard point values for pieces:
    - Pawn: 1 point
    - Knight: 3 points
    - Bishop: 3 points
    - Rook: 5 points
    - Queen: 9 points
    - The King has no point value.

    The initial score for both players is 39 (8 Pawns * 1 + 2 Knights * 3 + 2 Bishops * 3 + 2 Rooks * 5 + 1 Queen * 9).
    Analyze the 'capture' and 'captured_piece' fields for each turn to determine the board state and calculate the cumulative material score for each player at the end of that turn.

    Game Data:
    {game_data_str}

    Your response MUST be a single valid JSON object. This object should contain one key,
    "scores", which is a list of objects. Each object in the list should
    represent a single turn and have three keys: "turn", "white_score", and "black_score".
    The scores should be integers.

    Example format:
    {{
      "scores": [
        {{"turn": 1, "white_score": 39, "black_score": 39}},
        {{"turn": 2, "white_score": 39, "black_score": 39}},
        {{"turn": 3, "white_score": 39, "black_score": 36}}
      ]
    }}
    """
    try:
        response = visualizer_model.generate_content(prompt)
        # Clean the response to ensure it's valid JSON
        json_str = response.text.strip().replace("```json", "").replace("```", "").strip()
        return json_str
    except Exception as e:
        print(f"Error calling material advantage LLM: {e}")
        return None


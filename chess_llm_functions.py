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

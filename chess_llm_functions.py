import google.generativeai as genai
import json
import os
import random
from dotenv import load_dotenv
load_dotenv()

# --- API KEY CONFIG ---
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
AI_OPPONENT_KEY = os.environ.get("AI_OPPONENT_KEY")
COACH_KEY = os.environ.get("COACH_KEY")
COMMENTATOR_KEY = os.environ.get("COMMENTATOR_KEY")

# --- MODEL INITIALIZATION ---
# Using Flash for speed-sensitive tasks (commentary, opponent)
# Using Pro for complex analysis (coach)
commentator_model = genai.GenerativeModel('gemini-2.5-flash-lite-preview-09-2025') 
coach_model = genai.GenerativeModel('gemini-2.5-flash-lite')
opponent_model = genai.GenerativeModel('gemini-2.5-flash') 

# --- COMMENTATOR FUNCTION ---
def get_move_commentary(move_data_dict):
    """
    Uses the Commentator LLM to turn a single move's data into a
    natural language sentence.
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
        response = commentator_model.generate_content(prompt)
        print("--- COMMENTATOR RESPONSE ---")
        print(response.text.strip())
        print("------------------------------")
        return response.text.strip()
    except Exception as e:
        print(f"Error calling Commentator LLM: {e}")
        return "The commentator is speechless."

# --- AI OPPONENT FUNCTION (Refactored) ---
def get_ai_opponent_move(board_state_narrative, legal_moves_list):
    """
    Sends the board state narrative and legal moves to the Opponent LLM
    (stateless) to get its next move.
    """
    try:
        genai.configure(api_key=AI_OPPONENT_KEY)
        legal_moves_str = ", ".join(legal_moves_list)
        
        prompt = f"""
        You are an AI Chess Opponent. Your sole purpose is to play chess.
        You will be given two pieces of information:
        1.  `BOARD_STATE_NARRATIVE`: A 100% accurate, human-readable description of
            all piece locations, attack lines, and the current game status.
            **THIS IS YOUR ABSOLUTE SOURCE OF TRUTH.**
        2.  `LEGAL_MOVES`: A list of all legal moves you can make.

        Your task is to analyze the `BOARD_STATE_NARRATIVE`, decide on the
        strongest, most human-like move, and select it from the `LEGAL_MOVES` list.

        Your response MUST be a valid JSON object with one key: "move".
        - The "move" value must be one of the legal moves provided.

        BOARD_STATE_NARRATIVE:
        {board_state_narrative}

        LEGAL_MOVES:
        {legal_moves_str}

        Provide your response in the required JSON format.
        """
        
        response = opponent_model.generate_content(prompt)
        
        # Clean the response to extract only the JSON part
        json_str = response.text.strip().replace("```json", "").replace("```", "").strip()
        
        print("--- AI OPPONENT RESPONSE (RAW) ---")
        print(json_str)
        print("---------------------------------")
        
        parsed_json = json.loads(json_str)
        
        # Validate move
        if 'move' in parsed_json and parsed_json['move'] in legal_moves_list:
            return parsed_json
        else:
            # Fallback if LLM provides an invalid move
            raise ValueError(f"LLM returned invalid move: {parsed_json.get('move')}")
            
    except Exception as e:
        print(f"Error calling Opponent LLM or parsing JSON: {e}")
        print("--- AI OPPONENT ERROR: Choosing random fallback move. ---")
        # Fallback move if the LLM fails
        return {"move": random.choice(legal_moves_list)}


# --- COACH FUNCTIONS ---

class _MockChunk:
    """Mocks a stream chunk object with a .text attribute for fallback."""
    def __init__(self, text):
        self.text = text

def initialize_coach_chat():
    """
    Initializes and returns a new chat session with the Coach LLM,
    including the system persona prompt.
    """
    persona_prompt = """
    You are 'Coach Gemini,' a grandmaster-level chess player and expert coach.
    You excel at explaining complex ideas simply.
    Your sole purpose is to provide helpful, turn-by-turn feedback to a student
    to help them improve. YOU DO NOT PLAY THE GAME.

    You will be given two pieces of information:
    1.  `BOARD_STATE_NARRATIVE`: A 100% accurate, human-readable description of
        all piece locations, **the squares each piece is attacking**, and the
        current game status (turn, check status, etc.).
        **THIS NARRATIVE IS YOUR ABSOLUTE SOURCE OF TRUTH.** All your
        tactical analysis (checks, captures, piece safety) MUST be based
        *only* on this narrative.
    2.  `LAST_MOVE_COMMENTARY`: A simple sentence of the move just made.
        This tells you what to focus on.

    Your response MUST be a valid JSON object with one key: "commentary".

    There are three types of tasks:
    1.  **Move Analysis (Human Player):**
        - You will be given the narrative and the human's last move.
        - **Using the `BOARD_STATE_NARRATIVE` as your guide**, determine if
          this is a "key learning moment" (a major blunder, missed tactic,
          or critical strategic error).
        - If it IS a key moment, your commentary *MUST* start with the exact
          tag "[INTERVENTION]" (e.g., {"commentary": "[INTERVENTION] That move
          hangs your queen! Are you sure you want to play that?"}).
        - If it is NOT a key moment, just provide brief, encouraging feedback
          (e.g., {"commentary": "Good, solid developing move."}).
        - **DO NOT** hallucinate piece positions. Trust the narrative.

    2.  **AI Move Acknowledgment (AI Player):**
        - You will be given the narrative and the AI's last move.
        - Your task is to provide a *brief*, one-sentence acknowledgment of
          the AI's move (e.g., {"commentary": "Okay, the AI develops its knight."}).
          This is just to let the student know you saw the AI's move.

    3.  **User Chat (Q&A):**
        - You will be given a direct question from the user, plus the
          narrative.
        - Use the `BOARD_STATE_NARRATIVE` as
          context to provide a direct, helpful, natural language answer.
    """
    chat = coach_model.start_chat(history=[
        {'role': 'user', 'parts': [persona_prompt]},
        {'role': 'model', 'parts': ['{"commentary": "Understood. I am Coach Gemini. I will use the BOARD_STATE_NARRATIVE as my single source of truth for all piece positions, attacked squares, and game rules, and provide my feedback in the requested JSON format."}']}
    ])
    return chat

def get_coach_analysis(chat_session, last_move_commentary, board_state_narrative):
    """
    Sends the last move commentary and the board state
    narrative to the Coach LLM to get analysis on the *human's* last move.
    """
    prompt = f"""
    CONTEXT: The human player just made a move.
    
    TASK: Analyze this last move. Is this a "key learning moment"?
    Provide your response in the required JSON format.
    
    BOARD_STATE_NARRATIVE (ABSOLUTE TRUTH):
    {board_state_narrative}
    
    LAST_MOVE_COMMENTARY (Focus of Analysis):
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

def get_coach_ai_analysis(chat_session, last_move_commentary, board_state_narrative):
    """
    Sends the AI's last move (as commentary) and board state narrative
    to the Coach for brief, non-intervention acknowledgment.
    """
    prompt = f"""
    CONTEXT: The AI opponent just made a move.
    
    TASK: Provide a *brief* (one-sentence) acknowledgment of the AI's move
    for the student's benefit. Do NOT use the [INTERVENTION] tag.
    
    BOARD_STATE_NARRATIVE (ABSOLUTE TRUTH):
    {board_state_narrative}

    LAST_MOVE_COMMENTARY (Focus of Analysis):
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

def get_coach_qa_response(chat_session, user_query, board_state_narrative):
    """
    Sends a direct user question and board state narrative
    to the Coach LLM.
    """
    try:
        genai.configure(api_key=COACH_KEY)
        prompt = f"""
        CONTEXT: The human player is asking a direct question: "{user_query}"
        
        TASK: Based on the current game state, provide a direct, helpful,
        natural language answer.
        
        BOARD_STATE_NARRATIVE (ABSOLUTE TRUTH):
        {board_state_narrative}
        
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


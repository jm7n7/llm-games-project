import google.generativeai as genai
import json
import os
import time

# --- API KEY CONFIG ---
# This is set in app.py or by the environment
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

# --- MODEL INITIALIZATION ---
# Using Flash for speed-sensitive tasks
# Using Pro for complex analysis
flash_model = genai.GenerativeModel('gemini-2.5-flash') 
pro_model = genai.GenerativeModel('gemini-2.5-pro') 

# --- (NEW) Move Sanitizer Tool ---
def call_move_sanitizer_tool(malformed_move, legal_moves_str):
    """
    (NEW) An LLM-based tool to repair a malformed move string.
    It compares the bad string against the list of legal moves.
    """
    print(f"[SANITIZER TOOL] Repairing move: '{malformed_move}'")
    try:
        prompt = f"""
        You are a data sanitization expert. Your task is to repair a malformed chess move.
        You will be given a `MALFORMED_MOVE` and a `LEGAL_MOVES_LIST`.

        Your ONLY job is to find the single move from the `LEGAL_MOVES_LIST`
        that most closely matches the user's *intent* in the `MALFORMED_MOVE`.

        - If you find a clear match (e.g., "g, 5, -, e, 4" matches "g5-e4"), return that move.
        - If the malformed move is vague or no move in the list is a
          clear match, return "null".

        `MALFORMED_MOVE`:
        "{malformed_move}"

        `LEGAL_MOVES_LIST`:
        "{legal_moves_str}"

        Return your answer in this exact JSON format:
        {{"move": "g5-e4"}}
        
        Example for no match:
        {{"move": "null"}}
        """
        
        response = flash_model.generate_content(prompt)
        print(f"--- SANITIZER TOOL (RAW) ---\n{response.text}\n------------------------------")
        
        json_str = response.text.strip().replace("```json", "").replace("```", "").strip()
        parsed_json = json.loads(json_str)
        
        if "move" in parsed_json and parsed_json["move"] != "null":
            return parsed_json
        else:
            return {"move": None} # Return None if no match
            
    except Exception as e:
        print(f"!!! CRITICAL: Sanitizer Tool error: {e}")
        return {"move": None} # Fail safely

# --- Coach Agent Tools ---

def call_analyst_tool(last_move_data, board_state_narrative):
    """
    Specialist 1: The Grandmaster.
    Analyzes the move and returns a structured JSON report.
    """
    print("[ANALYST TOOL] Analyzing move...")
    try:
        prompt = f"""
        You are a grandmaster chess analysis engine. Your task is to analyze the
        `LAST_MOVE_DATA` based *only* on the `BOARD_STATE_NARRATIVE`.
        
        Your analysis MUST be grounded in the `BOARD_STATE_NARRATIVE`.
        This narrative is your absolute source of truth.

        `LAST_MOVE_DATA`:
        {json.dumps(last_move_data)}

        `BOARD_STATE_NARRATIVE`:
        {board_state_narrative}

        Definitions:
        - "best_move": An excellent, top-engine move.
        - "good": A solid, strong developing move.
        - "inaccuracy": A move that is okay but misses a better opportunity.
        - "mistake": A move that worsens your position or misses a simple tactic.
        - "blunder": A critical, game-losing error (e.g., hanging a queen).
        - "book_move": A standard opening move.

        Return your analysis in this exact JSON format.
        Do not add any other text or markdown.
        
        {{"move_quality": "best_move", "tactic_type": "None", "primary_threat": "Central control and opening lines.", "missed_opportunity": "None", "suggested_alternative": "e4"}}
        """
        
        response = pro_model.generate_content(prompt)
        print(f"--- ANALYST TOOL (RAW) ---\n{response.text}\n------------------------------")
        
        json_str = response.text.strip().replace("```json", "").replace("```", "").strip()
        parsed_json = json.loads(json_str)
        return parsed_json
            
    except Exception as e:
        print(f"!!! CRITICAL: Analyst Tool error: {e}")
        return {"move_quality": "error", "message": str(e)}

def call_pedagogy_tool(analysis_json, user_skill_level, player_color):
    """
    Specialist 2: The Teacher.
    Translates the Analyst's JSON into a human-readable packet.
    """
    print("[PEDAGOGY TOOL] Generating response...")
    try:
        # Define the persona and rules based on skill level
        if user_skill_level == "beginner":
            persona = f"""
            You are 'Coach Gemini,' a super friendly, Socratic, and encouraging
            chess teacher. Your student is a beginner.
            
            - Your student is playing as {player_color}. Frame all responses from
              their perspective (e.g., "Good move!" "You are in check!").
            - If `move_quality` is "blunder" or "mistake", you MUST
              return `"response_type": "intervention"`. Your message should be a
              simple, Socratic question (e.g., "Hold on! Look at your Queen.
              Is it safe there?"). Do NOT give the answer.
            - If `move_quality` is "best_move", return `"response_type": "praise"`.
              Be enthusiastic! (e.g., "Great move! You saw the fork!").
            - If `move_quality` is "good" or "book_move", return
              `"response_type": "encouragement"`. (e.g., "Solid opening!").
            - For "inaccuracy", return `"response_type": "silent"`.
              Beginners don't need to be overwhelmed.
            """
        elif user_skill_level == "intermediate":
            persona = f"""
            You are 'Coach Gemini,' an insightful and clear chess coach.
            Your student is intermediate.
            
            - Your student is playing as {player_color}. Frame all responses from
              their perspective (e.g., "That move defends your pawn well.").
            - If `move_quality` is "blunder", you MUST return
              `"response_type": "intervention"`. Explain the *immediate* threat
              clearly. (e.g., "[INTERVENTION] Be careful! That move hangs your
              Rook to their Bishop.").
            - If `move_quality` is "mistake", also return
              `"response_type": "intervention"`, but focus on the *missed
              opportunity* or positional problem.
            - If `move_quality` is "best_move", return `"response_type": "praise"`.
              Explain *why* it was a good move.
            - For "good", "book_move", or "inaccuracy", return
              `"response_type": "silent"`. Don't clutter the chat.
            """
        else: # "advanced"
            persona = f"""
            You are 'Coach Gemini,' a grandmaster-level analyst.
            Your student is advanced and wants critical, high-level feedback.
            
            - Your student is playing as {player_color}.
            - ONLY return `"response_type": "intervention"` for "blunder".
              Advanced players should spot their own mistakes.
            - If `move_quality` is "best_move", return `"response_type": "praise"`
              and provide deep, specific analysis.
            - If `move_quality` is "mistake" or "inaccuracy", return
              `"response_type": "encouragement"` and briefly explain the
              positional nuance or the better alternative.
            - For "good" or "book_move", return `"response_type": "silent"`.
            """
            
        prompt = f"""
        {persona}

        You will be given an `ANALYSIS_JSON` from a grandmaster engine.
        Your job is to translate this analysis into an "Instructional Packet"
        (JSON) for the student, following all rules of your persona.
        
        Do NOT analyze the board yourself. Trust the `ANALYSIS_JSON`.

        `ANALYSIS_JSON`:
        {json.dumps(analysis_json)}
        
        Return your response in this exact JSON format.
        Do not add any other text or markdown.
        
        {{"response_type": "praise", "message": "Great move! You're controlling the center."}}
        
        Example for Intervention:
        {{"response_type": "intervention", "message": "[INTERVENTION] Hold on! Look at your Queen. Is it safe there?"}}
        
        Example for Silence:
        {{"response_type": "silent", "message": null}}
        """
        
        response = flash_model.generate_content(prompt)
        print(f"--- PEDAGOGY TOOL (RAW) ---\n{response.text}\n------------------------------")
        
        json_str = response.text.strip().replace("```json", "").replace("```", "").strip()
        parsed_json = json.loads(json_str)
        return parsed_json
            
    except Exception as e:
        print(f"!!! CRITICAL: Pedagogy Tool error: {e}")
        return {"response_type": "silent", "message": None} # Fail silently

def call_post_game_analyst_tool(game_data_json, player_color):
    """
    (NEW) Specialist 3: The Post-Game Analyst.
    Provides a summary of the entire game.
    """
    print("[POST-GAME TOOL] Analyzing full game...")
    try:
        prompt = f"""
        You are a "Post-Game Analyst" coach. You will be given the `GAME_DATA`
        (a JSON list of all moves) and the `PLAYER_COLOR` (our student).
        
        - Your student played as {player_color}.
        - Analyze the full game and identify 3-5 key learning moments
          (e.g., the turning point, a critical blunder, a brilliant move,
          or a recurring mistake).
        - Provide a concise, helpful summary of these moments in a
          single `message`.
        - Frame your advice *to* the {player_color} player.
        - Start with "Here's a summary of your game:"

        `GAME_DATA`:
        {game_data_json}

        Return your analysis in this exact JSON format.
        Do not add any other text or markdown.
        
        {{"message": "Here's a summary of your game:\\n1. Your opening was strong...\\n2. The turning point was on move 15 when...\\n3. Great find on move 22!..."}}
        """
        
        response = pro_model.generate_content(prompt) # Use Pro for a better summary
        print(f"--- POST-GAME TOOL (RAW) ---\n{response.text}\n------------------------------")
        
        json_str = response.text.strip().replace("```json", "").replace("```", "").strip()
        parsed_json = json.loads(json_str)
        return parsed_json
            
    except Exception as e:
        print(f"!!! CRITICAL: Post-Game Tool error: {e}")
        return {"message": "Sorry, I had an error analyzing the full game."}

# --- Q&A Tool (Streaming) ---

def get_coach_qa_response(user_query, board_state_narrative, player_color):
    """
    Handles a direct Q&A question from the user.
    This is the only streaming function.
    """
    print("[Q&A TOOL] Answering user question...")
    try:
        prompt = f"""
        You are 'Coach Gemini,' a friendly, grandmaster-level chess coach.
        A student, who is playing as {player_color}, has a direct question.
        
        - Use the `BOARD_STATE_NARRATIVE` as your *only* source of truth
          for all piece positions and tactics.
        - Answer their question directly and helpfully.
        
        `BOARD_STATE_NARRATIVE (ABSOLUTE TRUTH)`:
        {board_state_narrative}

        `USER_QUESTION`:
        "{user_query}"

        Return your answer in this exact JSON format.
        Do not add any other text or markdown.

        {{"commentary": "That's a great question! The e4 pawn is..."}}
        """
        
        # This function *returns the stream* for app.py to handle
        response_stream = pro_model.generate_content(prompt, stream=True)
        return response_stream
            
    except Exception as e:
        print(f"!!! CRITICAL: Q&A Tool error: {e}")
        fallback_json = {"commentary": f"Sorry, an error occurred: {e}"}
        
        # Mock a stream for fallback
        class _MockChunk:
            def __init__(self, text):
                self.text = text
        def fallback_stream():
            yield _MockChunk(json.dumps(fallback_json))
        
        return fallback_stream()


# --- AI Opponent Agent Tools ---

def call_best_move_tool(board_state_narrative, legal_moves_str):
    """
    Opponent Tool 1: The Engine.
    Plays the strongest possible move.
    """
    print("[BEST MOVE TOOL] Calculating best move...")
    try:
        prompt = f"""
        You are a world-champion chess engine (Stockfish 16).
        Your sole purpose is to find the absolute strongest, most optimal,
        winning move from the `LEGAL_MOVES` list. You must win at all costs.
        
        - Your analysis MUST be grounded in the `BOARD_STATE_NARRATIVE`.
        - The `BOARD_STATE_NARRATIVE` is your absolute source of truth.
        - You MUST choose a move from the `LEGAL_MOVES` list.

        `BOARD_STATE_NARRATIVE`:
        {board_state_narrative}

        `LEGAL_MOVES`:
        {legal_moves_str}

        Return your move and a brief, confident reasoning in this exact
        JSON format. Do not add any other text or markdown.
        
        {{"move": "e2-e4", "reasoning": "This move seizes the center and opens lines for my Queen and Bishop."}}
        """
        
        response = pro_model.generate_content(prompt) # Use Pro for best move
        print(f"--- BEST MOVE TOOL (RAW) ---\n{response.text}\n------------------------------")
        
        json_str = response.text.strip().replace("```json", "").replace("```", "").strip()
        parsed_json = json.loads(json_str)
        return parsed_json
            
    except Exception as e:
        print(f"!!! CRITICAL: Best Move Tool error: {e}")
        return {"move": None, "reasoning": "Error"}

def call_human_like_move_tool(board_state_narrative, legal_moves_str):
    """
    Opponent Tool 2: The Club Player.
    Plays a solid, natural, "human-like" move.
    """
    print("[HUMAN MOVE TOOL] Calculating human-like move...")
    try:
        prompt = f"""
        You are an 1800 ELO "club" chess player.
        You want to win, but you prioritize solid, natural-looking moves.
        - You prioritize good development, king safety, and simple threats.
        - You might miss deep, complex 5+ move tactics.
        
        - Your analysis MUST be grounded in the `BOARD_STATE_NARRATIVE`.
        - The `BOARD_STATE_NARRATIVE` is your absolute source of truth.
        - You MUST choose a move from the `LEGAL_MOVES` list.

        `BOARD_STATE_NARRATIVE`:
        {board_state_narrative}

        `LEGAL_MOVES`:
        {legal_moves_str}

        Return your move and a "human-like" reasoning in this exact
        JSON format. Do not add any other text or markdown.
        
        {{"move": "g1-f3", "reasoning": "Just want to develop my knight and get ready to castle."}}
        """
        
        response = flash_model.generate_content(prompt)
        print(f"--- HUMAN MOVE TOOL (RAW) ---\n{response.text}\n------------------------------")
        
        json_str = response.text.strip().replace("```json", "").replace("```", "").strip()
        parsed_json = json.loads(json_str)
        return parsed_json
            
    except Exception as e:
        print(f"!!! CRITICAL: Human Move Tool error: {e}")
        return {"move": None, "reasoning": "Error"}

def call_teaching_blunder_tool(board_state_narrative, legal_moves_str):
    """
    Opponent Tool 3: The Teacher-in-Disguise.
    Intentionally makes an *instructive* blunder.
    """
    print("[BLUNDER TOOL] Calculating teaching blunder...")
    try:
        prompt = f"""
        You are a chess teacher *pretending* to be a beginner.
        Your goal is to make an *obvious, instructive mistake*
        that a beginner-level student can spot and punish.
        
        - Look for a move in the `LEGAL_MOVES` list that is a clear
          blunder (e.g., hangs a piece, moves the king into danger,
          blocks development).
        - If no obvious blunders are available, pick a "bad" move
          (e.g., moving the same piece twice, a useless pawn move).
        
        - Your analysis MUST be grounded in the `BOARD_STATE_NARRATIVE`.
        - The `BOARD_STATE_NARRATIVE` is your absolute source of truth.
        - You MUST choose a move from the `LEGAL_MOVES` list.

        `BOARD_STATE_NARRATIVE`:
        {board_state_narrative}

        `LEGAL_MOVES`:
        {legal_moves_str}

        Return your blunder and a "flawed" reasoning in this exact
        JSON format. Do not add any other text or markdown.
        
        {{"move": "b1-a3", "reasoning": "I want to get my knight to the edge of the board!"}}
        """
        
        response = flash_model.generate_content(prompt)
        print(f"--- BLUNDER TOOL (RAW) ---\n{response.text}\n------------------------------")
        
        json_str = response.text.strip().replace("```json", "").replace("```", "").strip()
        parsed_json = json.loads(json_str)
        return parsed_json
            
    except Exception as e:
        print(f"!!! CRITICAL: Blunder Tool error: {e}")
        return {"move": None, "reasoning": "Error"}


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

# --- (NEW) Core Definitions (For AI Opponent) ---
# This is the "Orchestration Level" logic you wanted.
# We define it here so all opponent tools can share this context.
CORE_CHESS_DEFINITIONS = """
**Core Chess Definitions (Your Knowledge Base):**

1.  **Piece Values:** Queen=9, Rook=5, Bishop=3, Knight=3, Pawn=1.
2.  **"Hanging Piece" (A Blunder):** This is when you make a move and your
    piece can be captured by an opponent's piece, but you *cannot*
    recapture it.
    *Example:* Moving your Knight (`f6-e4`) to a square where a Pawn or
    Knight can capture it, and you have no other piece that can
    recapture on that *same e4 square*. This is a *bad move* that loses
    a piece for free.
3.  **"Bad Trade" (A Blunder):** This is when you capture a *low-value*
    piece (like a Pawn) with a *high-value* piece (like your Queen),
    and the opponent can then recapture your Queen. You lose a Queen
    for a Pawn.
4.  **"Equal Trade":** This is when two pieces of *equal value* are
    exchanged (e.g., your Knight captures a Knight, and they recapture).
    This is neither good nor bad, just a decision.
5.  **"Good Trade" (Profit):** This is when you capture a *high-value*
    piece (like a Rook) with a *low-value* piece (like your Knight),
    and even if they recapture, you have won material.
6.  **"Tempo" (A Key Principle):** This is the concept of developing
    your pieces.
    * **"Good Tempo":** Moves that develop a *new* piece from your back
        rank (e.g., `previous_move_count: 0`).
    * **"Bad Tempo" (or "Loss of Tempo"):** Moving a piece that is
        *already developed* for no good reason (e.g., moving your
        Knight from f6 to e4 when it doesn't win material).
7.  **"Fork" (A Tactic):** When one of your pieces attacks *two or more*
    opponent pieces at the same time.
8.  **"Pin" (A Tactic):** When one of your pieces (like a Bishop)
    attacks a *lower-value* enemy piece (like a Knight), and
    *behind* that Knight on the same line is a *higher-value*
    enemy piece (like a Queen).
"""

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

def call_opponent_router_agent(enhanced_moves_json, tactical_threats_json, user_skill_level):
    """
    (NEW) This is the "Router Agent" or "Meta-Agent."
    It uses natural language logic to choose a personality ("tool")
    based on the user's skill level and the board state.
    It uses a fast model (Flash) for low latency.
    """
    print("[ROUTER AGENT] Selecting personality...")
    try:
        # (NEW) We create a *simplified* board state summary for the router.
        # It doesn't need all the data, just the *feel* of the game.
        threat_count = 0
        try:
            threat_count = len(json.loads(tactical_threats_json))
        except Exception:
            pass # Ignore if JSON is empty/invalid
            
        move_count = 0
        try:
            move_count = len(json.loads(enhanced_moves_json))
        except Exception:
            pass # Ignore if JSON is empty/invalid

        board_summary = ""
        
        if threat_count > 0:
            board_summary = f"The board is dangerous; I am currently in danger with {threat_count} threats."
        elif move_count < 25: # Arbitrary "opening" move count
            board_summary = "The board is in the opening phase; it is quiet."
        else:
            board_summary = "The board is in the mid-game; it is complex."

        prompt = f"""
        You are the "Opponent Router Agent." Your job is to *choose a
        personality* for the AI opponent based on the `USER_SKILL_LEVEL`
        and a `BOARD_SUMMARY`.
        
        You MUST choose one of three tools: "best", "human", or "blunder".

        {CORE_CHESS_DEFINITIONS}
        
        **Your Logic:**
        
        * **If `USER_SKILL_LEVEL` is "beginner":** You should try to
            teach the user. This means you should *mostly* choose
            **"blunder"** (to create "Hanging Piece" or "Bad Tempo"
            moves for the user to find) or **"human"** (to play a
            simple, non-threatening game). Randomly pick between
            them, prioritizing "blunder".
        * **If `USER_SKILL_LEVEL` is "intermediate":** You should play
            a solid, normal game. You should almost always choose
            **"human"**. You can occasionally choose **"best"** if the
            board is complex or **"blunder"** if the board is quiet
            and you want to test them.
        * **If `USER_SKILL_LEVEL` is "advanced":** You must play to
            win. You should choose **"best"** most of the time,
            and **"human"** occasionally. You should *never*
            choose "blunder".

        `USER_SKILL_LEVEL`:
        "{user_skill_level}"
        
        `BOARD_SUMMARY`:
        "{board_summary}"
        
        Return your choice and a *brief* justification in this exact JSON
        format. Do not add any other text or markdown.
        
        {{"tool_choice": "human", "reasoning": "User is intermediate and the board is quiet, so a solid 'human' move is appropriate."}}
        """
        
        response = flash_model.generate_content(prompt) # Use fast model
        print(f"--- ROUTER AGENT (RAW) ---\n{response.text}\n------------------------------")
        
        json_str = response.text.strip().replace("```json", "").replace("```", "").strip()
        parsed_json = json.loads(json_str)
        return parsed_json
            
    except Exception as e:
        print(f"!!! CRITICAL: Router Agent error: {e}")
        return {"tool_choice": "human", "reasoning": "Router failed, defaulting to human."}


def call_best_move_tool(enhanced_legal_moves_json, tactical_threats_json):
    """
    Opponent Tool 1: The Engine (Specialist).
    (MODIFIED) Now uses the CORE_CHESS_DEFINITIONS.
    """
    print("[BEST MOVE TOOL] Calculating best move...")
    try:
        prompt = f"""
        You are a world-champion chess engine (a "best" move specialist).

        Your task is to find the single best move by analyzing two data sources:
        1. `TACTICAL_THREATS_LIST`: (Your "Dangers List")
        2. `OPTIONS_LIST`: (Your "Opportunities List")
        
        You must strictly follow the `CORE_CHESS_DEFINITIONS`.

        {CORE_CHESS_DEFINITIONS}

        `TACTICAL_THREATS_LIST (Your Dangers)`:
        {tactical_threats_json}

        `OPTIONS_LIST (Your Opportunities & All Legal Moves)`:
        {enhanced_legal_moves_json}

        **GM's Decision-Making Principles (Your Logic):**

        1.  **Analyze Dangers (Defense First):** Your first job is to
            analyze the `TACTICAL_THREATS_LIST`.
            * **If `is_pin: true`:** This is a critical tactical situation.
                You know that moving the `threatened_piece` is a
                *catastrophic blunder* because it exposes the
                `pinned_to_piece`. You must **discard** all moves for that
                piece from the `OPTIONS_LIST` and instead find a move that
                solves the pin.
            * **If `is_pin: false`:** This is a simple threat. Is it a
                "Hanging Piece" or a "Bad Trade"? If yes, this is an
                *Urgent Crisis*. You must find a *safe* escape move from
                the `OPTIONS_LIST`.
            * **If it's just an "Equal Trade":** This is a *decision*, not
                a crisis. You are free to ignore it if you find a
                better *offensive* opportunity.
        
        2.  **Analyze Opportunities (Offense):** If (and only if) you are not
            in an immediate crisis, scan the `OPTIONS_LIST` for a winning attack.
            * **Find Forcing Tactics:** Look for moves where `is_fork: true`
                or `creates_pin: true`. These are top-tier, forcing moves.
            * **Find "Good Trades":** Look for moves that capture a
                high-value piece and are safe from recapture (check
                `retaliation`).

        3.  **Prioritize "Good Tempo":** If there are no immediate dangers
            *or* forcing opportunities, then (and only then) fall back to
            solid, positional chess:
            * You must **strongly prefer** developing a new piece (a move
                with `previous_move_count: 0`).
            * **Crucially:** Do not make a "Bad Tempo" move (like `f6-e4`
                in the opening) if it is also a "Hanging Piece" blunder
                (as defined in the Core Definitions).

        **Your Task:**
        Use these high-level principles to select the single best move. Your
        `reasoning` must explain your thought process.
        
        Return your move and reasoning in this exact JSON format.
        
        {{"move": "g8-f6", "reasoning": "I am not in any immediate danger. This move has 'Good Tempo' as it develops a new piece and controls the center. It's the most solid, positional move."}}
        
        {{"move": "Qe5-e6", "reasoning": "My Knight on c3 was attacked, but the TACTICAL_THREATS_LIST correctly identified it as a pin to my Queen. Moving the Knight would be a 'Blunder'. I am moving my Queen to e6, which breaks the pin safely."}}
        """
        
        response = pro_model.generate_content(prompt) # Use Pro for best move
        print(f"--- BEST MOVE TOOL (RAW) ---\n{response.text}\n------------------------------")
        
        json_str = response.text.strip().replace("```json", "").replace("```", "").strip()
        parsed_json = json.loads(json_str)
        return parsed_json
            
    except Exception as e:
        print(f"!!! CRITICAL: Best Move Tool error: {e}")
        return {"move": None, "reasoning": "Error"}

def call_human_like_move_tool(enhanced_legal_moves_json, tactical_threats_json):
    """
    Opponent Tool 2: The Club Player (Specialist).
    (MODIFIED) Now uses the CORE_CHESS_DEFINITIONS.
    """
    print("[HUMAN MOVE TOOL] Calculating human-like move...")
    try:
        prompt = f"""
        You are an 1800 ELO "club" chess player (a "human" move specialist).
        You prioritize solid, natural-looking moves. You are smart enough
        to not make an obvious "Hanging Piece" blunder.

        You must follow the `CORE_CHESS_DEFINITIONS`.

        {CORE_CHESS_DEFINITIONS}

        `TACTICAL_THREATS_LIST (Your Dangers)`:
        {tactical_threats_json}

        `OPTIONS_LIST (Your Opportunities & All Legal Moves)`:
        {enhanced_legal_moves_json}
        
        **Your Decision-Making Principles:**

        1.  **React to Dangers:** Look at the `TACTICAL_THREATS_LIST` first.
            * **"Oh no, a Pin!" (if `is_pin: true`):** This is bad. You know
                you can't move the piece that's pinned. You must find a
                move from the `OPTIONS_LIST` to save the piece behind it
                (the `pinned_to_piece`).
            * **"Oh no, my piece is hanging!" (if `is_pin: false`):**
                If you are about to make a "Hanging Piece" or "Bad Trade"
                blunder, you must find a safe escape move from the
                `OPTIONS_LIST`. Check its `retaliation`!
            * **"It's just an 'Equal Trade'.":** You're not worried about
                equal trades. You can ignore this if you see a good
                developing move.

        2.  **Find "Good Tempo" Moves:** If you're not in trouble, find a
            simple, good move from the `OPTIONS_LIST`:
            * **STRONGLY PREFER** a move with "Good Tempo"
                (`previous_move_count: 0`).
            * Avoid "Bad Tempo" moves if possible.
        
        3.  Select one of these safe, well-developed moves.

        Your `reasoning` must be simple and show you picked a safe, developed move.
        
        Return your move and reasoning in this exact JSON format.
        
        {{"move": "g1-f3", "reasoning": "No immediate threats. This is a solid, safe 'Good Tempo' move."}}
        
        {{"move": "Qd4-c5", "reasoning": "My Queen was attacked by a pawn! That would be a 'Hanging Piece' blunder. I moved it to c5, which looks like a safe square."}}
        """
        
        response = flash_model.generate_content(prompt) # Use Flash
        print(f"--- HUMAN MOVE TOOL (RAW) ---\n{response.text}\n------------------------------")
        
        json_str = response.text.strip().replace("```json", "").replace("```", "").strip()
        parsed_json = json.loads(json_str)
        return parsed_json
            
    except Exception as e:
        print(f"!!! CRITICAL: Human Move Tool error: {e}")
        return {"move": None, "reasoning": "Error"}

def call_teaching_blunder_tool(enhanced_legal_moves_json, tactical_threats_json):
    """
    Opponent Tool 3: The Teacher-in-Disguise (Specialist).
    (MODIFIED) Now *intentionally breaks* the CORE_CHESS_DEFINITIONS.
    """
    print("[BLUNDER TOOL] Calculating teaching blunder...")
    try:
        prompt = f"""
        You are a chess teacher *pretending* to be a beginner (a "blunder"
        move specialist).
        Your goal is to make an *obvious, instructive mistake*
        that a beginner-level student can spot and punish.
        
        You will *intentionally break* the `CORE_CHESS_DEFINITIONS`.

        {CORE_CHESS_DEFINITIONS}

        `TACTICAL_THREATS_LIST (Your Dangers)`:
        {tactical_threats_json}

        `OPTIONS_LIST (Your Opportunities & All Legal Moves)`:
        {enhanced_legal_moves_json}

        **Your Goal:** Find an obvious "Hanging Piece," "Bad Trade,"
        or "Bad Tempo" blunder.
        
        **How to Blunder:**
        
        1.  **Priority 1: Ignore a Crisis.**
            * Look at the `TACTICAL_THREATS_LIST`.
            * Is a piece in a pin? (`is_pin: true`)
            * Is a high-value piece (Queen, Rook) attacked by a low-value
                piece (a "Hanging Piece" crisis)?
            * If YES, this is a perfect teaching moment! **Deliberately
                play a *different* move** (like a "Bad Tempo" move or a
                pawn move) and *ignore the crisis*. This is the
                most "human beginner" blunder.

        2.  **Priority 2: Make a "Hanging Piece" Blunder.**
            * If there are no immediate dangers to ignore, scan the
                `OPTIONS_LIST`.
            * Find a move that *is* a "Hanging Piece" or a "Bad Trade"
                (e.g., moving a Queen to a square where a Pawn can
                capture it for free).
            * Play this move.

        3.  **Priority 3: Make a "Bad Tempo" Blunder.**
            * If no material blunders are obvious, just pick a "Bad Tempo"
                move (one where `previous_move_count > 0` but no
                new pieces are developed).

        Your `reasoning` must be a "flawed" one-sentence justification
        that shows *why* you made the mistake (e.g., "I forgot about...").
        
        Return your move and reasoning in this exact JSON format.
        
        {{"move": "Qd1-h5", "reasoning": "This move looks strong, it attacks the kingside! (I didn't see the pawn on g6...)"}}
        
        {{"move": "b2-b3", "reasoning": "Just developing my pawn. (I didn't see that my Queen on d4 was under attack!)"}}
        """
        
        response = flash_model.generate_content(prompt) # Use Flash
        print(f"--- BLUNDER TOOL (RAW) ---\n{response.text}\n------------------------------")
        
        json_str = response.text.strip().replace("```json", "").replace("```", "").strip()
        parsed_json = json.loads(json_str)
        return parsed_json
            
    except Exception as e:
        print(f"!!! CRITICAL: Blunder Tool error: {e}")
        return {"move": None, "reasoning": "Error"}


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

# --- (NEW) Core Definitions (Shared Knowledge Base) ---
# This is the "Orchestration Level" logic.
# We define it here so all opponent tools can share this context.
CORE_CHESS_DEFINITIONS = """
**Core Chess Definitions (Your Knowledge Base):**

 1. **Piece Values:** Queen=9, Rook=5, Bishop=3, Knight=3, Pawn=1.

 2. **"Hanging Piece" (A Blunder):** This is when you make a move and your piece can be captured by an opponent's piece, but you *cannot* recapture it.
    *Example:* Moving your Knight (`f6-e4`) to a square where a Pawn or Knight can capture it, and you have no other piece that can recapture on that *same e4 square*. This is a *bad move* that loses a piece for free.

3. **"Trading Pieces":** This is when you capture a piece with another piece.
    * **"Bad Trade" (A Blunder):** This is when you capture a *low-value* piece (like a Pawn) with a *high-value* piece (like your Queen), and the opponent can then recapture your Queen. You lose a Queen for a Pawn.
    * **"Equal Trade":** This is when two pieces of *equal value* are exchanged (e.g., your Knight captures a Knight, and they recapture). This is neither good nor bad, just a decision.
    * **"Good Trade" (Profit):** This is when you capture a *high-value* piece (like a Rook) with a *low-value* piece (like your Knight), and even if they recapture, you have won material.

 4. **"Tempo" (A Key Principle):** This is the concept of developing your pieces.
    * **"Good Tempo":** Moves that develop a *new* piece from your back rank (e.g., `previous_move_count: 0`).
    * **"Bad Tempo" (or "Loss of Tempo"):** Moving a piece that is *already developed* for no good reason (e.g., moving your Knight from f6 to e4 when it doesn't win material).

 5. **"Fork" (A Tactic):** When one of your pieces attacks *two or more* opponent pieces at the same time.

 6. **"Pin" (A Tactic):** A situation where an attacking piece (like a Bishop) threatens an enemy piece (e.g., a Knight), which cannot move *off the line of attack* without exposing a more valuable piece (e.g., a Queen) or the King behind it. Traditionally, pawns are not included in this definition.
    * **"Absolute Pin":** When the piece behind is the King. Moving the pinned piece *off the line of attack* is illegal.
    * **"Relative Pin":** When the piece behind is a high-value piece (like a Queen). Moving the pinned piece *off the line of attack* can result in a "Blunder" because it results in a "Bad Trade".
    * **"Defended Pin":** When the pinned piece is defended by a friendly piece (e.g., a Knight on e4 defending a Queen on e3). This is not a critical threat, but it is still a tactical situation.

 7. **"Castling" (A Special Move):** This is a special move where the King moves two squares toward a Rook, and the Rook moves to the square on the other side of the King.
    * **Why do it?** The two main goals are 1) to move the King to a safer position away from the center of the board, and 2) to develop the Rook (bring it into the game).

8. **"Early Game" (Opening):** This is the beginning of the game.
    * **Goals:** The primary goals are to achieve "Good Tempo" by developing your Knights and Bishops, controlling the center of the board (usually e4, d4, e5, d5 squares), and "Castling" to get your King to safety.

9. **"Mid Game":** This phase begins after most pieces are developed.
    * **Goals:** The focus shifts to long-term strategy, finding "Good Trades," executing "Tactics" (like "Forks" and "Pins"), and improving your pawn structure.

10. **"End Game":** This phase occurs when most pieces have been traded off the board.
    * **Goals:** The primary goal often becomes promoting a pawn to a Queen. The King, which was kept safe in the Mid Game, now becomes a powerful attacking piece.

11. **"Skewer" (A Tactic):** The opposite of a "Pin." This is when an attacking piece (like a Rook) threatens a *high-value* enemy piece (like a Queen). If the Queen moves to safety, a *lower-value* piece that was *behind* it on the same line (like a Bishop) is now exposed and can be captured.

12. **"Discovered Attack" (A Tactic):** A threat created by moving one piece, which *un-blocks* an attack from a *second* piece behind it.
    * *Example:* A Bishop on a1 is blocked by your own Knight on c3, which is aimed at the enemy King on g7. When the Knight moves (e.g., to e4), it "discovers" a check from the Bishop. This is a "Discovered Check" and is very powerful because the moving piece (the Knight) is free to capture or attack another piece at the same time.

13. **"King Safety" (A Positional Principle):** The goal of keeping your King shielded from checks and mating threats. "Castling" is the main way to achieve this. This principle means you should be careful about moving the pawns in front of your castled King, as they act as a "pawn shield."

14. **"Passed Pawn" (An End Game Goal):** A pawn that has no enemy pawns in front of it on its own file or on the adjacent files. This pawn is extremely dangerous because its path to promotion (becoming a Queen) is not blocked by other pawns.

15. **"Doubled Pawns" (A Positional Weakness):** Two friendly pawns on the same file. They are generally considered a weakness because they cannot defend each other and are less mobile.

 16. **"Open File" (A Positional Goal):** A file (a vertical column, e.g., 'a' through 'h') that has no pawns from *either* side on it. Open files are like highways for Rooks and Queens, allowing them to attack deep into the opponent's territory.
"""

# --- (NEW) Coach 4.0 Post-Move Tools ---

def call_triage_analyst_tool(last_move_data_json, dangers_before_json, options_before_json):
    """
    (NEW - Coach 4.0) Specialist Tool 1: The "Triage Analyst".
    This tool implements the "Offense-First" logic. Its *only* job is
    to analyze the situation and return a "verdict" JSON. It does not
    talk to the user.
    """
    print("[TRIAGE ANALYST TOOL] Analyzing move...")
    try:
        # We parse the JSON here to get the specific move notation
        chosen_move_data = json.loads(last_move_data_json)
        chosen_move_notation = chosen_move_data.get('move_notation', 'unknown')
        
        # (NEW) Pre-parse the chosen move data from the OPTIONS_LIST
        # This is so the LLM doesn't have to "find" it.
        chosen_move_full_data = "null"
        try:
            options = json.loads(options_before_json)
            for move in options:
                if move.get('move') == chosen_move_notation:
                    chosen_move_full_data = json.dumps(move)
                    break
        except Exception:
            pass # Will remain "null"
            
        
        prompt = f"""
        You are a "Triage Analyst" engine. Your ONLY job is to analyze the
        `CHOSEN_MOVE_DATA` based on the context and return a "verdict" JSON,
        including a brief `justification` for your decision.
        You must follow the "Offense-First" logic.
        
        {CORE_CHESS_DEFINITIONS}

        `DANGERS_LIST (The "Before" Picture - What was threatening me?)`:
        {dangers_before_json}
        
        `CHOSEN_MOVE_DATA (The *full data* for the human's move, from OPTIONS_LIST)`:
        {chosen_move_full_data}
        
        ---
        **Your "Offense-First" Logic (Follow This Precisely):**
        ---

        **Step 1: Analyze Offensive Forcing Moves & Captures (Top Priority).**
        
        * **Check for Game-Winners:** Does `CHOSEN_MOVE_DATA` show
            `checkmate: true`, a winning `is_fork: true`, or a
            winning `creates_pin: true`?
            * **If YES:** `verdict: "brilliant"`. Justification:
                "The move was a game-winning forcing tactic." **STOP.**
                
        * **Check for Captures:** Does `CHOSEN_MOVE_DATA` show
            `captured_piece: not null`?
            * **If NO:** This was not a capture. **Go to Step 2.**
            * **If YES:** This was a capture. Proceed to "Trade Analysis".

        **Trade Analysis (CRITICAL):**
        You must analyze the trade based *only* on the data.
        
        * **A) Check for "Free Piece":** Is the `retaliation: []`
            list **empty**? (This means the capture was defended,
            like the `Bxf7+` example, or was completely free).
            * **If YES:** `verdict: "brilliant"`. Justification:
                "The move captured a piece for free, as the
                `retaliation` list was empty (it was either undefended
                or safely defended)." **STOP.**

        * **B) Check for "Bad Trade":** Is the `retaliation: []`
            list **NOT empty**?
            * Get `Moving_Piece_Value` (from
                `CHOSEN_MOVE_DATA.moving_piece.value`).
            * Get `Captured_Piece_Value` (from
                `CHOSEN_MOVE_DATA.captured_piece.value`).
            * Get `Lowest_Retaliator_Value` (find the minimum
                `value` from the `retaliation` list).
            *
            * **If `Moving_Piece_Value > Captured_Piece_Value`**
                (e.g., Queen(9) takes Pawn(1)): This is a **"Bad Trade"**.
            * `verdict: "blunder"`. Justification: "The move was a
                'Bad Trade,' capturing a low-value piece with a
                high-value piece, leading to a loss of material."
                **STOP.**

        * **C) Check for "Good Trade":**
            * **If `Captured_Piece_Value > Moving_Piece_Value`**
                (e.g., Knight(3) takes Rook(5)): This is a **"Good Trade"**.
            * `verdict: "brilliant"`. Justification: "The move
                was a 'Good Trade,' winning material." **STOP.**
                
        * **D) Check for "Equal Trade" (The Pawn Recapture Bug):**
            * **If `Moving_Piece_Value == Lowest_Retaliator_Value`**
                (e.g., Bishop(3) takes Pawn(1), Pawn(1) *cannot*
                recapture, but another Bishop(3) can).
            * **If `Moving_Piece_Value == Captured_Piece_Value`**
                (e.g., Bishop(3) takes Knight(3)).
            * **If `Captured_Piece_Value < Moving_Piece_Value` BUT
                `Lowest_Retaliator_Value == Moving_Piece_Value`**
                (e.g. Bishop(3) takes Pawn(1), but is recaptured by
                a Knight(3) or Bishop(3)).
            * **If YES (to any of these):** This is an **"Equal Trade"**.
            * `verdict: "acknowledgment"`. Justification: "The
                move was an 'Equal Trade,' which is a safe and
                valid positional choice." **STOP.**

        ---
        **Step 2: Analyze Defensive Crisis (If not a capture/forcing move).**
        
        * Look at the `DANGERS_LIST`. Was there an "Urgent Crisis"
            (like a "Hanging Piece" or a "Pin" on a high-value piece)?
        * **If YES (and user *ignored* it):** `verdict: "blunder"`.
            Justification: "The DANGERS_LIST showed an urgent threat
            (like a hanging Queen) that the CHOSEN_MOVE ignored." **STOP.**
        * **If YES (and user *solved* it):** `verdict: "good"`.
            Justification: "The DANGERS_LIST showed an urgent threat,
            and the CHOSEN_MOVE successfully solved it." **STOP.**

        ---
        **Step 3: Analyze Principles (If safe, non-capture, non-defensive).**

        * **Check for "Hanging Piece" (CRITICAL FIX - Using `defenders` list):**
        * Does `CHOSEN_MOVE_DATA` have `captured_piece: null`
            AND a **non-empty** `retaliation: []` list?
            * **If NO:** The move is safe (not a capture, not attacked).
                **Go to "Check for Tempo".**
            * **If YES:** The move is *attacked*. Now we must
                check if it's a blunder.
            
            * **(NEW DEFENDER CHECK):** Look at `CHOSEN_MOVE_DATA.defenders`.
                Is the `defenders: []` list **non-empty**?
                * **If YES:** The piece is defended. This is **NOT** a
                    blunder, it is a normal, defended developing move
                    (like Nf3 or Bc4).
                * **Go to "Check for Tempo".**
            
            * **(FALLTHROUGH - IT IS ATTACKED *AND* UNDEFENDED):**
            * The `defenders: []` list is empty. This is a true
                "Hanging Piece" situation. Now check if it's a blunder.
            * Get `Moving_Piece_Value` (from
                `CHOSEN_MOVE_DATA.moving_piece.value`).
            * Get `Lowest_Retaliator_Value` (find the minimum
                `value` from the `retaliation` list).
            *
            * **If `Moving_Piece_Value > Lowest_Retaliator_Value`**
                (e.g., Queen(9) moves to an *undefended* square
                attacked by a Pawn(1)).
                * This is a true **"Hanging Piece" blunder**.
                * `verdict: "blunder"`. Justification: "This move is a
                    'Hanging Piece' blunder. It moved to an undefended
                    square where it can be captured by a lower-value
                    piece for free." **STOP.**
            *
            * **If `Moving_Piece_Value <= Lowest_Retaliator_Value`**
                (e.g., Knight(3) moves to an *undefended* square
                attacked by a Queen(9)): This is **NOT** a blunder,
                as the opponent would make a "Bad Trade" to
                capture it.
                * **Go to "Check for Tempo".**
                
        * **Check for Tempo:** The move is safe. Analyze its principle.
        * Does it follow "Good Tempo" (`previous_move_count: 0`)?
            * `verdict: "acknowledgment"`. Justification: "No dangers
                and no forcing moves. The move followed 'Good Tempo'
                by developing a new piece."
        * Does it follow "Bad Tempo"?
            * `verdict: "teaching"`. Justification: "No dangers/forcing
                moves. The move was 'Bad Tempo' (e.g., moving a
                pawn for no reason in the opening)."
        * Is it just a simple, safe, non-noteworthy move?
            * `verdict: "acknowledgment"`. Justification: "No dangers,
                no forcing moves, and the move was a simple, safe
                positional move."

        Return *only* the single-line JSON verdict, including your justification.
        """
        
        response = pro_model.generate_content(prompt)
        print(f"--- TRIAGE ANALYST (RAW) ---\n{response.text}\n------------------------------")
        
        json_str = response.text.strip().replace("```json", "").replace("```", "").strip()
        parsed_json = json.loads(json_str)
        return parsed_json
            
    except Exception as e:
        print(f"!!! CRITICAL: Triage Analyst Tool error: {e}")
        return {"verdict": "error", "focus": "tool_failure", "justification": str(e)}

def call_conversational_coach_tool(triage_verdict_json, 
                                   last_move_data_json,  # <-- NEW
                                   dangers_before_json,  # <-- NEW
                                   options_before_json,  # <-- NEW
                                   user_skill_level, 
                                   player_color):
    """
    (NEW - Coach 4.0) Specialist Tool 2: The "Conversationalist".
    This tool is the "mouth." It receives the "verdict" from the
    Triage Analyst and turns it into a human-like, conversational
    message, as requested by the user.
    """
    print("[CONVERSATIONALIST TOOL] Generating response...")
    try:
        prompt = f"""
        You are 'Coach Gemini,' a friendly, human-like, and concise
        chess coach. You are having an ongoing conversation with your
        student, who is `{user_skill_level}` and playing as `{player_color}`.
        
        Your internal "Triage Analyst" just handed you this verdict.
        Your job is to translate this verdict into a *single, supportive,
        conversational sentence*.
        
        **Your Goal:** Acknowledge *every* move to keep the conversation
        flowing. You MUST use the `FULL_MOVE_CONTEXT` and the
        `justification` inside the `TRIAGE_VERDICT` to be specific.
        **Do NOT use the example messages verbatim.**
        
        `TRIAGE_VERDICT (Your "Brain's" thought)`:
        {triage_verdict_json}

        `FULL_MOVE_CONTEXT (Use this for your response!)`:
        - CHOSEN_MOVE: {last_move_data_json}
        - DANGERS_BEFORE: {dangers_before_json}
        - OPTIONS_BEFORE: {options_before_json}

        **How to Respond (Use your *own* words and the context):**

        1.  **If `verdict` is "brilliant"**:
            * This is the "checkmate" or "hanging bishop" scenario!
            * Return `response_type: "praise"`.
            * **Example:** "Wow, brilliant move with your Bishop to f7!
                You found the checkmate and correctly ignored the
                hanging bishop."

        2.  **If `verdict` is "blunder"**:
            * This is a critical, "teachable moment."
            * Return `response_type: "intervention"`.
            * **Example (Socratic):** "[INTERVENTION] Hold on a
                second! I noticed you moved your pawn to a3. Did you see
                that your Queen on d8 was in danger?"

        3.  **If `verdict` is "good"**:
            * The user solved a tough problem.
            * Return `response_type: "praise"`.
            * **Example:** "Nice! Good eye, you saw your Bishop on c4
                was in trouble and moved it to safety."

        4.  **If `verdict` is "teaching" (e.g., "bad_tempo")**:
            * Return `response_type: "encouragement"`.
            * **Example:** "Okay, that's a safe move with your a-pawn.
                Just a small tip: in the opening, it's usually better to
                develop your Knights and Bishops to the center first."
                
        5.  **If `verdict` is "acknowledgment" (e.g., "good_tempo")**:
            * This is a standard, good move.
            * Return `response_type: "encouragement"`.
            * **Example:** "Nice. Moving your Knight to f3 is a solid,
                principled move that develops a piece."

        Return *only* the final JSON packet for the app.
        
        {{"response_type": "praise", "message": "Great find!"}}
        """
        
        response = flash_model.generate_content(prompt)
        print(f"--- CONVERSATIONALIST (RAW) ---\n{response.text}\n------------------------------")
        
        json_str = response.text.strip().replace("```json", "").replace("```", "").strip()
        parsed_json = json.loads(json_str)
        return parsed_json
            
    except Exception as e:
        print(f"!!! CRITICAL: Conversationalist Tool error: {e}")
        return {"response_type": "silent", "message": None} # Fail silently

# --- (NEW) Coach 4.0 Q&A Tools ---

def call_qa_router_tool(user_query, game_context_json):
    """
    (NEW - Q&A 2.0) Tool 1: The "Q&A Router".
    This tool's only job is to analyze the user's *intent*
    and choose the correct specialist tool.
    """
    print("[Q&A ROUTER TOOL] Analyzing user intent...")
    try:
        prompt = f"""
        You are a "Q&A Router" agent. Your job is to analyze the
        `USER_QUERY` and the `GAME_CONTEXT` to determine the
        user's *intent*. You must then choose one specialist tool.
        
        `GAME_CONTEXT`:
        {game_context_json}
        
        `USER_QUERY`:
        "{user_query}"
        
        **Available Specialist Tools:**
        
        1.  **`explain_last_move`**: Use if the user is asking
            *why* the AI (opponent) made its last move.
            *Examples: "Why did you move your knight?", "what was
            that move for?", "explain your reasoning"*
            
        2.  **`analyze_board`**: Use if the user is asking a
            *strategic question* about the *current board state*.
            *Examples: "Is my king safe?", "who is winning?",
            "what should I do next?", "am I in danger?"*
            
        3.  **`explain_concept`**: Use if the user is asking for
            the *definition* of a chess term.
            *Examples: "What is a 'pin'?", "What's 'tempo'?",
            "What is castling?"*
            
        4.  **`general_chit_chat`**: Use for any other social
            interaction, greeting, or unclear question.
            *Examples: "hi", "lol", "this is hard", "ok thanks"*

        Return *only* the JSON with your choice.
        {{"tool_choice": "explain_concept"}}
        """
        
        response = flash_model.generate_content(prompt)
        print(f"--- Q&A ROUTER (RAW) ---\n{response.text}\n------------------------------")
        
        json_str = response.text.strip().replace("```json", "").replace("```", "").strip()
        parsed_json = json.loads(json_str)
        return parsed_json
            
    except Exception as e:
        print(f"!!! CRITICAL: Q&A Router Tool error: {e}")
        return {"tool_choice": "general_chit_chat"}

def call_qa_explain_last_move_tool(user_query, game_context_json):
    """(NEW - Q&A 2.0) Specialist: Explains AI's last move."""
    try:
        context = json.loads(game_context_json)
        ai_reasoning = context.get("last_ai_reasoning", "I don't have a record of my last thought.")
        
        prompt = f"""
        You are 'Coach Gemini'. The user is asking about your
        (the AI opponent's) last move.
        
        Your internal reasoning was: "{ai_reasoning}"
        
        The user asked: "{user_query}"
        
        Your task: Explain your reasoning in a simple,
        first-person, conversational way.
        
        Example: "Good question! I moved my knight there to
        control the center and develop a new piece."
        
        Return *only* the JSON response.
        {{"commentary": "I moved my knight there because..."}}
        """
        response = flash_model.generate_content(prompt)
        json_str = response.text.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(json_str)
    except Exception as e:
        return {"commentary": f"Sorry, I had an error: {e}"}

def call_qa_analyze_board_tool(user_query, game_context_json):
    """(NEW - Q&A 2.0) Specialist: Analyzes the live board."""
    try:
        context = json.loads(game_context_json)
        dangers = context.get("dangers_list", "[]")
        options = context.get("options_list", "[]")
        
        prompt = f"""
        You are 'Coach Gemini'. The user is asking a strategic
        question about the *current* board state.
        
        User question: "{user_query}"
        
        Use the following *ground truth data* to answer them.
        Do not make things up.
        
        `GROUND_TRUTH_DANGERS (What's attacking me?)`:
        {dangers}
        
        `GROUND_TRUTH_OPTIONS (What can I do?)`:
        {options}
        
        Your task: Answer the user's question based *only* on the
        ground truth.
        
        Example ("Is my king safe?"): "Good question. Looking at the
        data, I don't see any immediate checks or threats to your king.
        However, the 'dangers' list shows your Rook on a8 is
        attacked by a Bishop."
        
        Return *only* the JSON response.
        {{"commentary": "That's a great question..."}}
        """
        response = pro_model.generate_content(prompt) # Use Pro for smart analysis
        json_str = response.text.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(json_str)
    except Exception as e:
        return {"commentary": f"Sorry, I had an error: {e}"}

def call_qa_explain_concept_tool(user_query, game_context_json):
    """(NEW - Q&A 2.0) Specialist: Explains a core concept."""
    try:
        prompt = f"""
        You are 'Coach Gemini'. The user is asking for the
        definition of a chess concept.
        
        User question: "{user_query}"
        
        Here is your entire knowledge base of definitions:
        {CORE_CHESS_DEFINITIONS}
        
        Your task: Find the *most relevant* definition from your
        knowledge base that answers the user's question. Explain it
        simply, like a human teacher.
        
        Example ("What is a pin?"): "A 'pin' is a cool tactic!
        It's when you attack an enemy piece, but it can't move
        because a *more valuable* piece (like a Queen or King)
        is hiding right behind it."
        
        Return *only* the JSON response.
        {{"commentary": "A 'pin' is when..."}}
        """
        response = flash_model.generate_content(prompt)
        json_str = response.text.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(json_str)
    except Exception as e:
        return {"commentary": f"Sorry, I had an error: {e}"}

def call_qa_chit_chat_tool(user_query, game_context_json):
    """(NEW - Q&A 2.0) Specialist: Handles small talk."""
    try:
        prompt = f"""
        You are 'Coach Gemini'. The user is just making
        small talk or saying something that isn't a question.
        
        User said: "{user_query}"
        
        Your task: Just be friendly and encouraging!
        
        Examples:
        - "lol" -> "Haha!"
        - "this is hard" -> "You're doing great! Keep it up."
        - "hi" -> "Hi there!"
        
        Return *only* the JSON response.
        {{"commentary": "You've got this!"}}
        """
        response = flash_model.generate_content(prompt)
        json_str = response.text.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(json_str)
    except Exception as e:
        return {"commentary": f"Sorry, I had an error: {e}"}

# --- (DEPRECATED) Coach 2.0 Tools ---

def call_analyst_tool(last_move_data_json, dangers_before_json, options_before_json):
    """
    (DEPRECATED - Coach 2.0) Specialist 1: The Grandmaster.
    Analyzes the move based on the *full context* before the move was made.
    """
    print("[DEPRECATED] call_analyst_tool was called.")
    return {"move_quality": "error", "message": "Deprecated function"}

def call_pedagogy_tool(analysis_json, user_skill_level, player_color):
    """
    (DEPRECATED - Coach 2.0) Specialist 2: The Teacher.
    Translates the Analyst's JSON into a human-readable packet.
    """
    print("[DEPRECATED] call_pedagogy_tool was called.")
    return {"response_type": "silent", "message": None}

def call_post_game_analyst_tool(game_data_json, player_color):
    """
    (NEW) Specialist 3: The Post-Game Analyst.
    Provides a summary of the entire game.
    (This function is unchanged and still used)
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

# --- (DEPRECATED) Q&A Tool (Streaming) ---

def get_coach_qa_response(user_query, board_state_narrative, player_color):
    """
    (DEPRECATED) Handles a direct Q&A question from the user.
    This streaming function is replaced by the new Q&A Router Agent.
    """
    print("[DEPRECATED] get_coach_qa_response was called.")
    fallback_json = {"commentary": "This function is deprecated."}
    class _MockChunk:
        def __init__(self, text):
            self.text = text
    def fallback_stream():
        yield _MockChunk(json.dumps(fallback_json))
    return fallback_stream()


# --- AI Opponent Agent Tools ---
# (All opponent functions below are unchanged)

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
            * **If `is_pin: true`:** This is a critical tactical situation. The `threatened_piece` is pinned to the `pinned_to_piece`.
                **Your Goal:** Find the best move that *solves the pin*. Moving the `threatened_piece` is *often* a blunder because it exposes the `pinned_to_piece`.
                You **MUST** analyze the `OPTIONS_LIST` (your ground truth) to find the solution. The `OPTIONS_LIST` *only* contains legal moves. Look for moves such as:
                1.  A move for the `threatened_piece` that is *in* the `OPTIONS_LIST`. (This is rare, but could be capturing the pinning piece).
                2.  A move that *blocks* the pin.
                3.  A move that moves the `pinned_to_piece` to safety.
            * **If `is_pin: false`:** This is a simple threat.
                **Your Goal:** Determine if it's an *Urgent Crisis* or just a *Decision*.
                1.  **Urgent Crisis:** Is it a "Hanging Piece" or "Bad Trade"? If yes, you must find a *safe* escape move from the `OPTIONS_LIST`.
                2.  **Decision:** Is it just an "Equal Trade"? If yes, this is not a crisis. You are free to ignore it if you find a better *offensive* opportunity.
        
        2.  **Analyze Opportunities (Offense):** If (and only if) you are not
            in an immediate crisis, scan the `OPTIONS_LIST` for a winning attack.
            **Your Goal:** Find a forcing, *safe* tactic or capitalize on capturing hanging rooks, bishops, knights, or queens.
            * **Find Forcing Tactics:** Look for moves in the `OPTIONS_LIST` where `is_fork: true` or `creates_pin: true`. (These are examples; also consider "Skewers" or "Discovered Attacks").
            * **Principle of Safety (CRITICAL):** A tactic is only good if it's not a blunder itself. Before selecting a "forcing" move, you **must** check its `retaliation` list.
                * If `retaliation` is empty, the tactic is safe.
                * If `retaliation` is *not* empty, you must evaluate that trade. If the `retaliation` results in a "Bad Trade" or "Hanging Piece" (based on `CORE_CHESS_DEFINITIONS`), then this tactic is a *mistake*, and you should avoid it.

        3.  **Prioritize "Good Tempo":** If there are no immediate dangers
            *or* safe, forcing opportunities, then (and only then) fall back to
            solid, positional chess:
            * You must **strongly prefer** developing a new piece (a move
                with `previous_move_count: 0`).
            * **Crucially:** Do not make a "Bad Tempo" move (like `f6-e4`
                in the opening) if it is also a "Hanging Piece" blunder
                (as defined in the Core Definitions).

        **Your Task:**
        Use these high-level principles to select the single best move.
        Weigh the credible threats and all possible offensive opportunities when deciding on which move to make.
        Your `reasoning` must explain your thought process.
        
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
            * **"Oh no, a Pin!" (if `is_pin: true`):** This is bad. The `threatened_piece` is pinned! This means it has very few legal moves. My goal is to solve this. I should **check the `OPTIONS_LIST`** to see what legal moves it *does* have (like maybe I can capture the attacker?). If it has no good moves, I must find a move from the `OPTIONS_LIST` to save the piece *behind* it (the `pinned_to_piece`).
            * **"Oh no, my piece is hanging!" (if `is_pin: false`):**
                If I am about to make a "Hanging Piece" or "Bad Trade"
                blunder, that's a crisis! My goal is to find a safe
                escape move. I must check the `OPTIONS_LIST` for a move
                where the `retaliation` is safe (not a 'Bad Trade').
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



import chess_llm_functions as llm_api
import random

def get_ai_move(board_state_narrative, legal_moves, user_skill_level):
    """
    This is the main "brain" of the AI Opponent Agent.
    It decides *what kind* of move to make (best, human, blunder)
    based on the user's skill level, then calls the appropriate tool.
    
    (MODIFIED) Implements new LLM-based move repair logic.
    """
    print(f"[OPPONENT AGENT] AI move requested. Skill level: {user_skill_level}")
    
    # --- 1. Weighted Choice Logic ---
    if user_skill_level == "beginner":
        # 60% chance of a bad move, 30% solid, 10% best
        tool_choice = random.choices(
            ["blunder", "human", "best"], 
            weights=[0.6, 0.3, 0.1], k=1
        )[0]
        
    elif user_skill_level == "intermediate":
        # 15% chance of a blunder, 65% solid, 20% best
        tool_choice = random.choices(
            ["blunder", "human", "best"], 
            weights=[0.15, 0.65, 0.20], k=1
        )[0]
        
    else: # "advanced"
        # 0% chance of a blunder, 40% solid, 60% best
        tool_choice = random.choices(
            ["blunder", "human", "best"], 
            weights=[0.0, 0.4, 0.6], k=1
        )[0]
    
    print(f"[OPPONENT AGENT] Weighted choice selected: '{tool_choice}'")

    # --- 2. Call the Selected Tool ---
    legal_moves_str = ", ".join(legal_moves) # Pass all legal moves to LLM
    packet = None
    
    if tool_choice == "best":
        print("[OPPONENT AGENT] Calling Best Move Tool...")
        packet = llm_api.call_best_move_tool(board_state_narrative, legal_moves_str)
    elif tool_choice == "blunder":
        print("[OPPONENT AGENT] Calling Teaching Blunder Tool...")
        packet = llm_api.call_teaching_blunder_tool(board_state_narrative, legal_moves_str)
    else: # "human"
        print("[OPPONENT AGENT] Calling Human-Like Move Tool...")
        packet = llm_api.call_human_like_move_tool(board_state_narrative, legal_moves_str)

    # --- 3. Validate and Return Final Packet ---
    if not packet or "move" not in packet or "reasoning" not in packet:
        print(f"!!! CRITICAL: AI Opponent Tool ({tool_choice}) failed or returned bad data.")
        print("[OPPONENT AGENT] Fallback: Choosing random move.")
        fallback_move = random.choice(legal_moves)
        return {
            "move": fallback_move,
            "reasoning": "I had a connection error, so I just picked a random move!",
            "move_type": "blunder" # Treat errors as blunders
        }

    # (NEW) Validation Flow
    raw_move = packet["move"]

    # 1. Happy Path: Check if the raw move is legal
    if raw_move in legal_moves:
        print(f"[OPPONENT AGENT] Raw move '{raw_move}' is legal.")
        print(f"[OPPONENT AGENT] Final move packet: {packet}")
        return {
            "move": raw_move,
            "reasoning": packet["reasoning"],
            "move_type": tool_choice
        }
    
    # 2. Repair Path: If not legal, call the Sanitizer Tool
    print(f"!!! WARNING: AI Opponent Tool ({tool_choice}) hallucinated an illegal move: '{raw_move}'.")
    print("[OPPONENT AGENT] Calling Move Sanitizer Tool to attempt repair...")
    
    repaired_packet = llm_api.call_move_sanitizer_tool(raw_move, legal_moves_str)
    repaired_move = repaired_packet.get("move") # Will be None if it fails

    # 3. Check if repair was successful
    if repaired_move and repaired_move in legal_moves:
        print(f"[OPPONENT AGENT] Repair successful! Sanitized '{raw_move}' to '{repaired_move}'.")
        return {
            "move": repaired_move, # Return the *repaired* move
            "reasoning": packet["reasoning"], # Keep the *original* reasoning
            "move_type": tool_choice
        }
        
    # 4. Final Fallback: Repair failed or returned an illegal move
    print(f"!!! CRITICAL: Move repair failed. Sanitized move '{repaired_move}' is still illegal.")
    print("[OPPONENT AGENT] Fallback: Choosing random move.")
    fallback_move = random.choice(legal_moves)
    return {
        "move": fallback_move,
        "reasoning": f"My brain short-circuited! I wanted to play {raw_move} but it wasn't a valid move. I played a random move instead.",
        "move_type": "blunder"
    }


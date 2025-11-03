import chess_llm_functions as llm_api
import random
import json

def get_ai_move(enhanced_moves_json, tactical_threats_json, legal_moves_list_simple, user_skill_level):
    """
    This is the main "brain" of the AI Opponent Agent.
    (NEW) It is now a "Router Agent" that first analyzes the situation,
    then calls a specialized tool ("best", "human", or "blunder").
    
    (MODIFIED) Uses "Move Consequence Mapping" ("Options List") and
    "Tactical Threats" ("Dangers List") as the new ground truth.
    """
    print(f"[OPPONENT AGENT] AI move requested. Skill level: {user_skill_level}")
    
    # --- 1. (NEW) Call the Router Agent ---
    # This call decides *which* personality to use based on high-level
    # definitions and principles.
    print(f"[OPPONENT AGENT] Calling Router Agent to select personality...")
    router_packet = llm_api.call_opponent_router_agent(
        enhanced_moves_json, 
        tactical_threats_json, 
        user_skill_level
    )
    
    tool_choice = router_packet.get("tool_choice")
    if not tool_choice or tool_choice not in ["best", "human", "blunder"]:
        print(f"!!! CRITICAL: Router Agent failed. Falling back to 'human' tool.")
        tool_choice = "human"
        
    print(f"[OPPONENT AGENT] Router Agent selected: '{tool_choice}' based on reasoning: {router_packet.get('reasoning')}")

    # --- 2. Call the Selected Specialist Tool ---
    # Data is already in JSON string format from app.py
    legal_moves_str = ", ".join(legal_moves_list_simple) # For sanitizer
    
    packet = None
    
    if tool_choice == "best":
        print("[OPPONENT AGENT] Calling Best Move Tool...")
        packet = llm_api.call_best_move_tool(enhanced_moves_json, tactical_threats_json)
    elif tool_choice == "blunder":
        print("[OPPONENT AGENT] Calling Teaching Blunder Tool...")
        packet = llm_api.call_teaching_blunder_tool(enhanced_moves_json, tactical_threats_json)
    else: # "human"
        print("[OPPONENT AGENT] Calling Human-Like Move Tool...")
        packet = llm_api.call_human_like_move_tool(enhanced_moves_json, tactical_threats_json)

    # --- 3. Validate and Return Final Packet ---
    if not packet or "move" not in packet or "reasoning" not in packet:
        print(f"!!! CRITICAL: AI Opponent Tool ({tool_choice}) failed or returned bad data.")
        print("[OPPONENT AGENT] Fallback: Choosing random move.")
        fallback_move = random.choice(legal_moves_list_simple)
        return {
            "move": fallback_move,
            "reasoning": "I had a connection error, so I just picked a random move!",
            "move_type": "blunder" # Treat errors as blunders
        }

    # Validation Flow
    raw_move = packet["move"]

    # 1. Happy Path: Check if the raw move is legal
    if raw_move in legal_moves_list_simple:
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
    if repaired_move and repaired_move in legal_moves_list_simple:
        print(f"[OPPONENT AGENT] Repair successful! Sanitized '{raw_move}' to '{repaired_move}'.")
        return {
            "move": repaired_move, # Return the *repaired* move
            "reasoning": packet["reasoning"], # Keep the *original* reasoning
            "move_type": tool_choice
        }
        
    # 4. Final Fallback: Repair failed or returned an illegal move
    print(f"!!! CRITICAL: Move repair failed. Sanitized move '{repaired_move}' is still illegal.")
    print("[OPPONENT AGENT] Fallback: Choosing random move.")
    fallback_move = random.choice(legal_moves_list_simple)
    return {
        "move": fallback_move,
        "reasoning": f"My brain short-circuited! I wanted to play {raw_move} but it wasn't a valid move. I played a random move instead.",
        "move_type": "blunder"
    }


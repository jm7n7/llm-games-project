import chess_llm_functions as llm_api
import json

# --- 1. POST-MOVE COACH AGENT (NEW "Offense-First" Pipeline) ---

def get_coaching_packet(last_move_data, dangers_before_json, options_before_json, user_skill_level, player_color):
    """
    (Coach 4.0) This is the main "brain" of the post-move Coach Agent.
    It orchestrates the "Triage -> Converse" pipeline to implement the
    "Offense-First" logic.
    """
    print("[COACH AGENT 4.0] Human move detected.")
    
    # --- STEP 1: Call the "Triage" tool (The "Brain") ---
    # This tool implements the "Offense-First" logic.
    print("[COACH AGENT 4.0] Calling Triage Analyst Tool...")
    triage_verdict_json = llm_api.call_triage_analyst_tool(
        json.dumps(last_move_data), 
        dangers_before_json, 
        options_before_json
    )
    
    if not triage_verdict_json:
        print("[COACH AGENT 4.0] Triage Analyst Tool failed. Aborting.")
        return {"response_type": "silent", "message": None} # Fail silently
        
    print(f"[COACH AGENT 4.0] Triage Verdict: {triage_verdict_json}")

    # --- STEP 2: Call the "Conversationalist" tool (The "Mouth") ---
    # This tool translates the cold verdict into a human-like response.
    print(f"[COACH AGENT 4.0] Calling Conversationalist Tool...")
    instruction_packet = llm_api.call_conversational_coach_tool(
        json.dumps(triage_verdict_json), 
        json.dumps(last_move_data),  # <-- NEW: Pass the move data
        dangers_before_json,        # <-- NEW: Pass the dangers context
        options_before_json,        # <-- NEW: Pass the options context
        user_skill_level, 
        player_color
    )
    
    if not instruction_packet:
        print("[COACH AGENT 4.0] Conversationalist Tool failed. Aborting.")
        return {"response_type": "silent", "message": None} # Fail silently

    print(f"[COACH AGENT 4.0] Final Conversational Packet: {instruction_packet}")
    
    # 3. Return the final, human-readable packet to the app
    return instruction_packet

# --- 2. Q&A CHAT AGENT (NEW "Router" Pipeline) ---

def get_qa_response(user_query, game_context_json):
    """
    (Coach 4.0) This is the main orchestrator for the Q&A chat.
    It uses a "Router -> Specialist" pipeline to understand the
    user's *intent* and provide a smart answer.
    """
    print("[COACH Q&A AGENT] New user query received.")
    
    try:
        # --- STEP 1: Call the Q&A Router Tool ---
        print("[COACH Q&A AGENT] Calling Q&A Router...")
        router_decision = llm_api.call_qa_router_tool(user_query, game_context_json)
        tool_choice = router_decision.get("tool_choice", "general_chit_chat")
        print(f"[COACH Q&A AGENT] Router chose tool: '{tool_choice}'")

        # --- STEP 2: Call the chosen Specialist Tool ---
        if tool_choice == "explain_last_move":
            print("[COACH Q&A AGENT] Calling 'Explain Last Move' specialist...")
            response_packet = llm_api.call_qa_explain_last_move_tool(user_query, game_context_json)
        
        elif tool_choice == "analyze_board":
            print("[COACH Q&A AGENT] Calling 'Analyze Board' specialist...")
            response_packet = llm_api.call_qa_analyze_board_tool(user_query, game_context_json)
        
        elif tool_choice == "explain_concept":
            print("[COACH Q&A AGENT] Calling 'Explain Concept' specialist...")
            response_packet = llm_api.call_qa_explain_concept_tool(user_query, game_context_json)
        
        else: # "general_chit_chat"
            print("[COACH Q&A AGENT] Calling 'Chit-Chat' specialist...")
            response_packet = llm_api.call_qa_chit_chat_tool(user_query, game_context_json)
        
        return response_packet

    except Exception as e:
        print(f"!!! CRITICAL: Q&A Agent Pipeline failed: {e}")
        return {"commentary": "My apologies, I had a connection issue while trying to answer that."}


# --- 3. POST-GAME SUMMARY (Unchanged) ---

def get_post_game_summary(game_data_json, player_color):
    """
    Orchestrator for calling the post-game summary tool.
    (This function is unchanged)
    """
    print("[COACH AGENT] Game over detected. Calling Post-Game Analyst Tool...")
    
    summary_packet = llm_api.call_post_game_analyst_tool(game_data_json, player_color)
    
    if not summary_packet:
        print("[COACH AGENT] Post-Game Analyst Tool failed.")
        return {"message": "Good game! I wasn't able to generate a summary this time."}

    print("[COACH AGENT] Post-Game summary packet received.")
    return summary_packet


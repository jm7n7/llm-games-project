import chess_llm_functions as llm_api
import json

def get_coaching_packet(last_move_data, dangers_before_json, options_before_json, user_skill_level, player_color):
    """
    (Coach 2.0) This is the main "brain" of the Coach Agent.
    It orchestrates the flow of:
    1. Getting a cold, hard analysis of the move *based on full context*.
    2. Translating that analysis into a friendly, skill-appropriate packet.
    """
    print("[COACH AGENT 2.0] Human move detected.")
    
    # 1. Call the Analyst Tool (Coach 2.0)
    print("[COACH AGENT 2.0] Calling Analyst Tool...")
    analyst_json = llm_api.call_analyst_tool(
        json.dumps(last_move_data), 
        dangers_before_json, 
        options_before_json
    )
    
    if not analyst_json:
        print("[COACH AGENT 2.0] Analyst Tool failed. Aborting.")
        return {"response_type": "silent", "message": None} # Fail silently
        
    print(f"[COACH AGENT 2.0] Analyst Tool Response: {analyst_json}")

    # 2. Call the Pedagogy Tool (this tool is unchanged)
    print(f"[COACH AGENT 2.0] Calling Pedagogy Tool with skill={user_skill_level} and color={player_color}...")
    instruction_packet = llm_api.call_pedagogy_tool(analyst_json, user_skill_level, player_color)
    
    if not instruction_packet:
        print("[COACH AGENT 2.0] Pedagogy Tool failed. Aborting.")
        return {"response_type": "silent", "message": None} # Fail silently

    print(f"[COACH AGENT 2.0] Pedagogy Tool Response: {instruction_packet}")
    
    # 3. Return the final packet to the app
    print("[COACH AGENT 2.0] Final packet sent to app.py.")
    return instruction_packet

def get_post_game_summary(game_data_json, player_color):
    """
    Orchestrator for calling the post-game summary tool.
    """
    print("[COACH AGENT] Game over detected. Calling Post-Game Analyst Tool...")
    
    summary_packet = llm_api.call_post_game_analyst_tool(game_data_json, player_color)
    
    if not summary_packet:
        print("[COACH AGENT] Post-Game Analyst Tool failed.")
        return {"message": "Good game! I wasn't able to generate a summary this time."}

    print("[COACH AGENT] Post-Game summary packet received.")
    return summary_packet


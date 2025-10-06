import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

# --- Configuration ---
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")

if not API_KEY:
    raise ValueError("GOOGLE_API_KEY not found. Please ensure your .env file is set up correctly.")

genai.configure(api_key=API_KEY)
llm = genai.GenerativeModel('gemini-2.5-pro')

def extract_graph_data(text_content):
    """
    Uses the Gemini API to extract entities and relations from text content.
    The prompt is now enhanced to capture the game's winner and winning move.
    """
    prompt = f"""
    From the chess game analysis provided below, extract all the entities and their relationships for each turn.
    The entities should be categorized into the following types:
    PLAYER
    PIECE
    TURN
    KEY_MOVE
    SQUARE
    STRATEGY
    GAME_OUTCOME

    
    Crucially, you MUST identify the following specific entities if they are mentioned:
    - The winning player (e.g., "White wins"). This should be a PLAYER attribute.
    - The move that resulted in checkmate. This should be a KEY_MOVE attribute.
    
    The relationships should describe how these entities are connected.
    
    Return the result as a single JSON object with two keys: "entities" and "relations".
    
    Example Relation:
    {{
      "subject": "entity_id_1",
      "object": "entity_id_2",
      "turn": "entity_turn_id",
      "relationship": "RELATIONSHIP_LABEL"
      "context": "CONTEXT_OF_RELATIONSHIP"
    }}

    Analysis Text:
    ---
    {text_content}
    ---
    
    JSON Output:
    """
    
    response = llm.generate_content(prompt)
    
    # Clean the response to ensure it's valid JSON
    cleaned_response = response.text.strip().replace("```json", "").replace("```", "")
    
    return json.loads(cleaned_response)

def main():
    """
    Main function to load analysis, extract data, and save it.
    """
    game_id = "chs-850-0001"
    input_filename = f"{game_id}_analysis.txt"
    output_filename = f"{game_id}_graph_data.json"

    try:
        with open(input_filename, 'r', encoding='utf-8') as f:
            analysis_text = f.read()
        print(f"Successfully loaded analysis from {input_filename}")

        print("Extracting entities and relations with Gemini...")
        graph_data = extract_graph_data(analysis_text)
        
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(graph_data, f, indent=4)
            
        print(f"Successfully extracted and saved graph data to {output_filename}")
        
        print("\n--- Extraction Preview ---")
        print(f"Found {len(graph_data.get('entities', []))} entities.")
        print(f"Found {len(graph_data.get('relations', []))} relations.")

    except FileNotFoundError:
        print(f"Error: The analysis file '{input_filename}' was not found.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()


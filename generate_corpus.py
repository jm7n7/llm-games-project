import pandas as pd
import google.generativeai as genai
import os

from dotenv import load_dotenv

load_dotenv()
# --- Configuration ---
# This is a placeholder for your API key.
# In a real application, use st.secrets for this.
API_KEY = os.getenv("GOOGLE_API_KEY")

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-2.5-pro')

def format_game_for_llm(game_df):
    """
    Formats the move data from a game's DataFrame into a PGN-like string.
    PGN (Portable Game Notation) is a standard format for recording chess games.
    """
    move_list = []
    for index, row in game_df.iterrows():
        # Simple formatting, can be improved to be more PGN-compliant
        move_text = f"{row['turn']}. {row['piece_moved']} {row['end_square']}"
        if row['capture']:
            move_text += f" (captures {row['captured_piece']})"
        if row['check']:
            move_text += "+"
        if row['checkmate']:
            move_text += "#"
        move_list.append(move_text)
    
    return " ".join(move_list)

def generate_game_analysis(game_moves_str):
    """
    Sends the formatted game data to the Gemini API to get a strategic analysis.
    """
    prompt = f"""
    You are a world-class chess commentator. Analyze the following chess game for each turn.
    _Structure_ your analysis by turn, with the first turn being the first move by white, and the second turn being the first move by black.
    _For key moments_ identify the strategic importance of specific pieces or squares.
    Describe the flow of the game, including tactical blunders and brilliant moves.
    Identify the winner and loser of the game, with any details about the moves that led to the win or loss.
    **You are broadcasting the game to a global audience, so use simple language and avoid using complex chess notation.**

    _Here is the game:_
    {game_moves_str}
    
    Provide your analysis as a single block of text.
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def main():
    """
    Main function to process the chess game CSV and generate a text file with the analysis.
    """
    # Load the first game from the provided CSV
    # We will need to adjust the filename to match the one you want to process
    try:
        df = pd.read_csv("Chess_dataset_game1.csv", skiprows=2) 
        game_id = df['game_id'].iloc[0]
        
        print(f"Processing game: {game_id}...")
        
        # Format the game moves into a string
        game_moves = format_game_for_llm(df)
        
        print("Generating analysis with Gemini...")
        # Get the analysis from the LLM
        analysis_text = generate_game_analysis(game_moves)
        
        if analysis_text:
            # Save the analysis to a text file
            output_filename = f"{game_id}_analysis.txt"
            with open(output_filename, "w") as f:
                f.write(analysis_text)
            print(f"Successfully saved analysis to {output_filename}")
            print("\n--- Analysis Preview ---")
            print(analysis_text[:500] + "...") # Print a preview
        else:
            print("Failed to generate analysis.")
            
    except FileNotFoundError:
        print("Error: Could not find 'Chess_dataset - Sheet1.csv'. Please make sure the file is in the same directory.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()

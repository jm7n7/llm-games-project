import json
import pandas as pd
import matplotlib.pyplot as plt
import chess_llm_functions as llm_api

def create_win_probability_chart(game_data_df, game_id):
    """
    Generates a chart visualizing the win probability for both players over the course of a game.

    Args:
        game_data_df (pd.DataFrame): The dataframe containing the full game history.
        game_id (str): The unique identifier for the game.

    Returns:
        str: The file path of the generated chart image, or None if generation fails.
    """
    try:
        # 1. Convert game data to a string format for the LLM
        game_data_str = game_data_df.to_json(orient='records')

        # 2. Get the probability data from the LLM
        probability_json = llm_api.get_win_probability_data(game_data_str)
        if not probability_json:
            print("Failed to get probability data from LLM.")
            return None

        # 3. Parse the JSON data
        data = json.loads(probability_json)
        prob_df = pd.DataFrame(data['probabilities'])

        # 4. Create the plot using Matplotlib
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.set_facecolor('#f0f0f0') # Set a light gray background for contrast

        ax.plot(prob_df['turn'], prob_df['white_win_prob'], label='White Win Probability', color='dimgray', marker='o', markersize=4)
        ax.plot(prob_df['turn'], prob_df['black_win_prob'], label='Black Win Probability', color='black', marker='o', markersize=4)

        # Fill the area between the lines to show the advantage
        ax.fill_between(prob_df['turn'], prob_df['white_win_prob'], 0.5, color='white', alpha=0.5, interpolate=True)
        ax.fill_between(prob_df['turn'], prob_df['black_win_prob'], 0.5, color='black', alpha=0.5, interpolate=True)
        
        # Formatting the plot
        ax.set_title(f'Win Probability Over Time for Game: {game_id}', fontsize=16)
        ax.set_xlabel('Turn Number', fontsize=12)
        ax.set_ylabel('Win Probability', fontsize=12)
        ax.set_ylim(0, 1)
        ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
        ax.axhline(0.5, color='red', linestyle='--', linewidth=1, label='Equal Advantage')
        ax.legend()
        ax.grid(True, which='both', linestyle='--', linewidth=0.5)
        
        # 5. Save the plot to a file
        image_path = f"{game_id}_win_probability.png"
        plt.savefig(image_path, facecolor=fig.get_facecolor())
        plt.close(fig) # Close the figure to free up memory

        return image_path

    except (json.JSONDecodeError, KeyError, Exception) as e:
        print(f"An error occurred while creating the win probability chart: {e}")
        return None

def create_material_advantage_chart(game_data_df, game_id):
    """
    Generates a chart visualizing the material advantage for both players over time.

    Args:
        game_data_df (pd.DataFrame): The dataframe containing the full game history.
        game_id (str): The unique identifier for the game.

    Returns:
        str: The file path of the generated chart image, or None if generation fails.
    """
    try:
        # 1. Convert game data to a string format for the LLM
        game_data_str = game_data_df.to_json(orient='records')

        # 2. Get the score data from the LLM
        score_json = llm_api.get_material_advantage_data(game_data_str)
        if not score_json:
            print("Failed to get material score data from LLM.")
            return None

        # 3. Parse the JSON data
        data = json.loads(score_json)
        score_df = pd.DataFrame(data['scores'])

        # 4. Create the plot using Matplotlib
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.set_facecolor('#f0f0f0') # Set a light gray background for contrast

        ax.plot(score_df['turn'], score_df['white_score'], label='White Material Score', color='blue', marker='.', linestyle='-')
        ax.plot(score_df['turn'], score_df['black_score'], label='Black Material Score', color='green', marker='.', linestyle='-')

        # Formatting the plot
        ax.set_title(f'Material Advantage Over Time for Game: {game_id}', fontsize=16)
        ax.set_xlabel('Turn Number', fontsize=12)
        ax.set_ylabel('Material Score (Points)', fontsize=12)
        ax.legend()
        ax.grid(True, which='both', linestyle='--', linewidth=0.5)
        ax.set_ylim(bottom=0) # Score cannot be negative

        # 5. Save the plot to a file
        image_path = f"{game_id}_material_advantage.png"
        plt.savefig(image_path, facecolor=fig.get_facecolor())
        plt.close(fig) # Close the figure to free up memory

        return image_path

    except (json.JSONDecodeError, KeyError, Exception) as e:
        print(f"An error occurred while creating the material advantage chart: {e}")
        return None


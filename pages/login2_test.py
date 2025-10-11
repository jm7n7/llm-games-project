import streamlit as st
import json
import os

st.markdown("""
    <style>
    [data-testid="stSidebarNav"] {display: none;}
    [data-testid="stSidebar"] {display: none;}
    [data-testid="stHeader"] {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)



# ---------- Helper Functions ----------
def load_json(filename, default_data):
    if not os.path.exists(filename):
        with open(filename, "w") as f:
            json.dump(default_data, f, indent=2)
        return default_data
    with open(filename, "r") as f:
        return json.load(f)

def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)

# ---------- Initialize ----------
GAMES_FILE = "game_hist_dict.json"
game_hist_dict = load_json(GAMES_FILE, {})

st.set_page_config(page_title="Chess Game", page_icon="♟️")

# ---------- Check if user is logged in ----------
if "username" not in st.session_state:
    st.warning("Please sign in first.")
    st.stop()

user = st.session_state["username"]
st.title(f"♟️ Welcome, {user}")
st.subheader("Chess Game Simulation")

# ---------- Game Simulation ----------
if st.button("Play New Game"):
    # Load user games
    user_games = game_hist_dict.get(user, {})
    game_count = len(user_games) + 1
    game_name = f"game{game_count}"

    # Placeholder data for now
    new_game_data = {
        "winner": user  # just store who won (you)
    }

    # Save new game
    user_games[game_name] = new_game_data
    game_hist_dict[user] = user_games
    save_json(GAMES_FILE, game_hist_dict)

    st.success(f"✅ {game_name} saved under your account!")

# ---------- Show User Game Data ----------
st.divider()
st.write("### Your Saved Games")
user_games = game_hist_dict.get(user, {})
if user_games:
    for game, data in user_games.items():
        st.write(f"**{game}** → Winner: {data['winner']}")
else:
    st.info("No games yet. Press 'Play New Game' to create one.")

# ---------- Log Out ----------
if st.button("Log Out"):
    del st.session_state["username"]
    st.switch_page("login1_test.py")

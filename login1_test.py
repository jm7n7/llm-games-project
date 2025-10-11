import streamlit as st
import json
import os
import secrets
import string


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

def generate_password(length=12):
    alphabet = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(alphabet) for _ in range(length))

# ---------- Initialize ----------
LOGIN_FILE = "login_data.json"
GAMES_FILE = "game_hist_dict.json"

login_dict = load_json(LOGIN_FILE, {})
game_hist_dict = load_json(GAMES_FILE, {})

# ---------- Streamlit UI ----------
st.set_page_config(page_title="Chess Login", page_icon="♟️")
st.title("♟️ Chess Login / Create Account")

username = st.text_input("Username")
password = st.text_input("Password", type="password")

col1, col2 = st.columns(2)
with col1:
    if st.button("Sign In"):
        if username in login_dict and login_dict[username]["password"] == password:
            st.success(f"Welcome back, {username}!")
            st.session_state["username"] = username
            st.switch_page("pages/app.py")
        else:
            st.error("Invalid username or password.")
with col2:
    if st.button("Create Account"):
        if username in login_dict:
            st.warning("That username already exists.")
        elif not username or not password:
            st.warning("Please enter both username and password.")
        else:
            login_dict[username] = {"password": password}
            save_json(LOGIN_FILE, login_dict)

            game_hist_dict[username] = {}
            save_json(GAMES_FILE, game_hist_dict)

            st.success(f"Account created for {username}!")
            st.session_state["username"] = username
            st.switch_page("pages/app.py")

st.caption("No rules on username or password — this is a local test build.")

# app.py
import os
from dotenv import load_dotenv
import streamlit as st
import google.generativeai as genai



# --- Load environment variables (.env) ---
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    st.error("❌ GOOGLE_API_KEY not found in .env file.")
    st.stop()

# --- Configure Gemini ---
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-2.5-flash")

# --- Streamlit UI setup ---
st.set_page_config(page_title="Gemini Chatbot", page_icon="💬")
st.title("💬 Simple Gemini Chatbot")

# --- Maintain chat session ---
if "chat" not in st.session_state:
    st.session_state.chat = model.start_chat()
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Display past chat history ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- Chat input ---
user_input = st.chat_input("Type your message...")

if user_input:
    # Show user message
    st.chat_message("user").markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Get Gemini response
    try:
        response = st.session_state.chat.send_message(user_input)
        reply = response.text
    except Exception as e:
        reply = f"⚠️ Error: {e}"

    # Show assistant message
    st.chat_message("assistant").markdown(reply)
    st.session_state.messages.append({"role": "assistant", "content": reply})

import streamlit as st
from graph_retriever import GraphRetriever
from multi_hop_retriever import MultiHopRetriever
import os
from PIL import Image

# --- Page Configuration ---
st.set_page_config(
    page_title="Chess Game RAG Analyzer",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Title and Description ---
st.title("♟️ Chess Game RAG Analyzer")
st.markdown("""
This application uses a custom-built Graph-RAG pipeline to answer complex questions 
about a specific chess game. Ask a question below to see how it works!
""")

# --- Functions ---

@st.cache_resource
def load_retriever():
    """
    Loads the multi-hop retriever. The Streamlit cache ensures this only runs once.
    """
    game_id = "chs-850-0001"
    graph_filename = f"{game_id}.graph"
    
    if not os.path.exists(graph_filename):
        st.error(f"Graph file '{graph_filename}' not found. Please run the full data pipeline (generate corpus, extract entities, build graph) first.")
        return None
        
    try:
        graph_retriever = GraphRetriever(graph_path=graph_filename)
        multi_hop_retriever = MultiHopRetriever(graph_retriever)
        return multi_hop_retriever
    except Exception as e:
        st.error(f"An error occurred while loading the system: {e}")
        return None

# --- Main Application Logic ---

# Load the retriever system
retriever = load_retriever()

if retriever:
    # Initialize session state for storing messages
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if "trace" in message and message["trace"]:
                with st.expander("Show Reasoning Trace and Knowledge Graph"):
                    st.text_area("Trace", message["trace"], height=200)
                    if os.path.exists("chs-850-0001_knowledge_graph.png"):
                        image = Image.open("chs-850-0001_knowledge_graph.png")
                        st.image(image, caption="Knowledge Graph Visualization")

    # User input
    if prompt := st.chat_input("Ask a question about the chess game..."):
        # Add user message to history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get assistant's response
        with st.chat_message("assistant"):
            with st.spinner("Analyzing the game..."):
                final_answer, reasoning_trace = retriever.retrieve(prompt)
                
                st.markdown(final_answer)

                with st.expander("Show Reasoning Trace and Knowledge Graph"):
                    # Display the reasoning trace correctly as a single block of text
                    st.text_area("Trace", reasoning_trace, height=200)
                    # Display the knowledge graph image
                    if os.path.exists("chs-850-0001_knowledge_graph.png"):
                        image = Image.open("chs-850-0001_knowledge_graph.png")
                        st.image(image, caption="Knowledge Graph Visualization")

                # Add assistant response to history
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": final_answer, 
                    "trace": reasoning_trace
                })
else:
    st.warning("Retriever could not be loaded. Please ensure the data pipeline has been run successfully.")


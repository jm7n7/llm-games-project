#--- imports----------
import streamlit as st

#--- PAGE CONFIG --
st.set_page_config(
    page_title="DS Capstone Project",
    layout="wide"
)

#--- APP TITLE AND HEADER------
st.title("DS Capstone Project")
st.header("This is a header")
#--- BASIC TEXT AND WIDGETS----------------------------------------------------
st.write("Hello, Streamlit! This is the basic framework for your new project.")
if st.button("Click Me"):
    st.write("You clicked the button!")

#--- SIDEBARE-------------
st.sidebar.header("About")
st.sidebar.write("This is a sidebar. You can put filters, navigation, or extra information here.")

# To run this app:
# 1. Run the command: streamlit run app.py


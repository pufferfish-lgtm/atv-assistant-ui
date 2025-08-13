import streamlit as st
import openai
import os

# --- CONFIG ---
st.set_page_config(page_title="VTA Assistant", layout="wide")
st.title("ATV Assistant Chat")

# Store your API key as a Streamlit secret (see Step 4)
openai.api_key = st.secrets["OPENAI_API_KEY"]

# --- SIDEBAR ---
with st.sidebar:
    st.header("Upload files for context")
    uploaded_files = st.file_uploader(
        "Attach PDF, DOCX, or TXT", 
        type=["pdf", "docx", "txt"], 
        accept_multiple_files=True
    )

# --- CHAT ---
if "messages" not in st.session_state:
    st.session_state["messages"] = []

for msg in st.session_state["messages"]:
    st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input("Ask me anything…"):
    st.session_state["messages"].append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    # Call your Assistant here — example uses Responses API
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",  # swap for your Assistant model
        messages=st.session_state["messages"]
    )

    answer = response.choices[0].message["content"]
    st.session_state["messages"].append({"role": "assistant", "content": answer})
    st.chat_message("assistant").write(answer)

import streamlit as st
from openai import OpenAI
import tempfile
import os
import time

# --- CONFIG ---
st.set_page_config(page_title="VTA Assistant", layout="wide")
st.title("VTA Assistant Chat")

# Get API key from Streamlit Secrets
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Replace with your actual Assistant ID from platform.openai.com
ASSISTANT_ID = "asst_JOYxBJ815e7lDGUD7Q6xcTQA"

# --- SESSION STATE ---
if "thread_id" not in st.session_state:
    thread = client.beta.threads.create()
    st.session_state.thread_id = thread.id

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- SIDEBAR: File Uploads ---
with st.sidebar:
    st.header("Upload files for context")
    uploaded_files = st.file_uploader(
        "Attach PDF, DOCX, or TXT",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True
    )

    if uploaded_files:
        for file in uploaded_files:
            with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                tmp_file.write(file.read())
                tmp_file_path = tmp_file.name

            # Upload file to OpenAI for Assistants
            file_obj = client.files.create(
                file=open(tmp_file_path, "rb"),
                purpose="assistants"
            )

            # Attach the file to the current thread
            client.beta.threads.files.create(
                thread_id=st.session_state.thread_id,
                file_id=file_obj.id
            )

            os.remove(tmp_file_path)
        st.success(f"{len(uploaded_files)} file(s) uploaded to Assistant.")

# --- DISPLAY CHAT HISTORY ---
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# --- CHAT INPUT ---
if prompt := st.chat_input("Ask me about CAAP, Sustainability Plan, or other docs…"):
    # Save user message locally and


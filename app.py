import streamlit as st
import time
import openai
import json
import os

st.set_page_config(page_title="ATV Assistant", page_icon="🤖", layout="centered")

client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
ASSISTANT_ID = st.secrets["ASSISTANT_ID"]
CHAT_HISTORY_PATH = st.secrets.get("CHAT_HISTORY_PATH", "chat_history.json")

def load_chat_history():
    if os.path.exists(CHAT_HISTORY_PATH):
        with open(CHAT_HISTORY_PATH, "r") as f:
            return json.load(f)
    return []

def save_chat_history(messages):
    with open(CHAT_HISTORY_PATH, "w") as f:
        json.dump(messages, f)

# --- SIDEBAR ---
st.sidebar.title("Settings")
# Expanded model list from OpenAI docs (as of 2025)
model = st.sidebar.selectbox(
    "Model",
    options=[
        "gpt-4.1-mini",
        "gpt-4.1",

    ],
    index=0
)
uploaded_file = st.sidebar.file_uploader("Upload a file (optional)", type=["pdf", "txt", "docx"])
search_term = st.sidebar.text_input("Search previous chats")

# --- SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = load_chat_history()
if "thread_id" not in st.session_state:
    thread = client.beta.threads.create()
    st.session_state.thread_id = thread.id

# --- MAIN CHAT INTERFACE ---
st.title("ATV Assistant 🤖")
st.markdown("Ask me about CAAP, Sustainability Plan, or other docs…")

# Display chat history (searchable)
if search_term:
    filtered_chats = [msg for msg in st.session_state.messages if search_term.lower() in msg["content"].lower()]
    st.markdown("### Search Results")
    for msg in filtered_chats:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
else:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# --- CHAT INPUT ---
prompt = st.chat_input("Type your question and press Enter...")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    # Add the message to the Assistant thread
    client.beta.threads.messages.create(
        thread_id=st.session_state.thread_id,
        role="user",
        content=prompt
    )

    # Run the Assistant
    run = client.beta.threads.runs.create(
        thread_id=st.session_state.thread_id,
        assistant_id=ASSISTANT_ID,
        model=model
    )

    # Poll until the run completes
    with st.spinner("Assistant is thinking..."):
        while True:
            run_status = client.beta.threads.runs.retrieve(
                thread_id=st.session_state.thread_id,
                run_id=run.id
            )
            if run_status.status == "completed":
                break
            elif run_status.status in ["failed", "expired", "cancelled"]:
                st.error(f"Run failed: {run_status.status}")
                st.stop()
            time.sleep(1)

    # Retrieve the latest assistant message
    messages = client.beta.threads.messages.list(thread_id=st.session_state.thread_id)
    latest = messages.data[0]  # most recent message

    # Extract text and citations, replacing weird citation markers with readable info
    answer_text = ""
    citations = []
    for content_block in latest.content:
        if content_block.type == "text":
            answer_text += content_block.text.value
            if content_block.text.annotations:
                for ann in content_block.text.annotations:
                    if getattr(ann, "file_citation", None):
                        cite = ann.file_citation
                        try:
                            fmeta = client.files.retrieve(cite.file_id)
                            fname = getattr(fmeta, "filename", cite.file_id)
                        except Exception:
                            fname = cite.file_id
                        # Remove file extension for display (e.g., VTA_CAAP_Vol_1.pdf -> VTA_CAAP)
                        display_name = os.path.splitext(fname)[0]
                        # Use (start_index-end_index, display_name) format
                        citation_str = f"({ann.start_index}-{ann.end_index}, {display_name})"
                        citations.append(citation_str)
                        # Replace marker in answer_text
                        marker = f"【{ann.start_index}:{ann.end_index}†{fname}】"
                        answer_text = answer_text.replace(marker, citation_str)

    st.session_state.messages.append({"role": "assistant", "content": answer_text})
    st.chat_message("assistant").write(answer_text)

    # Show citations only if present and not blank
    if citations:
        st.markdown("**Citations:**")
        for citation_str in citations:
            st.markdown(f"- {citation_str}")

    # Save chat history
    save_chat_history(st.session_state.messages)
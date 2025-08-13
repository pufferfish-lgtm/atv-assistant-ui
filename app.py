import streamlit as st
import time
import openai

st.set_page_config(page_title="ATV Assistant", page_icon="🤖", layout="centered")

client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
ASSISTANT_ID = st.secrets["ASSISTANT_ID"]

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

# --- SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    thread = client.beta.threads.create()
    st.session_state.thread_id = thread.id

# --- MAIN CHAT INTERFACE ---
st.title("ATV Assistant 🤖")
st.markdown("Ask me about CAAP, Sustainability Plan, or other docs…")

# Display chat history
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
    citation_map = {}
    for content_block in latest.content:
        if content_block.type == "text":
            answer_text += content_block.text.value
            # Replace citation markers with readable format
            if content_block.text.annotations:
                for ann in content_block.text.annotations:
                    if getattr(ann, "file_citation", None):
                        cite = ann.file_citation
                        try:
                            fmeta = client.files.retrieve(cite.file_id)
                            fname = getattr(fmeta, "filename", cite.file_id)
                        except Exception:
                            fname = cite.file_id
                        page = getattr(cite, "page", None)
                        # Build readable citation string
                        citation_str = f"{fname}"
                        if page is not None:
                            citation_str += f", page {page}"
                        citation_map[ann.start_index] = citation_str
                        citations.append(citation_str)
                # Replace markers like 【12:0†source】 with readable citation
                for idx, citation_str in citation_map.items():
                    # This is a simple replacement, you may need to adjust for your annotation format
                    marker = f"【{idx}:0†source】"
                    answer_text = answer_text.replace(marker, f"[{citation_str}]")

    st.session_state.messages.append({"role": "assistant", "content": answer_text})
    st.chat_message("assistant").write(answer_text)

    # Show citations only if present and not blank
    if citations:
        st.markdown("**Citations:**")
        for citation_str in citations:
            st.markdown(f"- {citation_str}")
# --- CHAT INPUT ---
if prompt := st.chat_input("Ask me about CAAP, Sustainability Plan, or other docs…"):
    # Save user message locally and in the UI
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
        assistant_id=ASSISTANT_ID
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

    # Extract text and citations
    answer_text = ""
    citations = []
    for content_block in latest.content:
        if content_block.type == "text":
            answer_text += content_block.text.value
            if content_block.text.annotations:
                for ann in content_block.text.annotations:
                    # Collect file citation annotations if present
                    if getattr(ann, "file_citation", None):
                        citations.append(ann.file_citation)

    # Display assistant answer
    st.session_state.messages.append({"role": "assistant", "content": answer_text})
    st.chat_message("assistant").write(answer_text)

    # Show citations (minimal, readable)
    if citations:
        st.markdown("**Citations:**")
        for cite in citations:
            # Try to resolve file name for readability
            try:
                fmeta = client.files.retrieve(cite.file_id)
                fname = getattr(fmeta, "filename", cite.file_id)
            except Exception:
                fname = cite.file_id
            st.markdown(f"- {fname} (chars {cite.start_index}–{cite.end_index})")

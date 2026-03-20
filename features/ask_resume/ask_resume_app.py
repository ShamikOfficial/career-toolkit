from __future__ import annotations

import streamlit as st

from agent.llm.answering import answer_question
from ai.ollama_client import OllamaConfig, OllamaError, list_models


def run() -> None:
    st.title("Ask Resume")
    st.caption("Ask any question using only your resume data.")

    with st.sidebar:
        st.subheader("LLM settings")
        default_model = "qwen2.5:7b-instruct"
        try:
            installed_models = list_models()
        except OllamaError as e:
            installed_models = []
            st.warning(str(e))

        model_options = installed_models or [default_model]
        default_index = model_options.index(default_model) if default_model in model_options else 0
        model = st.selectbox("Ollama model", options=model_options, index=default_index)

    if "ask_resume_answer" not in st.session_state:
        st.session_state.ask_resume_answer = ""

    question = st.text_area(
        "Your question",
        height=120,
        placeholder="Example: What are my top backend skills for a Python role?",
    )
    ask_clicked = st.button("Ask", type="primary")

    if ask_clicked:
        if not question.strip():
            st.error("Please enter a question.")
        else:
            with st.spinner("Getting answer from resume..."):
                try:
                    config = OllamaConfig(model=model, temperature=0.1, max_tokens=220)
                    st.session_state.ask_resume_answer = answer_question(question.strip(), config=config)
                except OllamaError as e:
                    st.error(str(e))
                except Exception as e:  # noqa: BLE001
                    st.error(f"Failed to answer question: {e}")

    st.text_area("Answer", height=220, key="ask_resume_answer")


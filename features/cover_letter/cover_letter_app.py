from __future__ import annotations

import streamlit as st

from ai.cover_letter import OllamaConfig, OllamaError, generate_cover_letter
from ai.ollama_client import list_models


def run() -> None:
    st.title("Cover Letter Generator")

    with st.sidebar:
        st.subheader("Generation settings")
        try:
            installed_models = list_models()
        except OllamaError as e:
            installed_models = []
            st.warning(str(e))

        default_model = "qwen2.5:7b-instruct"
        model_options = installed_models or [default_model]
        default_index = model_options.index(default_model) if default_model in model_options else 0

        model = st.selectbox("Ollama model", options=model_options, index=default_index)
        tone = st.selectbox(
            "Tone",
            options=["neutral", "formal", "enthusiastic"],
            index=0,
        )

    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.subheader("Inputs")
        role_title = st.text_input("Target role title (optional)")
        company_name = st.text_input("Target company (optional)")
        job_description = st.text_area(
            "Job description",
            height=260,
            placeholder="Paste the job description here...",
        )

        generate_clicked = st.button("Generate cover letter", type="primary")

    with col_right:
        st.subheader("Output")
        st.write(
            "The generated cover letter will appear here. "
            "You can edit it before copying or downloading."
        )

    if "cover_letter_text" not in st.session_state:
        st.session_state.cover_letter_text = ""
    if "cover_letter_editor" not in st.session_state:
        st.session_state.cover_letter_editor = ""

    if generate_clicked:
        if not job_description.strip():
            st.error("Please paste a job description before generating.")
        else:
            with st.spinner("Calling local Ollama model to generate cover letter..."):
                try:
                    config = OllamaConfig(model=model)
                    text = generate_cover_letter(
                        job_description,
                        role_title=role_title or None,
                        company_name=company_name or None,
                        tone=tone,
                        config=config,
                    )
                    st.session_state.cover_letter_text = text
                    st.session_state.cover_letter_editor = text
                except OllamaError as e:
                    st.error(str(e))
                except Exception as e:  # noqa: BLE001
                    st.error(f"Failed to generate cover letter: {e}")

    editable_text = st.text_area(
        "Cover letter",
        height=260,
        key="cover_letter_editor",
    )

    if editable_text:
        st.download_button(
            label="Download as .txt",
            data=editable_text,
            file_name="cover_letter.txt",
            mime="text/plain",
        )


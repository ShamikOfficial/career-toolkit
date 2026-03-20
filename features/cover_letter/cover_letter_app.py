from __future__ import annotations

import os
import subprocess
import tempfile

import streamlit as st

from ai.cover_letter import OllamaConfig, OllamaError, generate_cover_letter
from ai.ollama_client import list_models


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
COVER_LETTER_TEMPLATE = os.path.join(BASE_DIR, "cover_letter_template.tex")


def _latex_escape(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    for orig, repl in replacements.items():
        text = text.replace(orig, repl)
    return text


def _cover_letter_body_tex(text: str) -> str:
    paras = [p.strip() for p in text.splitlines()]
    out = []
    for p in paras:
        if not p:
            out.append("")
        else:
            out.append(_latex_escape(p))
    return "\n\n".join(out)


def _cover_letter_pdf_bytes(text: str) -> bytes:
    if not os.path.exists(COVER_LETTER_TEMPLATE):
        raise RuntimeError(f"Cover letter template not found: {COVER_LETTER_TEMPLATE}")

    with open(COVER_LETTER_TEMPLATE, "r", encoding="utf-8") as f:
        template = f.read()

    tex = template.replace("%%BODY%%", _cover_letter_body_tex(text))

    with tempfile.TemporaryDirectory(prefix="cover_letter_tex_") as td:
        tex_path = os.path.join(td, "cover_letter.tex")
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(tex)

        try:
            subprocess.run(
                [
                    "xelatex",
                    "-interaction=nonstopmode",
                    "-halt-on-error",
                    "-jobname=cover_letter",
                    "cover_letter.tex",
                ],
                cwd=td,
                check=True,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as e:
            raise RuntimeError(
                "LaTeX engine 'xelatex' was not found. Install MiKTeX/TeX Live and ensure xelatex is on PATH."
            ) from e
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"LaTeX compilation failed:\n{e.stderr}") from e

        pdf_path = os.path.join(td, "cover_letter.pdf")
        if not os.path.exists(pdf_path):
            raise RuntimeError("PDF was not produced by LaTeX.")
        with open(pdf_path, "rb") as f:
            return f.read()


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
        try:
            pdf_bytes = _cover_letter_pdf_bytes(editable_text)
            st.download_button(
                label="Download as PDF",
                data=pdf_bytes,
                file_name="cover_letter.pdf",
                mime="application/pdf",
            )
        except Exception as e:  # noqa: BLE001
            st.error(f"Could not build PDF: {e}")


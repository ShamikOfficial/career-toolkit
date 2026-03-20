from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import streamlit as st

from ai.ollama_client import OllamaError, list_models


def run() -> None:
    st.title("Job Apply Agent (Browser)")
    st.caption("Launches an in-browser floating assistant panel. Manual login/CAPTCHA required.")

    with st.sidebar:
        st.subheader("Mode")
        mode = st.selectbox(
            "Mode",
            options=["semiAuto (default)", "fullAuto", "quickAnswer"],
            index=0,
        )

        st.subheader("LLM")
        default_model = "qwen2.5:7b-instruct"
        try:
            models = list_models()
        except OllamaError as e:
            models = [default_model]
            st.warning(str(e))
        if default_model not in models:
            models = [default_model] + models
        model = st.selectbox("Ollama model", options=models, index=0)

    st.subheader("Application link")
    url = st.text_input("Job application URL", placeholder="https://...")
    jd = st.text_area("Job description (optional)", height=180)

    st.markdown(
        """
**How it works**
- Click **Launch in-browser assistant**
- A Chromium window opens with a floating panel:
  - `Scan`, `Fill`, `Next`, `Submit`, `Ask from resume`, `Quit`
- You stay on the job page; no need to return here between steps.
"""
    )

    if "job_apply_launcher_pid" not in st.session_state:
        st.session_state.job_apply_launcher_pid = None

    launch_clicked = st.button("Launch in-browser assistant", type="primary", disabled=not url.strip())

    if launch_clicked:
        try:
            payload = {
                "url": url.strip(),
                "mode": "semiAuto" if mode.startswith("semiAuto") else ("fullAuto" if mode.startswith("fullAuto") else "quickAnswer"),
                "model": model,
                "job_description": jd or "",
            }
            cfg_path = Path(tempfile.gettempdir()) / "job_apply_agent_config.json"
            cfg_path.write_text(json.dumps(payload), encoding="utf-8")

            proc = subprocess.Popen(
                [sys.executable, "-m", "agent.browser.interactive_assistant", "--config", str(cfg_path)],
                cwd=str(Path(__file__).resolve().parents[2]),
            )
            st.session_state.job_apply_launcher_pid = proc.pid
            st.success(f"Assistant launched (PID {proc.pid}). Use the floating panel inside Chromium.")
        except Exception as e:
            st.error(str(e))

    if st.session_state.job_apply_launcher_pid:
        st.info(f"Last launched assistant PID: {st.session_state.job_apply_launcher_pid}")


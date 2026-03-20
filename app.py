import streamlit as st

from features.resume import run as run_resume_builder
from features.ats import run as run_ats
from features.cover_letter import run as run_cover_letter
from features.job_apply import run as run_job_apply


def main() -> None:
    st.set_page_config(page_title="Career Toolkit", page_icon="📄", layout="wide")

    st.sidebar.title("Career Toolkit")
    tool = st.sidebar.radio(
        "Choose feature",
        ["Resume Builder", "Applicant Tracking", "Cover Letter Generator", "Job Apply Agent"],
        index=0,
    )

    if tool == "Resume Builder":
        run_resume_builder()
    elif tool == "Applicant Tracking":
        run_ats()
    elif tool == "Cover Letter Generator":
        run_cover_letter()
    elif tool == "Job Apply Agent":
        run_job_apply()


if __name__ == "__main__":
    main()


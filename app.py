import streamlit as st

from features.resume import run as run_resume_builder
from features.ats import run as run_ats


def main() -> None:
    st.set_page_config(page_title="Career Toolkit", page_icon="📄", layout="wide")

    st.sidebar.title("Career Toolkit")
    tool = st.sidebar.radio(
        "Choose feature",
        ["Resume Builder", "Applicant Tracking"],
        index=0,
    )

    if tool == "Resume Builder":
        run_resume_builder()
    elif tool == "Applicant Tracking":
        run_ats()


if __name__ == "__main__":
    main()


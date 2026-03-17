import streamlit as st

from features.resume import run as run_resume_builder


def main() -> None:
    st.set_page_config(page_title="Career Toolkit", page_icon="📄", layout="wide")

    st.sidebar.title("Career Toolkit")
    tool = st.sidebar.radio(
        "Choose feature",
        ["Resume Builder"],
        index=0,
    )

    if tool == "Resume Builder":
        run_resume_builder()


if __name__ == "__main__":
    main()


import os
from typing import Any, Dict, List, Optional

import streamlit as st

from db import (
    DbConfigError,
    create_application,
    ensure_job,
    list_applications,
    update_application_status,
)


STATUSES = ["draft", "applied", "interview", "rejected", "offer"]


def _db_help() -> None:
    st.info(
        "Set MySQL connection env vars and refresh:\n\n"
        "- `MYSQL_HOST`\n"
        "- `MYSQL_PORT` (optional, default 3306)\n"
        "- `MYSQL_USER`\n"
        "- `MYSQL_PASSWORD`\n"
        "- `MYSQL_DB`\n\n"
        "Then run `db_schema.sql` in that database."
    )


def _list_generated_pdfs() -> List[str]:
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    pdf_dir = os.path.join(base_dir, "processed", "pdf")
    if not os.path.isdir(pdf_dir):
        return []
    out = []
    for name in os.listdir(pdf_dir):
        if name.lower().endswith(".pdf"):
            out.append(os.path.join(pdf_dir, name))
    out.sort(reverse=True)
    return out


def _new_application_form() -> None:
    st.subheader("New job / application")

    with st.form("new_application_form", clear_on_submit=False):
        source_url = st.text_input("Job posting URL *")
        c1, c2 = st.columns(2)
        with c1:
            company = st.text_input("Company (optional)")
            title = st.text_input("Job title (optional)")
            location = st.text_input("Location (optional)")
        with c2:
            platform = st.text_input("Platform (optional)", help="e.g., LinkedIn, Indeed, Greenhouse")
            status = st.selectbox("Status", STATUSES, index=1)

        st.caption("Job description is optional for now (auto-fill agent will populate later).")
        job_description = st.text_area("Job description (optional)", height=150)

        pdfs = _list_generated_pdfs()
        resume_pdf_path = st.selectbox(
            "Tailored resume PDF path (optional)",
            options=["(none)"] + pdfs,
            index=0,
            help="Picks from `processed/pdf`. You can also paste a custom path below.",
        )
        resume_pdf_path_custom = st.text_input("Or paste resume PDF path (overrides selection)", value="")

        notes = st.text_area("Notes (optional)", height=100)

        submitted = st.form_submit_button("Create application")

    if not submitted:
        return

    if not source_url.strip():
        st.error("Job posting URL is required.")
        return

    final_resume_path = None
    if resume_pdf_path_custom.strip():
        final_resume_path = resume_pdf_path_custom.strip()
    elif resume_pdf_path != "(none)":
        final_resume_path = resume_pdf_path

    try:
        job_id = ensure_job(
            source_url=source_url.strip(),
            company=company.strip() or None,
            title=title.strip() or None,
            location=location.strip() or None,
            platform=platform.strip() or None,
            job_description=job_description.strip() or None,
            parsed_keywords_json=None,
        )
        app_id = create_application(
            job_id=job_id,
            status=status,
            resume_pdf_path=final_resume_path,
            cover_letter_path=None,
            notes=notes.strip() or None,
        )
        st.success(f"Created application #{app_id} (job #{job_id}).")
    except DbConfigError as e:
        st.error(str(e))
        _db_help()
    except Exception as e:
        st.error(f"Failed to create application: {e}")


def _applications_table() -> None:
    st.subheader("Applications")

    c1, c2 = st.columns([2, 1])
    with c1:
        q = st.text_input("Search (company/title/url)")
    with c2:
        status_filter = st.multiselect("Status filter", STATUSES, default=[])

    try:
        rows = list_applications(status_in=status_filter or None, q=q.strip() or None, limit=300)
    except DbConfigError as e:
        st.error(str(e))
        _db_help()
        return
    except Exception as e:
        st.error(f"Failed to load applications: {e}")
        return

    if not rows:
        st.info("No applications yet.")
        return

    st.dataframe(
        [
            {
                "Application ID": r["application_id"],
                "Status": r["status"],
                "Company": r["company"],
                "Title": r["title"],
                "Location": r["location"],
                "Platform": r["platform"],
                "Applied At": r["applied_at"],
                "Resume Path": r["resume_pdf_path"],
                "URL": r["source_url"],
            }
            for r in rows
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("---")
    st.subheader("Quick update")

    ids = [int(r["application_id"]) for r in rows]
    app_id = st.selectbox("Application ID", options=ids)
    new_status = st.selectbox("New status", options=STATUSES, index=STATUSES.index("applied"))
    new_notes = st.text_area("Replace notes (optional)", height=80)

    if st.button("Update status"):
        try:
            update_application_status(
                application_id=int(app_id),
                status=new_status,
                notes=new_notes.strip() or None,
            )
            st.success("Updated.")
            st.rerun()
        except DbConfigError as e:
            st.error(str(e))
            _db_help()
        except Exception as e:
            st.error(f"Failed to update: {e}")


def run() -> None:
    st.title("Applicant Tracking")

    tabs = st.tabs(["New application", "Applications", "Analytics"])
    with tabs[0]:
        _new_application_form()
    with tabs[1]:
        _applications_table()
    with tabs[2]:
        _analytics()


def _analytics() -> None:
    st.subheader("Analytics")

    try:
        rows = list_applications(status_in=None, q=None, limit=5000)
    except DbConfigError as e:
        st.error(str(e))
        _db_help()
        return
    except Exception as e:
        st.error(f"Failed to load data: {e}")
        return

    if not rows:
        st.info("No applications yet.")
        return

    # Status counts
    status_counts: Dict[str, int] = {}
    for r in rows:
        s = r.get("status") or "unknown"
        status_counts[s] = status_counts.get(s, 0) + 1

    st.markdown("**By status**")
    st.bar_chart(status_counts)

    # Applications over time (by date)
    by_date: Dict[str, int] = {}
    for r in rows:
        dt = r.get("applied_at")
        if not dt:
            continue
        day = str(dt.date())
        by_date[day] = by_date.get(day, 0) + 1

    if by_date:
        st.markdown("**Applications over time**")
        # Streamlit can plot dicts, but sorting improves readability.
        series = dict(sorted(by_date.items(), key=lambda kv: kv[0]))
        st.line_chart(series)


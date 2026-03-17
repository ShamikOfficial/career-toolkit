import os
from typing import Any, Dict, List, Optional, Tuple


class DbConfigError(RuntimeError):
    pass


def _env(name: str, default: Optional[str] = None) -> str:
    val = os.getenv(name, default)
    if val is None or val == "":
        raise DbConfigError(f"Missing required environment variable: {name}")
    return val


def get_db_config() -> Dict[str, Any]:
    """
    Read MySQL connection settings from environment variables.

    Required:
      - MYSQL_HOST
      - MYSQL_USER
      - MYSQL_PASSWORD (can be empty string if allowed)
      - MYSQL_DB

    Optional:
      - MYSQL_PORT (default 3306)
    """
    return {
        "host": _env("MYSQL_HOST"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": _env("MYSQL_USER"),
        # Password can be empty; require variable to exist for clarity.
        "password": os.getenv("MYSQL_PASSWORD", ""),
        "database": _env("MYSQL_DB"),
    }


def get_connection():
    """
    Create a new MySQL connection.

    Using local import keeps this module importable even if MySQL deps
    aren't installed yet (e.g., while working on non-DB features).
    """
    import mysql.connector  # type: ignore

    return mysql.connector.connect(**get_db_config())


# -----------------------
# ATS helpers
# -----------------------


def ensure_job(
    *,
    source_url: str,
    company: Optional[str] = None,
    title: Optional[str] = None,
    location: Optional[str] = None,
    platform: Optional[str] = None,
    job_description: Optional[str] = None,
    parsed_keywords_json: Optional[str] = None,
) -> int:
    """
    Create a job row if this source_url is new; otherwise return existing id.

    `parsed_keywords_json` should be a JSON string (or None).
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM jobs WHERE source_url = %s LIMIT 1", (source_url,))
        row = cur.fetchone()
        if row:
            return int(row[0])

        cur.execute(
            """
            INSERT INTO jobs (source_url, company, title, location, platform, job_description, parsed_keywords)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (source_url, company, title, location, platform, job_description, parsed_keywords_json),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def create_application(
    *,
    job_id: int,
    status: str = "applied",
    resume_pdf_path: Optional[str] = None,
    cover_letter_path: Optional[str] = None,
    notes: Optional[str] = None,
) -> int:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO applications (job_id, status, resume_pdf_path, cover_letter_path, notes)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (job_id, status, resume_pdf_path, cover_letter_path, notes),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def update_application_status(*, application_id: int, status: str, notes: Optional[str] = None) -> None:
    conn = get_connection()
    try:
        cur = conn.cursor()
        if notes is None:
            cur.execute("UPDATE applications SET status=%s WHERE id=%s", (status, application_id))
        else:
            cur.execute("UPDATE applications SET status=%s, notes=%s WHERE id=%s", (status, notes, application_id))
        conn.commit()
    finally:
        conn.close()


def list_applications(
    *,
    status_in: Optional[List[str]] = None,
    q: Optional[str] = None,
    limit: int = 200,
) -> List[Dict[str, Any]]:
    """
    Return recent applications joined with job fields.
    """
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        where = []
        params: List[Any] = []

        if status_in:
            where.append("a.status IN (" + ",".join(["%s"] * len(status_in)) + ")")
            params.extend(status_in)

        if q:
            where.append("(j.company LIKE %s OR j.title LIKE %s OR j.source_url LIKE %s)")
            like = f"%{q}%"
            params.extend([like, like, like])

        where_sql = (" WHERE " + " AND ".join(where)) if where else ""
        sql = f"""
        SELECT
          a.id AS application_id,
          a.status,
          a.resume_pdf_path,
          a.cover_letter_path,
          a.notes,
          a.applied_at,
          a.updated_at,
          j.id AS job_id,
          j.company,
          j.title,
          j.location,
          j.platform,
          j.source_url
        FROM applications a
        JOIN jobs j ON j.id = a.job_id
        {where_sql}
        ORDER BY a.applied_at DESC
        LIMIT %s
        """
        params.append(limit)
        cur.execute(sql, tuple(params))
        return list(cur.fetchall())
    finally:
        conn.close()


# -----------------------
# CRM helpers (v1)
# -----------------------


def upsert_contact(
    *,
    email: str,
    name: Optional[str] = None,
    linkedin_url: Optional[str] = None,
    company: Optional[str] = None,
    notes: Optional[str] = None,
) -> int:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM contacts WHERE email=%s LIMIT 1", (email,))
        row = cur.fetchone()
        if row:
            contact_id = int(row[0])
            cur.execute(
                """
                UPDATE contacts
                SET name=COALESCE(%s, name),
                    linkedin_url=COALESCE(%s, linkedin_url),
                    company=COALESCE(%s, company),
                    notes=COALESCE(%s, notes)
                WHERE id=%s
                """,
                (name, linkedin_url, company, notes, contact_id),
            )
            conn.commit()
            return contact_id

        cur.execute(
            """
            INSERT INTO contacts (name, email, linkedin_url, company, notes)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (name, email, linkedin_url, company, notes),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def link_contact_to_application(*, application_id: int, contact_id: int, relationship: Optional[str] = None) -> None:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO application_contacts (application_id, contact_id, relationship)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE relationship=VALUES(relationship)
            """,
            (application_id, contact_id, relationship),
        )
        conn.commit()
    finally:
        conn.close()


def list_contacts(*, q: Optional[str] = None, limit: int = 200) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        params: List[Any] = []
        where_sql = ""
        if q:
            where_sql = "WHERE (email LIKE %s OR name LIKE %s OR company LIKE %s)"
            like = f"%{q}%"
            params.extend([like, like, like])
        cur.execute(
            f"""
            SELECT id, name, email, linkedin_url, company, notes, created_at
            FROM contacts
            {where_sql}
            ORDER BY created_at DESC
            LIMIT %s
            """,
            tuple([*params, limit]),
        )
        return list(cur.fetchall())
    finally:
        conn.close()


def create_outreach_message(
    *,
    application_id: int,
    contact_id: int,
    subject: str,
    body: str,
    status: str = "draft",
) -> int:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO outreach_messages (application_id, contact_id, subject, body, status)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (application_id, contact_id, subject, body, status),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def mark_outreach_sent(
    *,
    outreach_id: int,
    gmail_message_id: Optional[str],
    gmail_thread_id: Optional[str],
) -> None:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE outreach_messages
            SET status='sent',
                sent_at=NOW(),
                gmail_message_id=%s,
                gmail_thread_id=%s,
                error=NULL
            WHERE id=%s
            """,
            (gmail_message_id, gmail_thread_id, outreach_id),
        )
        conn.commit()
    finally:
        conn.close()


def mark_outreach_failed(*, outreach_id: int, error: str) -> None:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE outreach_messages
            SET status='failed',
                error=%s
            WHERE id=%s
            """,
            (error, outreach_id),
        )
        conn.commit()
    finally:
        conn.close()


def list_outreach_messages(*, limit: int = 200) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """
            SELECT
              om.id AS outreach_id,
              om.status,
              om.subject,
              om.created_at,
              om.sent_at,
              om.gmail_message_id,
              om.gmail_thread_id,
              om.error,
              c.id AS contact_id,
              c.name AS contact_name,
              c.email AS contact_email,
              a.id AS application_id
            FROM outreach_messages om
            JOIN contacts c ON c.id = om.contact_id
            JOIN applications a ON a.id = om.application_id
            ORDER BY om.created_at DESC
            LIMIT %s
            """,
            (limit,),
        )
        return list(cur.fetchall())
    finally:
        conn.close()


from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from .ollama_client import OllamaConfig, OllamaError, generate as ollama_generate


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TEMPLATE_JSON_PATH = os.path.join(BASE_DIR, "resume_template.json")


def _load_profile() -> Dict[str, Any]:
    with open(TEMPLATE_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _summarize_experience(experiences: List[Dict[str, Any]], max_roles: int = 3) -> str:
    lines: List[str] = []
    for exp in experiences[:max_roles]:
        company = exp.get("company", "")
        role = exp.get("role", "")
        period = exp.get("period", "")
        location = exp.get("location", "")
        bullets = exp.get("highlights", []) or []
        first_bullet = bullets[0] if bullets else ""
        parts = [p for p in [role, company, location, period] if p]
        header = ", ".join(parts)
        if header:
            lines.append(f"- {header}")
        if first_bullet:
            lines.append(f"  * {first_bullet}")
    return "\n".join(lines)


def _summarize_skills(skills: List[str], max_skills: int = 12) -> str:
    return ", ".join(skills[:max_skills])


def build_prompt(
    job_description: str,
    *,
    role_title: Optional[str] = None,
    company_name: Optional[str] = None,
    tone: str = "neutral",
    max_words: int = 350,
) -> str:
    profile = _load_profile()
    contact = profile.get("contact", {})
    experiences = profile.get("experience", [])
    skills = profile.get("skills", [])

    name = contact.get("name", "the candidate")
    exp_summary = _summarize_experience(experiences)
    skills_summary = _summarize_skills(skills)

    role_title = role_title or "the role"
    company_name = company_name or "the hiring team"
    tone_phrase = {
        "formal": "formal and respectful",
        "enthusiastic": "enthusiastic but still professional",
        "neutral": "neutral and professional",
    }.get(tone, "neutral and professional")

    prompt = f"""
You are writing a concise, professional cover letter for a candidate.

Use ONLY the candidate information provided below. Do not invent new employers, job titles, degrees, locations, or dates.
You may lightly rephrase and combine the existing experience and skills to match the job description.

Candidate name: {name}

Candidate recent experience:
{exp_summary}

Candidate skills (subset):
{skills_summary}

Job description:
\"\"\" 
{job_description.strip()}
\"\"\"

Write a cover letter of at most {max_words} words, in a {tone_phrase} tone, addressed to {company_name}, for the position {role_title}.

Structure:
- Greeting
- First paragraph: why this role and company, referencing the job description
- One or two paragraphs: concrete evidence from the candidate's experience and skills
- Closing paragraph with call to action and thanks

Requirements:
- Do NOT invent new companies, roles, degrees, or specific metrics that are not implied by the candidate data.
- Do NOT use markdown or bullet lists; output plain text paragraphs only.
- Keep it concise and easy to read.
"""
    return prompt.strip()


def generate_cover_letter(
    job_description: str,
    *,
    role_title: Optional[str] = None,
    company_name: Optional[str] = None,
    tone: str = "neutral",
    config: Optional[OllamaConfig] = None,
) -> str:
    if not job_description.strip():
        raise ValueError("Job description cannot be empty.")

    prompt = build_prompt(
        job_description,
        role_title=role_title,
        company_name=company_name,
        tone=tone,
    )
    text = ollama_generate(prompt, config=config)

    # Post-process: strip fences if the model returned markdown
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.lstrip("`")
        # Drop possible language tag on first line
        lines = cleaned.splitlines()
        if lines:
            # remove first line (language tag)
            lines = lines[1:]
        cleaned = "\n".join(lines)
        # strip trailing fences
        if "```" in cleaned:
            cleaned = cleaned.split("```", 1)[0]

    return cleaned.strip()


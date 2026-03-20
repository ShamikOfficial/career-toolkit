from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ai.ollama_client import OllamaConfig, OllamaError, generate as ollama_generate


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RESUME_JSON_PATH = os.path.join(BASE_DIR, "resume_template.json")


@dataclass
class ApplyPlan:
    field_values: Dict[str, str]
    uploads: Dict[str, Any]
    notes: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {"field_values": self.field_values, "uploads": self.uploads, "notes": self.notes}


def _load_resume() -> Dict[str, Any]:
    with open(RESUME_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _extract_json(text: str) -> Dict[str, Any]:
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`")
    start = t.find("{")
    end = t.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in model output.")
    blob = t[start : end + 1]
    return json.loads(blob)


def build_planner_prompt(
    *,
    form_schema: Dict[str, Any],
    resume: Dict[str, Any],
    job_url: str,
    job_description: Optional[str] = None,
) -> str:
    # Keep prompt compact: only include key resume facts
    contact = resume.get("contact", {})
    education = resume.get("education", [])[:2]
    experience = resume.get("experience", [])[:4]
    skills = resume.get("skills", [])[:25]

    fields = form_schema.get("fields", [])
    # Reduce field payload for speed
    slim_fields = []
    for f in fields:
        slim_fields.append(
            {
                "selector": f.get("selector"),
                "field_id": f.get("field_id"),
                "tag": f.get("tag"),
                "input_type": f.get("input_type"),
                "label": f.get("label"),
                "required": f.get("required"),
                "options": f.get("options") if f.get("options") else None,
                "placeholder": f.get("placeholder"),
            }
        )

    payload = {
        "job_url": job_url,
        "candidate": {
            "contact": contact,
            "education": education,
            "experience": experience,
            "skills": skills,
        },
        "job_description": (job_description or "").strip(),
        "form_fields": slim_fields,
    }

    return (
        "You are an assistant that prepares job application form answers.\n"
        "Return ONLY valid JSON. No markdown.\n\n"
        "Rules:\n"
        "- Use only the candidate data provided.\n"
        "- If a field is required but you cannot infer a safe value, set it to \"__NEEDS_USER__\".\n"
        "- For selects/radios: choose the best matching option text exactly.\n"
        "- Keep answers concise.\n\n"
        "Output JSON schema:\n"
        "{\n"
        "  \"field_values\": {\"<selector>\": \"<value>\"},\n"
        "  \"uploads\": {\"resume\": true|false, \"cover_letter\": true|false, \"other\": []},\n"
        "  \"notes\": [\"...\"]\n"
        "}\n\n"
        f"INPUT:\n{json.dumps(payload, ensure_ascii=False)}"
    )


def plan_application(
    *,
    form_schema: Dict[str, Any],
    job_url: str,
    job_description: Optional[str] = None,
    config: Optional[OllamaConfig] = None,
) -> ApplyPlan:
    resume = _load_resume()
    prompt = build_planner_prompt(
        form_schema=form_schema, resume=resume, job_url=job_url, job_description=job_description
    )
    text = ollama_generate(prompt, config=config)
    data = _extract_json(text)
    fv = data.get("field_values") or {}
    uploads = data.get("uploads") or {"resume": False, "cover_letter": False, "other": []}
    notes = data.get("notes") or []
    if not isinstance(fv, dict):
        raise ValueError("Planner output missing field_values dict.")
    return ApplyPlan(field_values={str(k): str(v) for k, v in fv.items()}, uploads=uploads, notes=[str(n) for n in notes])


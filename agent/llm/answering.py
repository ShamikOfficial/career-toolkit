from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from ai.ollama_client import OllamaConfig, generate as ollama_generate


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RESUME_JSON_PATH = os.path.join(BASE_DIR, "resume_template.json")


def _load_resume() -> Dict[str, Any]:
    with open(RESUME_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def answer_question(question: str, *, config: Optional[OllamaConfig] = None) -> str:
    resume = _load_resume()
    payload = {
        "candidate": {
            "contact": resume.get("contact", {}),
            "education": resume.get("education", []),
            "experience": resume.get("experience", []),
            "skills": resume.get("skills", []),
            "roles": list((resume.get("roles") or {}).keys()),
        },
        "question": question.strip(),
    }
    prompt = (
        "You answer questions for a job application using ONLY the provided candidate data.\n"
        "Be concise and factual. If unknown, say you don't know.\n\n"
        f"INPUT:\n{json.dumps(payload, ensure_ascii=False)}\n\n"
        "ANSWER:"
    )
    return ollama_generate(prompt, config=config).strip()


from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

from playwright.sync_api import Page


@dataclass
class FieldSchema:
    field_id: str
    selector: str
    tag: str
    input_type: Optional[str]
    label: str
    placeholder: str
    required: bool
    options: Optional[List[str]] = None


@dataclass
class ButtonSchema:
    selector: str
    text: str
    kind: str  # next|submit|other


@dataclass
class FormSchema:
    url: str
    title: str
    fields: List[FieldSchema]
    buttons: List[ButtonSchema]
    errors: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "fields": [asdict(f) for f in self.fields],
            "buttons": [asdict(b) for b in self.buttons],
            "errors": list(self.errors),
        }


_CSS_PATH_JS = r"""
(el) => {
  function cssEscape(s) {
    return s.replace(/([ #;?%&,.+*~\':"!^$[\]()=>|\/@])/g,'\\$1');
  }
  if (!el) return '';
  if (el.id) return `#${cssEscape(el.id)}`;
  const parts = [];
  while (el && el.nodeType === 1 && el.tagName.toLowerCase() !== 'html') {
    let part = el.tagName.toLowerCase();
    if (el.getAttribute('name')) {
      part += `[name=\"${cssEscape(el.getAttribute('name'))}\"]`;
      parts.unshift(part);
      break;
    }
    const className = (el.className && typeof el.className === 'string') ? el.className.trim().split(/\s+/)[0] : '';
    if (className) part += `.${cssEscape(className)}`;
    const parent = el.parentElement;
    if (parent) {
      const siblings = Array.from(parent.children).filter(e => e.tagName === el.tagName);
      if (siblings.length > 1) {
        const idx = siblings.indexOf(el) + 1;
        part += `:nth-of-type(${idx})`;
      }
    }
    parts.unshift(part);
    el = parent;
  }
  return parts.join(' > ');
}
"""


def _best_label(page: Page, selector: str) -> str:
    # Try aria-label first
    aria = page.eval_on_selector(selector, "el => el.getAttribute('aria-label') || ''") or ""
    if aria.strip():
        return aria.strip()

    # Try associated <label for=id>
    el_id = page.eval_on_selector(selector, "el => el.id || ''") or ""
    if el_id:
        txt = page.eval_on_selector(
            f'label[for=\"{el_id}\"]',
            "el => (el && el.innerText) ? el.innerText : ''",
        )
        if isinstance(txt, str) and txt.strip():
            return txt.strip()

    # Nearby label heuristic: previous sibling label
    txt2 = page.eval_on_selector(
        selector,
        """el => {
          const prev = el.closest('div,section,form')?.querySelector('label');
          return prev && prev.innerText ? prev.innerText : '';
        }""",
    )
    if isinstance(txt2, str) and txt2.strip():
        return txt2.strip()
    return ""


def snapshot_form(page: Page, *, max_fields: int = 80) -> FormSchema:
    page.wait_for_load_state("domcontentloaded")
    url = page.url
    title = page.title() or ""

    fields: List[FieldSchema] = []

    # Collect visible inputs/selects/textareas
    selectors = [
        "input:not([type=hidden]):not([disabled])",
        "textarea:not([disabled])",
        "select:not([disabled])",
    ]
    handles = []
    for sel in selectors:
        handles.extend(page.query_selector_all(sel))

    seen_selectors: set[str] = set()
    for i, h in enumerate(handles):
        if len(fields) >= max_fields:
            break
        try:
            if not h.is_visible():
                continue
            css = h.evaluate(_CSS_PATH_JS)
            if not isinstance(css, str) or not css:
                continue
            if css in seen_selectors:
                continue
            seen_selectors.add(css)

            tag = (h.evaluate("el => el.tagName.toLowerCase()") or "").strip()
            input_type = None
            if tag == "input":
                input_type = (h.get_attribute("type") or "text").lower()

            placeholder = (h.get_attribute("placeholder") or "").strip()
            required = bool(h.evaluate("el => !!el.required")) if tag in ("input", "textarea", "select") else False

            label = _best_label(page, css) or placeholder
            name_attr = (h.get_attribute("name") or "").strip()
            field_id = name_attr or (h.get_attribute("id") or "").strip() or f"field_{i}"

            options: Optional[List[str]] = None
            if tag == "select":
                opts = h.evaluate("el => Array.from(el.options || []).map(o => (o.text || '').trim()).filter(Boolean)")
                if isinstance(opts, list):
                    options = [str(o) for o in opts][:80]

            fields.append(
                FieldSchema(
                    field_id=field_id,
                    selector=css,
                    tag=tag,
                    input_type=input_type,
                    label=label.strip(),
                    placeholder=placeholder,
                    required=required,
                    options=options,
                )
            )
        except Exception:
            continue

    # Buttons
    buttons: List[ButtonSchema] = []
    btn_handles = page.query_selector_all("button:not([disabled]), input[type=submit]:not([disabled])")
    for h in btn_handles[:40]:
        try:
            if not h.is_visible():
                continue
            css = h.evaluate(_CSS_PATH_JS)
            text = (h.inner_text() if h.evaluate("el => el.tagName.toLowerCase()") == "button" else (h.get_attribute("value") or "")).strip()
            t = text.lower()
            kind = "other"
            if any(k in t for k in ["next", "continue", "save and continue", "proceed"]):
                kind = "next"
            if any(k in t for k in ["submit", "apply", "send application"]):
                kind = "submit"
            if css and text:
                buttons.append(ButtonSchema(selector=css, text=text, kind=kind))
        except Exception:
            continue

    # Basic error extraction
    errors: List[str] = []
    err_texts = page.query_selector_all("[aria-invalid=true], .error, .errors, .field-error")
    for h in err_texts[:20]:
        try:
            if not h.is_visible():
                continue
            t = (h.inner_text() or "").strip()
            if t and t not in errors:
                errors.append(t[:200])
        except Exception:
            continue

    return FormSchema(url=url, title=title, fields=fields, buttons=buttons, errors=errors)


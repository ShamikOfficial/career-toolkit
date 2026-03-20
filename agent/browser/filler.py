from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

from playwright.sync_api import Page


@dataclass
class FillResult:
    applied: List[str]
    skipped: List[str]
    errors: List[str]


def _tag_and_type(page: Page, selector: str) -> Tuple[str, str]:
    tag = page.eval_on_selector(selector, "el => el.tagName.toLowerCase()") or ""
    typ = ""
    if tag == "input":
        typ = (page.eval_on_selector(selector, "el => el.type") or "").lower()
    return tag, typ


def fill_page_fields(
    page: Page,
    *,
    field_values: Dict[str, str],
    file_map: Optional[Dict[str, str]] = None,
    progress_cb: Optional[Callable[[int, int, str], None]] = None,
) -> FillResult:
    """
    Deterministically fill fields using CSS selectors produced by the snapshot.

    field_values: {selector: value}
    file_map: {selector: file_path} for file inputs if needed
    """
    applied: List[str] = []
    skipped: List[str] = []
    errors: List[str] = []
    file_map = file_map or {}

    total = len(field_values)
    for idx, (selector, value) in enumerate(field_values.items(), start=1):
        if progress_cb is not None:
            try:
                progress_cb(idx, total, selector)
            except Exception:
                pass
        v = (value or "").strip()
        if not selector or v == "":
            skipped.append(selector)
            continue
        if v == "__NEEDS_USER__":
            skipped.append(selector)
            continue

        try:
            loc = page.locator(selector).first
            if loc.count() == 0:
                skipped.append(selector)
                continue
            if not loc.is_visible():
                skipped.append(selector)
                continue

            tag, typ = _tag_and_type(page, selector)

            if tag == "select":
                # Try select by label text first
                loc.select_option(label=v)
                applied.append(selector)
                continue

            if tag == "textarea":
                loc.fill(v)
                applied.append(selector)
                continue

            if tag == "input" and typ in ("checkbox", "radio"):
                # Interpret truthy strings
                truthy = v.lower() in ("yes", "true", "1", "y", "checked")
                if truthy:
                    loc.check()
                else:
                    loc.uncheck()
                applied.append(selector)
                continue

            if tag == "input" and typ == "file":
                fp = file_map.get(selector)
                if not fp:
                    skipped.append(selector)
                    continue
                loc.set_input_files(fp)
                applied.append(selector)
                continue

            # Default: text-like input
            loc.fill(v)
            applied.append(selector)
        except Exception as e:
            errors.append(f"{selector}: {e}")

    return FillResult(applied=applied, skipped=skipped, errors=errors)


from __future__ import annotations

import argparse
import json
import time
from typing import Any, Dict, Optional

from ai.ollama_client import OllamaConfig
from agent.browser.filler import fill_page_fields
from agent.browser.page_snapshot import snapshot_form
from agent.browser.runner import open_browser
from agent.llm.answering import answer_question
from agent.llm.apply_planner import ApplyPlan, plan_application


OVERLAY_JS = r"""
() => {
  const existing = document.getElementById("__jobAgentPanel");
  if (existing) return;

  const shell = document.createElement("div");
  shell.id = "__jobAgentShell";
  shell.style.position = "fixed";
  shell.style.top = "72px";
  shell.style.right = "12px";
  shell.style.zIndex = "2147483647";
  shell.style.pointerEvents = "auto";
  shell.style.fontFamily = "Arial, sans-serif";

  const panel = document.createElement("div");
  panel.id = "__jobAgentPanel";
  panel.style.width = "320px";
  panel.style.maxHeight = "85vh";
  panel.style.overflow = "auto";
  panel.style.background = "rgba(20,20,20,0.96)";
  panel.style.color = "#f5f5f5";
  panel.style.border = "1px solid #555";
  panel.style.borderRadius = "10px";
  panel.style.padding = "10px";
  panel.style.boxShadow = "0 8px 30px rgba(0,0,0,.45)";
  panel.style.pointerEvents = "auto";

  const tab = document.createElement("button");
  tab.id = "__jobAgentTab";
  tab.textContent = "Assistant";
  tab.style.display = "none";
  tab.style.position = "fixed";
  tab.style.top = "72px";
  tab.style.right = "0";
  tab.style.padding = "8px 10px";
  tab.style.border = "1px solid #777";
  tab.style.borderLeft = "none";
  tab.style.borderRadius = "0 8px 8px 0";
  tab.style.background = "#2b2b2b";
  tab.style.color = "#f2f2f2";
  tab.style.cursor = "pointer";
  tab.style.pointerEvents = "auto";
  tab.style.zIndex = "2147483647";

  panel.innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
      <div style="font-weight:700;">Job Apply Assistant</div>
      <button id="ja_minimize" style="padding:4px 8px;border-radius:6px;border:1px solid #777;background:#2b2b2b;color:#f2f2f2;cursor:pointer;">_</button>
    </div>
    <div style="font-size:12px;opacity:.85;margin-bottom:8px;">Use these controls directly in-browser.</div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-bottom:8px;">
      <button id="ja_scan">Scan</button>
      <button id="ja_fill">Fill</button>
      <button id="ja_next">Next</button>
      <button id="ja_submit">Submit</button>
      <button id="ja_reinject">Reinject</button>
      <button id="ja_quit">Quit</button>
    </div>
    <div style="font-size:12px;margin-top:8px;margin-bottom:4px;">Quick answer</div>
    <textarea id="ja_q" rows="3" style="width:100%;box-sizing:border-box;"></textarea>
    <button id="ja_ask" style="margin-top:6px;width:100%;">Ask from resume</button>
    <div style="font-size:12px;margin-top:8px;margin-bottom:4px;">Status</div>
    <pre id="ja_status" style="white-space:pre-wrap;background:#111;padding:6px;border-radius:6px;max-height:120px;overflow:auto;">Ready.</pre>
    <div style="font-size:12px;margin-top:8px;margin-bottom:4px;">Progress</div>
    <pre id="ja_progress" style="white-space:pre-wrap;background:#111;padding:6px;border-radius:6px;max-height:80px;overflow:auto;">idle</pre>
    <div style="font-size:12px;margin-top:8px;margin-bottom:4px;">Answer</div>
    <pre id="ja_answer" style="white-space:pre-wrap;background:#111;padding:6px;border-radius:6px;max-height:140px;overflow:auto;"></pre>
    <div style="font-size:12px;margin-top:8px;margin-bottom:4px;">Debug console</div>
    <pre id="ja_debug" style="white-space:pre-wrap;background:#0f0f0f;padding:6px;border-radius:6px;max-height:200px;overflow:auto;"></pre>
  `;
  shell.appendChild(panel);
  document.body.appendChild(shell);
  document.body.appendChild(tab);

  window.__jobAgentQueue = window.__jobAgentQueue || [];
  const push = (obj) => window.__jobAgentQueue.push(obj);

  const ids = ["ja_scan","ja_fill","ja_next","ja_submit","ja_reinject","ja_quit"];
  ids.forEach((id) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.style.padding = "7px";
    el.style.borderRadius = "6px";
    el.style.border = "1px solid #777";
    el.style.background = "#2b2b2b";
    el.style.color = "#f2f2f2";
    el.style.cursor = "pointer";
    el.style.pointerEvents = "auto";
  });

  const queueAction = (actionName) => {
    push({ action: actionName });
    if (window.__jobAgentSetStatus) window.__jobAgentSetStatus(`queued: ${actionName}`);
    if (window.__jobAgentSetProgress) window.__jobAgentSetProgress("waiting for worker...");
    if (window.__jobAgentLog) window.__jobAgentLog(`queued action: ${actionName}`);
  };

  document.getElementById("ja_scan").addEventListener("click", (e) => { e.stopPropagation(); queueAction("scan"); });
  document.getElementById("ja_fill").addEventListener("click", (e) => { e.stopPropagation(); queueAction("fill"); });
  document.getElementById("ja_next").addEventListener("click", (e) => { e.stopPropagation(); queueAction("next"); });
  document.getElementById("ja_submit").addEventListener("click", (e) => { e.stopPropagation(); queueAction("submit"); });
  document.getElementById("ja_reinject").addEventListener("click", (e) => { e.stopPropagation(); queueAction("reinject"); });
  document.getElementById("ja_quit").addEventListener("click", (e) => { e.stopPropagation(); queueAction("quit"); });

  document.getElementById("ja_ask").addEventListener("click", (e) => {
    e.stopPropagation();
    const question = (document.getElementById("ja_q").value || "").trim();
    if (question) {
      push({ action: "quick_answer", question });
      if (window.__jobAgentSetStatus) window.__jobAgentSetStatus("queued: quick_answer");
      if (window.__jobAgentSetProgress) window.__jobAgentSetProgress("waiting for worker...");
      if (window.__jobAgentLog) window.__jobAgentLog("queued action: quick_answer");
    }
  });
  document.getElementById("ja_minimize").onclick = () => {
    panel.style.display = "none";
    tab.style.display = "block";
  };
  tab.onclick = () => {
    panel.style.display = "block";
    tab.style.display = "none";
  };

  window.__jobAgentSetStatus = (txt) => {
    const el = document.getElementById("ja_status");
    if (el) el.textContent = txt || "";
  };
  window.__jobAgentSetProgress = (txt) => {
    const el = document.getElementById("ja_progress");
    if (el) el.textContent = txt || "";
  };
  window.__jobAgentSetAnswer = (txt) => {
    const el = document.getElementById("ja_answer");
    if (el) el.textContent = txt || "";
  };
  window.__jobAgentLog = (txt) => {
    const el = document.getElementById("ja_debug");
    if (!el) return;
    const now = new Date().toLocaleTimeString();
    el.textContent = `[${now}] ${txt}\n` + el.textContent;
  };
}
"""


def _set_status(page, msg: str) -> None:
    try:
        page.evaluate("(m) => window.__jobAgentSetStatus && window.__jobAgentSetStatus(m)", msg)
    except Exception:
        pass


def _set_progress(page, msg: str) -> None:
    try:
        page.evaluate("(m) => window.__jobAgentSetProgress && window.__jobAgentSetProgress(m)", msg)
    except Exception:
        pass


def _log(page, msg: str) -> None:
    try:
        page.evaluate("(m) => window.__jobAgentLog && window.__jobAgentLog(m)", msg)
    except Exception:
        pass


def _set_answer(page, msg: str) -> None:
    try:
        page.evaluate("(m) => window.__jobAgentSetAnswer && window.__jobAgentSetAnswer(m)", msg)
    except Exception:
        pass


def _inject_overlay(page) -> None:
    page.evaluate(OVERLAY_JS)


def _pop_actions(page) -> list[dict]:
    try:
        actions = page.evaluate(
            """() => {
              const q = window.__jobAgentQueue || [];
              const out = q.slice();
              q.splice(0, q.length);
              return out;
            }"""
        )
        if isinstance(actions, list):
            return [a for a in actions if isinstance(a, dict)]
    except Exception:
        return []
    return []


def _click_button(page, schema: Optional[Dict[str, Any]], kind: str) -> bool:
    if not schema:
        return False
    for b in schema.get("buttons", []):
        if b.get("kind") == kind and b.get("selector"):
            try:
                page.locator(b["selector"]).first.click()
                return True
            except Exception:
                continue
    return False


def run_assistant(*, url: str, mode: str, model: str, job_description: str = "") -> None:
    sess = open_browser(url=url, headless=False)
    page = sess.page
    current_schema: Optional[Dict[str, Any]] = None
    current_plan: Optional[ApplyPlan] = None

    def _on_nav(frame):
        if frame == page.main_frame:
            try:
                _inject_overlay(page)
                _set_status(page, f"Navigated: {page.url}\nClick Scan to continue.")
            except Exception:
                pass

    page.on("framenavigated", _on_nav)
    _inject_overlay(page)
    _set_status(page, "Assistant ready. Solve login/CAPTCHA manually, then click Scan.")
    _set_progress(page, "idle")
    _log(page, f"assistant started | mode={mode} | model={model}")
    last_heartbeat = 0.0

    cfg = OllamaConfig(model=model, max_tokens=500)

    try:
        while True:
            now = time.time()
            if now - last_heartbeat > 1.0:
                _set_progress(page, "worker alive - waiting")
                last_heartbeat = now
            actions = _pop_actions(page)
            if not actions:
                time.sleep(0.25)
                continue

            for action in actions:
                try:
                    a = action.get("action", "")
                    _log(page, f"processing action: {a}")

                    if a == "quit":
                        _log(page, "quit requested")
                        _set_status(page, "Closing assistant...")
                        return

                    if a == "reinject":
                        _inject_overlay(page)
                        _set_status(page, "Overlay reinjected.")
                        _log(page, "overlay reinjected")
                        continue

                    if a == "scan":
                        _set_progress(page, "scanning...")
                        fs = snapshot_form(page).to_dict()
                        current_schema = fs
                        current_plan = None
                        _set_status(page, f"Scanned {len(fs.get('fields', []))} fields on this page.")
                        _set_progress(page, "scan complete")
                        _log(page, f"scan complete | fields={len(fs.get('fields', []))} | buttons={len(fs.get('buttons', []))}")
                        continue

                    if a == "fill":
                        if current_schema is None:
                            current_schema = snapshot_form(page).to_dict()
                        _set_status(page, "Planning one-shot answers with Ollama...")
                        _set_progress(page, "planning...")
                        _log(page, "planning with ollama (single-shot)")
                        current_plan = plan_application(
                            form_schema=current_schema,
                            job_url=current_schema.get("url") or page.url,
                            job_description=job_description or None,
                            config=cfg,
                        )
                        _set_progress(page, "filling...")
                        _log(page, f"plan ready | mapped_fields={len(current_plan.field_values)}")

                        def on_progress(i: int, total: int, selector: str) -> None:
                            _set_progress(page, f"filling {i} of {total} fields")
                            _log(page, f"fill progress {i}/{total} | {selector}")

                        res = fill_page_fields(page, field_values=current_plan.field_values, progress_cb=on_progress)
                        msg = (
                            f"Filled: {len(res.applied)} | Skipped: {len(res.skipped)} | Errors: {len(res.errors)}"
                        )
                        if current_plan.notes:
                            msg += "\nNotes: " + "; ".join(current_plan.notes[:3])
                        _set_status(page, msg)
                        _set_progress(page, "fill complete")
                        _log(page, msg)
                        if mode == "fullAuto":
                            if _click_button(page, current_schema, "next"):
                                _set_status(page, msg + "\nClicked Next (fullAuto).")
                                _log(page, "fullAuto clicked Next")
                            elif _click_button(page, current_schema, "submit"):
                                _set_status(page, msg + "\nClicked Submit (fullAuto).")
                                _log(page, "fullAuto clicked Submit")
                        continue

                    if a == "next":
                        ok = _click_button(page, current_schema, "next")
                        _set_status(page, "Clicked Next." if ok else "Could not find a Next button.")
                        _log(page, "next clicked" if ok else "next button not found")
                        continue

                    if a == "submit":
                        ok = _click_button(page, current_schema, "submit")
                        _set_status(page, "Clicked Submit." if ok else "Could not find a Submit button.")
                        _log(page, "submit clicked" if ok else "submit button not found")
                        continue

                    if a == "quick_answer":
                        q = (action.get("question") or "").strip()
                        if not q:
                            continue
                        _set_status(page, "Answering from resume data...")
                        _set_progress(page, "asking model...")
                        _log(page, f"quick_answer asked | chars={len(q)}")
                        ans = answer_question(q, config=OllamaConfig(model=model, max_tokens=220))
                        _set_answer(page, ans)
                        _set_status(page, "Answer ready.")
                        _set_progress(page, "answer complete")
                        _log(page, "quick_answer complete")
                        continue
                except Exception as action_err:
                    _set_status(page, f"Error while processing action: {action.get('action')}")
                    _set_progress(page, "worker alive - error")
                    _log(page, f"ERROR {type(action_err).__name__}: {action_err}")
                    continue
    finally:
        try:
            sess.close()
        except Exception:
            pass


def _load_config(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    parser = argparse.ArgumentParser(description="Interactive in-browser Job Apply Assistant")
    parser.add_argument("--config", required=True, help="Path to JSON config file")
    args = parser.parse_args()

    cfg = _load_config(args.config)
    run_assistant(
        url=cfg["url"],
        mode=cfg.get("mode", "semiAuto"),
        model=cfg.get("model", "qwen2.5:7b-instruct"),
        job_description=cfg.get("job_description", ""),
    )


if __name__ == "__main__":
    main()


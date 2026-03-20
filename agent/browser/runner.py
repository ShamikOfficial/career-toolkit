from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Optional

from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright


@dataclass
class BrowserSession:
    playwright: Playwright
    browser: Browser
    context: BrowserContext
    page: Page

    def close(self) -> None:
        try:
            self.context.close()
        finally:
            try:
                self.browser.close()
            finally:
                self.playwright.stop()


def _ensure_windows_asyncio_policy() -> None:
    """
    Playwright on Windows can fail with NotImplementedError on subprocess creation
    under incompatible event loop policies.
    Ensure Proactor policy so asyncio subprocess APIs are available.
    """
    if os.name == "nt":
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())  # type: ignore[attr-defined]
        except Exception:
            # Best effort; if it still fails we surface a clear error later.
            pass


def open_browser(
    *,
    url: str,
    headless: bool = False,
    user_agent: Optional[str] = None,
) -> BrowserSession:
    _ensure_windows_asyncio_policy()
    try:
        pw = sync_playwright().start()
        browser = pw.chromium.launch(headless=headless)
        context = browser.new_context(user_agent=user_agent)
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded")
        return BrowserSession(playwright=pw, browser=browser, context=context, page=page)
    except NotImplementedError as e:
        raise RuntimeError(
            "Playwright failed to start due to an asyncio policy issue on Windows. "
            "Please restart Streamlit after this patch, and ensure you're on a supported "
            "Python version for Playwright (3.11-3.13 recommended)."
        ) from e
    except Exception as e:
        msg = str(e)
        if "Executable doesn't exist" in msg or "Please run the following command" in msg:
            raise RuntimeError(
                "Playwright browser binaries are missing. Run: "
                "`python -m playwright install chromium`"
            ) from e
        raise


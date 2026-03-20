from __future__ import annotations

from dataclasses import dataclass

from playwright.sync_api import Page

from . import SiteAdapter


@dataclass
class LeverAdapter(SiteAdapter):
    name: str = "lever"

    def detect(self, page: Page) -> bool:
        url = page.url.lower()
        if "lever.co" in url:
            return True
        return page.locator("form[data-qa='application-form']").count() > 0


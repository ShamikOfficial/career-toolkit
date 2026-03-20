from __future__ import annotations

from dataclasses import dataclass

from playwright.sync_api import Page

from . import SiteAdapter


@dataclass
class GreenhouseAdapter(SiteAdapter):
    name: str = "greenhouse"

    def detect(self, page: Page) -> bool:
        url = page.url.lower()
        if "greenhouse.io" in url or "boards.greenhouse.io" in url:
            return True
        # Some embedded Greenhouse pages have recognizable form id/class
        return page.locator("form#application_form, form.application-form").count() > 0


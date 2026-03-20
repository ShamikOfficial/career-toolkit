from __future__ import annotations

from dataclasses import dataclass

from playwright.sync_api import Page

from . import SiteAdapter


@dataclass
class GenericAdapter(SiteAdapter):
    name: str = "generic"

    def detect(self, page: Page) -> bool:
        return True


from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from playwright.sync_api import Page

from .generic import GenericAdapter
from .greenhouse import GreenhouseAdapter
from .lever import LeverAdapter


@dataclass
class SiteAdapter:
    name: str

    def classify_button(self, text: str) -> str:
        return "other"

    def detect(self, page: Page) -> bool:
        return False


def get_adapter(page: Page) -> SiteAdapter:
    for adapter_cls in (GreenhouseAdapter, LeverAdapter):
        adapter = adapter_cls()
        try:
            if adapter.detect(page):
                return adapter
        except Exception:
            continue
    return GenericAdapter()


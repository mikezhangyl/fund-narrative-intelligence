from __future__ import annotations

from typing import Any

__all__ = ["NarrativeIntelligenceService"]


def __getattr__(name: str) -> Any:
    if name == "NarrativeIntelligenceService":
        from .service import NarrativeIntelligenceService

        return NarrativeIntelligenceService
    raise AttributeError(name)

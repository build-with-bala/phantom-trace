"""Core data models for Phantom Trace."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CheckType(Enum):
    STATUS_CODE = "status_code"
    RESPONSE_BODY = "response_body"


@dataclass
class SiteResult:
    site: str
    url: str
    category: str
    username: str
    found: bool = False
    status_code: int = 0
    error: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)
    api_data: dict[str, Any] | None = None


@dataclass
class PersonProfile:
    query: str
    query_type: str
    sites_found: list[SiteResult] = field(default_factory=list)
    sites_not_found: list[SiteResult] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    locations: list[str] = field(default_factory=list)
    real_name_guess: str | None = None
    confidence_score: float = 0.0

    @property
    def total_found(self) -> int:
        return len(self.sites_found)

    @property
    def total_checked(self) -> int:
        return len(self.sites_found) + len(self.sites_not_found)

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
class EmailResult:
    email: str
    provider: str
    valid: bool = False
    services: list[str] = field(default_factory=list)
    gravatar: str | None = None
    breach_count: int = 0
    breaches: list[str] = field(default_factory=list)


@dataclass
class PhoneResult:
    number: str
    carrier: str | None = None
    country: str | None = None
    services: list[str] = field(default_factory=list)


@dataclass
class PersonProfile:
    query: str
    query_type: str
    sites_found: list[SiteResult] = field(default_factory=list)
    sites_not_found: list[SiteResult] = field(default_factory=list)
    emails: list[EmailResult] = field(default_factory=list)
    phones: list[PhoneResult] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    related_usernames: list[str] = field(default_factory=list)
    locations: list[str] = field(default_factory=list)
    real_name_guess: str | None = None
    avatar_urls: list[str] = field(default_factory=list)
    social_graph: dict[str, list[str]] = field(default_factory=dict)
    confidence_score: float = 0.0

    @property
    def total_found(self) -> int:
        return len(self.sites_found)

    @property
    def total_checked(self) -> int:
        return len(self.sites_found) + len(self.sites_not_found)

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "query_type": self.query_type,
            "total_found": self.total_found,
            "total_checked": self.total_checked,
            "confidence_score": self.confidence_score,
            "real_name_guess": self.real_name_guess,
            "aliases": self.aliases,
            "locations": self.locations,
            "sites_found": [
                {"site": s.site, "url": s.url, "category": s.category, "metadata": s.metadata}
                for s in self.sites_found
            ],
            "avatar_urls": self.avatar_urls,
            "social_graph": self.social_graph,
        }

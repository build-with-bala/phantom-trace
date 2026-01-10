"""Extract and correlate metadata across discovered profiles."""

import re
from collections import Counter
from typing import Any

from src.models import SiteResult, PersonProfile


class MetadataExtractor:
    def __init__(self):
        self.locations: list[str] = []
        self.names: list[str] = []
        self.bios: list[str] = []
        self.avatars: list[str] = []
        self.links: list[str] = []

    def process_results(self, results: list[SiteResult]) -> dict[str, Any]:
        for r in results:
            if not r.found:
                continue
            meta = r.metadata or {}
            if meta.get("location"):
                self.locations.append(meta["location"])
            if meta.get("bio"):
                self.bios.append(meta["bio"])
                name = self._extract_name(meta["bio"])
                if name:
                    self.names.append(name)
            if r.api_data:
                self._process_api(r.site, r.api_data)

        return {
            "probable_location": self._most_common(self.locations),
            "probable_name": self._most_common(self.names),
            "all_locations": list(set(self.locations)),
            "avatar_urls": self.avatars,
            "external_links": list(set(self.links)),
        }

    def _process_api(self, site: str, data: dict):
        if site == "github":
            for k, lst in [("name", self.names), ("location", self.locations), ("bio", self.bios)]:
                if data.get(k):
                    lst.append(data[k])
            if data.get("avatar_url"):
                self.avatars.append(data["avatar_url"])
            if data.get("blog"):
                self.links.append(data["blog"])
        elif site == "reddit" and isinstance(data, dict) and "data" in data:
            if data["data"].get("icon_img"):
                self.avatars.append(data["data"]["icon_img"].split("?")[0])

    def _extract_name(self, bio: str) -> str | None:
        patterns = [
            r"(?:I'm|I am|my name is)\s+([A-Z][a-z]+ [A-Z][a-z]+)",
            r"^([A-Z][a-z]+ [A-Z][a-z]+)\s*[|\-–]",
        ]
        for p in patterns:
            m = re.search(p, bio, re.IGNORECASE)
            if m:
                return m.group(1).title()
        return None

    def _most_common(self, items: list[str]) -> str | None:
        if not items:
            return None
        normalized = [i.strip().lower() for i in items if i.strip()]
        if not normalized:
            return None
        best = Counter(normalized).most_common(1)[0][0]
        for item in items:
            if item.strip().lower() == best:
                return item.strip()
        return best


def calculate_confidence(profile: PersonProfile) -> float:
    score = 0.0
    score += min(profile.total_found * 2, 30)
    if profile.real_name_guess:
        score += 20
    if profile.locations:
        score += 10
    categories = set(s.category for s in profile.sites_found)
    score += min(len(categories) * 5, 20)
    return min(score / 100.0, 1.0)

"""Build social connection graphs from discovered profiles."""

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SocialNode:
    username: str
    platform: str
    url: str
    connections: list[str] = field(default_factory=list)


class SocialGraphBuilder:
    def __init__(self):
        self.nodes: dict[str, SocialNode] = {}
        self.edges: list[tuple[str, str, str]] = []

    def add_profile(self, username: str, platform: str, url: str, api_data: dict | None = None):
        node_id = f"{platform}:{username}"
        self.nodes[node_id] = SocialNode(username=username, platform=platform, url=url)
        if api_data:
            self._extract_connections(node_id, platform, api_data)

    def _extract_connections(self, node_id: str, platform: str, data: dict):
        if platform == "github":
            if data.get("company"):
                self.edges.append((node_id, f"org:{data['company']}", "member_of"))
            if data.get("blog"):
                self.edges.append((node_id, f"url:{data['blog']}", "owns"))

    def find_cross_references(self, results: list[Any]) -> dict[str, list[str]]:
        cross_refs: dict[str, list[str]] = {}
        for r in results:
            if not r.found or not r.metadata:
                continue
            bio = r.metadata.get("bio", "")
            if not bio:
                continue
            handles = re.findall(r"@(\w{3,30})", bio)
            for h in handles:
                if h.lower() != r.username.lower():
                    cross_refs.setdefault(h, []).append(f"mentioned in {r.site} bio")
        return cross_refs

    def to_dict(self) -> dict:
        return {
            "nodes": {k: {"username": v.username, "platform": v.platform, "url": v.url} for k, v in self.nodes.items()},
            "edges": [{"from": e[0], "to": e[1], "rel": e[2]} for e in self.edges],
        }

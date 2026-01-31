"""Reconnaissance agent - performs initial platform scanning."""

import json
from pathlib import Path

from src.agents.base import BaseAgent, AgentContext, AgentStatus
from src.engines.async_scanner import AsyncScanner


class ReconAgent(BaseAgent):
    """Scans target across all configured platforms."""

    name = "recon_agent"
    description = "Multi-platform username/email scanner"

    def __init__(self, max_concurrent: int = 80, timeout: int = 15):
        super().__init__()
        self.scanner = AsyncScanner(max_concurrent=max_concurrent, timeout=timeout)

    async def execute(self, context: AgentContext) -> AgentContext:
        sites_path = Path(__file__).parent.parent.parent / "data" / "sites.json"
        with open(sites_path) as f:
            sites = json.load(f)

        task = self.create_task("scan_platforms", description=f"Scan {len(sites)} platforms")
        task.status = AgentStatus.RUNNING

        results = await self.scanner.scan_all(context.target, sites)

        found = [r for r in results if r.found]
        not_found = [r for r in results if not r.found]

        context.add_finding("scan_results", {
            "found": [{"site": r.site, "url": r.url, "category": r.category, "metadata": r.metadata, "api_data": r.api_data} for r in found],
            "not_found_count": len(not_found),
            "error_count": len([r for r in results if r.error]),
        })

        context.metadata["total_sites_checked"] = len(results)
        context.metadata["total_found"] = len(found)

        task.status = AgentStatus.COMPLETED
        task.output_data = {"found": len(found), "checked": len(results)}
        return context

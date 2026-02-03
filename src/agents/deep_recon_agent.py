"""Deep reconnaissance agent - follows up on aliases and cross-references."""

import json
from pathlib import Path

from src.agents.base import BaseAgent, AgentContext, AgentStatus
from src.engines.async_scanner import AsyncScanner


class DeepReconAgent(BaseAgent):
    """Scans discovered aliases and cross-references for additional profiles."""

    name = "deep_recon_agent"
    description = "Deep scan of aliases and cross-platform references"

    def __init__(self, max_aliases: int = 5, max_concurrent: int = 50):
        super().__init__()
        self.max_aliases = max_aliases
        self.max_concurrent = max_concurrent

    async def execute(self, context: AgentContext) -> AgentContext:
        # Collect targets from aliases and cross-references
        targets = set()

        aliases = context.findings.get("aliases", [])
        if aliases and isinstance(aliases[-1], list):
            targets.update(aliases[-1][:self.max_aliases])

        graph_data = context.findings.get("social_graph", [])
        if graph_data:
            cross_refs = graph_data[-1].get("cross_refs", {})
            targets.update(list(cross_refs.keys())[:3])

        targets.discard(context.target)  # Don't re-scan original
        if not targets:
            return context

        sites_path = Path(__file__).parent.parent.parent / "data" / "sites.json"
        with open(sites_path) as f:
            sites = json.load(f)

        scanner = AsyncScanner(max_concurrent=self.max_concurrent, timeout=10)

        all_deep_results = {}
        for alias in targets:
            task = self.create_task(f"deep_scan_{alias}")
            task.status = AgentStatus.RUNNING

            results = await scanner.scan_all(alias, sites)
            found = [r for r in results if r.found]

            if found:
                all_deep_results[alias] = [
                    {"site": r.site, "url": r.url, "category": r.category}
                    for r in found
                ]

            task.status = AgentStatus.COMPLETED
            task.output_data = {"alias": alias, "found": len(found)}

        if all_deep_results:
            context.add_finding("deep_recon", all_deep_results)
            context.metadata["deep_recon_aliases"] = len(all_deep_results)

        return context

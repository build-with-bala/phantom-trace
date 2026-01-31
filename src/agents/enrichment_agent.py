"""Enrichment agent - extracts and correlates metadata from findings."""

from src.agents.base import BaseAgent, AgentContext, AgentStatus
from src.modules.metadata_extractor import MetadataExtractor
from src.modules.social_graph import SocialGraphBuilder
from src.modules.alias_generator import generate_aliases
from src.models import SiteResult


class EnrichmentAgent(BaseAgent):
    """Enriches raw scan data with metadata, aliases, and social graph."""

    name = "enrichment_agent"
    description = "Metadata extraction and cross-platform correlation"

    async def execute(self, context: AgentContext) -> AgentContext:
        scan_data = context.findings.get("scan_results", [{}])
        if not scan_data:
            return context

        latest = scan_data[-1]
        found_sites = latest.get("found", [])

        # Convert back to SiteResult for processing
        results = [
            SiteResult(
                site=s["site"], url=s["url"], category=s["category"],
                username=context.target, found=True,
                metadata=s.get("metadata", {}), api_data=s.get("api_data"),
            )
            for s in found_sites
        ]

        # Metadata extraction
        task1 = self.create_task("extract_metadata")
        task1.status = AgentStatus.RUNNING

        extractor = MetadataExtractor()
        meta = extractor.process_results(results)
        context.add_finding("metadata", meta)
        task1.status = AgentStatus.COMPLETED

        # Alias generation
        task2 = self.create_task("generate_aliases")
        task2.status = AgentStatus.RUNNING

        aliases = generate_aliases(context.target)
        context.add_finding("aliases", aliases)
        task2.status = AgentStatus.COMPLETED

        # Social graph
        task3 = self.create_task("build_social_graph")
        task3.status = AgentStatus.RUNNING

        graph = SocialGraphBuilder()
        for r in results:
            graph.add_profile(context.target, r.site, r.url, r.api_data)
        cross_refs = graph.find_cross_references(results)
        context.add_finding("social_graph", {"graph": graph.to_dict(), "cross_refs": cross_refs})
        task3.status = AgentStatus.COMPLETED

        return context

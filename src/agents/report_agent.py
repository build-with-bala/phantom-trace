"""Report agent - generates final intelligence reports."""

from datetime import datetime
from pathlib import Path

from src.agents.base import BaseAgent, AgentContext, AgentStatus
from src.models import PersonProfile, SiteResult
from src.modules.metadata_extractor import calculate_confidence
from src.exporters.json_export import export_json
from src.exporters.html_export import export_html


class ReportAgent(BaseAgent):
    """Compiles all findings into structured reports."""

    name = "report_agent"
    description = "Intelligence report generator"

    def __init__(self, output_dir: str = "output", formats: list[str] | None = None):
        super().__init__()
        self.output_dir = output_dir
        self.formats = formats or ["json", "html"]

    async def execute(self, context: AgentContext) -> AgentContext:
        task = self.create_task("compile_report")
        task.status = AgentStatus.RUNNING

        profile = self._build_profile(context)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        base = f"{self.output_dir}/{context.target}_{ts}"

        if "json" in self.formats:
            export_json(profile, f"{base}.json")
            context.add_finding("reports", {"json": f"{base}.json"})

        if "html" in self.formats:
            export_html(profile, f"{base}.html")
            context.add_finding("reports", {"html": f"{base}.html"})

        task.status = AgentStatus.COMPLETED
        task.output_data = {"path": base}
        return context

    def _build_profile(self, context: AgentContext) -> PersonProfile:
        profile = PersonProfile(query=context.target, query_type=context.target_type)

        scan_data = context.findings.get("scan_results", [{}])
        if scan_data:
            latest = scan_data[-1]
            profile.sites_found = [
                SiteResult(site=s["site"], url=s["url"], category=s["category"],
                          username=context.target, found=True, metadata=s.get("metadata", {}))
                for s in latest.get("found", [])
            ]

        meta_list = context.findings.get("metadata", [])
        if meta_list:
            meta = meta_list[-1]
            profile.real_name_guess = meta.get("probable_name")
            profile.locations = meta.get("all_locations", [])
            profile.avatar_urls = meta.get("avatar_urls", [])

        aliases = context.findings.get("aliases", [])
        if aliases and isinstance(aliases[-1], list):
            profile.aliases = aliases[-1]

        graph_data = context.findings.get("social_graph", [])
        if graph_data:
            profile.social_graph = graph_data[-1].get("cross_refs", {})

        profile.confidence_score = calculate_confidence(profile)
        return profile

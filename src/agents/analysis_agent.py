"""Analysis agent - AI-powered reasoning about OSINT findings."""

from src.agents.base import BaseAgent, AgentContext, AgentStatus
from src.ai.router import create_default_router
from src.ai.analyzer import ProfileAnalyzer
from src.models import PersonProfile, SiteResult


class AnalysisAgent(BaseAgent):
    """Uses AI to analyze findings and generate intelligence."""

    name = "analysis_agent"
    description = "AI-powered OSINT analysis and reasoning"

    def __init__(self, prefer_provider: str | None = None):
        super().__init__()
        self.prefer_provider = prefer_provider

    async def execute(self, context: AgentContext) -> AgentContext:
        router = create_default_router()
        status = await router.check_availability()

        available = [k for k, v in status.items() if v]
        if not available:
            context.add_finding("ai_analysis", {"error": "No AI providers available"})
            return context

        # Build profile from context findings
        profile = self._build_profile(context)

        analyzer = ProfileAnalyzer(router)

        # Task 1: Profile analysis
        task1 = self.create_task("analyze_profile")
        task1.status = AgentStatus.RUNNING
        try:
            analysis = await analyzer.analyze_profile(profile)
            context.add_finding("ai_analysis", analysis)
            task1.status = AgentStatus.COMPLETED
        except Exception as e:
            task1.status = AgentStatus.FAILED
            task1.error = str(e)

        # Task 2: Correlation analysis
        task2 = self.create_task("correlate_aliases")
        task2.status = AgentStatus.RUNNING
        try:
            scan_data = context.findings.get("scan_results", [{}])[-1]
            correlation = await analyzer.correlate_aliases(context.target, scan_data.get("found", []))
            context.add_finding("correlation", correlation)
            task2.status = AgentStatus.COMPLETED
        except Exception as e:
            task2.status = AgentStatus.FAILED
            task2.error = str(e)

        # Task 3: Investigation plan
        task3 = self.create_task("generate_plan")
        task3.status = AgentStatus.RUNNING
        try:
            plan = await analyzer.generate_investigation_plan(profile)
            context.add_finding("investigation_plan", plan)
            task3.status = AgentStatus.COMPLETED
        except Exception as e:
            task3.status = AgentStatus.FAILED
            task3.error = str(e)

        return context

    def _build_profile(self, context: AgentContext) -> PersonProfile:
        profile = PersonProfile(query=context.target, query_type=context.target_type)

        scan_data = context.findings.get("scan_results", [{}])[-1]
        profile.sites_found = [
            SiteResult(site=s["site"], url=s["url"], category=s["category"],
                      username=context.target, found=True, metadata=s.get("metadata", {}))
            for s in scan_data.get("found", [])
        ]

        meta_list = context.findings.get("metadata", [])
        if meta_list:
            meta = meta_list[-1]
            profile.real_name_guess = meta.get("probable_name")
            profile.locations = meta.get("all_locations", [])
            profile.avatar_urls = meta.get("avatar_urls", [])

        aliases_list = context.findings.get("aliases", [])
        if aliases_list:
            profile.aliases = aliases_list[-1] if isinstance(aliases_list[-1], list) else []

        return profile

"""Dorking agent - generates targeted search queries from all gathered intelligence."""

from src.agents.base import BaseAgent, AgentContext, AgentStatus
from src.modules.dorking import generate_dorks, format_dorks_markdown


class DorkingAgent(BaseAgent):
    """Generates Google dork queries from accumulated intelligence."""

    name = "dorking_agent"
    description = "Auto-generate targeted Google search queries"

    async def execute(self, context: AgentContext) -> AgentContext:
        task = self.create_task("generate_dorks")
        task.status = AgentStatus.RUNNING

        # Gather all known identifiers
        username = context.target if context.target_type == "username" else None
        email = context.target if context.target_type == "email" else None
        real_name = None
        domain = None

        # Extract from metadata
        meta_list = context.findings.get("metadata", [])
        if meta_list:
            meta = meta_list[-1]
            real_name = meta.get("probable_name")

        # Extract from GitHub intel
        github_intel = context.findings.get("github_intel", [])
        if github_intel:
            gh = github_intel[-1]
            profile = gh.get("profile", {})
            if profile.get("name") and not real_name:
                real_name = profile["name"]
            if profile.get("blog"):
                domain = profile["blog"]
                if domain.startswith("http"):
                    from urllib.parse import urlparse
                    domain = urlparse(domain).netloc

        # Get discovered emails
        discovered_emails = context.findings.get("discovered_emails", [])
        if discovered_emails and not email:
            email = discovered_emails[0]

        # Generate dorks
        dorks = generate_dorks(
            username=username,
            email=email,
            real_name=real_name,
            domain=domain,
        )

        context.add_finding("investigation_dorks", {
            "total_queries": len(dorks),
            "dorks": [
                {"category": d.category, "description": d.description, "query": d.query, "url": d.url}
                for d in dorks
            ],
            "markdown": format_dorks_markdown(dorks),
        })

        task.status = AgentStatus.COMPLETED
        task.output_data = {"total_dorks": len(dorks)}
        return context

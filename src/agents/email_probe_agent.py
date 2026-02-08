"""Email probe agent - runs Holehe-style service registration checks."""

import aiohttp

from src.agents.base import BaseAgent, AgentContext, AgentStatus
from src.modules.email_probe import probe_all_services
from src.modules.email_recon import check_email


class EmailProbeAgent(BaseAgent):
    """Checks which services an email is registered on."""

    name = "email_probe_agent"
    description = "Holehe-style email registration probing (10+ services)"

    async def execute(self, context: AgentContext) -> AgentContext:
        # Collect all known emails
        emails = set()

        if context.target_type == "email":
            emails.add(context.target)

        # Add discovered emails from GitHub commits, Gravatar, etc.
        discovered = context.findings.get("discovered_emails", [])
        emails.update(discovered[:5])

        if not emails:
            return context

        async with aiohttp.ClientSession() as session:
            for email in emails:
                task = self.create_task(f"probe_{email}")
                task.status = AgentStatus.RUNNING

                try:
                    # Run service probes
                    probes = await probe_all_services(email, session)
                    registered = [p for p in probes if p.registered]
                    failed = [p for p in probes if p.error]

                    context.add_finding("email_probes", {
                        "email": email,
                        "total_checked": len(probes),
                        "registered_on": [
                            {"service": p.service, "method": p.method, "extra": p.extra}
                            for p in registered
                        ],
                        "errors": len(failed),
                    })

                    # Also run standard email recon
                    recon = await check_email(email, session)
                    context.add_finding("email_recon", recon)

                    task.status = AgentStatus.COMPLETED
                    task.output_data = {"email": email, "registered_services": len(registered)}

                except Exception as e:
                    task.error = str(e)
                    task.status = AgentStatus.FAILED

        return context

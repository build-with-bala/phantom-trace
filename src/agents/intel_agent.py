"""Intelligence gathering agent - deep data extraction from discovered profiles.

This is the agent that does the REAL OSINT work. After ReconAgent finds
which platforms a username exists on, this agent:
1. Extracts commit emails from GitHub
2. Mines Gravatar linked accounts
3. Queries Keybase for verified proofs
4. Checks certificate transparency for owned domains
5. Searches PGP keyservers
6. Analyzes activity patterns for timezone estimation
7. Runs avatar perceptual hashing
8. Queries Wayback Machine for historical data
"""

import aiohttp

from src.agents.base import BaseAgent, AgentContext, AgentStatus
from src.modules.github_intel import extract_commit_emails, get_github_profile, get_activity_pattern
from src.modules.gravatar_intel import get_gravatar_profile
from src.modules.keybase_intel import lookup_keybase_user
from src.modules.cert_transparency import domain_intel_chain
from src.modules.pgp_keyserver import lookup_by_email, lookup_by_username
from src.modules.avatar_analysis import analyze_avatars
from src.modules.wayback_intel import check_wayback_availability, find_deleted_profiles


class IntelAgent(BaseAgent):
    """Deep intelligence extraction from discovered profiles."""

    name = "intel_agent"
    description = "Deep data extraction (emails, linked accounts, certificates, avatars)"

    async def execute(self, context: AgentContext) -> AgentContext:
        scan_data = context.findings.get("scan_results", [])
        if not scan_data:
            return context

        found_sites = scan_data[-1].get("found", [])
        found_names = {s["site"] for s in found_sites}

        async with aiohttp.ClientSession() as session:
            # 1. GitHub deep intel
            if "github" in found_names:
                task = self.create_task("github_deep_intel")
                task.status = AgentStatus.RUNNING
                try:
                    profile = await get_github_profile(context.target, session)
                    commit_emails = await extract_commit_emails(context.target, session)
                    activity = await get_activity_pattern(context.target, session)

                    intel = {"profile": profile, "commit_emails": commit_emails, "activity_pattern": activity}
                    context.add_finding("github_intel", intel)

                    # Cascade: discovered emails become new leads
                    for em in commit_emails:
                        context.add_finding("discovered_emails", em["email"])

                    # Cascade: blog URL becomes domain lead
                    if profile.get("blog"):
                        blog = profile["blog"]
                        if not blog.startswith("http"):
                            blog = f"https://{blog}"
                        context.add_finding("discovered_domains", blog)

                    task.status = AgentStatus.COMPLETED
                except Exception as e:
                    task.error = str(e)
                    task.status = AgentStatus.FAILED

            # 2. Keybase verification
            task = self.create_task("keybase_lookup")
            task.status = AgentStatus.RUNNING
            try:
                kb = await lookup_keybase_user(context.target, session)
                if kb["exists"]:
                    context.add_finding("keybase_proofs", kb)
                    # Cascade: verified proofs are gold
                    for proof in kb.get("verified_proofs", []):
                        if proof.get("verified"):
                            context.add_finding("verified_identities", {
                                "service": proof["service"],
                                "username": proof["username"],
                                "url": proof["url"],
                                "evidence_type": "cryptographic_proof",
                            })
                task.status = AgentStatus.COMPLETED
            except Exception as e:
                task.error = str(e)
                task.status = AgentStatus.FAILED

            # 3. Gravatar mining (if we have emails)
            discovered_emails = context.findings.get("discovered_emails", [])
            if discovered_emails:
                task = self.create_task("gravatar_mining")
                task.status = AgentStatus.RUNNING
                try:
                    for email in set(discovered_emails[:5]):
                        grav = await get_gravatar_profile(email, session)
                        if grav["exists"]:
                            context.add_finding("gravatar_profiles", grav)
                            # Cascade: linked accounts from Gravatar
                            for acct in grav.get("linked_accounts", []):
                                context.add_finding("discovered_accounts", {
                                    "service": acct["service"],
                                    "username": acct.get("username", ""),
                                    "url": acct.get("url", ""),
                                    "source": "gravatar_linked",
                                })
                    task.status = AgentStatus.COMPLETED
                except Exception as e:
                    task.error = str(e)
                    task.status = AgentStatus.FAILED

            # 4. PGP keyserver lookup
            if discovered_emails:
                task = self.create_task("pgp_lookup")
                task.status = AgentStatus.RUNNING
                try:
                    for email in set(discovered_emails[:3]):
                        pgp = await lookup_by_email(email, session)
                        if pgp["total_keys"] > 0:
                            context.add_finding("pgp_keys", pgp)
                    task.status = AgentStatus.COMPLETED
                except Exception as e:
                    task.error = str(e)
                    task.status = AgentStatus.FAILED

            # 5. Certificate transparency (if we discovered domains)
            domains = context.findings.get("discovered_domains", [])
            if domains:
                task = self.create_task("cert_transparency")
                task.status = AgentStatus.RUNNING
                try:
                    for domain_url in set(domains[:3]):
                        # Extract domain from URL
                        import tldextract
                        ext = tldextract.extract(domain_url)
                        domain = f"{ext.domain}.{ext.suffix}" if ext.suffix else ext.domain
                        if domain and "." in domain:
                            chain = await domain_intel_chain(domain, session)
                            context.add_finding("domain_intel", chain)
                    task.status = AgentStatus.COMPLETED
                except Exception as e:
                    task.error = str(e)
                    task.status = AgentStatus.FAILED

            # 6. Avatar analysis
            avatar_urls = {}
            for site in found_sites:
                api_data = site.get("api_data", {})
                if isinstance(api_data, dict) and api_data.get("avatar_url"):
                    avatar_urls[site["site"]] = api_data["avatar_url"]

            if len(avatar_urls) >= 2:
                task = self.create_task("avatar_analysis")
                task.status = AgentStatus.RUNNING
                try:
                    analysis = await analyze_avatars(avatar_urls, session)
                    context.add_finding("avatar_analysis", analysis)
                    task.status = AgentStatus.COMPLETED
                except Exception as e:
                    task.error = str(e)
                    task.status = AgentStatus.FAILED

            # 7. Deleted profile detection
            task = self.create_task("wayback_deleted_profiles")
            task.status = AgentStatus.RUNNING
            try:
                deleted = await find_deleted_profiles(context.target, session)
                if deleted:
                    context.add_finding("deleted_profiles", deleted)
                task.status = AgentStatus.COMPLETED
            except Exception as e:
                task.error = str(e)
                task.status = AgentStatus.FAILED

        return context

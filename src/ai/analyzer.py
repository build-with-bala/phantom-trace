"""AI-powered profile analysis and correlation."""

from src.ai.base import BaseAIProvider, AIResponse
from src.models import PersonProfile

SYSTEM_PROMPT = """You are an expert OSINT analyst. You analyze digital footprints
to build intelligence profiles. You identify patterns, correlations, and connections
across platforms. Be precise and factual. Only state what the evidence supports."""


class ProfileAnalyzer:
    """Use AI to analyze and correlate discovered profile data."""

    def __init__(self, provider: BaseAIProvider):
        self.provider = provider

    async def analyze_profile(self, profile: PersonProfile) -> dict:
        """Deep analysis of a discovered profile."""
        profile_summary = self._build_summary(profile)

        prompt = f"""Analyze this OSINT profile and provide intelligence assessment:

{profile_summary}

Provide analysis in these categories:
1. IDENTITY ASSESSMENT: Likely real identity based on cross-platform data
2. BEHAVIORAL PATTERNS: Online behavior patterns, posting times, interests
3. CONNECTIONS: Likely social/professional connections
4. RISK INDICATORS: Any security concerns or exposure risks
5. ADDITIONAL LEADS: Suggested next investigative steps
6. CONFIDENCE: Overall confidence in the profile correlation (low/medium/high)"""

        response = await self.provider.generate(prompt, system=SYSTEM_PROMPT)
        return {"analysis": response.content, "model": response.model, "usage": response.usage}

    async def correlate_aliases(self, username: str, found_sites: list[dict]) -> dict:
        """Use AI to suggest which aliases are likely the same person."""
        sites_text = "\n".join(f"- {s['site']}: {s.get('url', '')} (metadata: {s.get('metadata', {})})" for s in found_sites)

        prompt = f"""Given username "{username}" found on these platforms:

{sites_text}

1. Rate confidence (0-100) that all profiles belong to the same person
2. Identify any profiles that likely DON'T belong to the same person
3. Suggest additional usernames this person might use
4. Note any interesting cross-platform patterns"""

        response = await self.provider.generate(prompt, system=SYSTEM_PROMPT)
        return {"correlation": response.content, "model": response.model}

    async def generate_investigation_plan(self, profile: PersonProfile) -> dict:
        """Generate an investigation plan based on current findings."""
        summary = self._build_summary(profile)

        prompt = f"""Based on these OSINT findings, generate a structured investigation plan:

{summary}

Provide:
1. PRIORITY LEADS: Most promising leads to follow up on
2. DATA GAPS: What information is missing
3. RECOMMENDED TOOLS: Specific tools/techniques for next steps
4. OPSEC CONSIDERATIONS: How to investigate without detection
5. ESTIMATED EFFORT: Time and resources needed"""

        response = await self.provider.generate(prompt, system=SYSTEM_PROMPT)
        return {"plan": response.content, "model": response.model}

    def _build_summary(self, profile: PersonProfile) -> str:
        lines = [
            f"Target: {profile.query} (type: {profile.query_type})",
            f"Sites found: {profile.total_found}/{profile.total_checked}",
            f"Confidence: {profile.confidence_score:.0%}",
        ]
        if profile.real_name_guess:
            lines.append(f"Probable name: {profile.real_name_guess}")
        if profile.locations:
            lines.append(f"Locations: {', '.join(set(profile.locations))}")
        if profile.aliases:
            lines.append(f"Aliases: {', '.join(profile.aliases[:10])}")

        lines.append("\nDiscovered profiles:")
        for s in profile.sites_found:
            meta_str = ", ".join(f"{k}={v}" for k, v in (s.metadata or {}).items())
            lines.append(f"  - {s.site} ({s.category}): {s.url}" + (f" [{meta_str}]" if meta_str else ""))

        if profile.social_graph:
            lines.append("\nCross-references:")
            for u, sources in profile.social_graph.items():
                lines.append(f"  - @{u}: {', '.join(sources)}")

        return "\n".join(lines)

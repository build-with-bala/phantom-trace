"""Reasoning agent - chain-of-thought analysis for complex OSINT queries."""

import json
from src.agents.base import BaseAgent, AgentContext, AgentStatus
from src.ai.router import create_default_router

COT_SYSTEM = """You are an expert OSINT investigator using chain-of-thought reasoning.
Break down your analysis into clear logical steps. Show your reasoning process.
Consider multiple hypotheses and evaluate evidence for/against each."""

REASONING_SCHEMA = {
    "type": "object",
    "properties": {
        "hypotheses": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "hypothesis": {"type": "string"},
                    "evidence_for": {"type": "array", "items": {"type": "string"}},
                    "evidence_against": {"type": "array", "items": {"type": "string"}},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                },
            },
        },
        "conclusion": {"type": "string"},
        "next_steps": {"type": "array", "items": {"type": "string"}},
        "risk_assessment": {"type": "string"},
    },
}


class ReasoningAgent(BaseAgent):
    """Uses chain-of-thought prompting for deep analytical reasoning."""

    name = "reasoning_agent"
    description = "Chain-of-thought OSINT reasoning engine"

    def __init__(self, prefer_local: bool = True):
        super().__init__()
        self.prefer_local = prefer_local

    async def execute(self, context: AgentContext) -> AgentContext:
        router = create_default_router()
        await router.check_availability()

        prefer = "ollama" if self.prefer_local else None

        # Build comprehensive evidence summary
        evidence = self._compile_evidence(context)

        task = self.create_task("chain_of_thought_analysis")
        task.status = AgentStatus.RUNNING

        prompt = f"""Analyze the following OSINT evidence using chain-of-thought reasoning.

EVIDENCE:
{evidence}

INSTRUCTIONS:
1. List all hypotheses about the target's identity and digital footprint
2. For each hypothesis, list evidence FOR and AGAINST
3. Rate confidence for each hypothesis (0.0 - 1.0)
4. Provide an overall conclusion
5. Suggest concrete next investigative steps
6. Assess operational security risks

Think step by step. Be thorough but precise."""

        try:
            response = await router.generate(prompt, system=COT_SYSTEM, prefer=prefer)
            context.add_finding("reasoning", {
                "analysis": response.content,
                "model": response.model,
                "method": "chain_of_thought",
            })
            task.status = AgentStatus.COMPLETED
        except Exception as e:
            task.status = AgentStatus.FAILED
            task.error = str(e)
            context.add_finding("reasoning", {"error": str(e)})

        return context

    def _compile_evidence(self, context: AgentContext) -> str:
        lines = [f"Target: {context.target} (type: {context.target_type})"]

        # Scan results
        scan_data = context.findings.get("scan_results", [])
        if scan_data:
            found = scan_data[-1].get("found", [])
            lines.append(f"\nPlatforms found ({len(found)}):")
            for s in found:
                meta = s.get("metadata", {})
                meta_str = ", ".join(f"{k}={v}" for k, v in meta.items()) if meta else "none"
                lines.append(f"  - {s['site']} ({s['category']}): {s['url']} [meta: {meta_str}]")

        # Metadata correlations
        meta_list = context.findings.get("metadata", [])
        if meta_list:
            meta = meta_list[-1]
            if meta.get("probable_name"):
                lines.append(f"\nProbable name: {meta['probable_name']}")
            if meta.get("all_locations"):
                lines.append(f"Locations: {', '.join(set(meta['all_locations']))}")
            if meta.get("avatar_urls"):
                lines.append(f"Avatars found: {len(meta['avatar_urls'])}")

        # Social graph
        graph_data = context.findings.get("social_graph", [])
        if graph_data:
            cross_refs = graph_data[-1].get("cross_refs", {})
            if cross_refs:
                lines.append("\nCross-platform references:")
                for handle, sources in cross_refs.items():
                    lines.append(f"  @{handle}: {', '.join(sources)}")

        # Deep recon
        deep = context.findings.get("deep_recon", [])
        if deep:
            lines.append("\nAlias scan results:")
            for alias_data in deep:
                for alias, sites in alias_data.items():
                    lines.append(f"  @{alias}: found on {len(sites)} sites")

        return "\n".join(lines)

"""Pre-built investigation pipelines for common OSINT workflows."""

from src.agents.orchestrator import Orchestrator
from src.agents.base import AgentContext
from src.agents.recon_agent import ReconAgent
from src.agents.enrichment_agent import EnrichmentAgent
from src.agents.analysis_agent import AnalysisAgent
from src.agents.deep_recon_agent import DeepReconAgent
from src.agents.reasoning_agent import ReasoningAgent
from src.agents.intel_agent import IntelAgent
from src.agents.email_probe_agent import EmailProbeAgent
from src.agents.dorking_agent import DorkingAgent
from src.agents.report_agent import ReportAgent


def quick_scan_pipeline(show_progress: bool = True) -> Orchestrator:
    """Fast scan - recon + enrichment + report. No AI."""
    orch = Orchestrator(show_progress=show_progress)
    orch.add_stage(ReconAgent())
    orch.add_stage(EnrichmentAgent(), condition="has_scan_results")
    orch.add_stage(ReportAgent(), condition="has_findings")
    return orch


def standard_pipeline(show_progress: bool = True) -> Orchestrator:
    """Standard - recon + intel + enrichment + AI analysis + report."""
    orch = Orchestrator(show_progress=show_progress)
    orch.add_stage(ReconAgent())
    orch.add_stage(IntelAgent(), condition="has_scan_results")
    orch.add_stage(EnrichmentAgent(), condition="has_scan_results")
    orch.add_stage(AnalysisAgent(), condition="min_found:3")
    orch.add_stage(DorkingAgent(), condition="has_findings")
    orch.add_stage(ReportAgent(), condition="has_findings")
    return orch


def deep_pipeline(show_progress: bool = True) -> Orchestrator:
    """Deep - full pipeline: recon → intel → email probes → deep recon → reasoning → dorks → report."""
    orch = Orchestrator(show_progress=show_progress)
    orch.add_stage(ReconAgent())
    orch.add_stage(IntelAgent(), condition="has_scan_results")
    orch.add_stage(EmailProbeAgent(), condition="has_findings")
    orch.add_stage(EnrichmentAgent(), condition="has_scan_results")
    orch.add_stage(DeepReconAgent(), condition="min_found:2")
    orch.add_stage(ReasoningAgent(prefer_local=True), condition="has_scan_results")
    orch.add_stage(AnalysisAgent(), condition="min_found:3")
    orch.add_stage(DorkingAgent(), condition="has_findings")
    orch.add_stage(ReportAgent(), condition="has_findings")
    return orch


def stealth_pipeline(show_progress: bool = True) -> Orchestrator:
    """Stealth - slower scanning, local AI only, no email probing."""
    orch = Orchestrator(show_progress=show_progress)
    orch.add_stage(ReconAgent(max_concurrent=10, timeout=30))
    orch.add_stage(IntelAgent(), condition="has_scan_results")
    orch.add_stage(EnrichmentAgent(), condition="has_scan_results")
    orch.add_stage(ReasoningAgent(prefer_local=True), condition="min_found:1")
    orch.add_stage(ReportAgent(formats=["json"]), condition="has_findings")
    return orch


def email_pipeline(show_progress: bool = True) -> Orchestrator:
    """Email-focused investigation pipeline."""
    orch = Orchestrator(show_progress=show_progress)
    orch.add_stage(EmailProbeAgent())
    orch.add_stage(ReconAgent())  # Scan username from email prefix
    orch.add_stage(IntelAgent(), condition="has_scan_results")
    orch.add_stage(EnrichmentAgent(), condition="has_findings")
    orch.add_stage(DorkingAgent(), condition="has_findings")
    orch.add_stage(ReportAgent(), condition="has_findings")
    return orch


def create_context(target: str, target_type: str = "username") -> AgentContext:
    return AgentContext(target=target, target_type=target_type)

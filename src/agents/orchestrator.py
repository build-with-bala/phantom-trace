"""Agent orchestrator - coordinates multi-agent OSINT pipelines."""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box

from src.agents.base import BaseAgent, AgentContext, AgentStatus

logger = logging.getLogger(__name__)
console = Console()


@dataclass
class PipelineStage:
    """A stage in the orchestration pipeline."""

    agent: BaseAgent
    parallel: bool = False  # Can run in parallel with previous stage
    condition: str | None = None  # Run only if condition met
    timeout: float = 120.0


@dataclass
class PipelineResult:
    """Result of a full pipeline execution."""

    context: AgentContext
    stages_completed: list[str] = field(default_factory=list)
    stages_failed: list[str] = field(default_factory=list)
    total_duration: float = 0.0
    started_at: datetime | None = None
    completed_at: datetime | None = None

    @property
    def success(self) -> bool:
        return len(self.stages_failed) == 0


class Orchestrator:
    """Coordinates agent execution with dependency management and error handling."""

    def __init__(self, show_progress: bool = True):
        self.stages: list[PipelineStage] = []
        self.show_progress = show_progress

    def add_stage(self, agent: BaseAgent, parallel: bool = False, condition: str | None = None, timeout: float = 120.0):
        """Add an agent as a pipeline stage."""
        self.stages.append(PipelineStage(agent=agent, parallel=parallel, condition=condition, timeout=timeout))
        return self

    def _should_run(self, stage: PipelineStage, context: AgentContext) -> bool:
        """Check if a stage should run based on its condition."""
        if stage.condition is None:
            return True

        if stage.condition == "has_findings":
            return bool(context.findings)
        elif stage.condition == "has_scan_results":
            return bool(context.findings.get("scan_results"))
        elif stage.condition.startswith("min_found:"):
            threshold = int(stage.condition.split(":")[1])
            return context.metadata.get("total_found", 0) >= threshold

        return True

    async def execute(self, context: AgentContext) -> PipelineResult:
        """Execute the full pipeline."""
        result = PipelineResult(context=context, started_at=datetime.now())
        start_time = time.monotonic()

        if self.show_progress:
            console.print(Panel(
                f"[bold]Target:[/bold] {context.target}\n"
                f"[bold]Type:[/bold] {context.target_type}\n"
                f"[bold]Stages:[/bold] {len(self.stages)}",
                title="[bold cyan]Pipeline Starting[/bold cyan]",
                border_style="cyan",
            ))

        # Group parallel stages
        stage_groups = self._group_stages()

        for group in stage_groups:
            if len(group) == 1:
                stage = group[0]
                if not self._should_run(stage, context):
                    if self.show_progress:
                        console.print(f"  [dim]⊘ Skipping {stage.agent.name} (condition not met)[/dim]")
                    continue

                if self.show_progress:
                    console.print(f"\n  [bold cyan]▶ {stage.agent.name}[/bold cyan] - {stage.agent.description}")

                try:
                    context = await asyncio.wait_for(stage.agent.run(context), timeout=stage.timeout)
                    result.stages_completed.append(stage.agent.name)
                    if self.show_progress:
                        console.print(f"  [bold green]✓ {stage.agent.name}[/bold green] completed")
                except asyncio.TimeoutError:
                    result.stages_failed.append(stage.agent.name)
                    if self.show_progress:
                        console.print(f"  [bold red]✗ {stage.agent.name}[/bold red] timed out")
                except Exception as e:
                    result.stages_failed.append(stage.agent.name)
                    if self.show_progress:
                        console.print(f"  [bold red]✗ {stage.agent.name}[/bold red] failed: {e}")
            else:
                # Run parallel stages
                if self.show_progress:
                    names = ", ".join(s.agent.name for s in group)
                    console.print(f"\n  [bold cyan]▶▶ Parallel:[/bold cyan] {names}")

                tasks = []
                for stage in group:
                    if self._should_run(stage, context):
                        tasks.append(asyncio.wait_for(stage.agent.run(context), timeout=stage.timeout))

                results_list = await asyncio.gather(*tasks, return_exceptions=True)
                for stage, res in zip(group, results_list):
                    if isinstance(res, Exception):
                        result.stages_failed.append(stage.agent.name)
                        if self.show_progress:
                            console.print(f"  [red]✗ {stage.agent.name}[/red] failed: {res}")
                    else:
                        result.stages_completed.append(stage.agent.name)
                        if self.show_progress:
                            console.print(f"  [green]✓ {stage.agent.name}[/green] completed")

        result.completed_at = datetime.now()
        result.total_duration = time.monotonic() - start_time

        if self.show_progress:
            self._show_summary(result)

        return result

    def _group_stages(self) -> list[list[PipelineStage]]:
        """Group consecutive parallel stages together."""
        groups: list[list[PipelineStage]] = []
        current_group: list[PipelineStage] = []

        for stage in self.stages:
            if stage.parallel and current_group:
                current_group.append(stage)
            else:
                if current_group:
                    groups.append(current_group)
                current_group = [stage]

        if current_group:
            groups.append(current_group)
        return groups

    def _show_summary(self, result: PipelineResult):
        table = Table(title="Pipeline Summary", box=box.ROUNDED)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        table.add_row("Duration", f"{result.total_duration:.1f}s")
        table.add_row("Completed", str(len(result.stages_completed)))
        table.add_row("Failed", str(len(result.stages_failed)))
        table.add_row("Status", "[green]SUCCESS[/green]" if result.success else "[red]FAILED[/red]")

        findings = result.context.findings
        if "scan_results" in findings:
            scan = findings["scan_results"][-1]
            table.add_row("Profiles Found", str(len(scan.get("found", []))))

        console.print(table)

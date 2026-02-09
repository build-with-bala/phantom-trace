"""Tests for pipeline orchestrator."""

import asyncio
import pytest
from src.agents.base import BaseAgent, AgentContext, AgentStatus
from src.agents.orchestrator import Orchestrator


class CountingAgent(BaseAgent):
    name = "counter"
    description = "Counts executions"
    call_count = 0

    async def execute(self, context: AgentContext) -> AgentContext:
        CountingAgent.call_count += 1
        context.add_finding("counter", {"count": CountingAgent.call_count})
        context.metadata["total_found"] = CountingAgent.call_count
        return context


@pytest.mark.asyncio
async def test_simple_pipeline():
    CountingAgent.call_count = 0
    orch = Orchestrator(show_progress=False)
    orch.add_stage(CountingAgent())
    orch.add_stage(CountingAgent())

    ctx = AgentContext(target="test", target_type="username")
    result = await orch.execute(ctx)

    assert result.success
    assert len(result.stages_completed) == 2


@pytest.mark.asyncio
async def test_conditional_stage():
    orch = Orchestrator(show_progress=False)
    orch.add_stage(CountingAgent())
    orch.add_stage(CountingAgent(), condition="min_found:100")  # Should skip

    ctx = AgentContext(target="test", target_type="username")
    result = await orch.execute(ctx)

    assert result.success
    assert len(result.stages_completed) == 1  # Only first ran

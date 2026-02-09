"""Tests for agent framework."""

import asyncio
import pytest
from src.agents.base import BaseAgent, AgentContext, AgentStatus, AgentTask, TaskPriority


class MockAgent(BaseAgent):
    name = "mock_agent"
    description = "Test agent"

    async def execute(self, context: AgentContext) -> AgentContext:
        context.add_finding("test", {"result": "ok"})
        return context


class FailingAgent(BaseAgent):
    name = "failing_agent"
    description = "Always fails"

    async def execute(self, context: AgentContext) -> AgentContext:
        raise RuntimeError("Intentional failure")


def test_agent_task():
    task = AgentTask(name="test_task", priority=TaskPriority.HIGH)
    assert task.status == AgentStatus.IDLE
    assert task.priority == TaskPriority.HIGH
    assert task.duration is None


def test_agent_context():
    ctx = AgentContext(target="testuser", target_type="username")
    ctx.add_finding("scan", {"found": True})
    assert "scan" in ctx.findings
    assert len(ctx.findings["scan"]) == 1


@pytest.mark.asyncio
async def test_mock_agent():
    agent = MockAgent()
    ctx = AgentContext(target="test", target_type="username")
    result = await agent.run(ctx)
    assert agent.status == AgentStatus.COMPLETED
    assert "test" in result.findings
    assert "mock_agent" in result.tasks_completed


@pytest.mark.asyncio
async def test_failing_agent():
    agent = FailingAgent()
    ctx = AgentContext(target="test", target_type="username")
    with pytest.raises(RuntimeError):
        await agent.run(ctx)
    assert agent.status == AgentStatus.FAILED

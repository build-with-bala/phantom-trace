"""Base agent framework for OSINT task orchestration."""

import asyncio
import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING = "waiting"


class TaskPriority(Enum):
    LOW = 0
    MEDIUM = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class AgentTask:
    """A discrete unit of work for an agent."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    priority: TaskPriority = TaskPriority.MEDIUM
    status: AgentStatus = AgentStatus.IDLE
    input_data: dict[str, Any] = field(default_factory=dict)
    output_data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    dependencies: list[str] = field(default_factory=list)

    @property
    def duration(self) -> float | None:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


@dataclass
class AgentContext:
    """Shared context passed between agents in a pipeline."""

    target: str
    target_type: str  # username, email, phone, name
    findings: dict[str, Any] = field(default_factory=dict)
    tasks_completed: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_finding(self, category: str, data: Any):
        if category not in self.findings:
            self.findings[category] = []
        self.findings[category].append(data)


class BaseAgent(ABC):
    """Base class for all OSINT agents."""

    name: str = "base_agent"
    description: str = "Base agent"

    def __init__(self):
        self.status = AgentStatus.IDLE
        self.tasks: list[AgentTask] = []

    @abstractmethod
    async def execute(self, context: AgentContext) -> AgentContext:
        """Execute the agent's primary function."""
        pass

    async def run(self, context: AgentContext) -> AgentContext:
        """Run the agent with status tracking."""
        self.status = AgentStatus.RUNNING
        logger.info(f"Agent [{self.name}] started")

        try:
            result = await self.execute(context)
            self.status = AgentStatus.COMPLETED
            context.tasks_completed.append(self.name)
            logger.info(f"Agent [{self.name}] completed")
            return result
        except Exception as e:
            self.status = AgentStatus.FAILED
            logger.error(f"Agent [{self.name}] failed: {e}")
            raise

    def create_task(self, name: str, **kwargs) -> AgentTask:
        task = AgentTask(name=name, **kwargs)
        self.tasks.append(task)
        return task

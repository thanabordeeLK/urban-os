"""Base classes for Urban OS multi-agent workflow."""
from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass
class AgentResult:
    agent_name: str
    summary: str
    evidence: dict | None = None
    confidence: str = "medium"

    def to_dict(self) -> dict:
        return asdict(self)


class BaseAgent:
    name = "Base Agent"

    def run(self, task: str, context: dict) -> AgentResult:
        raise NotImplementedError

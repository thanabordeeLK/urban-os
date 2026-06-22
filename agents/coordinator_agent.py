"""Coordinator Agent / Smart City CEO."""
from __future__ import annotations

from agents.gis_agent import GISAgent
from agents.gemini_agent import GeminiAgent
from agents.gpt_agent import GPTAgent
from agents.domain_agents import (
    create_urban_agent,
    create_traffic_agent,
    create_economic_agent,
    create_environment_agent,
)
from agents.report_agent import ReportAgent


class CoordinatorAgent:
    """ควบคุม workflow: GIS evidence first -> specialist agents -> report."""

    def __init__(self):
        self.gis_agent = GISAgent()
        self.gpt_agent = GPTAgent()
        self.gemini_agent = GeminiAgent()
        self.domain_agents = {
            "Urban Agent": create_urban_agent(),
            "Traffic Agent": create_traffic_agent(),
            "Economic Agent": create_economic_agent(),
            "Environment Agent": create_environment_agent(),
            "Gemini Vision Agent": self.gemini_agent,
            "GPT Planning Agent": self.gpt_agent,
        }
        self.report_agent = ReportAgent()

    def run(self, task: str, context: dict, selected_agents: list[str]) -> dict:
        outputs: dict[str, dict] = {}

        # 1) GIS always runs first. This is the evidence anchor.
        gis_result = self.gis_agent.run(task, context)
        outputs[gis_result.agent_name] = gis_result.to_dict()

        enriched_context = dict(context)
        enriched_context["gis_evidence"] = gis_result.evidence

        # 2) Domain / model agents.
        for agent_name in selected_agents:
            agent = self.domain_agents.get(agent_name)
            if not agent:
                continue

            result = agent.run(task, enriched_context)
            outputs[result.agent_name] = result.to_dict()

        # 3) Final report.
        report_context = dict(enriched_context)
        report_context["agent_outputs"] = outputs
        report_result = self.report_agent.run(task, report_context)
        outputs[report_result.agent_name] = report_result.to_dict()

        return outputs

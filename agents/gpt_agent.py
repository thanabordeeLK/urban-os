"""GPT Planning Agent."""
from __future__ import annotations

from agents.base_agent import BaseAgent, AgentResult
from llm.openai_client import ask_openai


class GPTAgent(BaseAgent):
    name = "GPT Planning Agent"

    def run(self, task: str, context: dict) -> AgentResult:
        prompt = f"""
        คุณคือ GPT Planning Agent สำหรับ Urban OS
        ใช้หลักฐานจาก GIS Agent และข้อมูลเฉพาะพื้นที่เพื่อสร้างข้อเสนอเชิงผังเมือง

        คำถาม/เป้าหมาย:
        {task}

        บริบท:
        {context}

        กรุณาตอบ:
        - Planning diagnosis
        - Scenario ที่เหมาะสม
        - Policy / zoning implication
        - ข้อเสนอที่ทำได้จริง 3-5 ข้อ
        - data gap ที่ต้องตรวจสอบภาคสนาม
        """
        return AgentResult(
            agent_name=self.name,
            summary=ask_openai(prompt=prompt, temperature=0.2),
            confidence="medium",
        )

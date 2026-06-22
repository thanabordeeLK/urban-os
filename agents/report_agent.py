"""Report Agent: combine all agent outputs into an executive planning report."""
from __future__ import annotations

from agents.base_agent import BaseAgent, AgentResult
from llm.openai_client import ask_openai


class ReportAgent(BaseAgent):
    name = "Report Agent"

    def run(self, task: str, context: dict) -> AgentResult:
        prompt = f"""
        คุณคือ Report Agent สำหรับผู้บริหารเมือง
        รวมผลจาก Agent ทั้งหมดให้เป็นรายงานภาษาไทยที่ใช้ตัดสินใจได้

        เป้าหมายผู้ใช้:
        {task}

        ผลจาก Agent:
        {context.get("agent_outputs", {})}

        เขียนรายงานโดยใช้รูปแบบ:
        # Executive Summary
        # Key Spatial Evidence
        # Planning Diagnosis
        # Recommended Scenario
        # Action Plan
        # Data Gaps / Field Survey Needed

        กติกา:
        - แยกชัดระหว่างหลักฐานเชิงพื้นที่กับข้อเสนอของ AI
        - ถ้าข้อมูลไม่พอ ให้เขียนว่าไม่พอ ไม่ต้องเดา
        - ใช้ภาษาทางการ กระชับ และเหมาะกับงานผังเมือง
        """
        answer = ask_openai(prompt=prompt, temperature=0.2)
        return AgentResult(
            agent_name=self.name,
            summary=answer,
            evidence=None,
            confidence="medium",
        )

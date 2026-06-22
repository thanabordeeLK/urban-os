"""Gemini Vision/Spatial Agent.

เวอร์ชันนี้ส่งบริบทเชิงพื้นที่แบบ text ก่อน
ขั้นต่อไปสามารถเพิ่ม map screenshot / satellite image เข้า Gemini ได้
"""
from __future__ import annotations

from agents.base_agent import BaseAgent, AgentResult
from llm.gemini_client import ask_gemini


class GeminiAgent(BaseAgent):
    name = "Gemini Vision Agent"

    def run(self, task: str, context: dict) -> AgentResult:
        prompt = f"""
        คุณคือ Gemini Vision/Spatial Agent
        ช่วยตีความ pattern เชิงพื้นที่จากข้อมูล GIS/GEE ต่อไปนี้

        เป้าหมาย:
        {task}

        บริบท:
        {context}

        จงวิเคราะห์:
        1) Spatial pattern ที่ควรจับตา
        2) จุดที่ควรตรวจสอบจากภาพถ่ายดาวเทียมหรือ field survey
        3) ความเสี่ยงของการตีความผิด เช่น ดินโล่งคล้ายเมือง น้ำแห้งคล้ายสิ่งปลูกสร้าง
        4) ข้อเสนอการใช้ข้อมูลภาพ/remote sensing เพิ่มเติม
        """
        return AgentResult(
            agent_name=self.name,
            summary=ask_gemini(prompt=prompt, temperature=0.2),
            confidence="medium",
        )

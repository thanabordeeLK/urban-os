"""Domain specialist agents powered mainly by GPT."""
from __future__ import annotations

from agents.base_agent import BaseAgent, AgentResult
from llm.openai_client import ask_openai


PLANNER_SYSTEM = """
คุณคือผู้เชี่ยวชาญด้านผังเมืองไทยและ Smart City
วิเคราะห์อย่างมืออาชีพ ใช้หลักฐานเชิงพื้นที่ก่อนเสมอ
แยกให้ชัดว่าอะไรเป็นข้อมูลจริง อะไรเป็นข้อเสนอเชิงวิเคราะห์
ห้ามเดาข้อมูลเฉพาะพื้นที่ถ้าไม่มีหลักฐาน ให้ระบุเป็น data gap
"""


class DomainAgent(BaseAgent):
    def __init__(self, name: str, role_prompt: str):
        self.name = name
        self.role_prompt = role_prompt

    def run(self, task: str, context: dict) -> AgentResult:
        prompt = f"""
        บทบาทของคุณ:
        {self.role_prompt}

        คำถาม/เป้าหมายของผู้ใช้:
        {task}

        บริบทและหลักฐาน:
        {context}

        จงตอบเป็นหัวข้อ:
        1) ข้อค้นพบหลัก
        2) ความเสี่ยง/ข้อจำกัด
        3) ข้อเสนอเชิงปฏิบัติ
        4) ข้อมูลที่ควรสำรวจเพิ่ม
        """
        answer = ask_openai(
            prompt=prompt,
            system_prompt=PLANNER_SYSTEM,
            temperature=0.2,
        )
        return AgentResult(
            agent_name=self.name,
            summary=answer,
            evidence=None,
            confidence="medium",
        )


def create_urban_agent() -> DomainAgent:
    return DomainAgent(
        "Urban Agent",
        "วิเคราะห์ land use, zoning, urban form, settlement pattern, ความเหมาะสมในการพัฒนาเมือง และการจัดรูปที่ดิน",
    )


def create_traffic_agent() -> DomainAgent:
    return DomainAgent(
        "Traffic Agent",
        "วิเคราะห์โครงข่ายคมนาคม การเข้าถึง จุดเชื่อมต่อ road hierarchy, TOD, walkability และผลกระทบการจราจร",
    )


def create_economic_agent() -> DomainAgent:
    return DomainAgent(
        "Economic Agent",
        "วิเคราะห์ศักยภาพเศรษฐกิจเมือง มูลค่าที่ดิน กลไกลงทุน value capture และผลประโยชน์ต่อชุมชน",
    )


def create_environment_agent() -> DomainAgent:
    return DomainAgent(
        "Environment Agent",
        "วิเคราะห์น้ำท่วม แหล่งน้ำ พื้นที่สีเขียว heat risk ระบบนิเวศ และ Nature-based Solutions",
    )

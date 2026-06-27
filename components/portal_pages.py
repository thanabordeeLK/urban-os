from __future__ import annotations

import json
from datetime import datetime

import pandas as pd
import streamlit as st

try:
    from llm.openai_client import ask_openai
except Exception:
    ask_openai = None


def _safe_df(key: str) -> pd.DataFrame | None:
    value = st.session_state.get(key)
    if isinstance(value, pd.DataFrame):
        return value
    return None


def _role() -> str:
    return st.session_state.get("urban_os_user_role", "ผู้ใช้ทั่วไป")


def _metric_row() -> None:
    summary = st.session_state.get("suitability_summary") or {}
    heat = st.session_state.get("uhi_heat_summary") or {}
    ranking_df = _safe_df("candidate_ranking_df")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("พื้นที่เหมาะสมสูง", f"{summary.get('development_candidate_rai', 0):,.0f} ไร่")
    c2.metric("สัดส่วน Candidate", f"{summary.get('candidate_percent', 0):.1f}%")
    c3.metric("Heat Hotspot", f"{heat.get('hotspot_percent', 0):.1f}%")
    c4.metric("Candidate Ranked", f"{0 if ranking_df is None else len(ranking_df):,}")


def render_executive_portal(*, gee_ready: bool, selected_province: str, selected_district: str, is_whole_country: bool) -> None:
    st.markdown("### 🏙️ ผู้บริหารเมือง / Public Executive Portal")
    st.caption("หน้าสรุปสำหรับผู้บริหารเมืองและผู้ใช้ทั่วไป เน้นดูข้อมูล อ่านรายงาน และดูแผนที่สาธารณะ")

    if not gee_ready:
        st.warning("GEE ยังไม่พร้อม จะแสดงเฉพาะข้อมูลสรุป/รายงานที่ไม่ต้องประมวลผลใหม่")

    _metric_row()

    st.markdown("#### สิ่งที่ทำได้ในโหมดผู้ใช้ทั่วไป")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info("ดูรายงานสรุปเมือง / Planning Report")
    with col2:
        st.info("ดูแผนที่สาธารณะเมื่อระบบ GEE พร้อม")
    with col3:
        st.info("ถามข้อมูลกฎหมายผังเมืองแบบทั่วไป")

    st.markdown("#### คำแนะนำ")
    st.write(
        "หากต้องการวิเคราะห์พื้นที่ นำเข้า GIS หรือสร้างรายงานเชิงลึก ให้เข้าสู่ระบบเป็นสมาชิก / วิเคราะห์ได้"
    )


def render_research_portal(*, gee_ready: bool) -> None:
    st.markdown("### 📊 นักวิเคราะห์ วิจัย / Analysis Workspace")
    st.caption("ศูนย์รวมเครื่องมือสำหรับสมาชิกที่ต้องการวิเคราะห์ข้อมูลเมือง")

    if not gee_ready:
        st.warning("GEE ยังไม่พร้อม: Suitability / UHI / General Plan จะยังใช้งานไม่ได้จนกว่าจะตั้งค่า Service Account")

    st.markdown("#### Workflow แนะนำ")
    st.markdown(
        """
1. เลือกพื้นที่ศึกษา
2. Run Suitability Analysis
3. Run Urban Heat Island หากต้องการวิเคราะห์ความร้อนเมือง
4. Generate Candidate Area
5. Candidate Ranking
6. AI Recommendation
7. Planning Report
"""
    )

    st.markdown("#### เครื่องมือหลัก")
    c1, c2, c3 = st.columns(3)
    c1.success("Suitability Analysis")
    c2.success("Urban Heat Island")
    c3.success("Candidate Ranking / AI Recommendation")


def render_landuse_portal(*, gee_ready: bool) -> None:
    st.markdown("### 🗺️ ตรวจสอบการใช้ประโยชน์ที่ดิน / Land Use Monitoring")
    st.caption("พื้นที่ทำงานสำหรับนำเข้าข้อมูล GIS ตรวจสอบ zoning/land use และใช้ข้อมูลเป็นปัจจัยวิเคราะห์")

    st.markdown("#### Workflow แนะนำ")
    st.markdown(
        """
1. Upload Shapefile / GeoJSON / KML / CSV ใน Import Wizard
2. Preview geometry และตรวจ attribute
3. Import to PostGIS หากต้องการเก็บถาวร
4. เปิด Imported Layer Overlay
5. ใช้ Imported Layer ใน Suitability Criteria
6. Export Map / Report
"""
    )

    if not gee_ready:
        st.info("ยังสามารถใช้ Import Wizard / PostGIS / Overlay บางส่วนได้ แม้ GEE ยังไม่พร้อม")


def _rule_based_legal_answer(question: str, member: bool = False) -> str:
    q = question.lower()

    if not question.strip():
        return "กรุณาพิมพ์คำถามเกี่ยวกับกฎหมายผังเมือง การใช้ประโยชน์ที่ดิน หรือขั้นตอนวิเคราะห์พื้นที่"

    if "ผังเมือง" in q or "zoning" in q or "โซน" in q:
        base = (
            "การตรวจสอบข้อกำหนดผังเมืองควรเริ่มจากตรวจเขตผังเมืองรวม สี/ประเภทการใช้ประโยชน์ที่ดิน "
            "ข้อกำหนดอาคาร ความหนาแน่น ระยะร่น และข้อจำกัดเฉพาะพื้นที่ "
        )
    elif "ที่ดิน" in q or "ใช้ประโยชน์" in q:
        base = (
            "การใช้ประโยชน์ที่ดินควรตรวจทั้งสภาพการใช้จริง เอกสารสิทธิ์ ข้อกำหนดผังเมือง "
            "พื้นที่เสี่ยงภัย และข้อจำกัดด้านสิ่งแวดล้อมก่อนตัดสินใจพัฒนา "
        )
    elif "กฎหมาย" in q or "พรบ" in q:
        base = (
            "ประเด็นกฎหมายควรอ้างอิงกฎหมายและประกาศที่มีผลใช้บังคับล่าสุด พร้อมตรวจสอบกับหน่วยงานเจ้าของอำนาจ "
            "เช่น องค์กรปกครองส่วนท้องถิ่น โยธาธิการและผังเมือง หรือหน่วยงานสิ่งแวดล้อม "
        )
    else:
        base = (
            "คำถามนี้ควรพิจารณาร่วมกับข้อมูลพื้นที่จริง ผังเมืองที่มีผลใช้บังคับ ข้อจำกัดด้านสิ่งแวดล้อม "
            "และข้อเท็จจริงของโครงการ "
        )

    if member:
        base += "ในโหมดสมาชิก สามารถนำเข้าชั้นข้อมูล zoning/land use แล้วเชื่อมกับ Suitability, Candidate Ranking และ AI Recommendation เพื่อสร้างข้อเสนอเชิงผังเมืองได้"
    else:
        base += "สำหรับผู้ใช้ทั่วไป คำตอบนี้เป็นข้อมูลเบื้องต้น ไม่ใช่คำวินิจฉัยทางกฎหมาย"

    return base


def render_legal_planning_chat(*, is_member: bool = False) -> None:
    st.markdown("### ⚖️ พูดคุยข้อกฎหมายผังเมือง")
    st.caption("ถาม-ตอบกฎหมายผังเมือง การใช้ประโยชน์ที่ดิน และข้อควรระวังเชิงพื้นที่")

    question = st.text_area(
        "พิมพ์คำถาม",
        value=st.session_state.get("legal_chat_question", ""),
        height=120,
        key="legal_chat_question",
        placeholder="เช่น พื้นที่สีเขียวพัฒนาอาคารได้หรือไม่ / ต้องตรวจอะไรบ้างก่อนเปลี่ยนการใช้ประโยชน์ที่ดิน",
    )

    use_gpt = False
    if is_member:
        use_gpt = st.checkbox(
            "ใช้ GPT Legal/Planning Assistant",
            value=False,
            key="legal_chat_use_gpt",
            help="ต้องตั้งค่า OPENAI_API_KEY ก่อน",
        )

    if st.button("ตอบคำถาม", use_container_width=True, key="legal_chat_answer_btn"):
        answer = _rule_based_legal_answer(question, member=is_member)

        if use_gpt and ask_openai is not None:
            prompt = f"""
โปรดตอบคำถามกฎหมายผังเมืองภาษาไทยแบบระมัดระวัง ไม่ให้เป็นคำวินิจฉัยทางกฎหมาย
ให้ระบุขั้นตอนตรวจสอบ ข้อมูลที่ต้องใช้ และข้อควรปรึกษาหน่วยงานรัฐ

คำถาม:
{question}

บริบทระบบ:
role={_role()}
time={datetime.now().isoformat()}
"""
            ai_answer = ask_openai(
                prompt=prompt,
                system_prompt="You are a Thai urban planning legal assistant. Provide cautious planning/legal guidance, not legal judgment.",
                temperature=0.2,
            )
            answer = ai_answer

        st.session_state["legal_chat_last_answer"] = answer

    last = st.session_state.get("legal_chat_last_answer")
    if last:
        st.markdown("#### คำตอบ")
        st.info(last)

    st.caption(
        "หมายเหตุ: คำตอบเป็นข้อมูลเบื้องต้น ต้องตรวจเอกสารทางกฎหมายและปรึกษาหน่วยงานที่เกี่ยวข้องก่อนใช้ประกอบการตัดสินใจ"
    )

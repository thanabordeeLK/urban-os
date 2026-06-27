from __future__ import annotations

import pandas as pd
import streamlit as st

from config.external_apps import build_external_url, external_apps_status


def _safe_df(key: str) -> pd.DataFrame | None:
    value = st.session_state.get(key)
    if isinstance(value, pd.DataFrame):
        return value
    return None


def _role() -> str:
    return st.session_state.get("urban_os_user_role", "ผู้ใช้ทั่วไป")


def _role_slug() -> str:
    role = _role()
    if "ผู้ดูแล" in role:
        return "admin"
    if "สมาชิก" in role:
        return "member"
    return "public"


def _metric_row() -> None:
    summary = st.session_state.get("suitability_summary") or {}
    heat = st.session_state.get("uhi_heat_summary") or {}
    ranking_df = _safe_df("candidate_ranking_df")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("พื้นที่เหมาะสมสูง", f"{summary.get('development_candidate_rai', 0):,.0f} ไร่")
    c2.metric("สัดส่วน Candidate", f"{summary.get('candidate_percent', 0):.1f}%")
    c3.metric("Heat Hotspot", f"{heat.get('hotspot_percent', 0):.1f}%")
    c4.metric("Candidate Ranked", f"{0 if ranking_df is None else len(ranking_df):,}")


def _render_external_launcher(
    *,
    title: str,
    caption: str,
    app_key: str,
    portal: str,
    role: str | None = None,
    button_label: str = "เปิดแอป",
    expected_repo: str = "",
    local_hint: str = "",
) -> None:
    st.markdown(f"### {title}")
    st.caption(caption)

    role = role or _role_slug()
    app_url = build_external_url(app_key, role=role, portal=portal)

    if app_url:
        st.link_button(button_label, app_url, use_container_width=True)
        st.code(app_url, language="text")
    else:
        st.warning("ยังไม่ได้ตั้งค่า URL ของแอปภายนอกใน Streamlit Secrets / environment")
        st.markdown("#### ตั้งค่า Secrets")
        if app_key == "landuse_checker":
            st.code('LANDUSE_APP_URL = "https://your-landuse-checker.streamlit.app"', language="toml")
        elif app_key == "planning_law_chat":
            st.code('LEGAL_CHAT_APP_URL = "https://your-planning-law-chat.streamlit.app"', language="toml")
        else:
            st.code(f'{app_key.upper()}_URL = "https://your-app-url"', language="toml")

    if expected_repo:
        st.markdown("#### Repo / App ที่ควรแยก")
        st.info(expected_repo)

    if local_hint:
        st.markdown("#### Local development")
        st.code(local_hint, language="text")


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
        st.info("ถามข้อมูลกฎหมายผังเมืองแบบทั่วไปผ่านแอป Legal Chat")

    st.markdown("#### เชื่อมไปยังแอปหลัก")
    portal_home = build_external_url("portal_home", role=_role_slug(), portal="executive")
    if portal_home:
        st.link_button("กลับหน้า USDC / Urban OS Portal", portal_home, use_container_width=True)

    st.write("หากต้องการวิเคราะห์พื้นที่ นำเข้า GIS หรือสร้างรายงานเชิงลึก ให้เข้าสู่ระบบเป็นสมาชิก / วิเคราะห์ได้")


def render_research_portal(*, gee_ready: bool) -> None:
    st.markdown("### 📊 นักวิเคราะห์ วิจัย / Analysis Workspace")
    st.caption("ศูนย์รวมเครื่องมือสำหรับสมาชิกที่ต้องการวิเคราะห์ข้อมูลเมืองใน Urban OS Core")

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

    st.markdown("#### เครื่องมือหลักใน Urban OS Core")
    c1, c2, c3 = st.columns(3)
    c1.success("Suitability Analysis")
    c2.success("Urban Heat Island")
    c3.success("Candidate Ranking / AI Recommendation")

    st.markdown("#### แอปเฉพาะเรื่อง")
    c4, c5 = st.columns(2)
    with c4:
        landuse_url = build_external_url("landuse_checker", role=_role_slug(), portal="landuse")
        if landuse_url:
            st.link_button("เปิด Land Use Checker", landuse_url, use_container_width=True)
        else:
            st.info("ยังไม่ได้ตั้งค่า LANDUSE_APP_URL")
    with c5:
        legal_url = build_external_url("planning_law_chat", role=_role_slug(), portal="legal")
        if legal_url:
            st.link_button("เปิด Planning Law Chat", legal_url, use_container_width=True)
        else:
            st.info("ยังไม่ได้ตั้งค่า LEGAL_CHAT_APP_URL")


def render_landuse_portal(*, gee_ready: bool) -> None:
    _render_external_launcher(
        title="🗺️ ตรวจสอบการใช้ประโยชน์ที่ดิน / Land Use Checker",
        caption=(
            "ฟังก์ชันนี้ถูกแยกออกเป็นแอปเฉพาะเรื่อง เพื่อให้ตรวจ parcel, zoning, land use, "
            "ข้อจำกัดรายแปลง และรายงาน Land Use Check ได้ชัดเจนกว่า Urban OS Core"
        ),
        app_key="landuse_checker",
        portal="landuse",
        role=_role_slug(),
        button_label="เปิด Land Use Checker",
        expected_repo="แนะนำ repo: thanabordeeLK/usdc-landuse-checker",
        local_hint="Land Use Checker local: http://localhost:8502\nUrban OS Core local: http://localhost:8501",
    )

    st.markdown("#### ขอบเขตงานของแอปนี้")
    st.markdown(
        """
- ค้นหา/อัปโหลดแปลงที่ดิน
- ตรวจ zoning / land use
- ตรวจพื้นที่เสี่ยง / พื้นที่กันออก
- สรุปข้อจำกัดรายแปลง
- ออกรายงาน Land Use Check
"""
    )


def render_legal_planning_chat(*, is_member: bool = False) -> None:
    _render_external_launcher(
        title="⚖️ พูดคุยข้อกฎหมายผังเมือง / Planning Law Chat",
        caption=(
            "ฟังก์ชันนี้ถูกแยกออกเป็นแอปเฉพาะเรื่อง เพื่อให้จัดการ legal knowledge base, "
            "เอกสารกฎหมาย, public/member chat quota และ legal memo ได้ปลอดภัยกว่า"
        ),
        app_key="planning_law_chat",
        portal="legal",
        role=_role_slug(),
        button_label="เปิด Planning Law Chat",
        expected_repo="แนะนำ repo: thanabordeeLK/usdc-planning-law-chat",
        local_hint="Planning Law Chat local: http://localhost:8503\nUrban OS Core local: http://localhost:8501",
    )

    st.markdown("#### รูปแบบสิทธิ์ที่แนะนำในแอป Legal Chat")
    if is_member:
        st.success("สมาชิก: ใช้ Legal Assistant แบบเต็ม เช่น วิเคราะห์เอกสาร สร้าง planning memo และเชื่อมกับ project/zoning")
    else:
        st.info("ผู้ใช้ทั่วไป: ถาม-ตอบทั่วไป จำกัดจำนวนครั้ง และไม่วิเคราะห์เอกสารเฉพาะโครงการ")

    st.caption("หมายเหตุ: คำตอบด้านกฎหมายเป็นข้อมูลเบื้องต้น ต้องตรวจเอกสารทางกฎหมายและหน่วยงานที่เกี่ยวข้องก่อนใช้งานจริง")


def render_external_apps_status_panel() -> None:
    st.markdown("### 🔗 External App Links")
    status = external_apps_status()
    st.json(status)

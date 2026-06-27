from __future__ import annotations

import os
from dataclasses import dataclass

import streamlit as st


ROLE_PUBLIC = "ผู้ใช้ทั่วไป"
ROLE_MEMBER = "สมาชิก / วิเคราะห์ได้"
ROLE_ADMIN = "ผู้ดูแลระบบ"

ROLE_ORDER = {
    ROLE_PUBLIC: 0,
    ROLE_MEMBER: 1,
    ROLE_ADMIN: 2,
}

ALL_ROLES = [ROLE_PUBLIC, ROLE_MEMBER, ROLE_ADMIN]


@dataclass(frozen=True)
class ModeAccess:
    min_role: str
    gee_required: bool
    description: str = ""


MODE_ACCESS: dict[str, ModeAccess] = {
    "Planning Report": ModeAccess(ROLE_PUBLIC, False, "ดูรายงานที่สร้างแล้ว"),
    "General Plan": ModeAccess(ROLE_PUBLIC, True, "ดูข้อมูลแผนทั่วไปจาก GEE"),

    "AI Simulation": ModeAccess(ROLE_MEMBER, True, "จำลองสถานการณ์เชิงพื้นที่"),
    "Suitability Analysis": ModeAccess(ROLE_MEMBER, True, "วิเคราะห์ความเหมาะสม"),
    "Urban Heat Island": ModeAccess(ROLE_MEMBER, True, "วิเคราะห์ LST/UHI"),
    "Import Wizard": ModeAccess(ROLE_MEMBER, False, "นำเข้าไฟล์ GIS"),
    "Candidate Ranking": ModeAccess(ROLE_MEMBER, False, "จัดอันดับพื้นที่ candidate"),
    "AI Recommendation": ModeAccess(ROLE_MEMBER, False, "ข้อเสนอแนะเชิงผังเมือง"),

    "Local Data Manager": ModeAccess(ROLE_ADMIN, False, "จัดการ asset/dataset ของระบบ"),
    "Spatial Database": ModeAccess(ROLE_ADMIN, False, "จัดการ PostGIS / Supabase PostGIS"),
    "System Diagnostics": ModeAccess(ROLE_ADMIN, False, "ตรวจสถานะระบบและ cache"),
    "Multi-Agent": ModeAccess(ROLE_ADMIN, True, "ทดสอบ agent และ evidence layers"),
}


def _secret(name: str, default: str = "") -> str:
    try:
        value = st.secrets.get(name, None)
        if value:
            return str(value)
    except Exception:
        pass
    return os.getenv(name, default)


def _auth_mode() -> str:
    return (_secret("URBAN_OS_AUTH_MODE", "open") or "open").lower().strip()


def _role_allowed(role: str, min_role: str) -> bool:
    return ROLE_ORDER.get(role, 0) >= ROLE_ORDER.get(min_role, 0)


def get_current_user_role() -> str:
    role = st.session_state.get("urban_os_user_role", ROLE_PUBLIC)
    if role not in ROLE_ORDER:
        return ROLE_PUBLIC
    return role


def can_access_mode(mode: str, role: str | None = None, gee_ready: bool = True) -> tuple[bool, str]:
    role = role or get_current_user_role()
    access = MODE_ACCESS.get(mode)
    if access is None:
        return False, "ไม่พบสิทธิ์ของเมนูนี้"

    if not _role_allowed(role, access.min_role):
        return False, f"ต้องใช้สิทธิ์อย่างน้อย: {access.min_role}"

    if access.gee_required and not gee_ready:
        return False, "เมนูนี้ต้องใช้ Google Earth Engine"

    return True, ""


def available_modes_for_current_user(gee_ready: bool = True) -> list[str]:
    ordered_modes = [
        "General Plan",
        "AI Simulation",
        "Suitability Analysis",
        "Urban Heat Island",
        "Local Data Manager",
        "Import Wizard",
        "Candidate Ranking",
        "AI Recommendation",
        "Planning Report",
        "Spatial Database",
        "System Diagnostics",
        "Multi-Agent",
    ]

    role = get_current_user_role()
    modes = []
    for mode in ordered_modes:
        allowed, _ = can_access_mode(mode, role=role, gee_ready=gee_ready)
        if allowed:
            modes.append(mode)

    if not modes:
        modes = ["Planning Report"]

    return modes


def icon_for_mode(mode: str) -> str:
    return {
        "General Plan": "map",
        "AI Simulation": "cpu",
        "Suitability Analysis": "layers",
        "Urban Heat Island": "thermometer-half",
        "Local Data Manager": "database",
        "Import Wizard": "upload",
        "Candidate Ranking": "trophy",
        "AI Recommendation": "stars",
        "Planning Report": "file-earmark-text",
        "Spatial Database": "hdd-network",
        "System Diagnostics": "activity",
        "Multi-Agent": "robot",
    }.get(mode, "circle")


def render_user_access_panel() -> str:
    st.markdown("### 👤 กลุ่มผู้ใช้")

    auth_mode = _auth_mode()
    current = get_current_user_role()

    selected = st.selectbox(
        "User role",
        ALL_ROLES,
        index=ALL_ROLES.index(current),
        key="urban_os_user_role_selector",
        help="ผู้ใช้ทั่วไปดูรายงาน/แผน, สมาชิกวิเคราะห์ได้, ผู้ดูแลระบบจัดการหลังบ้าน",
    )

    member_code = _secret("URBAN_OS_MEMBER_CODE", "")
    admin_code = _secret("URBAN_OS_ADMIN_CODE", "")

    if auth_mode == "open" and not member_code and not admin_code:
        st.session_state["urban_os_user_role"] = selected
        st.caption("Access mode: open / prototype")
        return selected

    if selected == ROLE_PUBLIC:
        st.session_state["urban_os_user_role"] = ROLE_PUBLIC
        return ROLE_PUBLIC

    code = st.text_input(
        "Access code",
        type="password",
        key="urban_os_access_code",
        placeholder="ใส่รหัสสำหรับสมาชิกหรือผู้ดูแลระบบ",
    )

    if selected == ROLE_MEMBER:
        if member_code and code == member_code:
            st.session_state["urban_os_user_role"] = ROLE_MEMBER
            st.success("เข้าสู่โหมดสมาชิก")
            return ROLE_MEMBER
        if admin_code and code == admin_code:
            st.session_state["urban_os_user_role"] = ROLE_ADMIN
            st.success("เข้าสู่โหมดผู้ดูแลระบบ")
            return ROLE_ADMIN
        st.session_state["urban_os_user_role"] = ROLE_PUBLIC
        st.warning("รหัสสมาชิกไม่ถูกต้อง จะแสดงเป็นผู้ใช้ทั่วไป")
        return ROLE_PUBLIC

    if selected == ROLE_ADMIN:
        if admin_code and code == admin_code:
            st.session_state["urban_os_user_role"] = ROLE_ADMIN
            st.success("เข้าสู่โหมดผู้ดูแลระบบ")
            return ROLE_ADMIN
        st.session_state["urban_os_user_role"] = ROLE_PUBLIC
        st.warning("รหัสผู้ดูแลระบบไม่ถูกต้อง จะแสดงเป็นผู้ใช้ทั่วไป")
        return ROLE_PUBLIC

    st.session_state["urban_os_user_role"] = ROLE_PUBLIC
    return ROLE_PUBLIC


def render_access_summary(gee_ready: bool = True) -> None:
    role = get_current_user_role()
    modes = available_modes_for_current_user(gee_ready=gee_ready)
    st.caption(f"Role: {role}")
    st.caption(f"Available menus: {len(modes)}")

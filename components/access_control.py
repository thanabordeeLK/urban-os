from __future__ import annotations

import os
from dataclasses import dataclass

import streamlit as st


# ---------------------------------------------------------------------
# Research workspace mode
# ---------------------------------------------------------------------
# หน้า Urban OS นี้ถือเป็นพื้นที่ "นักวิเคราะห์ วิจัย" แล้ว
# ดังนั้นไม่แสดงเมนู Portal Hub เช่น ผู้บริหารเมือง / นักวิเคราะห์ วิจัย /
# ตรวจสอบการใช้ประโยชน์ที่ดิน / พูดคุยข้อกฎหมายผังเมือง อีกต่อไป
#
# การแยกผู้ใช้/สมาชิกให้ทำที่ usdc-city-portal กลาง
# ส่วน Urban OS ให้เน้นงานแผนที่ วิเคราะห์ วิจัย และรายงาน
# ---------------------------------------------------------------------

ROLE_PUBLIC = "ผู้ใช้ทั่วไป"
ROLE_MEMBER = "สมาชิก / วิเคราะห์ได้"
ROLE_ADMIN = "ผู้ดูแลระบบ"

ALL_ROLES = [ROLE_PUBLIC, ROLE_MEMBER, ROLE_ADMIN]

PORTAL_EXECUTIVE = "ผู้บริหารเมือง"
PORTAL_RESEARCH = "นักวิเคราะห์ วิจัย"
PORTAL_LANDUSE = "ตรวจสอบการใช้ประโยชน์ที่ดิน"
PORTAL_LEGAL = "พูดคุยข้อกฎหมายผังเมือง"

# รับไว้เพื่อรองรับ deep link เก่าจาก portal แต่จะ redirect เป็นเมนูวิเคราะห์แทน
PORTAL_MODE_MAP = {
    "executive": "General Plan",
    "public": "General Plan",
    "manager": "General Plan",
    "mayor": "General Plan",
    "research": "General Plan",
    "analyst": "General Plan",
    "analysis": "General Plan",
    "landuse": "Import Wizard",
    "zoning": "Import Wizard",
    "legal": "Planning Report",
    "law": "Planning Report",
    "admin": "System Diagnostics",
    "backoffice": "System Diagnostics",
}

# เมนูที่ควรแสดงใน Urban OS Research Workspace
# ไม่รวมเมนู Portal Hub และไม่รวมเมนูแอปเฉพาะเรื่อง
RESEARCH_WORKSPACE_MODES = [
    "General Plan",
    "Suitability Analysis",
    "Urban Heat Island",
    "AI Simulation",
    "Import Wizard",
    "Candidate Ranking",
    "AI Recommendation",
    "Planning Report",
]

# เมนูหลังบ้าน/diagnostics จะไม่แสดงในเมนูหลักของนักวิเคราะห์
# แต่ยังคง access ได้ด้วย direct mode query หากต้องใช้แก้ระบบ
ADMIN_UTILITY_MODES = [
    "Local Data Manager",
    "Spatial Database",
    "System Diagnostics",
    "Multi-Agent",
]

ALL_MODES = RESEARCH_WORKSPACE_MODES + ADMIN_UTILITY_MODES

GEE_REQUIRED_MODES = {
    "General Plan",
    "AI Simulation",
    "Suitability Analysis",
    "Urban Heat Island",
    "Multi-Agent",
}


@dataclass(frozen=True)
class ModeAccess:
    min_role: str
    gee_required: bool
    description: str = ""


MODE_ACCESS: dict[str, ModeAccess] = {
    mode: ModeAccess(
        min_role=ROLE_PUBLIC,
        gee_required=mode in GEE_REQUIRED_MODES,
        description="Research workspace; membership is handled by central portal",
    )
    for mode in ALL_MODES
}


def _secret(name: str, default: str = "") -> str:
    try:
        value = st.secrets.get(name, None)
        if value:
            return str(value)
    except Exception:
        pass

    return os.getenv(name, default)


def _query_params() -> dict:
    try:
        return dict(st.query_params)
    except Exception:
        return {}


def _query_first(key: str, default: str = "") -> str:
    params = _query_params()
    value = params.get(key, default)

    if isinstance(value, list):
        return str(value[0]) if value else default

    return str(value or default)


def _role_from_query() -> str:
    raw = _query_first("role", "public").lower().strip()

    if raw in {"admin", "backoffice", "administrator"}:
        return ROLE_ADMIN

    if raw in {"member", "analyst", "research", "legal_member", "landuse_member"}:
        return ROLE_MEMBER

    return ROLE_PUBLIC


def _mode_from_query() -> str | None:
    portal = _query_first("portal", "").lower().strip()
    mode = _query_first("mode", "").strip()

    if portal:
        return PORTAL_MODE_MAP.get(portal)

    if mode:
        for item in ALL_MODES:
            if mode == item or mode.lower() == item.lower():
                return item

    return None


def get_current_user_role() -> str:
    """
    Return role hint only.

    Role no longer gates access inside Urban OS.
    The central USDC City Portal should handle member/public/admin control.
    """

    role = _role_from_query()
    st.session_state["urban_os_user_role"] = role
    return role


def _portal_home_url() -> str:
    return _secret("PORTAL_HOME_URL", "")


def render_user_access_panel() -> str:
    """
    Sidebar top panel.

    เดิมฟังก์ชันนี้แสดง User role + Access code
    ตอนนี้เปลี่ยนเป็นปุ่มกลับหน้าเพจกลางเท่านั้น
    """

    role = get_current_user_role()

    home_url = _portal_home_url()
    if home_url:
        st.link_button("🏠 กลับหน้าเพจกลาง", home_url, use_container_width=True)
    else:
        st.markdown("### 🏠 หน้าเพจกลาง")
        st.caption("ยังไม่ได้ตั้งค่า PORTAL_HOME_URL")

    st.caption("Urban OS Research Workspace")
    return role


def render_access_summary(gee_ready: bool = True) -> None:
    """
    Backward-compatible no-op.

    ไม่แสดง Role / Available menus ใน sidebar แล้ว
    """

    return None


def can_access_mode(mode: str, *, role: str | None = None, gee_ready: bool = True) -> tuple[bool, str]:
    """
    Research workspace access check.

    ไม่ล็อกด้วย member/admin แล้ว
    จะ block เฉพาะเมนูที่ต้องใช้ GEE เมื่อ GEE ยังไม่พร้อมเท่านั้น
    """

    mode = mode or ""
    if mode in GEE_REQUIRED_MODES and not gee_ready:
        return False, "เมนูนี้ต้องใช้ Google Earth Engine แต่ระบบ GEE ยังไม่พร้อม"

    return True, ""


def available_modes_for_current_user(gee_ready: bool = True) -> list[str]:
    """
    แสดงเฉพาะเมนูงานวิเคราะห์/วิจัยใน Urban OS

    ไม่แสดง:
    - ผู้บริหารเมือง
    - นักวิเคราะห์ วิจัย
    - ตรวจสอบการใช้ประโยชน์ที่ดิน
    - พูดคุยข้อกฎหมายผังเมือง
    - เมนูหลังบ้าน/admin utility
    """

    return [
        mode
        for mode in RESEARCH_WORKSPACE_MODES
        if gee_ready or mode not in GEE_REQUIRED_MODES
    ]


def get_default_mode_for_menu(available_modes: list[str]) -> str:
    requested = _mode_from_query()

    if requested and requested in available_modes:
        return requested

    # เน้นเริ่มจากแผนที่/ข้อมูลพื้นฐานของงานวิเคราะห์
    if "General Plan" in available_modes:
        return "General Plan"

    if "Import Wizard" in available_modes:
        return "Import Wizard"

    if "Planning Report" in available_modes:
        return "Planning Report"

    return available_modes[0] if available_modes else "Planning Report"


def icon_for_mode(mode: str) -> str:
    icons = {
        "General Plan": "layers",
        "Suitability Analysis": "compass",
        "Urban Heat Island": "thermometer-half",
        "AI Simulation": "robot",
        "Import Wizard": "cloud-upload",
        "Candidate Ranking": "trophy",
        "AI Recommendation": "stars",
        "Planning Report": "file-earmark-text",
        "Local Data Manager": "folder2-open",
        "Spatial Database": "database",
        "System Diagnostics": "activity",
        "Multi-Agent": "cpu",
    }

    return icons.get(mode, "circle")

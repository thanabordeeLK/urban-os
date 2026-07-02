from __future__ import annotations

from dataclasses import dataclass

import streamlit as st


# ---------------------------------------------------------------------
# Open-access mode
# ---------------------------------------------------------------------
# การล็อกสมาชิก/ผู้ใช้ทั่วไปให้ไปทำที่หน้า USDC City Portal กลาง
# ไฟล์นี้คง API เดิมไว้ เพื่อไม่ให้ components/sidebar.py และ app.py พัง
# แต่ไม่แสดงช่อง User role / Access code และไม่ gate เมนูด้วย member/admin อีกต่อไป
# ---------------------------------------------------------------------

ROLE_PUBLIC = "ผู้ใช้ทั่วไป"
ROLE_MEMBER = "สมาชิก / วิเคราะห์ได้"
ROLE_ADMIN = "ผู้ดูแลระบบ"

ALL_ROLES = [ROLE_PUBLIC, ROLE_MEMBER, ROLE_ADMIN]

PORTAL_EXECUTIVE = "ผู้บริหารเมือง"
PORTAL_RESEARCH = "นักวิเคราะห์ วิจัย"
PORTAL_LANDUSE = "ตรวจสอบการใช้ประโยชน์ที่ดิน"
PORTAL_LEGAL = "พูดคุยข้อกฎหมายผังเมือง"

PORTAL_MODE_MAP = {
    "executive": PORTAL_EXECUTIVE,
    "public": PORTAL_EXECUTIVE,
    "manager": PORTAL_EXECUTIVE,
    "mayor": PORTAL_EXECUTIVE,
    "research": PORTAL_RESEARCH,
    "analyst": PORTAL_RESEARCH,
    "analysis": PORTAL_RESEARCH,
    "landuse": PORTAL_LANDUSE,
    "zoning": PORTAL_LANDUSE,
    "legal": PORTAL_LEGAL,
    "law": PORTAL_LEGAL,
    "admin": "System Diagnostics",
    "backoffice": "System Diagnostics",
}

ALL_MODES = [
    PORTAL_EXECUTIVE,
    PORTAL_RESEARCH,
    PORTAL_LANDUSE,
    PORTAL_LEGAL,
    "General Plan",
    "AI Simulation",
    "Suitability Analysis",
    "Urban Heat Island",
    "Import Wizard",
    "Candidate Ranking",
    "AI Recommendation",
    "Planning Report",
    "Local Data Manager",
    "Spatial Database",
    "System Diagnostics",
    "Multi-Agent",
]

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
        description="Open access; membership is handled by central portal",
    )
    for mode in ALL_MODES
}


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
        # accept exact Thai/English mode from URL
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


def render_user_access_panel() -> str:
    """
    Backward-compatible no-op.

    เดิมฟังก์ชันนี้แสดง User role + Access code ใน sidebar
    ตอนนี้ไม่แสดงอะไรแล้ว เพื่อให้สิทธิ์สมาชิกไปจัดการที่หน้า Portal กลาง
    """

    return get_current_user_role()


def render_access_summary(gee_ready: bool = True) -> None:
    """
    Backward-compatible no-op.

    ไม่แสดง Role / Available menus ใน sidebar แล้ว
    """

    return None


def can_access_mode(mode: str, *, role: str | None = None, gee_ready: bool = True) -> tuple[bool, str]:
    """
    Open-access check.

    ไม่ล็อกด้วย member/admin แล้ว
    จะ block เฉพาะเมนูที่ต้องใช้ GEE เมื่อ GEE ยังไม่พร้อมเท่านั้น
    """

    mode = mode or ""
    if mode in GEE_REQUIRED_MODES and not gee_ready:
        return False, "เมนูนี้ต้องใช้ Google Earth Engine แต่ระบบ GEE ยังไม่พร้อม"

    return True, ""


def available_modes_for_current_user(gee_ready: bool = True) -> list[str]:
    """
    Return all menus that can run under the current technical state.

    ไม่มีการตัดเมนูตาม member/admin แล้ว
    ตัดเฉพาะเมนูที่ต้องใช้ GEE เมื่อ GEE ยังไม่พร้อม
    """

    return [
        mode
        for mode in ALL_MODES
        if gee_ready or mode not in GEE_REQUIRED_MODES
    ]


def get_default_mode_for_menu(available_modes: list[str]) -> str:
    requested = _mode_from_query()

    if requested and requested in available_modes:
        return requested

    # ถ้า GEE พร้อม ให้เริ่มที่ผู้บริหารเมืองเพื่อเป็นหน้าอ่านง่าย
    if PORTAL_EXECUTIVE in available_modes:
        return PORTAL_EXECUTIVE

    return available_modes[0] if available_modes else "Planning Report"


def icon_for_mode(mode: str) -> str:
    icons = {
        PORTAL_EXECUTIVE: "briefcase",
        PORTAL_RESEARCH: "bar-chart",
        PORTAL_LANDUSE: "map",
        PORTAL_LEGAL: "chat-square-text",
        "General Plan": "layers",
        "AI Simulation": "robot",
        "Suitability Analysis": "compass",
        "Urban Heat Island": "thermometer-half",
        "Local Data Manager": "folder2-open",
        "Import Wizard": "cloud-upload",
        "Candidate Ranking": "trophy",
        "AI Recommendation": "stars",
        "Planning Report": "file-earmark-text",
        "Spatial Database": "database",
        "System Diagnostics": "activity",
        "Multi-Agent": "cpu",
    }

    return icons.get(mode, "circle")

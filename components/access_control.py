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


@dataclass(frozen=True)
class ModeAccess:
    min_role: str
    gee_required: bool
    description: str = ""


MODE_ACCESS: dict[str, ModeAccess] = {
    # Public portal / no-login pages
    PORTAL_EXECUTIVE: ModeAccess(ROLE_PUBLIC, False, "หน้าอ่านข้อมูลสำหรับผู้บริหาร/ประชาชนทั่วไป"),
    PORTAL_LEGAL: ModeAccess(ROLE_PUBLIC, False, "ถาม-ตอบกฎหมายผังเมืองแบบทั่วไป"),
    "Planning Report": ModeAccess(ROLE_PUBLIC, False, "ดูรายงานที่สร้างแล้ว"),
    "General Plan": ModeAccess(ROLE_PUBLIC, True, "ดูข้อมูลแผนทั่วไปจาก GEE"),

    # Member portal / analysis pages
    PORTAL_RESEARCH: ModeAccess(ROLE_MEMBER, False, "ศูนย์รวมเครื่องมือวิเคราะห์/วิจัย"),
    PORTAL_LANDUSE: ModeAccess(ROLE_MEMBER, False, "ตรวจสอบการใช้ประโยชน์ที่ดินและนำเข้าข้อมูล"),
    "AI Simulation": ModeAccess(ROLE_MEMBER, True, "จำลองสถานการณ์เชิงพื้นที่"),
    "Suitability Analysis": ModeAccess(ROLE_MEMBER, True, "วิเคราะห์ความเหมาะสม"),
    "Urban Heat Island": ModeAccess(ROLE_MEMBER, True, "วิเคราะห์ LST/UHI"),
    "Import Wizard": ModeAccess(ROLE_MEMBER, False, "นำเข้าไฟล์ GIS"),
    "Candidate Ranking": ModeAccess(ROLE_MEMBER, False, "จัดอันดับพื้นที่ candidate"),
    "AI Recommendation": ModeAccess(ROLE_MEMBER, False, "ข้อเสนอแนะเชิงผังเมือง"),

    # Admin / back office
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
    """
    Access modes:
    - public: default public-first mode, member/admin require code
    - passcode: same as public but explicit
    - open: development/prototype only, role selector freely changes role
    """

    return (_secret("URBAN_OS_AUTH_MODE", "public") or "public").lower().strip()


def _role_allowed(role: str, min_role: str) -> bool:
    return ROLE_ORDER.get(role, 0) >= ROLE_ORDER.get(min_role, 0)


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


def requested_role_from_query() -> str:
    role = _query_first("role", "").lower().strip()
    if role in {"member", "analyst", "research", "staff"}:
        return ROLE_MEMBER
    if role in {"admin", "backoffice", "system"}:
        return ROLE_ADMIN
    return ROLE_PUBLIC


def requested_mode_from_query() -> str:
    mode = _query_first("mode", "").strip()
    if mode:
        return mode

    portal = _query_first("portal", "").lower().strip()
    if portal:
        return PORTAL_MODE_MAP.get(portal, PORTAL_EXECUTIVE)

    return ""


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


def ordered_modes_for_role(role: str) -> list[str]:
    """
    Public-first menu order designed for portal workflow.
    """

    public_modes = [
        PORTAL_EXECUTIVE,
        PORTAL_LEGAL,
        "Planning Report",
        "General Plan",
    ]

    member_modes = [
        PORTAL_EXECUTIVE,
        PORTAL_RESEARCH,
        PORTAL_LANDUSE,
        PORTAL_LEGAL,
        "General Plan",
        "Suitability Analysis",
        "Urban Heat Island",
        "Import Wizard",
        "Candidate Ranking",
        "AI Recommendation",
        "Planning Report",
        "AI Simulation",
    ]

    admin_modes = member_modes + [
        "Local Data Manager",
        "Spatial Database",
        "System Diagnostics",
        "Multi-Agent",
    ]

    if role == ROLE_ADMIN:
        return admin_modes
    if role == ROLE_MEMBER:
        return member_modes
    return public_modes


def available_modes_for_current_user(gee_ready: bool = True) -> list[str]:
    role = get_current_user_role()
    modes = []
    for mode in ordered_modes_for_role(role):
        allowed, _ = can_access_mode(mode, role=role, gee_ready=gee_ready)
        if allowed:
            modes.append(mode)

    if not modes:
        modes = [PORTAL_EXECUTIVE, PORTAL_LEGAL, "Planning Report"]

    return modes


def get_default_mode_for_menu(available_modes: list[str]) -> str:
    requested = requested_mode_from_query()
    if requested in available_modes:
        return requested

    # If a public user tries a member portal, keep them on Executive Portal
    # and the access panel will ask for code if they select member/admin.
    if PORTAL_EXECUTIVE in available_modes:
        return PORTAL_EXECUTIVE

    return available_modes[0] if available_modes else "Planning Report"


def icon_for_mode(mode: str) -> str:
    return {
        PORTAL_EXECUTIVE: "briefcase",
        PORTAL_RESEARCH: "bar-chart-line",
        PORTAL_LANDUSE: "map",
        PORTAL_LEGAL: "chat-dots",
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


def _set_role(role: str) -> str:
    st.session_state["urban_os_user_role"] = role
    return role


def render_user_access_panel() -> str:
    """
    Portal-oriented role control.

    Public/no login:
    - Default role is public.
    - Public can enter Executive and Legal basic pages.

    Member:
    - Requires member/admin code unless URBAN_OS_AUTH_MODE=open.
    - Can access every main workspace.

    Admin:
    - Requires admin code unless URBAN_OS_AUTH_MODE=open.
    - Can access back office.
    """

    st.markdown("### 👤 กลุ่มผู้ใช้")

    auth_mode = _auth_mode()
    query_role = requested_role_from_query()

    if "urban_os_user_role" not in st.session_state:
        st.session_state["urban_os_user_role"] = ROLE_PUBLIC

    current = get_current_user_role()
    default_index = ALL_ROLES.index(query_role) if query_role in ALL_ROLES else ALL_ROLES.index(current)

    selected = st.selectbox(
        "User role",
        ALL_ROLES,
        index=default_index,
        key="urban_os_user_role_selector",
        help="ไม่ล็อกอิน = ผู้ใช้ทั่วไป, ล็อกอินสมาชิก = วิเคราะห์ได้ทุกหน้าหลัก, ผู้ดูแลระบบ = หลังบ้าน",
    )

    member_code = _secret("URBAN_OS_MEMBER_CODE", "")
    admin_code = _secret("URBAN_OS_ADMIN_CODE", "")

    if auth_mode == "open":
        st.caption("Access mode: open / development only")
        return _set_role(selected)

    if selected == ROLE_PUBLIC:
        st.caption("ไม่ล็อกอิน: ใช้งานโหมดผู้ใช้ทั่วไป")
        return _set_role(ROLE_PUBLIC)

    code = st.text_input(
        "Access code",
        type="password",
        key="urban_os_access_code",
        placeholder="ใส่รหัสสมาชิกหรือผู้ดูแลระบบ",
    )

    if selected == ROLE_MEMBER:
        if member_code and code == member_code:
            st.success("เข้าสู่โหมดสมาชิก / วิเคราะห์ได้")
            return _set_role(ROLE_MEMBER)
        if admin_code and code == admin_code:
            st.success("เข้าสู่โหมดผู้ดูแลระบบ")
            return _set_role(ROLE_ADMIN)
        st.warning("ต้องใส่รหัสสมาชิกก่อน จึงจะเข้าเครื่องมือวิเคราะห์ได้")
        return _set_role(ROLE_PUBLIC)

    if selected == ROLE_ADMIN:
        if admin_code and code == admin_code:
            st.success("เข้าสู่โหมดผู้ดูแลระบบ")
            return _set_role(ROLE_ADMIN)
        st.warning("ต้องใส่รหัสผู้ดูแลระบบก่อน จึงจะเข้าหลังบ้านได้")
        return _set_role(ROLE_PUBLIC)

    return _set_role(ROLE_PUBLIC)


def render_access_summary(gee_ready: bool = True) -> None:
    role = get_current_user_role()
    modes = available_modes_for_current_user(gee_ready=gee_ready)
    st.caption(f"Role: {role}")
    st.caption(f"Available menus: {len(modes)}")

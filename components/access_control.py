from __future__ import annotations

import streamlit as st


ROLE_PUBLIC = "public"
ROLE_MEMBER = "member"
ROLE_ADMIN = "admin"


def _query_role() -> str:
    try:
        raw = str(dict(st.query_params).get("role", "public")).lower()
    except Exception:
        raw = "public"

    if raw in {"member", "analyst", "research", "legal_member"}:
        return ROLE_MEMBER
    if raw in {"admin", "backoffice"}:
        return ROLE_ADMIN
    return ROLE_PUBLIC


def get_current_role() -> str:
    role = st.session_state.get("law_chat_role_hint")
    if role in {ROLE_PUBLIC, ROLE_MEMBER, ROLE_ADMIN}:
        return role
    return _query_role()


def is_member(role: str | None = None) -> bool:
    return True


def is_admin(role: str | None = None) -> bool:
    return (role or get_current_role()) == ROLE_ADMIN


def render_access_panel() -> str:
    """
    Open-access mode.

    Membership/authentication is handled by the central USDC City Portal.
    This app only reads role from query params as a hint.
    """

    role = _query_role()
    st.session_state["law_chat_role_hint"] = role

    st.markdown("### 🔓 Open Workspace")
    st.caption("แอปนี้ไม่ล็อกสมาชิกภายในตัวเอง")
    st.caption("Role hint from portal:")
    st.code(role, language="text")

    st.info("ถ้าต้องการจำกัดผู้ใช้ ให้กำหนดที่หน้า USDC City Portal ก่อน redirect มายังแอปนี้")
    return role

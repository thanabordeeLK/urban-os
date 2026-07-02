from __future__ import annotations

from datetime import datetime
import streamlit as st

from config.app_config import APP_TITLE, APP_SUBTITLE, get_external_url
from components.access_control import render_access_panel, get_current_role
from components.disclaimer import render_disclaimer
from components.legal_chat import render_legal_chat
from components.document_upload import render_document_upload
from components.memo_generator import render_memo_generator


def configure_page() -> None:
    st.set_page_config(
        page_title="USDC Planning Law Chat",
        page_icon="⚖️",
        layout="wide",
        initial_sidebar_state="expanded",
    )


def inject_css() -> None:
    st.markdown(
        """
        <style>
        .block-container { padding-top: 1.4rem; }
        .law-card {
            border: 1px solid rgba(0,242,254,.24);
            background: rgba(13,27,42,.72);
            border-radius: 14px;
            padding: 16px 18px;
            margin-bottom: 12px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header() -> None:
    st.title(APP_TITLE)
    st.markdown(f"*{APP_SUBTITLE}*")


def render_workspace() -> None:
    st.markdown("### ⚖️ Planning Law Assistant Workspace")
    st.caption(
        "Open workspace: การล็อกสมาชิก/ผู้ใช้ทั่วไปให้กำหนดที่หน้า USDC City Portal กลาง "
        "เพื่อให้แอปนี้เชื่อมต่อกับระบบอื่นได้ง่าย"
    )

    tab_chat, tab_docs, tab_memo, tab_settings = st.tabs(
        ["💬 Legal Chat", "📎 Document Upload", "📝 Planning Legal Memo", "⚙️ Settings"]
    )

    with tab_chat:
        render_disclaimer(compact=False)
        render_legal_chat(member_mode=True)

    with tab_docs:
        render_document_upload()

    with tab_memo:
        render_memo_generator()

    with tab_settings:
        st.markdown("#### External links")
        portal_url = get_external_url("PORTAL_HOME_URL")
        urban_os_url = get_external_url("URBAN_OS_APP_URL")
        landuse_url = get_external_url("LANDUSE_APP_URL")

        if portal_url:
            st.link_button("กลับ USDC Portal", portal_url, use_container_width=True)
        else:
            st.info("ยังไม่ได้ตั้งค่า PORTAL_HOME_URL")

        if urban_os_url:
            st.link_button("เปิด Urban OS Core", urban_os_url, use_container_width=True)
        else:
            st.info("ยังไม่ได้ตั้งค่า URBAN_OS_APP_URL")

        if landuse_url:
            st.link_button("เปิด Land Use Checker", landuse_url, use_container_width=True)
        else:
            st.info("ยังไม่ได้ตั้งค่า LANDUSE_APP_URL")

        st.markdown("#### Session status")
        st.json(
            {
                "access": "open_workspace",
                "role_hint": get_current_role(),
                "documents": len(st.session_state.get("law_documents", [])),
                "chat_messages": len(st.session_state.get("law_chat_history", [])),
                "generated_at": datetime.now().isoformat(),
            }
        )


def main() -> None:
    configure_page()
    inject_css()
    render_header()

    with st.sidebar:
        render_access_panel()
        st.markdown("---")
        st.caption("USDC Planning Law Chat")
        st.caption("Open workspace: สิทธิ์สมาชิกให้กำหนดที่หน้า Portal กลาง")

    render_workspace()


if __name__ == "__main__":
    main()

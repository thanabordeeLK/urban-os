from __future__ import annotations

from datetime import datetime
import streamlit as st

from config.app_config import APP_TITLE, APP_SUBTITLE, get_external_url
from components.access_control import render_access_panel, get_current_role
from components.file_import import render_upload_panel
from components.map_viewer import render_map_viewer
from components.report import render_landuse_report


def configure_page() -> None:
    st.set_page_config(page_title="USDC Land Use Checker", page_icon="🗺️", layout="wide")


def inject_css() -> None:
    st.markdown(
        """
        <style>
        .block-container { padding-top: 1.4rem; }
        .usdc-card { border:1px solid rgba(0,242,254,.25); background:rgba(13,27,42,.72);
        border-radius:14px; padding:16px 18px; margin-bottom:12px; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header() -> None:
    st.title(APP_TITLE)
    st.markdown(f"*{APP_SUBTITLE}*")


def render_workspace() -> None:
    st.markdown("### 🗺️ Land Use Checker Workspace")
    st.caption(
        "Open workspace: การล็อกสมาชิก/ผู้ใช้ทั่วไปให้กำหนดที่หน้า USDC City Portal กลาง "
        "เพื่อให้แอปนี้เชื่อมต่อกับระบบอื่นได้ง่าย"
    )

    tab_upload, tab_map, tab_report, tab_settings = st.tabs(
        ["📤 Upload / Input", "🗺️ Map Preview", "📄 Land Use Report", "⚙️ Settings"]
    )

    with tab_upload:
        render_upload_panel()

    with tab_map:
        render_map_viewer()

    with tab_report:
        render_landuse_report()

    with tab_settings:
        st.markdown("#### External links")
        urban_os_url = get_external_url("URBAN_OS_APP_URL")
        portal_url = get_external_url("PORTAL_HOME_URL")

        if urban_os_url:
            st.link_button("กลับ Urban OS Core", urban_os_url, use_container_width=True)
        else:
            st.info("ยังไม่ได้ตั้งค่า URBAN_OS_APP_URL")

        if portal_url:
            st.link_button("กลับ USDC Portal", portal_url, use_container_width=True)
        else:
            st.info("ยังไม่ได้ตั้งค่า PORTAL_HOME_URL")

        st.markdown("#### Session state")
        st.json(
            {
                "access": "open_workspace",
                "role_hint": get_current_role(),
                "features": len(st.session_state.get("landuse_geojson", {}).get("features", []))
                if isinstance(st.session_state.get("landuse_geojson"), dict)
                else 0,
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
        st.caption("USDC Land Use Checker")
        st.caption("Open workspace: สิทธิ์สมาชิกให้กำหนดที่หน้า Portal กลาง")

    render_workspace()


if __name__ == "__main__":
    main()

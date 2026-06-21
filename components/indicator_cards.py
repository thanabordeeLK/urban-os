"""Indicator cards for Urban OS dashboard."""
import streamlit as st


def _format_rai(value: float) -> str:
    return f"{value:,.0f} ไร่"


def _format_percent(value: float) -> str:
    return f"{value:,.1f}%"


def render_indicator_cards() -> None:
    """Render quick planning indicators from latest ESA statistics in session state."""
    st.markdown("### 📊 Planning Indicator Cards")

    summary = st.session_state.get("esa_indicator_summary")
    df = st.session_state.get("esa_landcover_stats_df")

    col1, col2, col3, col4 = st.columns(4)

    if not summary:
        with col1:
            st.metric("Green Area", "รอคำนวณ", "เปิด ESA แล้วกดคำนวณ")
        with col2:
            st.metric("Built-up Area", "รอคำนวณ", "-")
        with col3:
            st.metric("Water Area", "รอคำนวณ", "-")
        with col4:
            st.metric("Planning Score", "รอคำนวณ", "prototype")
        st.caption("เปิดชั้นข้อมูล ESA Land Cover แล้วกดปุ่ม ‘📈 คำนวณสถิติพื้นที่’ ใน Sidebar เพื่อเติมค่าจริง")
        return

    with col1:
        st.metric(
            "Green Area",
            _format_rai(summary["green_area_rai"]),
            _format_percent(summary["green_percent"]),
        )
    with col2:
        st.metric(
            "Built-up Area",
            _format_rai(summary["builtup_area_rai"]),
            _format_percent(summary["builtup_percent"]),
        )
    with col3:
        st.metric(
            "Water Area",
            _format_rai(summary["water_area_rai"]),
            _format_percent(summary["water_percent"]),
        )
    with col4:
        st.metric(
            "Planning Score",
            f"{summary['planning_score']:,.1f}/100",
            "Quick index",
        )

    st.caption(
        "คะแนน Planning Score ในเวอร์ชันนี้เป็น quick prototype จาก ESA WorldCover เท่านั้น "
        "ยังไม่ใช่ suitability model ฉบับสมบูรณ์"
    )

    if df is not None:
        with st.expander("📋 ตารางพื้นที่จาก ESA WorldCover"):
            st.dataframe(df.drop(columns=["code"], errors="ignore"), use_container_width=True, hide_index=True)

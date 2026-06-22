import sys
import json
from pathlib import Path

import streamlit as st

# ---------------------------------------------------------
# ทำให้ Streamlit Cloud และ local runner มองเห็นโมดูลภายในโปรเจกต์
# ---------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from config.settings import configure_page, inject_css
from config.auth import initialize_earth_engine

from components.sidebar import render_sidebar
from components.map_renderer import create_base_map, add_boundary, render_map
from components.indicator_cards import render_indicator_cards

from core_engine.general_plan import add_general_plan_layers
from core_engine.ai_simulation import (
    run_ai_simulation_if_requested,
    render_ai_result_chart,
)
from core_engine.suitability import (
    add_suitability_layers,
    render_suitability_methodology,
)
from core_engine.multi_agent import (
    add_multi_agent_evidence_layers,
    run_multi_agent_if_requested,
    render_multi_agent_outputs,
)
from core_engine.report_export import render_suitability_export_panel


def render_header() -> None:
    """แสดงหัวเว็บหลักของระบบ Urban OS"""
    st.title("🌐 Urban OS : Spatial AI Dashboard")
    st.markdown("*ระบบปฏิบัติการผังเมืองอัจฉริยะ และการจำลองสถานการณ์เชิงพื้นที่*")


def main() -> None:
    """Main entry point ของ Streamlit App"""

    # -----------------------------------------------------
    # 1. Page config / CSS / Header
    # -----------------------------------------------------
    configure_page()
    inject_css()
    render_header()

    # -----------------------------------------------------
    # 2. Initialize Google Earth Engine
    # -----------------------------------------------------
    initialize_earth_engine()

    # -----------------------------------------------------
    # 3. Sidebar state
    # -----------------------------------------------------
    state = render_sidebar()

    selected_mode = state.get("selected_mode", "General Plan")
    roi = state.get("roi")
    is_whole_country = state.get("is_whole_country", False)
    basemap_choice = state.get("basemap_choice", "OpenStreetMap")

    selected_province = state.get("selected_province", "")
    selected_district = state.get("selected_district", "")

    # -----------------------------------------------------
    # 4. Create base map
    # -----------------------------------------------------
    Map = create_base_map(
        basemap_choice=basemap_choice,
        roi=roi,
        is_whole_country=is_whole_country,
        selected_province=selected_province,
        selected_district=selected_district,
    )

    add_boundary(
        Map=Map,
        roi=roi,
        is_whole_country=is_whole_country,
    )

    # สำหรับเก็บผลลัพธ์กราฟ AI Simulation
    df_trend = None

    # -----------------------------------------------------
    # 5. Mode: General Plan
    # -----------------------------------------------------
    if selected_mode == "General Plan":
        add_general_plan_layers(
            Map=Map,
            roi=roi,
            is_whole_country=is_whole_country,
            layer_settings=state.get("layer_settings", {}),
        )

    # -----------------------------------------------------
    # 6. Mode: AI Simulation
    # -----------------------------------------------------
    elif selected_mode == "AI Simulation":
        df_trend = run_ai_simulation_if_requested(
            Map=Map,
            roi=roi,
            is_whole_country=is_whole_country,
            ai_settings=state.get("ai_settings", {}),
        )

    # -----------------------------------------------------
    # 7. Mode: Suitability Analysis
    # -----------------------------------------------------
    elif selected_mode == "Suitability Analysis":
        suitability_config = state.get("suitability_config")

        if suitability_config and suitability_config.get("run_suitability"):
            weights = suitability_config.get("weights", {})
            show_factors = suitability_config.get("show_factor_layers", False)
            constraint_config = suitability_config.get("constraint_config", {})
            road_config = suitability_config.get("road_config", {})
            facility_config = suitability_config.get("facility_config", {})
            config_signature = json.dumps(
                {
                    "province": selected_province,
                    "district": selected_district,
                    "is_whole_country": is_whole_country,
                    "weights": weights,
                    "show_factors": show_factors,
                    "constraint_config": constraint_config,
                    "road_config": road_config,
                    "facility_config": facility_config,
                },
                sort_keys=True,
                ensure_ascii=False,
            )

            previous_signature = st.session_state.get("suitability_config_signature")
            calculate_stats = (
                suitability_config.get("run_clicked", False)
                or previous_signature != config_signature
                or "suitability_stats_df" not in st.session_state
            )
            st.session_state["suitability_config_signature"] = config_signature

            add_suitability_layers(
                Map=Map,
                roi=roi,
                weights=weights,
                show_factors=show_factors,
                is_whole_country=is_whole_country,
                calculate_stats=calculate_stats,
                constraint_config=constraint_config,
                road_config=road_config,
                facility_config=facility_config,
            )
        else:
            st.info(
                "เลือกน้ำหนักปัจจัยใน Sidebar แล้วกด ▶️ Run Suitability Analysis "
                "เพื่อสร้างแผนที่ความเหมาะสมต่อการพัฒนาเมือง"
            )

        render_suitability_methodology()

    # -----------------------------------------------------
    # 8. Mode: Multi-Agent
    # -----------------------------------------------------
    elif selected_mode == "Multi-Agent":
        add_multi_agent_evidence_layers(
            Map=Map,
            roi=roi,
            is_whole_country=is_whole_country,
            settings=state.get("multi_agent_settings", {}) or {},
        )

    # -----------------------------------------------------
    # 9. Render Map
    # -----------------------------------------------------
    render_map(Map)

    # -----------------------------------------------------
    # 9. Render mode-specific outputs
    # -----------------------------------------------------
    if selected_mode == "General Plan":
        render_indicator_cards()

    elif selected_mode == "AI Simulation":
        render_ai_result_chart(df_trend)

    elif selected_mode == "Suitability Analysis":
        st.markdown("### 🧭 Suitability Analysis Result")
        st.caption(
            "แผนที่นี้เป็นแบบจำลองเบื้องต้นสำหรับประเมินพื้นที่เหมาะสมต่อการพัฒนาเมือง "
            "โดยอ้างอิง slope, flood history, land cover, urbanization, road accessibility, water proximity "
            "และพื้นที่กันออก เช่น ป่า/พื้นที่คุ้มครอง"
        )

        df = st.session_state.get("suitability_stats_df")
        summary = st.session_state.get("suitability_summary") or {}

        if df is not None:
            col1, col2, col3 = st.columns(3)
            col1.metric(
                "พื้นที่เหมาะสมสูง–สูงมาก",
                f"{summary.get('development_candidate_rai', 0):,.0f} ไร่",
                f"{summary.get('candidate_percent', 0):.1f}%",
            )
            col2.metric(
                "พื้นที่ควรหลีกเลี่ยง/จำกัด",
                f"{summary.get('restricted_rai', 0):,.0f} ไร่",
            )
            col3.metric(
                "พื้นที่รวมที่คำนวณได้",
                f"{summary.get('total_rai', 0):,.0f} ไร่",
            )
            st.dataframe(df, use_container_width=True)

            render_suitability_export_panel(
                selected_province=selected_province,
                selected_district=selected_district,
                is_whole_country=is_whole_country,
                summary=summary,
                df=df,
                suitability_config=state.get("suitability_config") or {},
            )
        elif st.session_state.get("suitability_run_active", False):
            st.warning("กำลังรอผลสรุปพื้นที่จาก Google Earth Engine")
        else:
            st.info("ยังไม่มีผลวิเคราะห์ กด Run Suitability Analysis ใน Sidebar ก่อน")

    elif selected_mode == "Multi-Agent":
        outputs = run_multi_agent_if_requested(
            roi=roi,
            is_whole_country=is_whole_country,
            selected_province=selected_province,
            selected_district=selected_district,
            multi_agent_settings=state.get("multi_agent_settings", {}) or {},
        )
        render_multi_agent_outputs(outputs)


if __name__ == "__main__":
    main()

import streamlit as st
import sys
from pathlib import Path

# ให้ Streamlit Cloud และ local runner มองเห็นโฟลเดอร์โมดูลภายในโปรเจกต์เสมอ
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


def render_header() -> None:
    """หัวเว็บหลัก"""
    st.title("🌐 Urban OS : Spatial AI Dashboard")
    st.markdown("*ระบบปฏิบัติการผังเมืองอัจฉริยะ และการจำลองสถานการณ์เชิงพื้นที่*")


def main() -> None:
    configure_page()
    inject_css()
    render_header()

    initialize_earth_engine()

    state = render_sidebar()

    selected_mode = state["selected_mode"]
    roi = state["roi"]
    is_whole_country = state["is_whole_country"]
    basemap_choice = state["basemap_choice"]

    Map = create_base_map(basemap_choice)
    add_boundary(Map, roi, is_whole_country)

    df_trend = None

    if selected_mode == "General Plan":
        add_general_plan_layers(
            Map=Map,
            roi=roi,
            is_whole_country=is_whole_country,
            layer_settings=state["layer_settings"],
        )

    elif selected_mode == "AI Simulation":
        df_trend = run_ai_simulation_if_requested(
            Map=Map,
            roi=roi,
            is_whole_country=is_whole_country,
            ai_settings=state["ai_settings"],
        )

    render_map(Map)
    render_indicator_cards()
    render_ai_result_chart(df_trend)


if __name__ == "__main__":
    main()

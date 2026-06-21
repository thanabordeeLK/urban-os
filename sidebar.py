import streamlit as st
from streamlit_option_menu import option_menu

from config.settings import (
    THAILAND_ALL_LABEL,
    THAILAND_DISTRICT_ALL_LABEL,
    PROVINCE_ALL_LABEL,
    DEFAULT_PROVINCE,
    DEFAULT_DISTRICT,
)
from services.roi_service import get_provinces, get_districts, get_roi


def render_sidebar() -> dict:
    """
    แสดง UI ด้านซ้ายทั้งหมด และคืนค่าการตั้งค่าที่ผู้ใช้เลือก

    Returns:
        dict: ค่าที่ใช้ใน app.py และ core_engine
    """
    with st.sidebar:
        st.markdown(
            "<h3 style='text-align: center; margin-bottom: 20px;'>⚙️ CONTROL PANEL</h3>",
            unsafe_allow_html=True,
        )

        selected_mode = option_menu(
            menu_title=None,
            options=["General Plan", "AI Simulation"],
            icons=["map", "cpu"],
            menu_icon="cast",
            default_index=0,
            styles={
                "container": {"padding": "0!important", "background-color": "#0B132B"},
                "icon": {"color": "#00F2FE", "font-size": "18px"},
                "nav-link": {
                    "color": "#E2E8F0",
                    "font-size": "16px",
                    "text-align": "left",
                    "margin": "0px",
                },
                "nav-link-selected": {
                    "background-color": "rgba(0, 242, 254, 0.2)",
                    "color": "#00F2FE",
                    "border-left": "4px solid #00F2FE",
                    "font-weight": "bold",
                },
            },
        )

        st.markdown("<hr style='border-color: #1E293B;'>", unsafe_allow_html=True)
        st.markdown("**📍 กำหนดพื้นที่วิเคราะห์**")

        provinces_list = [THAILAND_ALL_LABEL] + get_provinces()
        default_prov_idx = (
            provinces_list.index(DEFAULT_PROVINCE)
            if DEFAULT_PROVINCE in provinces_list
            else 0
        )

        selected_province = st.selectbox(
            "เลือกจังหวัด (Province)",
            provinces_list,
            index=default_prov_idx,
        )

        is_whole_country = selected_province == THAILAND_ALL_LABEL

        if is_whole_country:
            selected_district = THAILAND_DISTRICT_ALL_LABEL
            st.selectbox(
                "เลือกอำเภอ (District)",
                [selected_district],
                disabled=True,
            )
        else:
            districts = get_districts(selected_province)
            dist_options = [PROVINCE_ALL_LABEL] + districts

            default_dist_idx = (
                dist_options.index(DEFAULT_DISTRICT)
                if DEFAULT_DISTRICT in dist_options
                else 0
            )

            selected_district = st.selectbox(
                "เลือกอำเภอ (District)",
                dist_options,
                index=default_dist_idx,
            )

        roi, is_whole_country = get_roi(selected_province, selected_district)

        st.markdown("<hr style='border-color: #1E293B;'>", unsafe_allow_html=True)

        if selected_mode == "General Plan":
            st.markdown("### 🥞 Data Layers (ชั้นข้อมูล)")
            basemap_choice = st.selectbox(
                "🗺️ Basemap (แผนที่ฐาน)",
                ["HYBRID", "SATELLITE", "ROADMAP", "TERRAIN", "OSM"],
            )

            layer_settings = render_general_plan_controls()
            ai_settings = {}
        else:
            basemap_choice = "SATELLITE"
            layer_settings = {}
            ai_settings = render_ai_simulation_controls()

    return {
        "selected_mode": selected_mode,
        "selected_province": selected_province,
        "selected_district": selected_district,
        "is_whole_country": is_whole_country,
        "roi": roi,
        "basemap_choice": basemap_choice,
        "layer_settings": layer_settings,
        "ai_settings": ai_settings,
    }


def render_general_plan_controls() -> dict:
    """Sidebar controls สำหรับโหมด General Plan"""
    settings = {}

    st.markdown("**🌍 ข้อมูลภูมิประเทศ & แหล่งน้ำ**")
    settings["show_cop_dem"] = st.checkbox("⛰️ Copernicus DEM", value=False)
    settings["op_cop_dem"] = (
        st.slider("ความโปร่งแสง DEM", 0.0, 1.0, 0.7)
        if settings["show_cop_dem"]
        else 0.7
    )

    settings["show_dswx_s1"] = st.checkbox("💧 DSWx-S1 (แหล่งน้ำ Radar)", value=False)
    settings["op_dswx_s1"] = (
        st.slider("ความโปร่งแสง DSWx-S1", 0.0, 1.0, 0.7)
        if settings["show_dswx_s1"]
        else 0.7
    )

    settings["show_gfd"] = st.checkbox("🌊 Global Flood Database", value=False)
    settings["op_gfd"] = (
        st.slider("ความโปร่งแสง ประวัติน้ำท่วม", 0.0, 1.0, 0.7)
        if settings["show_gfd"]
        else 0.7
    )

    st.markdown("**🌱 ข้อมูลการใช้ที่ดิน & อากาศ**")
    settings["show_landcover"] = st.checkbox("🟢 ESA Land Cover", value=False)
    settings["op_landcover"] = (
        st.slider("ความโปร่งแสง ESA", 0.0, 1.0, 0.7)
        if settings["show_landcover"]
        else 0.7
    )

    settings["show_dw"] = st.checkbox("🌿 Dynamic World V1", value=False)
    settings["op_dw"] = (
        st.slider("ความโปร่งแสง Dynamic World", 0.0, 1.0, 0.7)
        if settings["show_dw"]
        else 0.7
    )

    settings["show_chirts"] = st.checkbox("🌡️ CHIRTS Max Temp", value=False)
    settings["op_chirts"] = (
        st.slider("ความโปร่งแสง อุณหภูมิ", 0.0, 1.0, 0.7)
        if settings["show_chirts"]
        else 0.7
    )

    st.markdown("**🏙️ ข้อมูลความเป็นเมือง & ประชากร**")
    settings["show_urban"] = st.checkbox("🏢 GHSL: Degree of Urbanization", value=False)
    settings["op_urban"] = (
        st.slider("ความโปร่งแสง ความเป็นเมือง", 0.0, 1.0, 0.7)
        if settings["show_urban"]
        else 0.7
    )

    settings["show_pop"] = st.checkbox("👥 GHSL: Global Population", value=False)
    settings["op_pop"] = (
        st.slider("ความโปร่งแสง ประชากร", 0.0, 1.0, 0.7)
        if settings["show_pop"]
        else 0.7
    )

    return settings


def render_ai_simulation_controls() -> dict:
    """Sidebar controls สำหรับโหมด AI Simulation"""
    st.markdown("### 🏢 1. Import Data")
    uploaded_file = st.file_uploader("Upload Shapefile / KML", type=["zip", "kml"])

    st.markdown("### 🔍 2. Spatial Analysis")
    analysis_type = st.selectbox(
        "Model Type",
        ["Urban Growth Tracking", "Flood Risk Simulation"],
    )

    start_year = None
    if analysis_type == "Urban Growth Tracking":
        start_year = st.slider(
            "เลือกปีเริ่มต้นอดีต",
            min_value=2014,
            max_value=2021,
            value=2015,
        )

    st.markdown("### 📈 3. Predictive Modeling")
    predict_years = st.slider("Forecast Timeline", 1, 30, 10)

    st.markdown("### 🛡️ 4. Engineering Mitigation")
    mitigation_tool = st.radio(
        "Simulation Tools",
        ["กั้นแนวคันดิน", "จำลองฝายชะลอน้ำ", "ปรับแก้ระดับตลิ่ง"],
    )

    run_ai = st.button("▶️ RUN AI ENGINE")

    return {
        "uploaded_file": uploaded_file,
        "analysis_type": analysis_type,
        "start_year": start_year,
        "predict_years": predict_years,
        "mitigation_tool": mitigation_tool,
        "run_ai": run_ai,
    }

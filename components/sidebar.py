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


# ---------------------------------------------------------
# Basemap options
# ต้องสอดคล้องกับ BASEMAP_ALIASES ใน components/map_renderer.py
# ---------------------------------------------------------
BASEMAP_OPTIONS = [
    "OpenStreetMap",
    "Esri Satellite",
    "Esri Topographic",
    "CartoDB Positron",
    "CartoDB Dark",
]


def render_sidebar() -> dict:
    """
    แสดง UI ด้านซ้ายทั้งหมด และคืนค่าการตั้งค่าที่ผู้ใช้เลือก

    Return:
        dict:
            selected_mode
            selected_province
            selected_district
            is_whole_country
            roi
            basemap_choice
            layer_settings
            ai_settings
            suitability_config
    """

    with st.sidebar:
        st.markdown(
            "<h3 style='text-align: center; margin-bottom: 20px;'>⚙️ CONTROL PANEL</h3>",
            unsafe_allow_html=True,
        )

        selected_mode = option_menu(
            menu_title=None,
            options=["General Plan", "AI Simulation", "Suitability Analysis"],
            icons=["map", "cpu", "layers"],
            menu_icon="cast",
            default_index=0,
            styles={
                "container": {
                    "padding": "0!important",
                    "background-color": "#0B132B",
                },
                "icon": {
                    "color": "#00F2FE",
                    "font-size": "18px",
                },
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

        selected_province, selected_district, roi, is_whole_country = render_area_selector()

        st.markdown("<hr style='border-color: #1E293B;'>", unsafe_allow_html=True)

        layer_settings = {}
        ai_settings = {}
        suitability_config = None

        # -------------------------------------------------
        # General Plan Mode
        # -------------------------------------------------
        if selected_mode == "General Plan":
            st.markdown("### 🥞 Data Layers")

            basemap_choice = render_basemap_selector(
                key="general_basemap",
                default="OpenStreetMap",
            )

            layer_settings = render_general_plan_controls()

        # -------------------------------------------------
        # AI Simulation Mode
        # -------------------------------------------------
        elif selected_mode == "AI Simulation":
            st.markdown("### 🤖 AI Simulation")

            basemap_choice = render_basemap_selector(
                key="ai_basemap",
                default="Esri Satellite",
            )

            ai_settings = render_ai_simulation_controls()

        # -------------------------------------------------
        # Suitability Analysis Mode
        # -------------------------------------------------
        elif selected_mode == "Suitability Analysis":
            st.markdown("### 🧭 Suitability Analysis")

            basemap_choice = render_basemap_selector(
                key="suitability_basemap",
                default="Esri Satellite",
            )

            suitability_config = render_suitability_controls()

        else:
            basemap_choice = "OpenStreetMap"

    return {
        "selected_mode": selected_mode,
        "selected_province": selected_province,
        "selected_district": selected_district,
        "is_whole_country": is_whole_country,
        "roi": roi,
        "basemap_choice": basemap_choice,
        "layer_settings": layer_settings,
        "ai_settings": ai_settings,
        "suitability_config": suitability_config,
    }


# ---------------------------------------------------------
# Area selector
# ---------------------------------------------------------
def render_area_selector():
    """
    แสดงตัวเลือกพื้นที่วิเคราะห์ จังหวัด/อำเภอ
    """

    st.markdown("**📍 กำหนดพื้นที่วิเคราะห์**")

    try:
        provinces = get_provinces()
    except Exception as e:
        st.error(f"โหลดรายชื่อจังหวัดไม่สำเร็จ: {e}")
        provinces = []

    provinces_list = [THAILAND_ALL_LABEL] + provinces

    # fallback ถ้า DEFAULT_PROVINCE ไม่มีใน GAUL list
    if DEFAULT_PROVINCE in provinces_list:
        default_prov_idx = provinces_list.index(DEFAULT_PROVINCE)
    elif "Uttaradit" in provinces_list:
        default_prov_idx = provinces_list.index("Uttaradit")
    else:
        default_prov_idx = 0

    selected_province = st.selectbox(
        "เลือกจังหวัด (Province)",
        provinces_list,
        index=default_prov_idx,
        key="selected_province",
    )

    is_whole_country = selected_province == THAILAND_ALL_LABEL

    if is_whole_country:
        selected_district = THAILAND_DISTRICT_ALL_LABEL

        st.selectbox(
            "เลือกอำเภอ (District)",
            [selected_district],
            index=0,
            disabled=True,
            key="selected_district_country",
        )

    else:
        try:
            districts = get_districts(selected_province)
        except Exception as e:
            st.warning(f"โหลดรายชื่ออำเภอไม่สำเร็จ: {e}")
            districts = []

        dist_options = [PROVINCE_ALL_LABEL] + districts

        if DEFAULT_DISTRICT in dist_options:
            default_dist_idx = dist_options.index(DEFAULT_DISTRICT)
        elif "Mueang Uttaradit" in dist_options:
            default_dist_idx = dist_options.index("Mueang Uttaradit")
        else:
            default_dist_idx = 0

        selected_district = st.selectbox(
            "เลือกอำเภอ (District)",
            dist_options,
            index=default_dist_idx,
            key="selected_district",
        )

    try:
        roi, is_whole_country = get_roi(selected_province, selected_district)
    except Exception as e:
        st.error(f"สร้างพื้นที่วิเคราะห์ไม่สำเร็จ: {e}")
        roi = None

    return selected_province, selected_district, roi, is_whole_country


# ---------------------------------------------------------
# Basemap selector
# ---------------------------------------------------------
def render_basemap_selector(key: str, default: str = "OpenStreetMap") -> str:
    """
    Basemap selector ที่ใช้ชื่อ basemap ซึ่งรองรับจริงใน map_renderer.py
    """

    if default in BASEMAP_OPTIONS:
        default_index = BASEMAP_OPTIONS.index(default)
    else:
        default_index = 0

    return st.selectbox(
        "🗺️ Basemap",
        BASEMAP_OPTIONS,
        index=default_index,
        key=key,
    )


# ---------------------------------------------------------
# General Plan controls
# ---------------------------------------------------------
def render_general_plan_controls() -> dict:
    """
    Sidebar controls สำหรับโหมด General Plan
    """

    settings = {}

    st.markdown("**🌍 ภูมิประเทศ / แหล่งน้ำ / ภัยพิบัติ**")

    settings["show_cop_dem"] = st.checkbox(
        "⛰️ Copernicus DEM",
        value=False,
        key="show_cop_dem",
    )
    settings["op_cop_dem"] = (
        st.slider(
            "ความโปร่งแสง DEM",
            0.0,
            1.0,
            0.7,
            0.05,
            key="op_cop_dem",
        )
        if settings["show_cop_dem"]
        else 0.7
    )

    settings["show_dswx_s1"] = st.checkbox(
        "💧 DSWx-S1 แหล่งน้ำ Radar",
        value=False,
        key="show_dswx_s1",
    )
    settings["op_dswx_s1"] = (
        st.slider(
            "ความโปร่งแสง DSWx-S1",
            0.0,
            1.0,
            0.7,
            0.05,
            key="op_dswx_s1",
        )
        if settings["show_dswx_s1"]
        else 0.7
    )

    settings["show_gfd"] = st.checkbox(
        "🌊 Global Flood Database",
        value=False,
        key="show_gfd",
    )
    settings["op_gfd"] = (
        st.slider(
            "ความโปร่งแสง ประวัติน้ำท่วม",
            0.0,
            1.0,
            0.7,
            0.05,
            key="op_gfd",
        )
        if settings["show_gfd"]
        else 0.7
    )

    st.markdown("**🌱 การใช้ที่ดิน / สิ่งแวดล้อม / อากาศ**")

    settings["show_landcover"] = st.checkbox(
        "🟢 ESA Land Cover",
        value=False,
        key="show_landcover",
    )
    settings["op_landcover"] = (
        st.slider(
            "ความโปร่งแสง ESA Land Cover",
            0.0,
            1.0,
            0.7,
            0.05,
            key="op_landcover",
        )
        if settings["show_landcover"]
        else 0.7
    )

    settings["show_dw"] = st.checkbox(
        "🌿 Dynamic World V1",
        value=False,
        key="show_dw",
    )
    settings["op_dw"] = (
        st.slider(
            "ความโปร่งแสง Dynamic World",
            0.0,
            1.0,
            0.7,
            0.05,
            key="op_dw",
        )
        if settings["show_dw"]
        else 0.7
    )

    settings["show_chirts"] = st.checkbox(
        "🌡️ CHIRTS Max Temp",
        value=False,
        key="show_chirts",
    )
    settings["op_chirts"] = (
        st.slider(
            "ความโปร่งแสง อุณหภูมิ",
            0.0,
            1.0,
            0.7,
            0.05,
            key="op_chirts",
        )
        if settings["show_chirts"]
        else 0.7
    )

    st.markdown("**🏙️ เมือง / ประชากร**")

    settings["show_urban"] = st.checkbox(
        "🏢 GHSL Degree of Urbanization",
        value=False,
        key="show_urban",
    )
    settings["op_urban"] = (
        st.slider(
            "ความโปร่งแสง ความเป็นเมือง",
            0.0,
            1.0,
            0.7,
            0.05,
            key="op_urban",
        )
        if settings["show_urban"]
        else 0.7
    )

    settings["show_pop"] = st.checkbox(
        "👥 GHSL Global Population",
        value=False,
        key="show_pop",
    )
    settings["op_pop"] = (
        st.slider(
            "ความโปร่งแสง ประชากร",
            0.0,
            1.0,
            0.7,
            0.05,
            key="op_pop",
        )
        if settings["show_pop"]
        else 0.7
    )

    return settings


# ---------------------------------------------------------
# AI Simulation controls
# ---------------------------------------------------------
def render_ai_simulation_controls() -> dict:
    """
    Sidebar controls สำหรับโหมด AI Simulation

    รองรับ:
    1. Urban Growth Tracking
    2. Flood Risk Simulation
    """

    st.markdown("### 🏢 1. Import Data")

    uploaded_file = st.file_uploader(
        "Upload Shapefile / KML",
        type=["zip", "kml"],
        key="ai_upload_file",
    )

    st.caption(
        "หมายเหตุ: เวอร์ชันนี้ยังใช้ ROI จากจังหวัด/อำเภอเป็นหลัก "
        "ส่วนไฟล์อัปโหลดเตรียมไว้สำหรับพัฒนาขั้นต่อไป"
    )

    st.markdown("### 🔍 2. Spatial Analysis")

    analysis_type = st.selectbox(
        "Model Type",
        ["Urban Growth Tracking", "Flood Risk Simulation"],
        key="ai_analysis_type",
    )

    # ค่า default ต้องมีเสมอ เพื่อให้ return dict ไม่ขาด key
    start_year = 2015
    predict_years = 10
    mitigation_tool = None

    water_level_rise = 2.0
    flood_distance_m = 3000
    flood_max_slope = 10.0

    # -----------------------------------------------------
    # Urban Growth Tracking
    # -----------------------------------------------------
    if analysis_type == "Urban Growth Tracking":
        st.markdown("### 📈 3. Urban Growth Parameters")

        start_year = st.slider(
            "เลือกปีเริ่มต้นอดีต",
            min_value=2014,
            max_value=2021,
            value=2015,
            step=1,
            key="ai_start_year",
        )

        predict_years = st.slider(
            "Forecast Timeline",
            min_value=1,
            max_value=30,
            value=10,
            step=1,
            key="ai_predict_years",
        )

        st.markdown("### 🛡️ 4. Planning Mitigation")

        mitigation_tool = st.radio(
            "Simulation Tools",
            ["กั้นแนวคันดิน", "จำลองฝายชะลอน้ำ", "ปรับแก้ระดับตลิ่ง"],
            key="ai_mitigation_tool",
        )

        with st.expander("ℹ️ คำอธิบาย Urban Growth Tracking", expanded=False):
            st.markdown(
                """
                โมเดลนี้ใช้ดัชนี **NDBI จาก Landsat 8** เพื่อประเมินการเพิ่มขึ้นของพื้นที่สิ่งปลูกสร้างย้อนหลัง
                แล้วสร้างเส้นแนวโน้มเพื่อคาดการณ์การขยายตัวในอนาคต

                **ข้อจำกัด**
                - NDBI อาจสับสนกับพื้นที่ดินโล่งหรือพื้นผิวสะท้อนแสงสูง
                - ผลลัพธ์เหมาะสำหรับการดูแนวโน้มเบื้องต้น ไม่ใช่ขอบเขตสิ่งปลูกสร้างทางกฎหมาย
                """
            )

    # -----------------------------------------------------
    # Flood Risk Simulation
    # -----------------------------------------------------
    elif analysis_type == "Flood Risk Simulation":
        st.markdown("### 🌊 3. Flood Simulation Parameters")

        water_level_rise = st.slider(
            "ระดับน้ำเพิ่มขึ้น / น้ำล้นตลิ่ง (เมตร)",
            min_value=0.0,
            max_value=10.0,
            value=2.0,
            step=0.5,
            key="flood_water_level_rise",
        )

        flood_distance_m = st.slider(
            "ระยะอิทธิพลจากแหล่งน้ำ (เมตร)",
            min_value=500,
            max_value=10000,
            value=3000,
            step=500,
            key="flood_distance_m",
        )

        flood_max_slope = st.slider(
            "ความลาดชันสูงสุดที่น้ำขังได้ (องศา)",
            min_value=2.0,
            max_value=30.0,
            value=10.0,
            step=1.0,
            key="flood_max_slope",
        )

        st.markdown("### 🛡️ 4. Flood Mitigation Scenario")

        mitigation_tool = st.radio(
            "Simulation Tools",
            ["กั้นแนวคันดิน", "จำลองฝายชะลอน้ำ", "ปรับแก้ระดับตลิ่ง"],
            key="flood_mitigation_tool",
        )

        with st.expander("ℹ️ คำอธิบาย Flood Risk Simulation", expanded=False):
            st.markdown(
                """
                โมเดลนี้ใช้แนวคิด **Modified Bathtub Model** เพื่อจำลองพื้นที่ที่มีโอกาสจมน้ำ
                จากระดับน้ำที่เพิ่มขึ้น โดยพิจารณา 3 เงื่อนไขหลัก:

                1. ความสูงภูมิประเทศต่ำกว่าระดับน้ำจำลอง  
                2. ความลาดชันไม่สูงเกินไป  
                3. อยู่ในระยะอิทธิพลจากแหล่งน้ำ  

                พร้อมเปรียบเทียบกับประวัติน้ำท่วมจาก Global Flood Database

                **ข้อจำกัด**
                - ไม่ใช่แบบจำลองไฮดรอลิกเต็มรูปแบบ
                - ยังไม่คำนวณปริมาณฝน ความจุลำน้ำ ระบบระบายน้ำ หรือสิ่งกีดขวางทางน้ำ
                - เหมาะสำหรับการคัดกรองพื้นที่เสี่ยงเบื้องต้นในงานผังเมือง
                """
            )

    run_ai = st.button(
        "▶️ RUN AI ENGINE",
        key="run_ai_engine",
    )

    return {
        "uploaded_file": uploaded_file,
        "analysis_type": analysis_type,
        "start_year": start_year,
        "predict_years": predict_years,
        "mitigation_tool": mitigation_tool,
        "run_ai": run_ai,
        "water_level_rise": water_level_rise,
        "flood_distance_m": flood_distance_m,
        "flood_max_slope": flood_max_slope,
    }


# ---------------------------------------------------------
# Suitability controls
# ---------------------------------------------------------
def render_suitability_controls() -> dict:
    """
    Sidebar controls สำหรับโหมด Suitability Analysis
    """

    st.markdown("### 🧭 Suitability Analysis")
    st.caption("ปรับน้ำหนักปัจจัย ระบบจะ normalize ให้อัตโนมัติ")

    with st.expander("ℹ️ คำอธิบายปัจจัย", expanded=False):
        st.markdown(
            """
            - **Slope**: พื้นที่ราบเหมาะต่อการพัฒนามากกว่า
            - **Flood Risk**: พื้นที่เคยน้ำท่วมบ่อยจะถูกลดคะแนน
            - **Land Cover**: พื้นที่โล่ง/พุ่มไม้เหมาะกว่า ป่า น้ำ และเมืองเดิม
            - **Urbanization**: พื้นที่ชานเมืองได้คะแนนสูง เพราะใกล้โครงสร้างพื้นฐาน
            - **Water Proximity**: ใกล้น้ำในระยะเหมาะสมดี แต่ชิดลำน้ำเกินไปควรจำกัด
            """
        )

    w_slope = st.slider(
        "Slope",
        0.0,
        1.0,
        0.20,
        0.05,
        key="suit_w_slope",
    )

    w_flood = st.slider(
        "Flood Risk",
        0.0,
        1.0,
        0.25,
        0.05,
        key="suit_w_flood",
    )

    w_landcover = st.slider(
        "Land Cover",
        0.0,
        1.0,
        0.25,
        0.05,
        key="suit_w_landcover",
    )

    w_urban = st.slider(
        "Urbanization",
        0.0,
        1.0,
        0.20,
        0.05,
        key="suit_w_urban",
    )

    w_water = st.slider(
        "Water Proximity",
        0.0,
        1.0,
        0.10,
        0.05,
        key="suit_w_water",
    )

    total_weight = w_slope + w_flood + w_landcover + w_urban + w_water

    if total_weight == 0:
        st.warning("น้ำหนักรวมเป็น 0 กรุณาเพิ่มน้ำหนักอย่างน้อย 1 ปัจจัย")
    else:
        st.caption(f"น้ำหนักรวมปัจจุบัน: {total_weight:.2f}")
        st.caption("ระบบจะ normalize น้ำหนักให้อัตโนมัติในขั้นคำนวณ")

    show_factor_layers = st.checkbox(
        "แสดง Factor Layers",
        value=False,
        key="show_factor_layers",
    )

    run_suitability = st.button(
        "▶️ Run Suitability Analysis",
        key="run_suitability_analysis",
    )

    return {
        "weights": {
            "slope": w_slope,
            "flood": w_flood,
            "landcover": w_landcover,
            "urban": w_urban,
            "water": w_water,
        },
        "show_factor_layers": show_factor_layers,
        "run_suitability": run_suitability,
    }

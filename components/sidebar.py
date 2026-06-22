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
from components.local_data_manager import get_registry_asset_ids_by_category


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
            options=["General Plan", "AI Simulation", "Suitability Analysis", "Local Data Manager", "Multi-Agent"],
            icons=["map", "cpu", "layers", "database", "robot"],
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
        multi_agent_settings = None

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

        # -------------------------------------------------
        # Local Data Manager Mode
        # -------------------------------------------------
        elif selected_mode == "Local Data Manager":
            st.markdown("### 🗂️ Local Data Manager")

            basemap_choice = render_basemap_selector(
                key="local_data_basemap",
                default="Esri Satellite",
            )

            st.caption("จัดการ GEE Asset ID และข้อมูลเฉพาะพื้นที่ แล้วนำไปใช้กับ Suitability Analysis")

        # -------------------------------------------------
        # Multi-Agent Mode
        # -------------------------------------------------
        elif selected_mode == "Multi-Agent":
            st.markdown("### 🤖 Multi-Agent")

            basemap_choice = render_basemap_selector(
                key="multi_agent_basemap",
                default="Esri Satellite",
            )

            multi_agent_settings = render_multi_agent_controls()

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
        "multi_agent_settings": multi_agent_settings,
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

    แก้ปัญหา:
    - RUN AI ENGINE ไม่หายหลัง Streamlit rerun
    - ซ่อน Planning Mitigation จาก Urban Growth เพราะยังไม่ถูกใช้ในสมการ
    - เพิ่มปุ่ม Clear AI Result
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

    # -----------------------------------------------------
    # Default values ต้องมีเสมอ เพื่อไม่ให้ return dict ขาด key
    # -----------------------------------------------------
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

        with st.expander("ℹ️ คำอธิบาย Urban Growth Tracking", expanded=False):
             st.markdown(
                """
                โมเดลนี้ใช้ **Hybrid Built-up Detection** เพื่อประเมินพื้นที่สิ่งปลูกสร้างรายปี
                และสร้างแนวโน้มการขยายตัวเมือง

                ระบบไม่ได้ใช้ NDBI เดี่ยว แต่ใช้ตัวกรองร่วมกัน:

                - **Dynamic World Built-up Class / Built Probability**
                - **NDBI** สำหรับช่วยตรวจจับสิ่งปลูกสร้าง
                - **MNDWI** สำหรับตัดพื้นที่น้ำออก
                - **ESA WorldCover Water Mask** สำหรับตัดแหล่งน้ำถาวร
                - **Dynamic World Water Probability** สำหรับกรองน้ำรายปี
                - **NDVI** สำหรับลดความสับสนกับพื้นที่พืชหนาแน่น
                - **Slope Mask** สำหรับลด false positive บนพื้นที่ลาดชัน/ขอบอ่างเก็บน้ำ

                **ข้อจำกัด**
                - ยังไม่ใช่ข้อมูล building footprint รายหลังคา
                - พื้นที่โรงงาน เหมือง ดินโล่ง หรือพื้นผิวสะท้อนแสงสูงบางชนิดอาจยังคลาดเคลื่อนได้
                - เหมาะสำหรับดูแนวโน้มเชิงพื้นที่เบื้องต้น ไม่ใช่ขอบเขตสิ่งปลูกสร้างทางกฎหมาย
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
            "Scenario Option",
            [
                "ยังไม่ใช้มาตรการ",
                "กั้นแนวคันดิน",
                "จำลองฝายชะลอน้ำ",
                "ปรับแก้ระดับตลิ่ง",
            ],
            index=0,
            key="flood_mitigation_tool",
        )

        st.caption(
            "หมายเหตุ: ตัวเลือก mitigation ตอนนี้เป็น scenario label เท่านั้น "
            "ยังไม่ถูกนำไปเปลี่ยนสมการน้ำท่วมโดยตรง"
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

    # -----------------------------------------------------
    # Persistent RUN state
    # -----------------------------------------------------
    if "ai_run_active" not in st.session_state:
        st.session_state["ai_run_active"] = False

    st.markdown("### 🚀 5. Run Model")

    col_run, col_clear = st.columns([2, 1])

    with col_run:
        run_clicked = st.button(
            "▶️ RUN AI ENGINE",
            key="run_ai_engine",
            use_container_width=True,
        )

    with col_clear:
        clear_clicked = st.button(
            "🧹 Clear",
            key="clear_ai_result",
            use_container_width=True,
        )

    if run_clicked:
        st.session_state["ai_run_active"] = True

    if clear_clicked:
        st.session_state["ai_run_active"] = False

        for key in [
            "ai_growth_trend_df",
            "flood_simulation_summary",
        ]:
            if key in st.session_state:
                del st.session_state[key]

    if st.session_state.get("ai_run_active", False):
        st.success("AI Result Active: ระบบจะคงผลวิเคราะห์ไว้จนกว่าจะกด Clear")
    else:
        st.info("กด RUN AI ENGINE เพื่อเริ่มวิเคราะห์")

    return {
        "uploaded_file": uploaded_file,
        "analysis_type": analysis_type,
        "start_year": start_year,
        "predict_years": predict_years,
        "mitigation_tool": mitigation_tool,
        "run_ai": st.session_state.get("ai_run_active", False),
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

    # ดึง Asset ID จาก Local Data Registry มาเติมเป็นค่าเริ่มต้น
    # ทำเฉพาะเมื่อ widget key ยังไม่เคยถูกสร้าง เพื่อไม่ทับค่าที่ผู้ใช้แก้เอง
    if "suit_road_asset_ids" not in st.session_state:
        registry_roads = get_registry_asset_ids_by_category("roads")
        if registry_roads:
            st.session_state["suit_road_asset_ids"] = "\n".join(registry_roads)
            st.session_state["suit_use_road_accessibility"] = True

    if "suit_facility_asset_ids" not in st.session_state:
        registry_facilities = get_registry_asset_ids_by_category("public_facilities")
        if registry_facilities:
            st.session_state["suit_facility_asset_ids"] = "\n".join(registry_facilities)
            st.session_state["suit_use_public_facilities"] = True

    if "suit_forest_asset_ids" not in st.session_state:
        registry_forests = get_registry_asset_ids_by_category("protected_forest")
        if registry_forests:
            st.session_state["suit_forest_asset_ids"] = "\n".join(registry_forests)


    with st.expander("ℹ️ คำอธิบายปัจจัย", expanded=False):
        st.markdown(
            """
            - **Slope**: พื้นที่ราบเหมาะต่อการพัฒนามากกว่า
            - **Flood Risk**: พื้นที่เคยน้ำท่วมบ่อยจะถูกลดคะแนน
            - **Land Cover**: พื้นที่โล่ง/พุ่มไม้เหมาะกว่า ป่า น้ำ และเมืองเดิม
            - **Urbanization**: พื้นที่ชานเมืองได้คะแนนสูง เพราะใกล้โครงสร้างพื้นฐาน
            - **Road Accessibility**: ใกล้ถนนในระยะเหมาะสมจะได้คะแนนสูง ไกลถนนมากจะลดคะแนน
            - **Public Facility Proximity**: ใกล้โรงพยาบาล โรงเรียน ศูนย์ราชการ ตลาด หรือบริการเมืองสำคัญจะได้คะแนนสูง
            - **Water Proximity**: ใกล้น้ำในระยะเหมาะสมดี แต่ชิดลำน้ำเกินไปควรจำกัด
            - **Protected / Forest Constraint**: ป่าอนุรักษ์ ป่าสงวน หรือพื้นที่คุ้มครองถูกกันออกเป็น hard constraint
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
        0.15,
        0.05,
        key="suit_w_urban",
    )

    w_road = st.slider(
        "Road Accessibility",
        0.0,
        1.0,
        0.20,
        0.05,
        key="suit_w_road",
    )

    w_facility = st.slider(
        "Public Facility Proximity",
        0.0,
        1.0,
        0.10,
        0.05,
        key="suit_w_facility",
    )

    w_water = st.slider(
        "Water Proximity",
        0.0,
        1.0,
        0.10,
        0.05,
        key="suit_w_water",
    )

    total_weight = w_slope + w_flood + w_landcover + w_urban + w_road + w_facility + w_water

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


    st.markdown("### 🛣️ Road Accessibility")
    use_road_accessibility = st.checkbox(
        "ใช้ชั้นข้อมูลถนนเป็นปัจจัยวิเคราะห์",
        value=False,
        key="suit_use_road_accessibility",
        help="ต้องใส่ GEE Asset ID ของถนนก่อน ระบบจึงจะนำถนนเข้าคำนวณ",
    )

    road_asset_text = st.text_area(
        "GEE Asset ID ของถนน / โครงข่ายคมนาคม",
        value="",
        key="suit_road_asset_ids",
        height=90,
        placeholder=(
            "ใส่ 1 Asset ID ต่อ 1 บรรทัด เช่น\n"
            "projects/your-project/assets/roads_uttaradit\n"
            "users/yourname/local_roads"
        ),
        help="รองรับ ee.FeatureCollection ที่เป็น line หรือ polygon ของถนนจาก Google Earth Engine Assets",
    )

    road_buffer_m = st.number_input(
        "Buffer เส้นถนนก่อนคำนวณระยะ (เมตร)",
        min_value=0,
        max_value=200,
        value=20,
        step=5,
        key="suit_road_buffer_m",
        help="ช่วยให้เส้นถนน rasterize ชัดขึ้น โดยเฉพาะเส้นถนนจาก shapefile",
    )

    road_max_distance_m = st.number_input(
        "ระยะไกลสุดที่ใช้ประเมินถนน (เมตร)",
        min_value=1000,
        max_value=20000,
        value=5000,
        step=500,
        key="suit_road_max_distance_m",
    )

    road_asset_ids = [
        item.strip()
        for line in road_asset_text.splitlines()
        for item in line.split(",")
        if item.strip()
    ]

    if use_road_accessibility and road_asset_ids:
        st.caption(f"เปิดใช้ Road Accessibility: {len(road_asset_ids)} ชั้นข้อมูล")
    elif use_road_accessibility and not road_asset_ids:
        st.warning("เปิดใช้ถนนแล้ว แต่ยังไม่ได้ใส่ Road Asset ID ระบบจะยังไม่นำถนนเข้าคะแนน")
    else:
        st.caption("ยังไม่ใช้ Road Accessibility ในสมการ")


    st.markdown("### 🏥 Public Facility Proximity")
    use_public_facilities = st.checkbox(
        "ใช้ชั้นข้อมูลบริการสาธารณะเป็นปัจจัยวิเคราะห์",
        value=False,
        key="suit_use_public_facilities",
        help="ใช้กับ GEE Asset ID ของโรงพยาบาล โรงเรียน ศูนย์ราชการ ตลาด สถานีขนส่ง หรือจุดบริการเมือง",
    )

    facility_asset_text = st.text_area(
        "GEE Asset ID ของบริการสาธารณะ / จุดศูนย์กลางเมือง",
        value="",
        key="suit_facility_asset_ids",
        height=90,
        placeholder=(
            "ใส่ 1 Asset ID ต่อ 1 บรรทัด เช่น\n"
            "projects/your-project/assets/public_facilities_uttaradit\n"
            "users/yourname/hospitals_schools_markets"
        ),
        help="รองรับ ee.FeatureCollection ที่เป็น point/line/polygon ของบริการสาธารณะจาก Google Earth Engine Assets",
    )

    facility_buffer_m = st.number_input(
        "Buffer จุดบริการก่อนคำนวณระยะ (เมตร)",
        min_value=0,
        max_value=500,
        value=60,
        step=10,
        key="suit_facility_buffer_m",
        help="ช่วยให้จุดบริการสาธารณะ rasterize ชัดขึ้น โดยเฉพาะข้อมูลจุดจาก POI",
    )

    facility_max_distance_m = st.number_input(
        "ระยะไกลสุดที่ใช้ประเมินบริการสาธารณะ (เมตร)",
        min_value=1000,
        max_value=30000,
        value=10000,
        step=500,
        key="suit_facility_max_distance_m",
    )

    facility_asset_ids = [
        item.strip()
        for line in facility_asset_text.splitlines()
        for item in line.split(",")
        if item.strip()
    ]

    if use_public_facilities and facility_asset_ids:
        st.caption(f"เปิดใช้ Public Facility Proximity: {len(facility_asset_ids)} ชั้นข้อมูล")
    elif use_public_facilities and not facility_asset_ids:
        st.warning("เปิดใช้บริการสาธารณะแล้ว แต่ยังไม่ได้ใส่ Facility Asset ID ระบบจะยังไม่นำเข้าคะแนน")
    else:
        st.caption("ยังไม่ใช้ Public Facility Proximity ในสมการ")

    st.markdown("### 🌲 Protected / Forest Constraints")
    use_wdpa = st.checkbox(
        "ใช้ WDPA Protected Areas เป็นพื้นที่กันออก",
        value=True,
        key="suit_use_wdpa",
        help="ใช้ฐานข้อมูล WCMC/WDPA/current/polygons จาก Google Earth Engine",
    )

    forest_asset_text = st.text_area(
        "GEE Asset ID ของป่าสงวน/ป่าอนุรักษ์/พื้นที่ห้ามพัฒนา",
        value="",
        key="suit_forest_asset_ids",
        height=90,
        placeholder=(
            "ใส่ 1 Asset ID ต่อ 1 บรรทัด เช่น\n"
            "projects/your-project/assets/forest_reserve_uttaradit\n"
            "users/yourname/protected_forest"
        ),
        help="รองรับ ee.FeatureCollection ที่อัปโหลดไว้ใน Google Earth Engine Assets",
    )

    forest_buffer_m = st.number_input(
        "Buffer รอบพื้นที่คุ้มครอง (เมตร)",
        min_value=0,
        max_value=5000,
        value=0,
        step=50,
        key="suit_forest_buffer_m",
        help="ใช้เมื่อต้องการกันชนรอบป่า/พื้นที่คุ้มครอง เช่น 100–500 เมตร",
    )

    forest_asset_ids = [
        item.strip()
        for line in forest_asset_text.splitlines()
        for item in line.split(",")
        if item.strip()
    ]

    if use_wdpa or forest_asset_ids:
        st.caption(
            f"เปิดใช้พื้นที่กันออก: WDPA={'เปิด' if use_wdpa else 'ปิด'}, "
            f"Custom Assets={len(forest_asset_ids)} ชั้นข้อมูล"
        )
    else:
        st.warning("ยังไม่ได้เปิดใช้พื้นที่คุ้มครอง/ป่าสงวนเป็น hard constraint")

    # -------------------------------------------------
    # Persistent RUN state
    # -------------------------------------------------
    # ปัญหาเดิม: st.button() เป็น True แค่รอบเดียว พอ Streamlit rerun
    # จากการซูม/แพนแผนที่ หรือเปลี่ยน widget ผลวิเคราะห์จะหายทันที
    # วิธีแก้: เก็บสถานะ run ไว้ใน session_state จนกว่าจะกด Clear
    if "suitability_run_active" not in st.session_state:
        st.session_state["suitability_run_active"] = False

    st.markdown("### 🚀 Run Model")
    col_run, col_clear = st.columns([2, 1])

    with col_run:
        run_clicked = st.button(
            "▶️ Run Suitability Analysis",
            key="run_suitability_analysis",
            use_container_width=True,
        )

    with col_clear:
        clear_clicked = st.button(
            "🧹 Clear",
            key="clear_suitability_result",
            use_container_width=True,
        )

    if run_clicked:
        st.session_state["suitability_run_active"] = True

    if clear_clicked:
        st.session_state["suitability_run_active"] = False
        for key in [
            "suitability_stats_df",
            "suitability_summary",
            "suitability_config_signature",
            "suitability_final_class",
            "suitability_raw_score",
            "suitability_weights_normalized",
            "candidate_export_geojson_bytes",
            "candidate_export_csv_bytes",
            "candidate_export_df",
            "candidate_export_count",
            "candidate_export_settings",
        ]:
            if key in st.session_state:
                del st.session_state[key]

    if st.session_state.get("suitability_run_active", False):
        st.success("Suitability Result Active: ผลวิเคราะห์จะคงอยู่จนกว่าจะกด Clear")
    else:
        st.info("กด Run เพื่อเริ่มวิเคราะห์")

    return {
        "weights": {
            "slope": w_slope,
            "flood": w_flood,
            "landcover": w_landcover,
            "urban": w_urban,
            "water": w_water,
            "road": w_road,
            "facility": w_facility,
        },
        "show_factor_layers": show_factor_layers,
        "constraint_config": {
            "use_wdpa": use_wdpa,
            "asset_ids": forest_asset_ids,
            "buffer_m": forest_buffer_m,
        },
        "road_config": {
            "enabled": use_road_accessibility,
            "asset_ids": road_asset_ids,
            "buffer_m": road_buffer_m,
            "max_distance_m": road_max_distance_m,
        },
        "facility_config": {
            "enabled": use_public_facilities,
            "asset_ids": facility_asset_ids,
            "buffer_m": facility_buffer_m,
            "max_distance_m": facility_max_distance_m,
        },
        "run_suitability": st.session_state.get("suitability_run_active", False),
        "run_clicked": run_clicked,
        "clear_clicked": clear_clicked,
    }



# ---------------------------------------------------------
# Multi-Agent controls
# ---------------------------------------------------------
def render_multi_agent_controls() -> dict:
    """
    Sidebar controls สำหรับโหมด Multi-Agent

    หลักคิด:
    - GIS Agent ทำงานเสมอเพื่อเป็นฐานความจริง
    - ผู้ใช้เลือก Agent เฉพาะทางที่จะเรียกเพิ่ม
    - Report Agent รวมผลทุกครั้ง
    """

    st.caption("GIS Agent จะทำงานเสมอเพื่อดึง evidence จาก GEE ก่อน")

    selected_agents = st.multiselect(
        "เลือก Agent ที่ต้องการเรียกใช้",
        [
            "Urban Agent",
            "Traffic Agent",
            "Economic Agent",
            "Environment Agent",
            "Gemini Vision Agent",
            "GPT Planning Agent",
        ],
        default=[
            "Urban Agent",
            "Environment Agent",
            "Gemini Vision Agent",
            "GPT Planning Agent",
        ],
        key="multi_agent_selected_agents",
    )

    task = st.text_area(
        "คำถาม / เป้าหมายการวิเคราะห์",
        value=(
            "วิเคราะห์พื้นที่นี้เพื่อประเมินความเหมาะสมในการพัฒนาเมือง "
            "โดยพิจารณาความลาดชัน น้ำท่วม การใช้ที่ดิน โครงสร้างเมือง "
            "และเสนอแนวทาง zoning พร้อมข้อควรสำรวจภาคสนาม"
        ),
        height=150,
        key="multi_agent_task",
    )

    local_data_note = st.text_area(
        "ข้อมูลเฉพาะพื้นที่เพิ่มเติม เช่น ถนน โครงการ ผังสี ข้อจำกัดท้องถิ่น",
        value="",
        height=100,
        key="multi_agent_local_note",
    )

    with st.expander("🗺️ Evidence Layers บนแผนที่", expanded=False):
        show_cop_dem = st.checkbox("DEM", value=True, key="ma_show_cop_dem")
        show_gfd = st.checkbox("Global Flood Database", value=True, key="ma_show_gfd")
        show_landcover = st.checkbox("ESA Land Cover", value=True, key="ma_show_landcover")
        show_urban = st.checkbox("GHSL Urbanization", value=True, key="ma_show_urban")
        show_dswx_s1 = st.checkbox("DSWx-S1 Water", value=False, key="ma_show_dswx_s1")
        show_dw = st.checkbox("Dynamic World", value=False, key="ma_show_dw")
        show_chirts = st.checkbox("CHIRTS Temperature", value=False, key="ma_show_chirts")
        show_pop = st.checkbox("GHSL Population", value=False, key="ma_show_pop")

    col_run, col_clear = st.columns([2, 1])

    with col_run:
        run_multi_agent = st.button(
            "▶️ Run Multi-Agent",
            key="run_multi_agent",
            use_container_width=True,
        )

    with col_clear:
        clear_multi_agent = st.button(
            "🧹 Clear",
            key="clear_multi_agent",
            use_container_width=True,
        )

    if clear_multi_agent and "multi_agent_outputs" in st.session_state:
        del st.session_state["multi_agent_outputs"]

    return {
        "selected_agents": selected_agents,
        "task": task,
        "local_data_note": local_data_note,
        "run_multi_agent": run_multi_agent,
        "evidence_layers": {
            "show_cop_dem": show_cop_dem,
            "show_gfd": show_gfd,
            "show_landcover": show_landcover,
            "show_urban": show_urban,
            "show_dswx_s1": show_dswx_s1,
            "show_dw": show_dw,
            "show_chirts": show_chirts,
            "show_pop": show_pop,
        },
    }

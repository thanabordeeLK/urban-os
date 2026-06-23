
def _is_probable_gee_asset_id(asset_id: str) -> bool:
    asset_id = str(asset_id or "").strip()
    lowered = asset_id.lower()

    if not asset_id:
        return False
    if lowered.startswith("http://") or lowered.startswith("https://"):
        return False
    if "code.earthengine.google.com" in lowered:
        return False
    if " " in asset_id:
        return False

    return asset_id.startswith("projects/") or asset_id.startswith("users/")


def _split_valid_invalid_asset_ids(text: str) -> tuple[list[str], list[str]]:
    raw_items = [
        item.strip()
        for line in str(text or "").splitlines()
        for item in line.split(",")
        if item.strip()
    ]

    valid = [item for item in raw_items if _is_probable_gee_asset_id(item)]
    invalid = [item for item in raw_items if not _is_probable_gee_asset_id(item)]

    return list(dict.fromkeys(valid)), list(dict.fromkeys(invalid))


def _render_invalid_asset_warning(label: str, invalid_items: list[str]) -> None:
    if not invalid_items:
        return

    st.error(
        f"{label}: พบค่าที่ไม่ใช่ GEE Asset ID จริง "
        "อย่าใช้ URL จากปุ่ม Get Link ของ Code Editor ให้ใช้ path ที่ขึ้นต้นด้วย projects/.../assets/... หรือ users/..."
    )

    for item in invalid_items[:3]:
        st.code(item, language="text")



import streamlit as st
from datetime import date
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
from config.planning_standards import (
    get_standard_profile,
    get_suitability_weight_preset,
    get_road_defaults,
    get_public_facility_defaults,
    get_restrictive_area_defaults,
    get_uhi_defaults,
    get_density_reference,
    get_psa_residential_factors,
)


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
    # Default state containers for all modes
    # Prevent UnboundLocalError when returning state from modes that do not use every config group.
    suitability_config = {}
    multi_agent_settings = {}
    uhi_settings = {}
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
            options=["General Plan", "AI Simulation", "Suitability Analysis", "Urban Heat Island", "Local Data Manager", "Multi-Agent"],
            icons=["map", "cpu", "layers", "thermometer-half", "database", "robot"],
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
        # Urban Heat Island Mode
        # -------------------------------------------------
        elif selected_mode == "Urban Heat Island":
            st.markdown("### 🌡️ Urban Heat Island")

            basemap_choice = render_basemap_selector(
                key="uhi_basemap",
                default="Esri Satellite",
            )

            uhi_settings = render_uhi_controls()

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
        "uhi_settings": uhi_settings,
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
# Planning standards preset helpers
# ---------------------------------------------------------
def apply_dpt_suitability_preset_to_session() -> None:
    weights = get_suitability_weight_preset()
    road_defaults = get_road_defaults()
    facility_defaults = get_public_facility_defaults()
    restrictive_defaults = get_restrictive_area_defaults()

    st.session_state["suit_w_slope"] = float(weights.get("slope", 0.10))
    st.session_state["suit_w_flood"] = float(weights.get("flood", 0.20))
    st.session_state["suit_w_landcover"] = float(weights.get("landcover", 0.15))
    st.session_state["suit_w_urban"] = float(weights.get("urban", 0.10))
    st.session_state["suit_w_road"] = float(weights.get("road", 0.20))
    st.session_state["suit_w_facility"] = float(weights.get("facility", 0.20))
    st.session_state["suit_w_water"] = float(weights.get("water", 0.05))

    st.session_state["suit_road_buffer_m"] = int(road_defaults.get("buffer_m", 20))
    st.session_state["suit_road_max_distance_m"] = int(road_defaults.get("max_distance_m", 5000))

    st.session_state["suit_facility_buffer_m"] = int(facility_defaults.get("buffer_m", 60))
    st.session_state["suit_facility_max_distance_m"] = int(facility_defaults.get("max_distance_m", 10000))

    st.session_state["suit_use_wdpa"] = bool(restrictive_defaults.get("use_wdpa", True))
    st.session_state["suit_forest_buffer_m"] = int(restrictive_defaults.get("forest_buffer_m", 100))

    st.session_state["show_factor_layers"] = False
    st.session_state["planning_standard_profile_applied"] = get_standard_profile().get("profile_id")


def render_planning_standard_profile_box(context: str = "suitability") -> None:
    profile = get_standard_profile()

    with st.expander("📘 Planning Standards Profile", expanded=False):
        st.markdown(f"**{profile.get('profile_name_th')}**")
        st.caption(profile.get("description", ""))

        if context == "suitability":
            st.markdown("**PSA / Residential Potential Factors ที่นำมาใช้กับโมเดล**")
            for factor in get_psa_residential_factors()[:15]:
                st.markdown(f"- {factor}")

            st.markdown("**Community Density Reference (ตัวอย่าง)**")
            density_ref = get_density_reference()
            small_city = density_ref.get("เมืองขนาดเล็ก", {})
            for key, val in small_city.items():
                st.caption(f"{key}: {val} คน/ไร่")

        elif context == "uhi":
            st.markdown(
                """
                UHI ใช้เป็น climate/livability evidence layer เพื่อสนับสนุนแนวคิดเมืองน่าอยู่ 
                เมืองสีเขียว และแผนแหล่งทรัพยากรธรรมชาติและสิ่งแวดล้อม
                """
            )

        st.warning(
            "Preset นี้เป็นค่าเริ่มต้นเพื่อช่วยวิเคราะห์ ไม่ใช่ข้อกำหนดกฎหมายสำเร็จรูป "
            "ต้องตรวจสอบกับผังเมืองรวมและข้อมูลพื้นที่จริงอีกครั้ง"
        )


def apply_dpt_uhi_preset_to_session() -> None:
    defaults = get_uhi_defaults()
    today_year = date.today().year
    analysis_year = today_year - 1 if today_year >= 2024 else 2025

    st.session_state["uhi_start_date"] = date(
        analysis_year,
        int(defaults.get("start_month", 3)),
        int(defaults.get("start_day", 1)),
    )
    st.session_state["uhi_end_date"] = date(
        analysis_year,
        int(defaults.get("end_month", 5)),
        int(defaults.get("end_day", 31)),
    )
    st.session_state["uhi_composite_method"] = defaults.get("composite_method", "median")
    st.session_state["uhi_risk_mode"] = defaults.get("risk_mode", "relative")
    st.session_state["uhi_cloud_cover_max"] = int(defaults.get("cloud_cover_max", 60))
    st.session_state["uhi_use_landsat8"] = bool(defaults.get("use_landsat8", True))
    st.session_state["uhi_use_landsat9"] = bool(defaults.get("use_landsat9", True))
    st.session_state["uhi_show_lst_layer"] = bool(defaults.get("show_lst_layer", True))
    st.session_state["uhi_show_heat_risk_layer"] = bool(defaults.get("show_heat_risk_layer", True))
    st.session_state["uhi_show_hotspot_layer"] = bool(defaults.get("show_hotspot_layer", True))
    st.session_state["planning_standard_uhi_profile_applied"] = get_standard_profile().get("profile_id")


# ---------------------------------------------------------
# Suitability controls
# ---------------------------------------------------------
def render_suitability_controls() -> dict:
    """
    Sidebar controls สำหรับโหมด Suitability Analysis
    """

    st.markdown("### 🧭 Suitability Analysis")
    st.caption("ปรับน้ำหนักปัจจัย ระบบจะ normalize ให้อัตโนมัติ")

    render_planning_standard_profile_box(context="suitability")

    col_std_a, col_std_b = st.columns([2, 1])
    with col_std_a:
        apply_standard_clicked = st.button(
            "📘 Apply DPT Standards Preset",
            key="apply_dpt_standards_preset",
            use_container_width=True,
            help="ตั้งค่าน้ำหนัก/ระยะถนน/ระยะบริการ/พื้นที่กันออก ตาม standard profile",
        )
    with col_std_b:
        if st.session_state.get("planning_standard_profile_applied"):
            st.success("Applied")

    if apply_standard_clicked:
        apply_dpt_suitability_preset_to_session()
        st.success("ใช้ค่า DPT Standards Preset แล้ว")
        st.rerun()

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
        0.10,
        0.05,
        key="suit_w_slope",
    )

    w_flood = st.slider(
        "Flood Risk",
        0.0,
        1.0,
        0.20,
        0.05,
        key="suit_w_flood",
    )

    w_landcover = st.slider(
        "Land Cover",
        0.0,
        1.0,
        0.15,
        0.05,
        key="suit_w_landcover",
    )

    w_urban = st.slider(
        "Urbanization",
        0.0,
        1.0,
        0.10,
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
        0.20,
        0.05,
        key="suit_w_facility",
    )

    w_water = st.slider(
        "Water Proximity",
        0.0,
        1.0,
        0.05,
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

    road_asset_ids, invalid_road_asset_ids = _split_valid_invalid_asset_ids(road_asset_text)
    _render_invalid_asset_warning("Road Asset ID", invalid_road_asset_ids)

    if use_road_accessibility and road_asset_ids:
        st.caption(f"เปิดใช้ Road Accessibility: {len(road_asset_ids)} ชั้นข้อมูล")
    elif use_road_accessibility and invalid_road_asset_ids:
        st.warning("เปิดใช้ถนนแล้ว แต่ค่าที่ใส่ไม่ใช่ Asset ID ระบบจะยังไม่นำถนนเข้าคะแนน")
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

    facility_asset_ids, invalid_facility_asset_ids = _split_valid_invalid_asset_ids(facility_asset_text)
    _render_invalid_asset_warning("Facility Asset ID", invalid_facility_asset_ids)

    if use_public_facilities and facility_asset_ids:
        st.caption(f"เปิดใช้ Public Facility Proximity: {len(facility_asset_ids)} ชั้นข้อมูล")
    elif use_public_facilities and invalid_facility_asset_ids:
        st.warning("เปิดใช้บริการสาธารณะแล้ว แต่ค่าที่ใส่ไม่ใช่ Asset ID ระบบจะยังไม่นำเข้าคะแนน")
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
        value=100,
        step=50,
        key="suit_forest_buffer_m",
        help="ใช้เมื่อต้องการกันชนรอบป่า/พื้นที่คุ้มครอง เช่น 100–500 เมตร",
    )

    forest_asset_ids, invalid_forest_asset_ids = _split_valid_invalid_asset_ids(forest_asset_text)
    _render_invalid_asset_warning("Forest / Constraint Asset ID", invalid_forest_asset_ids)

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
# Urban Heat Island controls
# ---------------------------------------------------------
def render_uhi_controls() -> dict:
    """
    Sidebar controls สำหรับโหมด Urban Heat Island / Land Surface Temperature
    """

    st.caption("ดึง Landsat 8/9 LST จาก Google Earth Engine เพื่อวิเคราะห์ความร้อนผิวดิน")

    with st.expander("ℹ️ UHI Method", expanded=False):
        st.markdown(
            """
            - ใช้ Landsat 8/9 Collection 2 Level 2
            - Band หลักคือ `ST_B10`
            - แปลงเป็น Land Surface Temperature หน่วย Celsius
            - กรองเมฆ/เงาเมฆด้วย `QA_PIXEL`
            - Heat Risk แบบ Relative แบ่งจาก percentile ภายในพื้นที่ศึกษา
            """
        )

    st.markdown("### 🗓️ Time Window")
    col_start, col_end = st.columns(2)

    with col_start:
        start_date = st.date_input(
            "Start date",
            value=date(2025, 3, 1),
            key="uhi_start_date",
        )

    with col_end:
        end_date = st.date_input(
            "End date",
            value=date(2025, 5, 31),
            key="uhi_end_date",
        )

    composite_method = st.selectbox(
        "Composite method",
        ["median", "mean", "max"],
        index=0,
        key="uhi_composite_method",
        help="median เสถียรสุดสำหรับแผนที่ทั่วไป, max ใช้ดูความร้อนสูงสุดแต่เสี่ยง noise",
    )

    risk_mode = st.selectbox(
        "Heat Risk Classification",
        ["relative", "absolute"],
        index=0,
        key="uhi_risk_mode",
        help="relative = แบ่งตาม percentile ในพื้นที่ศึกษา, absolute = แบ่งตาม °C คงที่",
    )

    cloud_cover_max = st.slider(
        "Cloud cover max (%)",
        0,
        100,
        60,
        5,
        key="uhi_cloud_cover_max",
    )

    st.markdown("### 🛰️ Landsat Sources")
    use_landsat8 = st.checkbox("Landsat 8", value=True, key="uhi_use_landsat8")
    use_landsat9 = st.checkbox("Landsat 9", value=True, key="uhi_use_landsat9")

    st.markdown("### 🗺️ Display Layers")
    show_lst_layer = st.checkbox("แสดง LST Celsius", value=True, key="uhi_show_lst_layer")
    lst_opacity = st.slider("LST opacity", 0.0, 1.0, 0.75, 0.05, key="uhi_lst_opacity")

    show_heat_risk_layer = st.checkbox("แสดง Heat Risk Class", value=True, key="uhi_show_heat_risk_layer")
    heat_risk_opacity = st.slider("Heat Risk opacity", 0.0, 1.0, 0.72, 0.05, key="uhi_heat_risk_opacity")

    show_hotspot_layer = st.checkbox("แสดง Hotspot Class 5", value=True, key="uhi_show_hotspot_layer")

    calculate_stats = st.checkbox(
        "คำนวณสถิติพื้นที่ความร้อน",
        value=True,
        key="uhi_calculate_stats",
    )

    col_run, col_clear = st.columns([2, 1])

    with col_run:
        run_uhi = st.button(
            "▶️ Run UHI Analysis",
            key="run_uhi_analysis",
            use_container_width=True,
        )

    with col_clear:
        clear_uhi = st.button(
            "🧹 Clear",
            key="clear_uhi_analysis",
            use_container_width=True,
        )

    if clear_uhi:
        for key in [
            "uhi_run_active",
            "uhi_lst_image",
            "uhi_heat_risk_image",
            "uhi_image_count",
            "uhi_settings",
            "uhi_lst_summary",
            "uhi_heat_area_df",
            "uhi_heat_summary",
        ]:
            st.session_state.pop(key, None)
        st.success("ล้างผล UHI แล้ว")

    if run_uhi:
        st.session_state["uhi_run_active"] = True

    if st.session_state.get("uhi_run_active", False):
        st.success("UHI Result Active: ผลวิเคราะห์จะคงอยู่จนกว่าจะกด Clear")

    return {
        "start_date": str(start_date),
        "end_date": str(end_date),
        "composite_method": composite_method,
        "risk_mode": risk_mode,
        "cloud_cover_max": cloud_cover_max,
        "use_landsat8": use_landsat8,
        "use_landsat9": use_landsat9,
        "show_lst_layer": show_lst_layer,
        "lst_opacity": lst_opacity,
        "show_heat_risk_layer": show_heat_risk_layer,
        "heat_risk_opacity": heat_risk_opacity,
        "show_hotspot_layer": show_hotspot_layer,
        "calculate_stats": calculate_stats,
        "run_uhi": run_uhi,
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

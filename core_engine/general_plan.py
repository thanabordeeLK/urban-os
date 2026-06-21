import streamlit as st
import ee

from config.datasets import DATASET_CATALOG, VIS_PARAMS, LEGENDS
from components.map_renderer import add_custom_legend
from services.gee_service import safe_clip
from services.statistics_service import calculate_esa_landcover_statistics


# ---------------------------------------------------------
# Fallback dataset catalog
# ใช้กรณี config.datasets.DATASET_CATALOG ไม่มีบาง key
# ---------------------------------------------------------
FALLBACK_DATASET_CATALOG = {
    "copernicus_dem": {"id": "COPERNICUS/DEM/GLO30"},
    "dswx_s1": {"id": "OPERA/DSWX/L3_V1/S1"},
    "global_flood_db": {"id": "GLOBAL_FLOOD_DB/MODIS_EVENTS/V1"},
    "esa_worldcover": {"id": "ESA/WorldCover/v200"},
    "dynamic_world": {"id": "GOOGLE/DYNAMICWORLD/V1"},
    "chirts": {"id": "UCSB-CHG/CHIRTS/DAILY"},
    "ghsl_smod": {"id": "JRC/GHSL/P2023A/GHS_SMOD_V2-0/2030"},
    "ghsl_pop": {"id": "JRC/GHSL/P2023A/GHS_POP/2020"},
}


# ---------------------------------------------------------
# Fallback visual parameters
# ใช้กรณี config.datasets.VIS_PARAMS ไม่มีบาง key
# ---------------------------------------------------------
FALLBACK_VIS_PARAMS = {
    "copernicus_dem": {
        "min": 0,
        "max": 1000,
        "palette": ["006633", "E5FFCC", "662A00", "D8D8D8", "F5F5F5"],
    },
    "dswx_s1": {
        "min": 0,
        "max": 5,
        "palette": ["ffffff", "0000ff", "0088ff", "f2f2f2", "dfdfdf", "da00ff"],
    },
    "global_flood_db": {
        "min": 0,
        "max": 10,
        "palette": ["c3effe", "1341e8", "051cb0", "001133"],
    },
    "esa_worldcover_display": {
        "min": 0,
        "max": 10,
        "palette": [
            "006400",  # 0 Trees
            "ffbb22",  # 1 Shrubland
            "ffff4c",  # 2 Grassland
            "f096ff",  # 3 Cropland
            "fa0000",  # 4 Built-up
            "b4b4b4",  # 5 Bare / sparse vegetation
            "f0f0f0",  # 6 Snow and ice
            "0064c8",  # 7 Permanent water bodies
            "0096a0",  # 8 Herbaceous wetland
            "00cf75",  # 9 Mangroves
            "fae6a0",  # 10 Moss and lichen
        ],
    },
    "dynamic_world": {
        "min": 0,
        "max": 8,
        "palette": [
            "419bdf",  # Water
            "397d49",  # Trees
            "88b053",  # Grass
            "7a87c6",  # Flooded vegetation
            "e49635",  # Crops
            "dfc35a",  # Shrub & scrub
            "c4281b",  # Built area
            "a59b8f",  # Bare ground
            "b39fe1",  # Snow & ice
        ],
    },
    "chirts": {
        "min": 20,
        "max": 40,
        "palette": [
            "00008b",
            "0000ff",
            "00ffff",
            "008000",
            "ffff00",
            "ffa500",
            "ff0000",
            "8b0000",
        ],
    },
    "ghsl_smod_display": {
        "min": 0,
        "max": 7,
        "palette": [
            "419bdf",  # 0 Water
            "ffffcc",  # 1 Very rural
            "c2e699",  # 2 Rural cluster
            "78c679",  # 3 Low density rural
            "31a354",  # 4 Suburban
            "006837",  # 5 Semi-dense
            "fd8d3c",  # 6 Dense cluster
            "bd0026",  # 7 Urban centre
        ],
    },
    "ghsl_pop": {
        "min": 0.0,
        "max": 100.0,
        "palette": [
            "000004",
            "320A5A",
            "781B6C",
            "BB3654",
            "EC6824",
            "FBB41A",
            "FCFFA4",
        ],
    },
}


# ---------------------------------------------------------
# Fallback legends
# ใช้ในกรณี config.datasets.LEGENDS ยังไม่มี key บางตัว
# ---------------------------------------------------------
FALLBACK_LEGENDS = {
    "copernicus_dem": {
        "DEM: พื้นที่ต่ำ": "006633",
        "DEM: พื้นที่ราบ/เนินต่ำ": "E5FFCC",
        "DEM: พื้นที่สูง": "662A00",
        "DEM: ภูเขาสูง": "D8D8D8",
    },
    "dswx_s1": {
        "DSWx-S1: น้ำผิวดิน": "0000ff",
        "DSWx-S1: น้ำท่วมขัง/น้ำชั่วคราว": "0088ff",
        "DSWx-S1: ไม่มีข้อมูล/เงา/เมฆ": "dfdfdf",
    },
    "global_flood_db": {
        "Flood History: น้ำท่วมสะสมต่ำ": "c3effe",
        "Flood History: น้ำท่วมสะสมปานกลาง": "1341e8",
        "Flood History: น้ำท่วมสะสมสูง": "001133",
    },
    "esa_worldcover": {
        "ESA: ป่าไม้ / Trees": "006400",
        "ESA: พุ่มไม้ / Shrubland": "ffbb22",
        "ESA: ทุ่งหญ้า / Grassland": "ffff4c",
        "ESA: เกษตรกรรม / Cropland": "f096ff",
        "ESA: เมือง / Built-up": "fa0000",
        "ESA: ดินโล่ง / Bare ground": "b4b4b4",
        "ESA: แหล่งน้ำ / Water": "0064c8",
        "ESA: พื้นที่ชุ่มน้ำ / Wetland": "0096a0",
        "ESA: ป่าชายเลน / Mangroves": "00cf75",
    },
    "dynamic_world": {
        "DW: น้ำ / Water": "419bdf",
        "DW: ต้นไม้ / Trees": "397d49",
        "DW: หญ้า / Grass": "88b053",
        "DW: พืชน้ำ/น้ำท่วม / Flooded vegetation": "7a87c6",
        "DW: พืชเกษตร / Crops": "e49635",
        "DW: พุ่มไม้ / Shrub & scrub": "dfc35a",
        "DW: สิ่งปลูกสร้าง / Built area": "c4281b",
        "DW: ดินโล่ง / Bare ground": "a59b8f",
    },
    "chirts": {
        "CHIRTS: อุณหภูมิต่ำ": "00008b",
        "CHIRTS: อุณหภูมิปานกลาง": "ffff00",
        "CHIRTS: อุณหภูมิสูง": "ff0000",
        "CHIRTS: อุณหภูมิสูงมาก": "8b0000",
    },
    "ghsl_smod": {
        "GHSL: น้ำ": "419bdf",
        "GHSL: พื้นที่ชนบทมาก": "ffffcc",
        "GHSL: ชุมชนชนบท": "c2e699",
        "GHSL: ชานเมือง": "31a354",
        "GHSL: เมืองกึ่งหนาแน่น": "006837",
        "GHSL: กลุ่มเมืองหนาแน่น": "fd8d3c",
        "GHSL: ศูนย์กลางเมืองหนาแน่น": "bd0026",
    },
    "ghsl_pop": {
        "Population: ความหนาแน่นต่ำ": "320A5A",
        "Population: ความหนาแน่นปานกลาง": "BB3654",
        "Population: ความหนาแน่นสูง": "FBB41A",
        "Population: ความหนาแน่นสูงมาก": "FCFFA4",
    },
}


# ---------------------------------------------------------
# Helper functions
# ---------------------------------------------------------
def get_dataset_id(key: str) -> str:
    """
    ดึง dataset id จาก config.datasets.DATASET_CATALOG
    ถ้าไม่มีให้ใช้ fallback
    """
    if key in DATASET_CATALOG and "id" in DATASET_CATALOG[key]:
        return DATASET_CATALOG[key]["id"]

    return FALLBACK_DATASET_CATALOG[key]["id"]


def get_vis_params(key: str) -> dict:
    """
    ดึง visual parameters จาก config.datasets.VIS_PARAMS
    ถ้าไม่มี หรือเป็น dict ว่าง ให้ใช้ fallback
    """
    vis = VIS_PARAMS.get(key)

    if isinstance(vis, dict) and len(vis) > 0:
        return vis

    return FALLBACK_VIS_PARAMS.get(key, {})


def get_legend(key: str) -> dict:
    """
    ดึง legend จาก config.datasets.LEGENDS
    ถ้าไม่มี หรือเป็น dict ว่าง ให้ใช้ fallback legend
    """
    legend = LEGENDS.get(key)

    if isinstance(legend, dict) and len(legend) > 0:
        return legend

    return FALLBACK_LEGENDS.get(key, {})


# ---------------------------------------------------------
# Main layer controller
# ---------------------------------------------------------
def add_general_plan_layers(
    Map,
    roi,
    is_whole_country: bool,
    layer_settings: dict,
) -> dict:
    """
    เพิ่ม layer ทั้งหมดของโหมด General Plan

    Returns:
        dict: master_legend
    """

    master_legend = {}
    landcover = None

    # -----------------------------------------------------
    # Copernicus DEM
    # -----------------------------------------------------
    if layer_settings.get("show_cop_dem"):
        try:
            add_copernicus_dem(
                Map=Map,
                roi=roi,
                is_whole_country=is_whole_country,
                opacity=layer_settings.get("op_cop_dem", 0.7),
            )
            master_legend.update(get_legend("copernicus_dem"))
        except Exception as exc:
            st.warning(f"โหลด Copernicus DEM ไม่สำเร็จ: {exc}")

    # -----------------------------------------------------
    # DSWx-S1
    # -----------------------------------------------------
    if layer_settings.get("show_dswx_s1"):
        try:
            add_dswx_s1(
                Map=Map,
                roi=roi,
                is_whole_country=is_whole_country,
                opacity=layer_settings.get("op_dswx_s1", 0.7),
            )
            master_legend.update(get_legend("dswx_s1"))
        except Exception as exc:
            st.warning(f"โหลด DSWx-S1 ไม่สำเร็จ: {exc}")

    # -----------------------------------------------------
    # Global Flood Database
    # -----------------------------------------------------
    if layer_settings.get("show_gfd"):
        try:
            add_global_flood_database(
                Map=Map,
                roi=roi,
                is_whole_country=is_whole_country,
                opacity=layer_settings.get("op_gfd", 0.7),
            )
            master_legend.update(get_legend("global_flood_db"))
        except Exception as exc:
            st.warning(f"โหลด Global Flood Database ไม่สำเร็จ: {exc}")

    # -----------------------------------------------------
    # ESA WorldCover
    # -----------------------------------------------------
    if layer_settings.get("show_landcover"):
        try:
            landcover = add_esa_landcover(
                Map=Map,
                roi=roi,
                is_whole_country=is_whole_country,
                opacity=layer_settings.get("op_landcover", 0.7),
            )
            master_legend.update(get_legend("esa_worldcover"))
        except Exception as exc:
            st.warning(f"โหลด ESA Land Cover ไม่สำเร็จ: {exc}")

    # -----------------------------------------------------
    # Dynamic World
    # -----------------------------------------------------
    if layer_settings.get("show_dw"):
        try:
            add_dynamic_world(
                Map=Map,
                roi=roi,
                is_whole_country=is_whole_country,
                opacity=layer_settings.get("op_dw", 0.7),
            )
            master_legend.update(get_legend("dynamic_world"))
        except Exception as exc:
            st.warning(f"โหลด Dynamic World ไม่สำเร็จ: {exc}")

    # -----------------------------------------------------
    # CHIRTS Max Temperature
    # -----------------------------------------------------
    if layer_settings.get("show_chirts"):
        try:
            add_chirts_max_temp(
                Map=Map,
                roi=roi,
                is_whole_country=is_whole_country,
                opacity=layer_settings.get("op_chirts", 0.7),
            )
            master_legend.update(get_legend("chirts"))
        except Exception as exc:
            st.warning(f"โหลด CHIRTS Max Temperature ไม่สำเร็จ: {exc}")

    # -----------------------------------------------------
    # GHSL Urbanization
    # -----------------------------------------------------
    if layer_settings.get("show_urban"):
        try:
            add_ghsl_urbanization(
                Map=Map,
                roi=roi,
                is_whole_country=is_whole_country,
                opacity=layer_settings.get("op_urban", 0.7),
            )
            master_legend.update(get_legend("ghsl_smod"))
        except Exception as exc:
            st.warning(f"โหลด GHSL Urbanization ไม่สำเร็จ: {exc}")

    # -----------------------------------------------------
    # GHSL Population
    # -----------------------------------------------------
    if layer_settings.get("show_pop"):
        try:
            add_ghsl_population(
                Map=Map,
                roi=roi,
                is_whole_country=is_whole_country,
                opacity=layer_settings.get("op_pop", 0.7),
            )
            master_legend.update(get_legend("ghsl_pop"))
        except Exception as exc:
            st.warning(f"โหลด GHSL Population ไม่สำเร็จ: {exc}")

    # -----------------------------------------------------
    # Custom Legend
    # -----------------------------------------------------
    if master_legend:
        add_custom_legend(
            Map=Map,
            title="คำอธิบายชั้นข้อมูล",
            legend_dict=master_legend,
            position="bottomright",
        )

    render_landcover_stats_button(
        landcover=landcover,
        roi=roi,
        is_whole_country=is_whole_country,
        show_landcover=layer_settings.get("show_landcover", False),
    )

    return master_legend


# ---------------------------------------------------------
# Layer functions
# ---------------------------------------------------------
def add_copernicus_dem(Map, roi, is_whole_country: bool, opacity: float) -> None:
    dem = (
        ee.ImageCollection(get_dataset_id("copernicus_dem"))
        .select("DEM")
        .mosaic()
    )

    dem = safe_clip(dem, roi, is_whole_country)

    Map.addLayer(
        dem,
        get_vis_params("copernicus_dem"),
        "Copernicus DEM 30m",
        opacity=opacity,
    )


def add_dswx_s1(Map, roi, is_whole_country: bool, opacity: float) -> None:
    img = (
        ee.ImageCollection(get_dataset_id("dswx_s1"))
        .filterBounds(roi)
        .filterDate("2022-01-01", "2024-12-31")
        .mosaic()
        .select("WTR_Water_classification")
    )

    img = safe_clip(img, roi, is_whole_country)

    wtr_remapped = img.remap(
        [0, 1, 2, 252, 253, 254],
        [0, 1, 2, 3, 4, 5],
    )

    Map.addLayer(
        wtr_remapped,
        get_vis_params("dswx_s1"),
        "DSWx-S1 Water Classification",
        opacity=opacity,
    )


def add_global_flood_database(Map, roi, is_whole_country: bool, opacity: float) -> None:
    gfd_flooded_sum = (
        ee.ImageCollection(get_dataset_id("global_flood_db"))
        .filterBounds(roi)
        .select("flooded")
        .sum()
    )

    gfd_flooded_sum = safe_clip(gfd_flooded_sum, roi, is_whole_country)

    Map.addLayer(
        gfd_flooded_sum.selfMask(),
        get_vis_params("global_flood_db"),
        "Global Flood Database",
        opacity=opacity,
    )


def add_esa_landcover(Map, roi, is_whole_country: bool, opacity: float):
    """
    ESA WorldCover:
    - ใช้ภาพ original สำหรับคำนวณสถิติ
    - ใช้ remap 0..10 สำหรับแสดงผล categorical palette ให้สีตรง legend
    """

    landcover = (
        ee.ImageCollection(get_dataset_id("esa_worldcover"))
        .first()
        .select("Map")
    )

    landcover = safe_clip(landcover, roi, is_whole_country)

    esa_display = landcover.remap(
        [10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 100],
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    ).rename("ESA_WorldCover_Display")

    Map.addLayer(
        esa_display,
        get_vis_params("esa_worldcover_display"),
        "ESA WorldCover 2021",
        opacity=opacity,
    )

    return landcover


def add_dynamic_world(Map, roi, is_whole_country: bool, opacity: float) -> None:
    dw_image = (
        ee.ImageCollection(get_dataset_id("dynamic_world"))
        .filterBounds(roi)
        .filterDate("2023-01-01", "2024-01-01")
        .select("label")
        .mode()
    )

    dw_image = safe_clip(dw_image, roi, is_whole_country)

    Map.addLayer(
        dw_image,
        get_vis_params("dynamic_world"),
        "Dynamic World Land Cover",
        opacity=opacity,
    )


def add_chirts_max_temp(Map, roi, is_whole_country: bool, opacity: float) -> None:
    max_temp = (
        ee.ImageCollection(get_dataset_id("chirts"))
        .filter(ee.Filter.date("2016-05-01", "2016-05-31"))
        .select("maximum_temperature")
        .mean()
    )

    max_temp = safe_clip(max_temp, roi, is_whole_country)

    Map.addLayer(
        max_temp,
        get_vis_params("chirts"),
        "CHIRTS Maximum Temperature",
        opacity=opacity,
    )


def add_ghsl_urbanization(Map, roi, is_whole_country: bool, opacity: float) -> None:
    """
    GHSL SMOD:
    - ใช้ smod_code original
    - remap เป็น 0..7 เพื่อแสดงสีแบบ categorical
    """

    urban_image = (
        ee.Image(get_dataset_id("ghsl_smod"))
        .select("smod_code")
    )

    urban_image = safe_clip(urban_image, roi, is_whole_country)

    urban_display = urban_image.remap(
        [10, 11, 12, 13, 21, 22, 23, 30],
        [0, 1, 2, 3, 4, 5, 6, 7],
    ).rename("GHSL_SMOD_Display")

    Map.addLayer(
        urban_display,
        get_vis_params("ghsl_smod_display"),
        "GHSL Degree of Urbanization",
        opacity=opacity,
    )


def add_ghsl_population(Map, roi, is_whole_country: bool, opacity: float) -> None:
    pop_image = ee.Image(get_dataset_id("ghsl_pop"))

    pop_image = safe_clip(pop_image, roi, is_whole_country)
    pop_image = pop_image.updateMask(pop_image.gt(0))

    Map.addLayer(
        pop_image,
        get_vis_params("ghsl_pop"),
        "GHSL Population",
        opacity=opacity,
    )


# ---------------------------------------------------------
# Statistics
# ---------------------------------------------------------
def render_landcover_stats_button(
    landcover,
    roi,
    is_whole_country: bool,
    show_landcover: bool,
) -> None:
    """
    ปุ่มคำนวณสถิติพื้นที่จาก ESA Land Cover
    """

    st.sidebar.markdown("<hr style='border-color: #1E293B;'>", unsafe_allow_html=True)

    if not show_landcover:
        return

    if st.sidebar.button("📈 คำนวณสถิติพื้นที่", key="calculate_landcover_stats"):
        if landcover is None:
            st.sidebar.warning("กรุณาเปิด ESA Land Cover ก่อนคำนวณ")
            return

        with st.spinner("AI กำลังสแกนพื้นที่..."):
            try:
                calc_scale = 1000 if is_whole_country else 100

                df, summary = calculate_esa_landcover_statistics(
                    landcover=landcover,
                    roi=roi,
                    scale=calc_scale,
                )

                if df.empty:
                    st.sidebar.warning("ไม่พบข้อมูลสถิติพื้นที่")
                    return

                st.session_state["esa_landcover_stats_df"] = df
                st.session_state["esa_indicator_summary"] = summary

                st.sidebar.bar_chart(
                    df.set_index("ประเภทพื้นที่")["ขนาด (ไร่)"]
                )
                st.sidebar.success("คำนวณสถิติพื้นที่สำเร็จ")

            except Exception as exc:
                st.sidebar.error(f"คำนวณสถิติพื้นที่ไม่สำเร็จ: {exc}")

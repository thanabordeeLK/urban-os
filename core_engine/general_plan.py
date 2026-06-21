import streamlit as st
import ee

from config.datasets import DATASET_CATALOG, VIS_PARAMS, LEGENDS
from components.map_renderer import add_custom_legend
from services.gee_service import safe_clip
from services.statistics_service import calculate_esa_landcover_statistics


# ---------------------------------------------------------
# Fallback dataset catalog
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
# Classified visual parameters
# สีในนี้ต้องตรงกับ legend เสมอ
# ---------------------------------------------------------
FALLBACK_VIS_PARAMS = {
    "copernicus_dem_class": {
        "min": 1,
        "max": 5,
        "palette": [
            "1a9850",  # 1 ต่ำมาก
            "91cf60",  # 2 ต่ำ
            "ffffbf",  # 3 ปานกลาง
            "fc8d59",  # 4 สูง
            "d73027",  # 5 สูงมาก
        ],
    },
    "dswx_s1": {
        "min": 0,
        "max": 5,
        "palette": [
            "ffffff",
            "0000ff",
            "0088ff",
            "f2f2f2",
            "dfdfdf",
            "da00ff",
        ],
    },
    "global_flood_db_class": {
        "min": 1,
        "max": 4,
        "palette": [
            "f7fbff",  # 1 ไม่พบประวัติน้ำท่วม
            "9ecae1",  # 2 น้ำท่วมต่ำ
            "3182bd",  # 3 น้ำท่วมปานกลาง
            "08519c",  # 4 น้ำท่วมสูง
        ],
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
    "chirts_class": {
        "min": 1,
        "max": 5,
        "palette": [
            "0000ff",  # 1 < 24°C
            "00ffff",  # 2 24–28°C
            "ffff00",  # 3 28–32°C
            "ff0000",  # 4 32–36°C
            "8b0000",  # 5 > 36°C
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
    "ghsl_pop_class": {
        "min": 1,
        "max": 5,
        "palette": [
            "ffffcc",  # 1 ต่ำมาก
            "c2e699",  # 2 ต่ำ
            "78c679",  # 3 ปานกลาง
            "31a354",  # 4 สูง
            "006837",  # 5 สูงมาก
        ],
    },
}


# ---------------------------------------------------------
# Classified legends
# legend ต้องตรงกับ class และสีใน FALLBACK_VIS_PARAMS
# ---------------------------------------------------------
FALLBACK_LEGENDS = {
    "copernicus_dem_class": {
        "DEM: 0–50 ม. พื้นที่ต่ำ": "1a9850",
        "DEM: 50–200 ม. ที่ราบ/เนินต่ำ": "91cf60",
        "DEM: 200–500 ม. เนินเขา": "ffffbf",
        "DEM: 500–1,000 ม. พื้นที่สูง": "fc8d59",
        "DEM: > 1,000 ม. ภูเขาสูง": "d73027",
    },
    "dswx_s1": {
        "DSWx-S1: น้ำผิวดิน": "0000ff",
        "DSWx-S1: น้ำท่วมขัง/น้ำชั่วคราว": "0088ff",
        "DSWx-S1: ไม่มีข้อมูล/เงา/เมฆ": "dfdfdf",
    },
    "global_flood_db_class": {
        "Flood: ไม่พบประวัติน้ำท่วม": "f7fbff",
        "Flood: ท่วม 1–2 ครั้ง": "9ecae1",
        "Flood: ท่วม 3–5 ครั้ง": "3182bd",
        "Flood: ท่วมมากกว่า 5 ครั้ง": "08519c",
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
    "chirts_class": {
        "CHIRTS: < 24°C ต่ำมาก": "0000ff",
        "CHIRTS: 24–28°C ต่ำ/ค่อนข้างเย็น": "00ffff",
        "CHIRTS: 28–32°C ปานกลาง": "ffff00",
        "CHIRTS: 32–36°C สูง": "ff0000",
        "CHIRTS: > 36°C สูงมาก": "8b0000",
    },
    "ghsl_smod": {
        "GHSL: น้ำ": "419bdf",
        "GHSL: พื้นที่ชนบทมาก": "ffffcc",
        "GHSL: ชุมชนชนบท": "c2e699",
        "GHSL: ชนบทความหนาแน่นต่ำ": "78c679",
        "GHSL: ชานเมือง": "31a354",
        "GHSL: เมืองกึ่งหนาแน่น": "006837",
        "GHSL: กลุ่มเมืองหนาแน่น": "fd8d3c",
        "GHSL: ศูนย์กลางเมืองหนาแน่น": "bd0026",
    },
    "ghsl_pop_class": {
        "Population: 1–10 คน/พิกเซล ต่ำมาก": "ffffcc",
        "Population: 10–50 คน/พิกเซล ต่ำ": "c2e699",
        "Population: 50–100 คน/พิกเซล ปานกลาง": "78c679",
        "Population: 100–500 คน/พิกเซล สูง": "31a354",
        "Population: > 500 คน/พิกเซล สูงมาก": "006837",
    },
}


# ---------------------------------------------------------
# Helper functions
# ---------------------------------------------------------
def get_dataset_id(key: str) -> str:
    if key in DATASET_CATALOG and "id" in DATASET_CATALOG[key]:
        return DATASET_CATALOG[key]["id"]

    return FALLBACK_DATASET_CATALOG[key]["id"]


def get_vis_params(key: str) -> dict:
    """
    ใช้ fallback ก่อนสำหรับ classified layer
    เพื่อป้องกัน config เก่าดึง continuous palette มาใช้ผิด
    """
    if key in FALLBACK_VIS_PARAMS:
        return FALLBACK_VIS_PARAMS[key]

    vis = VIS_PARAMS.get(key)

    if isinstance(vis, dict) and len(vis) > 0:
        return vis

    return {}


def get_legend(key: str) -> dict:
    """
    ใช้ fallback ก่อนสำหรับ classified legend
    เพื่อให้ legend ตรงกับ classified layer เสมอ
    """
    if key in FALLBACK_LEGENDS:
        return FALLBACK_LEGENDS[key]

    legend = LEGENDS.get(key)

    if isinstance(legend, dict) and len(legend) > 0:
        return legend

    return {}


# ---------------------------------------------------------
# Main layer controller
# ---------------------------------------------------------
def add_general_plan_layers(
    Map,
    roi,
    is_whole_country: bool,
    layer_settings: dict,
) -> dict:
    master_legend = {}
    landcover = None

    if layer_settings.get("show_cop_dem"):
        try:
            add_copernicus_dem(
                Map=Map,
                roi=roi,
                is_whole_country=is_whole_country,
                opacity=layer_settings.get("op_cop_dem", 0.7),
            )
            master_legend.update(get_legend("copernicus_dem_class"))
        except Exception as exc:
            st.warning(f"โหลด Copernicus DEM ไม่สำเร็จ: {exc}")

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

    if layer_settings.get("show_gfd"):
        try:
            add_global_flood_database(
                Map=Map,
                roi=roi,
                is_whole_country=is_whole_country,
                opacity=layer_settings.get("op_gfd", 0.7),
            )
            master_legend.update(get_legend("global_flood_db_class"))
        except Exception as exc:
            st.warning(f"โหลด Global Flood Database ไม่สำเร็จ: {exc}")

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

    if layer_settings.get("show_chirts"):
        try:
            add_chirts_max_temp(
                Map=Map,
                roi=roi,
                is_whole_country=is_whole_country,
                opacity=layer_settings.get("op_chirts", 0.7),
            )
            master_legend.update(get_legend("chirts_class"))
        except Exception as exc:
            st.warning(f"โหลด CHIRTS Max Temperature ไม่สำเร็จ: {exc}")

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

    if layer_settings.get("show_pop"):
        try:
            add_ghsl_population(
                Map=Map,
                roi=roi,
                is_whole_country=is_whole_country,
                opacity=layer_settings.get("op_pop", 0.7),
            )
            master_legend.update(get_legend("ghsl_pop_class"))
        except Exception as exc:
            st.warning(f"โหลด GHSL Population ไม่สำเร็จ: {exc}")

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
# Layer functions: classified continuous layers
# ---------------------------------------------------------
def add_copernicus_dem(Map, roi, is_whole_country: bool, opacity: float) -> None:
    dem = (
        ee.ImageCollection(get_dataset_id("copernicus_dem"))
        .select("DEM")
        .mosaic()
    )

    dem = safe_clip(dem, roi, is_whole_country)

    dem_class = (
        ee.Image(1)
        .where(dem.gte(50), 2)
        .where(dem.gte(200), 3)
        .where(dem.gte(500), 4)
        .where(dem.gte(1000), 5)
        .rename("DEM_Class")
    )

    Map.addLayer(
        dem_class,
        get_vis_params("copernicus_dem_class"),
        "Copernicus DEM Classified",
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
    flood_sum = (
        ee.ImageCollection(get_dataset_id("global_flood_db"))
        .filterBounds(roi)
        .select("flooded")
        .sum()
    )

    flood_sum = safe_clip(flood_sum, roi, is_whole_country)

    flood_class = (
        ee.Image(1)
        .where(flood_sum.gt(0), 2)
        .where(flood_sum.gt(2), 3)
        .where(flood_sum.gt(5), 4)
        .rename("Flood_History_Class")
    )

    Map.addLayer(
        flood_class,
        get_vis_params("global_flood_db_class"),
        "Global Flood Database Classified",
        opacity=opacity,
    )


def add_esa_landcover(Map, roi, is_whole_country: bool, opacity: float):
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

    temp_class = (
        ee.Image(1)
        .where(max_temp.gte(24), 2)
        .where(max_temp.gte(28), 3)
        .where(max_temp.gte(32), 4)
        .where(max_temp.gte(36), 5)
        .rename("CHIRTS_Temp_Class")
    )

    Map.addLayer(
        temp_class,
        get_vis_params("chirts_class"),
        "CHIRTS Max Temp Classified",
        opacity=opacity,
    )


def add_ghsl_urbanization(Map, roi, is_whole_country: bool, opacity: float) -> None:
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

    pop_class = (
        ee.Image(1)
        .where(pop_image.gte(10), 2)
        .where(pop_image.gte(50), 3)
        .where(pop_image.gte(100), 4)
        .where(pop_image.gte(500), 5)
        .rename("GHSL_Population_Class")
    )

    pop_class = pop_class.updateMask(pop_image.gt(0))

    Map.addLayer(
        pop_class,
        get_vis_params("ghsl_pop_class"),
        "GHSL Population Classified",
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

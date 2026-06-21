import streamlit as st
import ee

from config.datasets import DATASET_CATALOG, VIS_PARAMS, LEGENDS
from components.map_renderer import add_custom_legend
from services.gee_service import safe_clip
from services.statistics_service import calculate_esa_landcover_statistics


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
        "DSWx-S1: พื้นที่ไม่มีข้อมูล/เมฆ/เงา": "dfdfdf",
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
        "GHSL: พื้นที่ชนบทมาก": "ffffcc",
        "GHSL: ชุมชนชนบท": "c2e699",
        "GHSL: ชานเมือง": "78c679",
        "GHSL: เมืองกึ่งหนาแน่น": "31a354",
        "GHSL: ศูนย์กลางเมืองหนาแน่น": "006837",
    },
    "ghsl_pop": {
        "Population: ความหนาแน่นต่ำ": "320A5A",
        "Population: ความหนาแน่นปานกลาง": "BB3654",
        "Population: ความหนาแน่นสูง": "FBB41A",
        "Population: ความหนาแน่นสูงมาก": "FCFFA4",
    },
}


def get_vis_params(key: str) -> dict:
    """
    ดึง visual parameters จาก config.datasets.VIS_PARAMS
    ถ้าไม่มี key ให้คืนค่า empty dict เพื่อป้องกัน KeyError
    """
    return VIS_PARAMS.get(key, {})


def get_legend(key: str) -> dict:
    """
    ดึง legend จาก config.datasets.LEGENDS
    ถ้าไม่มีให้ใช้ fallback legend
    """
    if key in LEGENDS:
        return LEGENDS[key]

    return FALLBACK_LEGENDS.get(key, {})


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
        ee.ImageCollection(DATASET_CATALOG["copernicus_dem"]["id"])
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
        ee.ImageCollection(DATASET_CATALOG["dswx_s1"]["id"])
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
        ee.ImageCollection(DATASET_CATALOG["global_flood_db"]["id"])
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
    landcover = (
        ee.ImageCollection(DATASET_CATALOG["esa_worldcover"]["id"])
        .first()
        .select("Map")
    )

    landcover = safe_clip(landcover, roi, is_whole_country)

    Map.addLayer(
        landcover,
        get_vis_params("esa_worldcover"),
        "ESA WorldCover 2021",
        opacity=opacity,
    )

    return landcover


def add_dynamic_world(Map, roi, is_whole_country: bool, opacity: float) -> None:
    dw_image = (
        ee.ImageCollection(DATASET_CATALOG["dynamic_world"]["id"])
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
        ee.ImageCollection(DATASET_CATALOG["chirts"]["id"])
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
    urban_image = (
        ee.Image(DATASET_CATALOG["ghsl_smod"]["id"])
        .select("smod_code")
    )

    urban_image = safe_clip(urban_image, roi, is_whole_country)

    Map.addLayer(
        urban_image,
        get_vis_params("ghsl_smod"),
        "GHSL Degree of Urbanization",
        opacity=opacity,
    )


def add_ghsl_population(Map, roi, is_whole_country: bool, opacity: float) -> None:
    pop_image = ee.Image(DATASET_CATALOG["ghsl_pop"]["id"])

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

import streamlit as st
import ee

from config.datasets import DATASET_CATALOG, VIS_PARAMS, LEGENDS
from services.gee_service import safe_clip
from services.statistics_service import calculate_esa_landcover_statistics


def add_general_plan_layers(Map, roi, is_whole_country: bool, layer_settings: dict) -> dict:
    """
    เพิ่ม layer ทั้งหมดของโหมด General Plan

    Returns:
        dict: master_legend
    """
    master_legend = {}

    if layer_settings.get("show_cop_dem"):
        add_copernicus_dem(
            Map,
            roi,
            is_whole_country,
            layer_settings.get("op_cop_dem", 0.7),
        )

    if layer_settings.get("show_dswx_s1"):
        try:
            add_dswx_s1(
                Map,
                roi,
                is_whole_country,
                layer_settings.get("op_dswx_s1", 0.7),
            )
            master_legend.update(LEGENDS["dswx_s1"])
        except Exception as exc:
            st.warning(f"โหลด DSWx-S1 ไม่สำเร็จ: {exc}")

    if layer_settings.get("show_gfd"):
        try:
            add_global_flood_database(
                Map,
                roi,
                is_whole_country,
                layer_settings.get("op_gfd", 0.7),
            )
        except Exception as exc:
            st.warning(f"โหลด Global Flood Database ไม่สำเร็จ: {exc}")

    landcover = None
    if layer_settings.get("show_landcover"):
        landcover = add_esa_landcover(
            Map,
            roi,
            is_whole_country,
            layer_settings.get("op_landcover", 0.7),
        )
        master_legend.update(LEGENDS["esa_worldcover"])

    if layer_settings.get("show_dw"):
        add_dynamic_world(
            Map,
            roi,
            is_whole_country,
            layer_settings.get("op_dw", 0.7),
        )
        master_legend.update(LEGENDS["dynamic_world"])

    if layer_settings.get("show_chirts"):
        add_chirts_max_temp(
            Map,
            roi,
            is_whole_country,
            layer_settings.get("op_chirts", 0.7),
        )

    if layer_settings.get("show_urban"):
        add_ghsl_urbanization(
            Map,
            roi,
            is_whole_country,
            layer_settings.get("op_urban", 0.7),
        )
        master_legend.update(LEGENDS["ghsl_smod"])

    if layer_settings.get("show_pop"):
        add_ghsl_population(
            Map,
            roi,
            is_whole_country,
            layer_settings.get("op_pop", 0.7),
        )

    if master_legend:
        try:
            Map.add_legend(title="สัญลักษณ์", legend_dict=master_legend)
        except Exception:
            pass

    render_landcover_stats_button(
        landcover=landcover,
        roi=roi,
        is_whole_country=is_whole_country,
        show_landcover=layer_settings.get("show_landcover", False),
    )

    return master_legend


def add_copernicus_dem(Map, roi, is_whole_country: bool, opacity: float) -> None:
    dem = ee.ImageCollection(DATASET_CATALOG["copernicus_dem"]["id"]).select("DEM").mosaic()
    dem = safe_clip(dem, roi, is_whole_country)
    Map.addLayer(dem, VIS_PARAMS["copernicus_dem"], "Copernicus DEM 30m", opacity=opacity)


def add_dswx_s1(Map, roi, is_whole_country: bool, opacity: float) -> None:
    img = (
        ee.ImageCollection(DATASET_CATALOG["dswx_s1"]["id"])
        .filterBounds(roi)
        .filterDate("2022-01-01", "2024-12-31")
        .mosaic()
        .select("WTR_Water_classification")
    )
    img = safe_clip(img, roi, is_whole_country)
    wtr_remapped = img.remap([0, 1, 2, 252, 253, 254], [0, 1, 2, 3, 4, 5])
    Map.addLayer(wtr_remapped, VIS_PARAMS["dswx_s1"], "DSWx-S1", opacity=opacity)


def add_global_flood_database(Map, roi, is_whole_country: bool, opacity: float) -> None:
    gfd_flooded_sum = (
        ee.ImageCollection(DATASET_CATALOG["global_flood_db"]["id"])
        .filterBounds(roi)
        .select("flooded")
        .sum()
    )
    gfd_flooded_sum = safe_clip(gfd_flooded_sum, roi, is_whole_country)
    Map.addLayer(gfd_flooded_sum.selfMask(), VIS_PARAMS["global_flood_db"], "GFD Flood", opacity=opacity)


def add_esa_landcover(Map, roi, is_whole_country: bool, opacity: float):
    landcover = ee.ImageCollection(DATASET_CATALOG["esa_worldcover"]["id"]).first()
    landcover = safe_clip(landcover, roi, is_whole_country)
    Map.addLayer(landcover, {}, "ESA Land Use", opacity=opacity)
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
    Map.addLayer(dw_image, VIS_PARAMS["dynamic_world"], "Dynamic World", opacity=opacity)


def add_chirts_max_temp(Map, roi, is_whole_country: bool, opacity: float) -> None:
    max_temp = (
        ee.ImageCollection(DATASET_CATALOG["chirts"]["id"])
        .filter(ee.Filter.date("2016-05-01", "2016-05-31"))
        .select("maximum_temperature")
        .mean()
    )
    max_temp = safe_clip(max_temp, roi, is_whole_country)
    Map.addLayer(max_temp, VIS_PARAMS["chirts"], "CHIRTS Temp", opacity=opacity)


def add_ghsl_urbanization(Map, roi, is_whole_country: bool, opacity: float) -> None:
    urban_image = ee.Image(DATASET_CATALOG["ghsl_smod"]["id"]).select("smod_code")
    urban_image = safe_clip(urban_image, roi, is_whole_country)
    Map.addLayer(urban_image, {}, "Urbanization", opacity=opacity)


def add_ghsl_population(Map, roi, is_whole_country: bool, opacity: float) -> None:
    pop_image = ee.Image(DATASET_CATALOG["ghsl_pop"]["id"])
    pop_image = safe_clip(pop_image, roi, is_whole_country)
    pop_image = pop_image.updateMask(pop_image.gt(0))
    Map.addLayer(pop_image, VIS_PARAMS["ghsl_pop"], "Population", opacity=opacity)


def render_landcover_stats_button(landcover, roi, is_whole_country: bool, show_landcover: bool) -> None:
    """ปุ่มคำนวณสถิติพื้นที่จาก ESA Land Cover"""
    st.sidebar.markdown("<hr style='border-color: #1E293B;'>", unsafe_allow_html=True)

    if not show_landcover:
        return

    if st.sidebar.button("📈 คำนวณสถิติพื้นที่"):
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

                st.sidebar.bar_chart(df.set_index("ประเภทพื้นที่")["ขนาด (ไร่)"])
                st.sidebar.success("คำนวณสถิติพื้นที่สำเร็จ")
            except Exception as exc:
                st.sidebar.error(f"คำนวณสถิติพื้นที่ไม่สำเร็จ: {exc}")

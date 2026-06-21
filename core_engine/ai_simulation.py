import streamlit as st
import ee
import pandas as pd

from components.map_renderer import add_custom_legend
from services.gee_service import safe_clip


# ---------------------------------------------------------
# Dataset IDs
# ---------------------------------------------------------
DATASETS = {
    "landsat8": "LANDSAT/LC08/C02/T1_TOA",
    "dynamic_world": "GOOGLE/DYNAMICWORLD/V1",
    "copernicus_dem": "COPERNICUS/DEM/GLO30",
    "esa_worldcover": "ESA/WorldCover/v200",
    "global_flood_db": "GLOBAL_FLOOD_DB/MODIS_EVENTS/V1",
}


# ---------------------------------------------------------
# Utility
# ---------------------------------------------------------
def get_roi_geometry(roi):
    """
    คืน geometry สำหรับ reduceRegion
    รองรับ ee.FeatureCollection / ee.Feature / ee.Geometry
    """
    try:
        return roi.geometry()
    except Exception:
        return roi


def get_reduce_scale(is_whole_country: bool, local_scale: int = 100) -> int:
    """
    ปรับ scale ให้เหมาะกับขนาดพื้นที่
    ถ้าทั้งประเทศใช้ scale ใหญ่ขึ้นเพื่อลดภาระ GEE
    """
    return 1000 if is_whole_country else local_scale


def safe_number(value, default=0):
    """
    แปลงค่าที่อาจเป็น None ให้เป็นตัวเลข
    """
    if value is None:
        return default

    try:
        return float(value)
    except Exception:
        return default


def reset_ai_outputs():
    """
    ล้างผล AI เดิมใน session_state
    ใช้กรณีเปลี่ยน mode หรือ clear result จาก sidebar
    """
    for key in [
        "ai_growth_trend_df",
        "ai_growth_summary",
        "flood_simulation_summary",
        "ai_active_analysis_type",
    ]:
        if key in st.session_state:
            del st.session_state[key]


# ---------------------------------------------------------
# Main router
# ---------------------------------------------------------
def run_ai_simulation_if_requested(
    Map,
    roi,
    is_whole_country: bool,
    ai_settings: dict,
):
    """
    Router หลักของโหมด AI Simulation

    รองรับ:
    1. Urban Growth Tracking
    2. Flood Risk Simulation
    """

    analysis_type = ai_settings.get("analysis_type")
    run_ai = ai_settings.get("run_ai", False)

    st.session_state["current_ai_analysis_type"] = analysis_type

    if not run_ai:
        return None

    st.session_state["ai_active_analysis_type"] = analysis_type

    if analysis_type == "Urban Growth Tracking":
        return run_urban_growth_tracking(
            Map=Map,
            roi=roi,
            is_whole_country=is_whole_country,
            ai_settings=ai_settings,
        )

    if analysis_type == "Flood Risk Simulation":
        run_flood_risk_simulation(
            Map=Map,
            roi=roi,
            is_whole_country=is_whole_country,
            ai_settings=ai_settings,
        )
        return None

    st.warning("ยังไม่รองรับ Simulation ประเภทนี้")
    return None


# ---------------------------------------------------------
# Built-up Detection Helper
# ---------------------------------------------------------
def get_yearly_builtup_image(
    year: int,
    roi,
    is_whole_country: bool,
) -> ee.Image:
    """
    Hybrid Built-up Detection สำหรับ Urban Growth Tracking

    ไม่ใช้ NDBI เดี่ยว เพราะ NDBI สับสนกับ:
    - ดินแห้ง
    - ตะกอนริมอ่างเก็บน้ำ
    - ทราย / ลูกรัง
    - พื้นที่โล่งสะท้อนแสงสูง

    ใช้ตัวกรองร่วมกัน:
    1. Dynamic World Built-up class / built probability
    2. Landsat NDBI เพื่อช่วยยืนยันสิ่งปลูกสร้าง
    3. Landsat MNDWI เพื่อตัดน้ำ
    4. ESA WorldCover เพื่อตัดแหล่งน้ำถาวร
    5. Dynamic World water probability เพื่อตัดน้ำรายปี
    6. NDVI เพื่อตัดพืชหนาแน่น
    7. Slope เพื่อลด false positive บนภูเขา/ขอบอ่างเก็บน้ำ
    """

    # -----------------------------------------------------
    # 1. Landsat 8 indices: NDBI, MNDWI, NDVI
    # -----------------------------------------------------
    landsat = (
        ee.ImageCollection(DATASETS["landsat8"])
        .filterBounds(roi)
        .filterDate(f"{year}-01-01", f"{year}-12-31")
        .filter(ee.Filter.lt("CLOUD_COVER", 30))
    )

    def calc_indices(img):
        ndbi = img.normalizedDifference(["B6", "B5"]).rename("NDBI")
        mndwi = img.normalizedDifference(["B3", "B6"]).rename("MNDWI")
        ndvi = img.normalizedDifference(["B5", "B4"]).rename("NDVI")
        return img.addBands([ndbi, mndwi, ndvi])

    indices = ee.Image(
        ee.Algorithms.If(
            landsat.size().gt(0),
            landsat.map(calc_indices).select(["NDBI", "MNDWI", "NDVI"]).median(),
            ee.Image.constant([0, 1, 1]).rename(["NDBI", "MNDWI", "NDVI"]),
        )
    )

    indices = safe_clip(indices, roi, is_whole_country)

    ndbi = indices.select("NDBI")
    mndwi = indices.select("MNDWI")
    ndvi = indices.select("NDVI")

    # -----------------------------------------------------
    # 2. Dynamic World built-up / water
    # -----------------------------------------------------
    dw = (
        ee.ImageCollection(DATASETS["dynamic_world"])
        .filterBounds(roi)
        .filterDate(f"{year}-01-01", f"{year}-12-31")
    )

    dw_label_mode = ee.Image(
        ee.Algorithms.If(
            dw.size().gt(0),
            dw.select("label").mode(),
            ee.Image(0).rename("label"),
        )
    )

    dw_built_prob = ee.Image(
        ee.Algorithms.If(
            dw.size().gt(0),
            dw.select("built").mean(),
            ee.Image(0).rename("built"),
        )
    )

    dw_water_prob = ee.Image(
        ee.Algorithms.If(
            dw.size().gt(0),
            dw.select("water").mean(),
            ee.Image(1).rename("water"),
        )
    )

    dw_label_mode = safe_clip(dw_label_mode, roi, is_whole_country)
    dw_built_prob = safe_clip(dw_built_prob, roi, is_whole_country)
    dw_water_prob = safe_clip(dw_water_prob, roi, is_whole_country)

    # Dynamic World label:
    # 0 = water
    # 6 = built
    built_from_dw = dw_label_mode.eq(6)

    # ใช้ NDBI เป็นตัวช่วย ไม่ใช่ตัวตัดสินเดี่ยว
    built_from_ndbi_confirmed = (
        ndbi.gt(0.08)
        .And(dw_built_prob.gte(0.25))
    )

    built_candidate = built_from_dw.Or(built_from_ndbi_confirmed)

    # -----------------------------------------------------
    # 3. ESA WorldCover hard masks
    # -----------------------------------------------------
    esa_lc = (
        ee.ImageCollection(DATASETS["esa_worldcover"])
        .first()
        .select("Map")
    )

    esa_lc = safe_clip(esa_lc, roi, is_whole_country)

    # ESA classes:
    # 80 = water
    # 90 = wetland
    # 95 = mangroves
    esa_water_or_wetland = (
        esa_lc.eq(80)
        .Or(esa_lc.eq(90))
        .Or(esa_lc.eq(95))
    )

    # -----------------------------------------------------
    # 4. DEM / Slope mask
    # -----------------------------------------------------
    dem = (
        ee.ImageCollection(DATASETS["copernicus_dem"])
        .select("DEM")
        .mosaic()
    )

    dem = safe_clip(dem, roi, is_whole_country)

    slope = ee.Terrain.slope(dem)

    # -----------------------------------------------------
    # 5. Hybrid filter rules
    # -----------------------------------------------------
    not_water = (
        esa_water_or_wetland.Not()
        .And(dw_label_mode.neq(0))
        .And(dw_water_prob.lt(0.35))
        .And(mndwi.lt(0.0))
    )

    not_dense_vegetation = ndvi.lt(0.65)

    reasonable_slope = slope.lt(20)

    built_up = (
        built_candidate
        .And(not_water)
        .And(not_dense_vegetation)
        .And(reasonable_slope)
        .rename("BuiltUp")
        .toInt()
        .unmask(0)
    )

    built_up = safe_clip(built_up, roi, is_whole_country)

    return built_up


# ---------------------------------------------------------
# 1. Urban Growth Tracking
# ---------------------------------------------------------
def run_urban_growth_tracking(
    Map,
    roi,
    is_whole_country: bool,
    ai_settings: dict,
):
    """
    วิเคราะห์การขยายตัวเมืองแบบ Hybrid Built-up Detection

    ใช้:
    - Dynamic World Built-up
    - Landsat NDBI
    - Landsat MNDWI
    - Landsat NDVI
    - ESA WorldCover Water/Wetland Mask
    - DEM Slope Mask
    """

    start_year = int(ai_settings.get("start_year", 2015))
    predict_years = int(ai_settings.get("predict_years", 10))

    current_max_year = 2023

    if start_year > current_max_year:
        st.warning("ปีเริ่มต้นต้องไม่มากกว่าปีข้อมูลล่าสุด")
        return None

    years = list(range(start_year, current_max_year + 1))

    my_bar = st.progress(0, text="กำลังสแกนพื้นที่เมืองด้วย AI...")

    with st.spinner("ดึงข้อมูลพื้นที่เมืองด้วย Hybrid Remote Sensing Model..."):
        try:
            time_series_data = []

            built_past = None
            built_present = None

            geometry = get_roi_geometry(roi)
            calc_scale = get_reduce_scale(is_whole_country, local_scale=30)

            for i, year in enumerate(years):
                my_bar.progress(
                    (i + 1) / len(years),
                    text=f"กำลังจำแนกพื้นที่สิ่งปลูกสร้าง ปี {year}...",
                )

                built_up = get_yearly_builtup_image(
                    year=year,
                    roi=roi,
                    is_whole_country=is_whole_country,
                )

                area_stats = (
                    built_up
                    .multiply(ee.Image.pixelArea())
                    .rename("built_area_sqm")
                    .reduceRegion(
                        reducer=ee.Reducer.sum(),
                        geometry=geometry,
                        scale=calc_scale,
                        maxPixels=1e13,
                        bestEffort=True,
                        tileScale=4,
                    )
                    .getInfo()
                )

                area_sqm = area_stats.get("built_area_sqm", 0) or 0
                area_rai = area_sqm / 1600.0

                time_series_data.append(
                    {
                        "Year": year,
                        "Intensity": area_rai,
                    }
                )

                if year == start_year:
                    built_past = built_up

                if year == current_max_year:
                    built_present = built_up

            my_bar.empty()

            df_history = pd.DataFrame(time_series_data)

            if df_history.empty:
                st.warning("ไม่พบข้อมูลสำหรับวิเคราะห์การขยายตัวเมือง")
                return None

            # -------------------------------------------------
            # Forecast: simple linear trend
            # -------------------------------------------------
            x = df_history["Year"].values
            y = df_history["Intensity"].values
            n = len(x)

            denominator = n * (x**2).sum() - (x.sum()) ** 2

            if denominator == 0:
                m = 0
            else:
                m = (n * (x * y).sum() - x.sum() * y.sum()) / denominator

            c = (y.sum() - m * x.sum()) / n if n > 0 else 0

            future_years = list(
                range(
                    current_max_year + 1,
                    current_max_year + predict_years + 1,
                )
            )

            final_chart_data = []

            for year in years + future_years:
                if year <= current_max_year:
                    hist_value = float(
                        df_history.loc[
                            df_history["Year"] == year,
                            "Intensity",
                        ].values[0]
                    )
                else:
                    hist_value = None

                forecast_value = max(0, m * year + c)

                final_chart_data.append(
                    {
                        "ปี": str(year),
                        "พื้นที่เมืองจริง (ไร่)": hist_value,
                        "เส้นพยากรณ์การขยายตัว (ไร่)": forecast_value,
                    }
                )

            df_trend = pd.DataFrame(final_chart_data)

            # -------------------------------------------------
            # Map layers
            # -------------------------------------------------
            current_urban_rai = 0.0
            growth_rai = 0.0

            if built_present is not None and built_past is not None:
                urban_growth = (
                    built_present.eq(1)
                    .And(built_past.eq(0))
                    .rename("UrbanGrowth")
                    .toInt()
                )

                Map.addLayer(
                    built_present.selfMask(),
                    {"palette": ["00F2FE"]},
                    "เมืองปัจจุบัน Hybrid Built-up",
                    opacity=0.70,
                )

                Map.addLayer(
                    urban_growth.selfMask(),
                    {"palette": ["FF007F"]},
                    f"พื้นที่ขยายตัวใหม่ {start_year}-{current_max_year}",
                    opacity=0.85,
                )

                add_custom_legend(
                    Map=Map,
                    title="การวิเคราะห์การขยายตัวเมือง",
                    legend_dict={
                        "เมืองปัจจุบัน Hybrid Built-up": "00F2FE",
                        f"พื้นที่ขยายตัวใหม่ {start_year}-{current_max_year}": "FF007F",
                    },
                    position="bottomright",
                )

                # Summary area
                area_rai = ee.Image.pixelArea().divide(1600).rename("area_rai")

                summary_image = ee.Image.cat(
                    [
                        area_rai.updateMask(built_present).rename("current_urban_rai"),
                        area_rai.updateMask(urban_growth).rename("growth_rai"),
                    ]
                )

                summary_stats = summary_image.reduceRegion(
                    reducer=ee.Reducer.sum(),
                    geometry=geometry,
                    scale=calc_scale,
                    maxPixels=1e13,
                    bestEffort=True,
                    tileScale=4,
                ).getInfo()

                current_urban_rai = safe_number(
                    summary_stats.get("current_urban_rai"),
                    default=0,
                )

                growth_rai = safe_number(
                    summary_stats.get("growth_rai"),
                    default=0,
                )

            st.session_state["ai_growth_trend_df"] = df_trend
            st.session_state["ai_growth_summary"] = {
                "start_year": start_year,
                "current_max_year": current_max_year,
                "current_urban_rai": round(current_urban_rai, 2),
                "growth_rai": round(growth_rai, 2),
            }

            render_urban_growth_summary()

            st.toast("จำลองการขยายตัวเมืองเสร็จสิ้น", icon="✨")

            return df_trend

        except Exception as exc:
            my_bar.empty()
            st.error(f"ระบบวิเคราะห์การขยายตัวเมืองขัดข้อง: {exc}")
            return None


def render_urban_growth_summary():
    """
    แสดง summary ของ Urban Growth Tracking ใน sidebar
    """

    summary = st.session_state.get("ai_growth_summary")

    if not summary:
        return

    st.sidebar.markdown("<hr style='border-color: #1E293B;'>", unsafe_allow_html=True)
    st.sidebar.markdown("### 🏙️ Urban Growth Summary")

    st.sidebar.metric(
        "เมืองปัจจุบัน",
        f"{summary.get('current_urban_rai', 0):,.0f} ไร่",
    )

    st.sidebar.metric(
        f"พื้นที่ขยายตัวใหม่ {summary.get('start_year')}-{summary.get('current_max_year')}",
        f"{summary.get('growth_rai', 0):,.0f} ไร่",
    )

    st.sidebar.caption(
        "โมเดลใช้ Hybrid Built-up Detection: Dynamic World + NDBI + MNDWI + NDVI + ESA Water Mask + Slope Mask"
    )


# ---------------------------------------------------------
# 2. Flood Risk Simulation
# ---------------------------------------------------------
def run_flood_risk_simulation(
    Map,
    roi,
    is_whole_country: bool,
    ai_settings: dict,
):
    """
    Modified Bathtub Flood Simulation

    Logic:
    1. หาแหล่งน้ำจาก ESA WorldCover class 80
    2. หา base elevation จากความสูงต่ำสุดของแหล่งน้ำในพื้นที่
    3. จำลองระดับน้ำเพิ่มจาก slider
    4. พื้นที่น้ำท่วมต้อง:
       - DEM <= simulated flood level
       - slope ต่ำกว่าค่าที่กำหนด
       - อยู่ใกล้แหล่งน้ำภายในระยะที่กำหนด
    5. Overlay กับ Global Flood Database เพื่อดูพื้นที่ท่วมซ้ำซาก
    """

    water_level_rise = float(ai_settings.get("water_level_rise", 2.0))
    max_distance_m = int(ai_settings.get("flood_distance_m", 3000))
    max_slope_deg = float(ai_settings.get("flood_max_slope", 10.0))
    mitigation_tool = ai_settings.get("mitigation_tool")

    with st.spinner("กำลังคำนวณแบบจำลองน้ำท่วม Modified Bathtub Model..."):
        try:
            geometry = get_roi_geometry(roi)
            calc_scale = get_reduce_scale(is_whole_country, local_scale=100)

            # -------------------------------------------------
            # 1. Load DEM
            # -------------------------------------------------
            dem = (
                ee.ImageCollection(DATASETS["copernicus_dem"])
                .select("DEM")
                .mosaic()
            )

            dem = safe_clip(dem, roi, is_whole_country)
            slope = ee.Terrain.slope(dem)

            # -------------------------------------------------
            # 2. ESA WorldCover water mask
            # -------------------------------------------------
            esa_lc = (
                ee.ImageCollection(DATASETS["esa_worldcover"])
                .first()
                .select("Map")
            )

            esa_lc = safe_clip(esa_lc, roi, is_whole_country)

            water_mask = (
                esa_lc.eq(80)
                .rename("WaterMask")
                .unmask(0)
            )

            # -------------------------------------------------
            # 3. Historical flood
            # -------------------------------------------------
            gfd = (
                ee.ImageCollection(DATASETS["global_flood_db"])
                .filterBounds(roi)
                .select("flooded")
                .sum()
            )

            gfd = safe_clip(gfd, roi, is_whole_country)

            historical_flood = (
                gfd.gt(0)
                .And(water_mask.Not())
                .rename("HistoricalFlood")
            )

            # -------------------------------------------------
            # 4. Base water elevation
            # -------------------------------------------------
            # ถ้าไม่มี water pixel ใน ROI จะได้ 999999 แล้ว fallback ไปใช้ DEM percentile 5
            water_elevation_for_stats = (
                dem
                .updateMask(water_mask)
                .unmask(999999)
            )

            water_stats = water_elevation_for_stats.reduceRegion(
                reducer=ee.Reducer.min(),
                geometry=geometry,
                scale=calc_scale,
                maxPixels=1e13,
                bestEffort=True,
                tileScale=4,
            )

            dem_stats = dem.reduceRegion(
                reducer=ee.Reducer.percentile([5]),
                geometry=geometry,
                scale=calc_scale,
                maxPixels=1e13,
                bestEffort=True,
                tileScale=4,
            )

            water_min = ee.Number(ee.Dictionary(water_stats).get("DEM"))
            dem_p5 = ee.Number(ee.Dictionary(dem_stats).get("DEM_p5"))

            base_elev = ee.Number(
                ee.Algorithms.If(
                    water_min.gt(900000),
                    dem_p5,
                    water_min,
                )
            )

            simulated_flood_level = base_elev.add(water_level_rise)

            # -------------------------------------------------
            # 5. Distance to water
            # -------------------------------------------------
            # ESA WorldCover resolution ประมาณ 10m
            max_distance_px = max(1, int(max_distance_m / 10))

            dist_to_water = (
                water_mask
                .fastDistanceTransform(max_distance_px)
                .sqrt()
                .multiply(10)
                .rename("DistanceToWater")
            )

            # -------------------------------------------------
            # 6. Flood simulation rules
            # -------------------------------------------------
            is_below_water_level = dem.lte(simulated_flood_level)
            is_flat = slope.lte(max_slope_deg)
            is_near_water = dist_to_water.lte(max_distance_m)

            simulated_inundation = (
                is_below_water_level
                .And(is_flat)
                .And(is_near_water)
                .And(water_mask.Not())
                .rename("SimulatedInundation")
            )

            new_flood = (
                simulated_inundation
                .And(historical_flood.Not())
                .rename("NewFlood")
            )

            overlap_flood = (
                simulated_inundation
                .And(historical_flood)
                .rename("OverlapFlood")
            )

            # -------------------------------------------------
            # 7. Map layers
            # -------------------------------------------------
            Map.addLayer(
                water_mask.selfMask(),
                {"palette": ["0064c8"]},
                "แหล่งน้ำและลำน้ำเดิม",
                opacity=0.75,
            )

            Map.addLayer(
                historical_flood.selfMask(),
                {"palette": ["00008B"]},
                "พื้นที่น้ำท่วมซ้ำซาก",
                opacity=0.65,
            )

            Map.addLayer(
                new_flood.selfMask(),
                {"palette": ["00FFFF"]},
                f"พื้นที่เสี่ยงน้ำท่วมใหม่ +{water_level_rise}m",
                opacity=0.80,
            )

            Map.addLayer(
                overlap_flood.selfMask(),
                {"palette": ["FF00FF"]},
                "พื้นที่จำลองท่วมซ้ำกับประวัติเดิม",
                opacity=0.85,
            )

            add_custom_legend(
                Map=Map,
                title="Flood Risk Simulation",
                legend_dict={
                    "แหล่งน้ำและลำน้ำเดิม": "0064c8",
                    "พื้นที่น้ำท่วมซ้ำซากเดิม": "00008B",
                    f"พื้นที่เสี่ยงใหม่เมื่อระดับน้ำ +{water_level_rise}m": "00FFFF",
                    "พื้นที่ท่วมซ้ำกับประวัติเดิม": "FF00FF",
                },
                position="bottomright",
            )

            # -------------------------------------------------
            # 8. Area statistics
            # -------------------------------------------------
            area_rai = ee.Image.pixelArea().divide(1600).rename("area_rai")

            area_image = ee.Image.cat(
                [
                    area_rai.updateMask(new_flood).rename("new_flood_rai"),
                    area_rai.updateMask(historical_flood).rename("historical_flood_rai"),
                    area_rai.updateMask(overlap_flood).rename("overlap_flood_rai"),
                ]
            )

            area_stats = area_image.reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=geometry,
                scale=calc_scale,
                maxPixels=1e13,
                bestEffort=True,
                tileScale=4,
            ).getInfo()

            new_flood_rai = safe_number(area_stats.get("new_flood_rai"), default=0)
            historical_flood_rai = safe_number(
                area_stats.get("historical_flood_rai"),
                default=0,
            )
            overlap_flood_rai = safe_number(
                area_stats.get("overlap_flood_rai"),
                default=0,
            )

            try:
                base_elev_value = base_elev.getInfo()
                flood_level_value = simulated_flood_level.getInfo()
            except Exception:
                base_elev_value = None
                flood_level_value = None

            st.session_state["flood_simulation_summary"] = {
                "water_level_rise": water_level_rise,
                "max_distance_m": max_distance_m,
                "max_slope_deg": max_slope_deg,
                "mitigation_tool": mitigation_tool,
                "new_flood_rai": round(new_flood_rai, 2),
                "historical_flood_rai": round(historical_flood_rai, 2),
                "overlap_flood_rai": round(overlap_flood_rai, 2),
                "base_elev_m": base_elev_value,
                "simulated_flood_level_m": flood_level_value,
            }

            render_flood_simulation_summary()

            st.toast("จำลองสถานการณ์น้ำท่วมเสร็จสิ้น", icon="💦")

        except Exception as exc:
            st.error(f"ระบบ Flood Risk Simulation ขัดข้อง: {exc}")


def render_flood_simulation_summary():
    """
    แสดง summary ของ Flood Risk Simulation ใน sidebar
    """

    summary = st.session_state.get("flood_simulation_summary")

    if not summary:
        return

    st.sidebar.markdown("<hr style='border-color: #1E293B;'>", unsafe_allow_html=True)
    st.sidebar.markdown("### 🌊 Flood Simulation Summary")

    base_elev = summary.get("base_elev_m")
    flood_level = summary.get("simulated_flood_level_m")

    if base_elev is not None and flood_level is not None:
        st.sidebar.caption(
            f"Base elevation: {base_elev:.2f} m | "
            f"Simulated flood level: {flood_level:.2f} m"
        )

    st.sidebar.caption(
        f"Water rise: +{summary.get('water_level_rise', 0)} m | "
        f"Distance: {summary.get('max_distance_m', 0):,} m | "
        f"Slope ≤ {summary.get('max_slope_deg', 0)}°"
    )

    if summary.get("mitigation_tool"):
        st.sidebar.caption(
            f"Scenario: {summary.get('mitigation_tool')} "
            "(ยังเป็น label ประกอบการอธิบาย ไม่ได้เปลี่ยนสมการโดยตรง)"
        )

    st.sidebar.metric(
        "พื้นที่เสี่ยงใหม่",
        f"{summary.get('new_flood_rai', 0):,.0f} ไร่",
    )

    st.sidebar.metric(
        "พื้นที่เคยท่วมเดิม",
        f"{summary.get('historical_flood_rai', 0):,.0f} ไร่",
    )

    st.sidebar.metric(
        "พื้นที่ท่วมซ้ำซ้อน",
        f"{summary.get('overlap_flood_rai', 0):,.0f} ไร่",
    )


# ---------------------------------------------------------
# Chart renderer
# ---------------------------------------------------------
def render_ai_result_chart(df_trend):
    """
    แสดงกราฟผลลัพธ์ AI Simulation

    ใช้กับ Urban Growth Tracking เท่านั้น
    ถ้าอยู่ใน Flood Risk Simulation จะไม่แสดงกราฟเมืองเดิม
    """

    current_analysis_type = st.session_state.get("current_ai_analysis_type")
    active_analysis_type = st.session_state.get("ai_active_analysis_type")

    if current_analysis_type != "Urban Growth Tracking":
        return

    if active_analysis_type and active_analysis_type != "Urban Growth Tracking":
        return

    if df_trend is None:
        df_trend = st.session_state.get("ai_growth_trend_df")

    if df_trend is None:
        return

    if not isinstance(df_trend, pd.DataFrame):
        return

    if df_trend.empty:
        return

    st.markdown("### 📈 ผลลัพธ์การสกัดข้อมูลอนุกรมเวลา และเส้นทางทำนายอนาคต")
    st.line_chart(df_trend.set_index("ปี"))

    with st.expander("🔍 ดูตารางตัวเลขผลลัพธ์เชิงลึก"):
        st.dataframe(
            df_trend,
            use_container_width=True,
            hide_index=True,
        )

    with st.expander("📘 Methodology: Hybrid Built-up Detection", expanded=False):
        st.markdown(
            """
            โมเดลนี้ใช้ **Hybrid Built-up Detection** แทนการใช้ NDBI เดี่ยว

            ### เหตุผลที่ไม่ใช้ NDBI เดี่ยว
            NDBI สามารถสับสนกับพื้นที่ดินแห้ง ตะกอนริมอ่างเก็บน้ำ ทราย ลูกรัง หรือพื้นที่โล่งสะท้อนแสงสูงได้

            ### ตัวกรองที่ใช้
            - **Dynamic World Built-up Class / Built Probability**
            - **NDBI** เพื่อช่วยตรวจจับสิ่งปลูกสร้าง
            - **MNDWI** เพื่อตัดพื้นที่น้ำ
            - **ESA WorldCover Water / Wetland Mask**
            - **Dynamic World Water Probability**
            - **NDVI** เพื่อลดความสับสนกับพื้นที่พืชหนาแน่น
            - **Slope Mask** เพื่อลด false positive บนภูเขาและขอบอ่างเก็บน้ำ

            ### ข้อจำกัด
            - ยังไม่ใช่ข้อมูล building footprint รายหลังคา
            - พื้นที่โรงงาน เหมือง ดินโล่ง หรือพื้นผิวสะท้อนแสงสูงบางชนิดอาจยังคลาดเคลื่อนได้
            - เหมาะสำหรับดูแนวโน้มเชิงพื้นที่เบื้องต้น ไม่ใช่ขอบเขตสิ่งปลูกสร้างทางกฎหมาย
            """
        )

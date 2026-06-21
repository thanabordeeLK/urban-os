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
    "copernicus_dem": "COPERNICUS/DEM/GLO30",
    "esa_worldcover": "ESA/WorldCover/v200",
    "global_flood_db": "GLOBAL_FLOOD_DB/MODIS_EVENTS/V1",
}


# ---------------------------------------------------------
# Utility
# ---------------------------------------------------------
def get_roi_geometry(roi):
    try:
        return roi.geometry()
    except Exception:
        return roi


def get_reduce_scale(is_whole_country: bool, local_scale: int = 100) -> int:
    return 1000 if is_whole_country else local_scale


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

    if not run_ai:
        return None

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
# 1. Urban Growth Tracking
# ---------------------------------------------------------
def run_urban_growth_tracking(
    Map,
    roi,
    is_whole_country: bool,
    ai_settings: dict,
):
    """
    วิเคราะห์การขยายตัวเมืองด้วย NDBI จาก Landsat 8

    หมายเหตุ:
    - เป็น model เบื้องต้น
    - NDBI อาจสับสนกับดินโล่งหรือพื้นผิวสะท้อนแสงสูง
    """

    start_year = ai_settings.get("start_year", 2015)
    predict_years = ai_settings.get("predict_years", 10)

    my_bar = st.progress(0, text="กำลังสแกนพื้นที่เมืองด้วย AI...")

    with st.spinner("ดึงข้อมูลโครงสร้างเมืองจาก Landsat 8..."):
        try:
            current_max_year = 2023
            years = list(range(start_year, current_max_year + 1))
            time_series_data = []

            ndbi_past = None
            ndbi_present = None

            for i, year in enumerate(years):
                my_bar.progress(
                    (i + 1) / len(years),
                    text=f"กำลังสกัดสิ่งปลูกสร้าง ปี {year}...",
                )

                landsat = (
                    ee.ImageCollection(DATASETS["landsat8"])
                    .filterBounds(roi)
                    .filterDate(f"{year}-01-01", f"{year}-12-31")
                    .filter(ee.Filter.lt("CLOUD_COVER", 30))
                )

                def calc_ndbi(img):
                    return img.normalizedDifference(["B6", "B5"]).rename("NDBI")

                ndbi_year = landsat.map(calc_ndbi).median()
                ndbi_year = safe_clip(ndbi_year, roi, is_whole_country)

                built_up = ndbi_year.gt(0.0).rename("BuiltUp")

                calc_scale = get_reduce_scale(is_whole_country, local_scale=30)
                geometry = get_roi_geometry(roi)

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
                    ndbi_past = built_up

                if year == current_max_year:
                    ndbi_present = built_up

            my_bar.empty()

            df_history = pd.DataFrame(time_series_data)

            if df_history.empty:
                st.warning("ไม่พบข้อมูลสำหรับวิเคราะห์การขยายตัวเมือง")
                return None

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
                range(current_max_year + 1, current_max_year + predict_years + 1)
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

                forecast_value = m * year + c

                final_chart_data.append(
                    {
                        "ปี": str(year),
                        "พื้นที่เมืองจริง (ไร่)": hist_value,
                        "เส้นพยากรณ์การขยายตัว (ไร่)": forecast_value,
                    }
                )

            df_trend = pd.DataFrame(final_chart_data)

            if ndbi_present is not None and ndbi_past is not None:
                urban_growth = ndbi_present.eq(1).And(ndbi_past.eq(0))

                Map.addLayer(
                    ndbi_present.selfMask(),
                    {"palette": ["00F2FE"]},
                    "เมืองปัจจุบัน",
                    opacity=0.65,
                )

                Map.addLayer(
                    urban_growth.selfMask(),
                    {"palette": ["FF007F"]},
                    f"พื้นที่ขยายตัวใหม่ ({start_year}-{current_max_year})",
                    opacity=0.85,
                )

                add_custom_legend(
                    Map=Map,
                    title="การวิเคราะห์การขยายตัวเมือง",
                    legend_dict={
                        "เมืองปัจจุบัน": "00F2FE",
                        f"พื้นที่ขยายตัวใหม่ {start_year}-{current_max_year}": "FF007F",
                    },
                    position="bottomright",
                )

            st.toast("จำลองการขยายตัวเมืองเสร็จสิ้น", icon="✨")

            return df_trend

        except Exception as exc:
            my_bar.empty()
            st.error(f"ระบบวิเคราะห์การขยายตัวเมืองขัดข้อง: {exc}")
            return None


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
            # 2. Load ESA WorldCover water mask
            # -------------------------------------------------
            esa_lc = (
                ee.ImageCollection(DATASETS["esa_worldcover"])
                .first()
                .select("Map")
            )

            esa_lc = safe_clip(esa_lc, roi, is_whole_country)

            water_mask = esa_lc.eq(80).rename("WaterMask")

            # -------------------------------------------------
            # 3. Load historical flood
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
            water_elevation = dem.updateMask(water_mask)

            water_stats = water_elevation.reduceRegion(
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

            water_dict = ee.Dictionary(water_stats)
            dem_dict = ee.Dictionary(dem_stats)

            # ถ้าใน ROI ไม่มีแหล่งน้ำ ให้ใช้ค่า percentile 5 ของ DEM เป็นฐานสำรอง
            base_elev = ee.Number(
                ee.Algorithms.If(
                    water_dict.contains("DEM"),
                    water_dict.get("DEM"),
                    dem_dict.get("DEM_p5"),
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

            new_flood_rai = area_stats.get("new_flood_rai", 0) or 0
            historical_flood_rai = area_stats.get("historical_flood_rai", 0) or 0
            overlap_flood_rai = area_stats.get("overlap_flood_rai", 0) or 0

            try:
                base_elev_value = base_elev.getInfo()
                flood_level_value = simulated_flood_level.getInfo()
            except Exception:
                base_elev_value = None
                flood_level_value = None

            st.sidebar.markdown("<hr style='border-color: #1E293B;'>", unsafe_allow_html=True)
            st.sidebar.markdown("### 🌊 Flood Simulation Summary")

            if base_elev_value is not None and flood_level_value is not None:
                st.sidebar.caption(
                    f"Base elevation: {base_elev_value:.2f} m | "
                    f"Simulated flood level: {flood_level_value:.2f} m"
                )

            st.sidebar.metric(
                "พื้นที่เสี่ยงใหม่",
                f"{new_flood_rai:,.0f} ไร่",
            )

            st.sidebar.metric(
                "พื้นที่เคยท่วมเดิม",
                f"{historical_flood_rai:,.0f} ไร่",
            )

            st.sidebar.metric(
                "พื้นที่ท่วมซ้ำซ้อน",
                f"{overlap_flood_rai:,.0f} ไร่",
            )

            st.session_state["flood_simulation_summary"] = {
                "water_level_rise": water_level_rise,
                "max_distance_m": max_distance_m,
                "max_slope_deg": max_slope_deg,
                "new_flood_rai": round(new_flood_rai, 2),
                "historical_flood_rai": round(historical_flood_rai, 2),
                "overlap_flood_rai": round(overlap_flood_rai, 2),
                "base_elev_m": base_elev_value,
                "simulated_flood_level_m": flood_level_value,
            }

            st.toast("จำลองสถานการณ์น้ำท่วมเสร็จสิ้น", icon="💦")

        except Exception as exc:
            st.error(f"ระบบ Flood Risk Simulation ขัดข้อง: {exc}")


# ---------------------------------------------------------
# Chart renderer
# ---------------------------------------------------------
def render_ai_result_chart(df_trend):
    """
    แสดงกราฟผลลัพธ์ AI Simulation

    ตอนนี้ใช้กับ Urban Growth Tracking
    ส่วน Flood Simulation แสดงผลผ่าน Sidebar summary และ Map layer
    """

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

import streamlit as st
import ee
import pandas as pd

from config.datasets import DATASET_CATALOG
from services.gee_service import safe_clip


def run_ai_simulation_if_requested(Map, roi, is_whole_country: bool, ai_settings: dict):
    """
    รันโหมด AI Simulation เมื่อผู้ใช้กด RUN AI ENGINE

    Returns:
        pd.DataFrame | None: ตารางอนุกรมเวลาและผลพยากรณ์
    """
    if not ai_settings:
        return None

    analysis_type = ai_settings.get("analysis_type")
    run_ai = ai_settings.get("run_ai", False)

    if analysis_type == "Urban Growth Tracking" and run_ai:
        return run_urban_growth_tracking(
            Map=Map,
            roi=roi,
            is_whole_country=is_whole_country,
            start_year=ai_settings.get("start_year", 2015),
            predict_years=ai_settings.get("predict_years", 10),
        )

    if analysis_type == "Flood Risk Simulation" and run_ai:
        st.warning("Flood Risk Simulation ยังเป็น placeholder — ขั้นต่อไปควรแยกโมเดลน้ำท่วมจริง")
        return None

    return None


def run_urban_growth_tracking(
    Map,
    roi,
    is_whole_country: bool,
    start_year: int,
    predict_years: int,
):
    """
    วิเคราะห์การขยายตัวเมืองด้วย NDBI จาก Landsat 8

    รักษา logic เดิม:
    - ใช้ LANDSAT/LC08/C02/T1_TOA
    - NDBI = normalizedDifference(['B6', 'B5'])
    - built-up = NDBI > 0
    - พื้นที่หน่วยไร่
    - linear trend forecast
    """
    my_bar = st.progress(0, text="กำลังสแกนพื้นที่ด้วย AI...")

    with st.spinner("ดึงข้อมูลโครงสร้างพื้นฐานระดับ High-Res (30m)..."):
        try:
            current_max_year = 2023
            years = list(range(start_year, current_max_year + 1))
            time_series_data = []

            ndbi_past = None
            ndbi_present = None

            for i, year in enumerate(years):
                my_bar.progress(
                    (i + 1) / len(years),
                    text=f"กำลังสกัดตึกและสิ่งปลูกสร้าง ปี {year}...",
                )

                l8 = (
                    ee.ImageCollection(DATASET_CATALOG["landsat8_toa"]["id"])
                    .filterBounds(roi)
                    .filterDate(f"{year}-01-01", f"{year}-12-31")
                    .filter(ee.Filter.lt("CLOUD_COVER", 30))
                )

                ndbi_year = l8.map(calculate_ndbi_landsat8).median()

                ndbi_year = safe_clip(ndbi_year, roi, is_whole_country)

                built_up = ndbi_year.gt(0.0)

                calc_scale = 1000 if is_whole_country else 30
                area_stats = (
                    built_up.multiply(ee.Image.pixelArea())
                    .reduceRegion(
                        reducer=ee.Reducer.sum(),
                        geometry=roi.geometry(),
                        scale=calc_scale,
                        maxPixels=1e13,
                    )
                    .getInfo()
                )

                area_sqm = area_stats.get("NDBI", 0)
                area_rai = area_sqm / 1600.0 if area_sqm else 0

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
            df_trend = build_linear_forecast(
                df_history=df_history,
                current_max_year=current_max_year,
                predict_years=predict_years,
            )

            if ndbi_present is not None and ndbi_past is not None:
                urban_growth = ndbi_present.eq(1).And(ndbi_past.eq(0))

                Map.addLayer(
                    ndbi_present.selfMask(),
                    {"palette": ["#00F2FE"]},
                    "เมือง (ปัจจุบัน)",
                )
                Map.addLayer(
                    urban_growth.selfMask(),
                    {"palette": ["#FF007F"]},
                    f"พื้นที่ขยายตัวใหม่ ({start_year}-{current_max_year})",
                )

                try:
                    Map.add_legend(
                        title="การวิเคราะห์เมือง (30m)",
                        legend_dict={
                            "เมืองและสิ่งปลูกสร้างเดิม": "00F2FE",
                            "พื้นที่ขยายตัวใหม่": "FF007F",
                        },
                    )
                except Exception:
                    pass

            st.toast("จำลองโมเดลเสร็จสิ้น!", icon="✨")
            return df_trend

        except Exception as exc:
            st.error(f"❌ ระบบ AI ขัดข้องชั่วคราว: {exc}")
            my_bar.empty()
            return None


def calculate_ndbi_landsat8(img):
    """คำนวณ NDBI จาก Landsat 8 TOA"""
    return img.normalizedDifference(["B6", "B5"]).rename("NDBI")


def build_linear_forecast(
    df_history: pd.DataFrame,
    current_max_year: int,
    predict_years: int,
) -> pd.DataFrame:
    """สร้างเส้นพยากรณ์ด้วย linear regression แบบ manual ตาม logic เดิม"""
    x = df_history["Year"].values
    y = df_history["Intensity"].values
    n = len(x)

    denominator = n * (x**2).sum() - (x.sum()) ** 2
    if n > 0 and denominator != 0:
        m = (n * (x * y).sum() - x.sum() * y.sum()) / denominator
        c = (y.sum() - m * x.sum()) / n
    else:
        m = 0
        c = 0

    years = list(df_history["Year"].values)
    future_years = list(range(current_max_year + 1, current_max_year + predict_years + 1))

    final_chart_data = []
    for year in years + future_years:
        if year <= current_max_year:
            hist_val = float(
                df_history[df_history["Year"] == year]["Intensity"].values[0]
            )
        else:
            hist_val = None

        final_chart_data.append(
            {
                "ปี พ.ศ./ค.ศ.": str(year),
                "พื้นที่เมืองจริง (ไร่)": hist_val,
                "เส้นพยากรณ์การขยายตัว (ไร่)": m * year + c,
            }
        )

    return pd.DataFrame(final_chart_data)


def render_ai_result_chart(df_trend) -> None:
    """แสดงกราฟและตารางผลลัพธ์ AI Simulation"""
    if df_trend is None:
        return

    st.markdown(
        "### 📈 ผลลัพธ์การสกัดข้อมูลอนุกรมเวลา และเส้นทางทำนายอนาคต "
        "(Predictive Timeline)"
    )
    st.line_chart(df_trend.set_index("ปี พ.ศ./ค.ศ."))

    with st.expander("🔍 ดูตารางตัวเลขผลลัพธ์เชิงลึก (Data Sheets)"):
        st.dataframe(df_trend, use_container_width=True, hide_index=True)

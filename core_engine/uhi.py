from __future__ import annotations

from datetime import datetime
import json

import ee
import pandas as pd
import streamlit as st

from components.map_renderer import add_custom_legend
from services.gee_service import safe_clip
from core_engine.suitability import get_roi_geometry


# ---------------------------------------------------------
# Visualization
# ---------------------------------------------------------
LST_VIS = {
    "min": 22,
    "max": 45,
    "palette": [
        "08306b",
        "2171b5",
        "6baed6",
        "ffffbf",
        "fdae61",
        "f46d43",
        "a50026",
    ],
}

HEAT_RISK_VIS = {
    "min": 1,
    "max": 5,
    "palette": [
        "2c7bb6",  # 1 cool
        "abd9e9",  # 2 low
        "ffffbf",  # 3 moderate
        "fdae61",  # 4 high
        "d7191c",  # 5 very high
    ],
}

HEAT_RISK_LEGEND = {
    "1: เย็น / ความเสี่ยงต่ำมาก": "2c7bb6",
    "2: ค่อนข้างเย็น": "abd9e9",
    "3: ปานกลาง": "ffffbf",
    "4: ร้อน / ควรเฝ้าระวัง": "fdae61",
    "5: ร้อนมาก / Heat Hotspot": "d7191c",
}

HOTSPOT_VIS = {
    "palette": ["ff0000"],
}


HEAT_CLASS_LABELS = {
    1: "เย็น / ความเสี่ยงต่ำมาก",
    2: "ค่อนข้างเย็น",
    3: "ปานกลาง",
    4: "ร้อน / ควรเฝ้าระวัง",
    5: "ร้อนมาก / Heat Hotspot",
}


# ---------------------------------------------------------
# Landsat helpers
# ---------------------------------------------------------
def mask_landsat_l2_clouds(image: ee.Image) -> ee.Image:
    """
    Cloud mask สำหรับ Landsat Collection 2 Level 2 จาก QA_PIXEL

    ตัด:
    - Fill
    - Dilated cloud
    - Cirrus
    - Cloud
    - Cloud shadow
    """

    qa = image.select("QA_PIXEL")

    fill = qa.bitwiseAnd(1 << 0).eq(0)
    dilated_cloud = qa.bitwiseAnd(1 << 1).eq(0)
    cirrus = qa.bitwiseAnd(1 << 2).eq(0)
    cloud = qa.bitwiseAnd(1 << 3).eq(0)
    cloud_shadow = qa.bitwiseAnd(1 << 4).eq(0)

    mask = fill.And(dilated_cloud).And(cirrus).And(cloud).And(cloud_shadow)

    # QA_RADSAT = 0 หมายถึงไม่ saturated
    try:
        saturation_mask = image.select("QA_RADSAT").eq(0)
        mask = mask.And(saturation_mask)
    except Exception:
        pass

    return image.updateMask(mask)


def add_landsat_lst_celsius(image: ee.Image) -> ee.Image:
    """
    ST_B10 scale factor ของ Landsat Collection 2 L2:
    Kelvin = DN * 0.00341802 + 149.0
    Celsius = Kelvin - 273.15
    """

    lst_c = (
        image
        .select("ST_B10")
        .multiply(0.00341802)
        .add(149.0)
        .subtract(273.15)
        .rename("LST_C")
    )

    return image.addBands(lst_c, overwrite=True)


def get_landsat_lst_collection(
    roi,
    start_date: str,
    end_date: str,
    cloud_cover_max: float = 60,
    use_landsat8: bool = True,
    use_landsat9: bool = True,
) -> ee.ImageCollection:
    geometry = get_roi_geometry(roi)

    collections = []

    if use_landsat8:
        lc08 = (
            ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
            .filterBounds(geometry)
            .filterDate(start_date, end_date)
            .filter(ee.Filter.lte("CLOUD_COVER", cloud_cover_max))
        )
        collections.append(lc08)

    if use_landsat9:
        lc09 = (
            ee.ImageCollection("LANDSAT/LC09/C02/T1_L2")
            .filterBounds(geometry)
            .filterDate(start_date, end_date)
            .filter(ee.Filter.lte("CLOUD_COVER", cloud_cover_max))
        )
        collections.append(lc09)

    if not collections:
        return ee.ImageCollection([])

    merged = collections[0]
    for coll in collections[1:]:
        merged = merged.merge(coll)

    return (
        merged
        .map(mask_landsat_l2_clouds)
        .map(add_landsat_lst_celsius)
        .select("LST_C")
    )


def build_lst_composite(
    roi,
    settings: dict,
    is_whole_country: bool = False,
) -> tuple[ee.Image | None, int, str | None]:
    start_date = settings.get("start_date", "2025-03-01")
    end_date = settings.get("end_date", "2025-05-31")
    cloud_cover_max = float(settings.get("cloud_cover_max", 60))
    composite_method = settings.get("composite_method", "median")
    use_landsat8 = bool(settings.get("use_landsat8", True))
    use_landsat9 = bool(settings.get("use_landsat9", True))

    collection = get_landsat_lst_collection(
        roi=roi,
        start_date=start_date,
        end_date=end_date,
        cloud_cover_max=cloud_cover_max,
        use_landsat8=use_landsat8,
        use_landsat9=use_landsat9,
    )

    try:
        image_count = int(collection.size().getInfo())
    except Exception as exc:
        return None, 0, f"ตรวจจำนวนภาพ Landsat ไม่สำเร็จ: {exc}"

    if image_count == 0:
        return None, 0, "ไม่พบภาพ Landsat LST ในช่วงเวลา/พื้นที่/เงื่อนไขเมฆที่เลือก"

    if composite_method == "mean":
        lst = collection.mean().rename("LST_C")
    elif composite_method == "max":
        lst = collection.max().rename("LST_C")
    else:
        lst = collection.median().rename("LST_C")

    lst = safe_clip(lst, roi, is_whole_country)

    return lst, image_count, None


# ---------------------------------------------------------
# Heat risk classification
# ---------------------------------------------------------
def classify_heat_risk_relative(lst_c: ee.Image, roi, is_whole_country: bool = False) -> ee.Image:
    """
    แบ่ง Heat Risk 1–5 ด้วย percentile ภายใน ROI
    เหมาะกับการดู hotspot ในพื้นที่ศึกษา
    """

    geometry = get_roi_geometry(roi)
    scale = 500 if is_whole_country else 100

    percentiles = lst_c.reduceRegion(
        reducer=ee.Reducer.percentile([20, 40, 60, 80]),
        geometry=geometry,
        scale=scale,
        maxPixels=1e13,
        bestEffort=True,
        tileScale=4,
    )

    p20 = ee.Number(percentiles.get("LST_C_p20"))
    p40 = ee.Number(percentiles.get("LST_C_p40"))
    p60 = ee.Number(percentiles.get("LST_C_p60"))
    p80 = ee.Number(percentiles.get("LST_C_p80"))

    heat_risk = (
        ee.Image(1)
        .where(lst_c.gt(p20), 2)
        .where(lst_c.gt(p40), 3)
        .where(lst_c.gt(p60), 4)
        .where(lst_c.gt(p80), 5)
        .rename("Heat_Risk_Class")
        .toInt()
    )

    return safe_clip(heat_risk, roi, is_whole_country)


def classify_heat_risk_absolute(lst_c: ee.Image, roi, is_whole_country: bool = False) -> ee.Image:
    """
    แบ่ง Heat Risk 1–5 ด้วย threshold Celsius แบบคงที่
    เหมาะกับการเทียบหลายพื้นที่ แต่ต้องระวังฤดูกาล/ช่วงเวลาถ่ายภาพ
    """

    heat_risk = (
        ee.Image(1)
        .where(lst_c.gte(28), 2)
        .where(lst_c.gte(32), 3)
        .where(lst_c.gte(36), 4)
        .where(lst_c.gte(40), 5)
        .rename("Heat_Risk_Class")
        .toInt()
    )

    return safe_clip(heat_risk, roi, is_whole_country)


def build_heat_risk_image(
    lst_c: ee.Image,
    roi,
    settings: dict,
    is_whole_country: bool = False,
) -> ee.Image:
    mode = settings.get("risk_mode", "relative")
    if mode == "absolute":
        return classify_heat_risk_absolute(lst_c, roi, is_whole_country)
    return classify_heat_risk_relative(lst_c, roi, is_whole_country)


# ---------------------------------------------------------
# Statistics
# ---------------------------------------------------------
def calculate_lst_summary(lst_c: ee.Image, roi, is_whole_country: bool = False) -> dict:
    geometry = get_roi_geometry(roi)
    scale = 500 if is_whole_country else 100

    reducer = (
        ee.Reducer.mean()
        .combine(ee.Reducer.minMax(), "", True)
        .combine(ee.Reducer.stdDev(), "", True)
        .combine(ee.Reducer.percentile([20, 50, 80, 90]), "", True)
    )

    stats = lst_c.reduceRegion(
        reducer=reducer,
        geometry=geometry,
        scale=scale,
        maxPixels=1e13,
        bestEffort=True,
        tileScale=4,
    ).getInfo()

    return stats or {}


def calculate_heat_risk_area(heat_risk: ee.Image, roi, is_whole_country: bool = False) -> tuple[pd.DataFrame, dict]:
    geometry = get_roi_geometry(roi)
    scale = 500 if is_whole_country else 100

    area_rai = ee.Image.pixelArea().divide(1600).rename("area_rai")
    grouped = (
        area_rai
        .addBands(heat_risk.rename("class"))
        .reduceRegion(
            reducer=ee.Reducer.sum().group(groupField=1, groupName="class"),
            geometry=geometry,
            scale=scale,
            maxPixels=1e13,
            bestEffort=True,
            tileScale=4,
        )
        .get("groups")
    )

    groups = ee.List(grouped).getInfo() if grouped is not None else []

    rows = []
    total_rai = 0.0
    hotspot_rai = 0.0

    for item in groups or []:
        class_id = int(item.get("class", 0))
        area = float(item.get("sum", 0) or 0)
        total_rai += area
        if class_id >= 5:
            hotspot_rai += area

        rows.append(
            {
                "ระดับ": class_id,
                "ความหมาย": HEAT_CLASS_LABELS.get(class_id, ""),
                "พื้นที่ (ไร่)": round(area, 2),
            }
        )

    df = pd.DataFrame(rows).sort_values("ระดับ") if rows else pd.DataFrame()

    summary = {
        "total_rai": total_rai,
        "hotspot_rai": hotspot_rai,
        "hotspot_percent": (hotspot_rai / total_rai * 100) if total_rai > 0 else 0,
    }

    return df, summary


def _fmt(value, digits: int = 1) -> str:
    try:
        return f"{float(value):,.{digits}f}"
    except Exception:
        return "-"


def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    if df is None or df.empty:
        return "".encode("utf-8-sig")
    return df.to_csv(index=False).encode("utf-8-sig")


def build_uhi_report_markdown(
    *,
    selected_province: str,
    selected_district: str,
    is_whole_country: bool,
    settings: dict,
    lst_summary: dict,
    heat_area_df: pd.DataFrame,
    heat_summary: dict,
    image_count: int,
) -> str:
    area_name = "ทั้งประเทศไทย" if is_whole_country else f"{selected_district}, {selected_province}"
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if heat_area_df is not None and not heat_area_df.empty:
        rows = ["| ระดับ | ความหมาย | พื้นที่ (ไร่) |", "|---|---|---:|"]
        for _, row in heat_area_df.iterrows():
            rows.append(
                f"| {row.get('ระดับ')} | {row.get('ความหมาย')} | {float(row.get('พื้นที่ (ไร่)', 0)):,.2f} |"
            )
        area_table = "\n".join(rows)
    else:
        area_table = "_ไม่มีตารางพื้นที่ความร้อน_"

    return f"""# Urban Heat Island / Land Surface Temperature Report

วันที่สร้างรายงาน: {generated_at}

## 1. พื้นที่ศึกษา
- พื้นที่: {area_name}
- ช่วงเวลา: {settings.get("start_date")} ถึง {settings.get("end_date")}
- จำนวนภาพ Landsat ที่ใช้: {image_count:,}
- Composite: {settings.get("composite_method")}
- Heat Risk Mode: {settings.get("risk_mode")}

## 2. LST Summary
- Mean LST: **{_fmt(lst_summary.get("LST_C_mean"))} °C**
- Min LST: **{_fmt(lst_summary.get("LST_C_min"))} °C**
- Max LST: **{_fmt(lst_summary.get("LST_C_max"))} °C**
- Median LST: **{_fmt(lst_summary.get("LST_C_p50"))} °C**
- P80 LST: **{_fmt(lst_summary.get("LST_C_p80"))} °C**
- P90 LST: **{_fmt(lst_summary.get("LST_C_p90"))} °C**

## 3. Heat Risk Area
- พื้นที่ Heat Hotspot Class 5: **{heat_summary.get("hotspot_rai", 0):,.0f} ไร่**
- สัดส่วนพื้นที่ Heat Hotspot: **{heat_summary.get("hotspot_percent", 0):.1f}%**

{area_table}

## 4. Planning Interpretation
พื้นที่ Heat Risk Class 5 ควรถูกพิจารณาเป็นพื้นที่เร่งด่วนสำหรับการเพิ่มร่มเงา พื้นที่สีเขียว ทางเดินร่มเงา วัสดุผิวสะท้อนความร้อนต่ำ และมาตรการลดความร้อนเมือง

## 5. Recommended Next Actions
1. ตรวจสอบ Heat Hotspot เทียบกับ built-up / land cover / ถนน / พื้นที่โล่ง
2. วางแนว Green Corridor หรือ Urban Tree Canopy ในพื้นที่ Class 4–5
3. เชื่อม Heat Risk เข้า Suitability Analysis เป็น Heat Penalty ในขั้นต่อไป
4. ตรวจภาคสนามในพื้นที่ hotspot ที่มีประชาชนหรือกิจกรรมเมืองหนาแน่น

หมายเหตุ: LST จาก Landsat คืออุณหภูมิผิวดิน ไม่ใช่อุณหภูมิอากาศโดยตรง
"""


# ---------------------------------------------------------
# Main map / panel functions
# ---------------------------------------------------------
def add_uhi_layers(
    Map,
    roi,
    is_whole_country: bool = False,
    settings: dict | None = None,
) -> None:
    settings = settings or {}

    if not (settings.get("run_uhi") or st.session_state.get("uhi_run_active", False)):
        return

    with st.spinner("กำลังคำนวณ Urban Heat Island / Land Surface Temperature..."):
        lst_c, image_count, error_message = build_lst_composite(
            roi=roi,
            settings=settings,
            is_whole_country=is_whole_country,
        )

        if error_message:
            st.error(error_message)
            return

        heat_risk = build_heat_risk_image(
            lst_c=lst_c,
            roi=roi,
            settings=settings,
            is_whole_country=is_whole_country,
        )

        st.session_state["uhi_lst_image"] = lst_c
        st.session_state["uhi_heat_risk_image"] = heat_risk
        st.session_state["uhi_image_count"] = image_count
        st.session_state["uhi_settings"] = settings

        if settings.get("show_lst_layer", True):
            Map.addLayer(
                lst_c,
                LST_VIS,
                "Landsat LST Celsius",
                opacity=float(settings.get("lst_opacity", 0.75)),
            )

        if settings.get("show_heat_risk_layer", True):
            Map.addLayer(
                heat_risk,
                HEAT_RISK_VIS,
                "Urban Heat Risk Class",
                opacity=float(settings.get("heat_risk_opacity", 0.72)),
            )

        if settings.get("show_hotspot_layer", True):
            hotspot = heat_risk.gte(5).selfMask()
            Map.addLayer(
                hotspot,
                HOTSPOT_VIS,
                "Heat Hotspot Class 5",
                opacity=0.85,
            )

        add_custom_legend(
            Map=Map,
            title="Urban Heat Risk",
            legend_dict=HEAT_RISK_LEGEND,
            position="bottomright",
        )

        if settings.get("calculate_stats", True):
            try:
                lst_summary = calculate_lst_summary(lst_c, roi, is_whole_country)
                heat_area_df, heat_summary = calculate_heat_risk_area(heat_risk, roi, is_whole_country)

                st.session_state["uhi_lst_summary"] = lst_summary
                st.session_state["uhi_heat_area_df"] = heat_area_df
                st.session_state["uhi_heat_summary"] = heat_summary
            except Exception as exc:
                st.warning(f"คำนวณสถิติ UHI ไม่สำเร็จ แต่ยังแสดงแผนที่ได้: {exc}")


def render_uhi_result_panel(
    *,
    selected_province: str,
    selected_district: str,
    is_whole_country: bool = False,
) -> None:
    st.markdown("### 🌡️ Urban Heat Island / LST Result")

    if not st.session_state.get("uhi_run_active", False):
        st.info("ยังไม่มีผลวิเคราะห์ กด Run UHI Analysis ใน Sidebar ก่อน")
        return

    settings = st.session_state.get("uhi_settings", {}) or {}
    lst_summary = st.session_state.get("uhi_lst_summary") or {}
    heat_area_df = st.session_state.get("uhi_heat_area_df")
    heat_summary = st.session_state.get("uhi_heat_summary") or {}
    image_count = int(st.session_state.get("uhi_image_count") or 0)

    if not lst_summary:
        st.warning("ยังไม่มีสถิติ UHI อาจเกิดจากภาพ Landsat ถูก mask เมฆหมด หรือยังคำนวณไม่เสร็จ")
        return

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Mean LST", f"{_fmt(lst_summary.get('LST_C_mean'))} °C")
    col2.metric("Max LST", f"{_fmt(lst_summary.get('LST_C_max'))} °C")
    col3.metric("Heat Hotspot", f"{heat_summary.get('hotspot_rai', 0):,.0f} ไร่")
    col4.metric("Landsat Images", f"{image_count:,}")

    with st.expander("📊 Heat Risk Area Table", expanded=True):
        if heat_area_df is not None and not heat_area_df.empty:
            st.dataframe(heat_area_df, use_container_width=True, hide_index=True)
        else:
            st.info("ไม่มีตารางพื้นที่ Heat Risk")

    with st.expander("🧪 Methodology / ข้อควรระวัง", expanded=False):
        st.markdown(
            """
            - ใช้ Landsat 8/9 Collection 2 Level 2 band `ST_B10`
            - แปลงเป็น Celsius ด้วย scale factor และ offset ของ Landsat L2
            - กรองเมฆ/เงาเมฆด้วย `QA_PIXEL`
            - Heat Risk แบบ Relative จะแบ่ง 1–5 ตาม percentile ภายใน ROI
            - LST คืออุณหภูมิผิวดิน ไม่ใช่อุณหภูมิอากาศโดยตรง
            - พื้นที่น้ำ เมฆ และเงาเมฆอาจทำให้ข้อมูลบางส่วนว่างหรือดูเย็นผิดปกติ
            """
        )

    st.markdown("### 📤 Export UHI Output")

    report_md = build_uhi_report_markdown(
        selected_province=selected_province,
        selected_district=selected_district,
        is_whole_country=is_whole_country,
        settings=settings,
        lst_summary=lst_summary,
        heat_area_df=heat_area_df if heat_area_df is not None else pd.DataFrame(),
        heat_summary=heat_summary,
        image_count=image_count,
    )

    col_a, col_b, col_c = st.columns(3)

    with col_a:
        st.download_button(
            "⬇️ Download Heat Area CSV",
            data=dataframe_to_csv_bytes(heat_area_df if heat_area_df is not None else pd.DataFrame()),
            file_name="urban_os_uhi_heat_area_summary.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with col_b:
        st.download_button(
            "⬇️ Download UHI Report Markdown",
            data=report_md.encode("utf-8"),
            file_name="urban_os_uhi_report.md",
            mime="text/markdown",
            use_container_width=True,
        )

    with col_c:
        payload = {
            "settings": settings,
            "lst_summary": lst_summary,
            "heat_summary": heat_summary,
            "image_count": image_count,
        }
        st.download_button(
            "⬇️ Download UHI JSON",
            data=json.dumps(payload, ensure_ascii=False, indent=2, default=str).encode("utf-8"),
            file_name="urban_os_uhi_summary.json",
            mime="application/json",
            use_container_width=True,
        )


def clear_uhi_session_state() -> None:
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

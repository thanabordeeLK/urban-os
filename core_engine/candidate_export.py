from __future__ import annotations

from datetime import datetime
import json

import ee
import pandas as pd
import streamlit as st

from core_engine.suitability import CLASS_LABELS, CLASS_COLORS, get_roi_geometry


def _safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _feature_collection_to_geojson_bytes(fc: ee.FeatureCollection) -> bytes:
    info = fc.getInfo()
    return json.dumps(info, ensure_ascii=False).encode("utf-8")


def _feature_collection_to_dataframe(fc: ee.FeatureCollection) -> pd.DataFrame:
    info = fc.getInfo()
    features = info.get("features", []) if info else []

    rows = []
    for idx, feature in enumerate(features, start=1):
        props = feature.get("properties", {}) or {}
        class_id = int(_safe_float(props.get("class"), 0))

        rows.append(
            {
                "ลำดับ": idx,
                "class": class_id,
                "ความหมาย": CLASS_LABELS.get(class_id, "Candidate Area"),
                "พื้นที่ (ไร่)": round(_safe_float(props.get("area_rai"), 0), 2),
                "centroid_lon": round(_safe_float(props.get("centroid_lon"), 0), 6),
                "centroid_lat": round(_safe_float(props.get("centroid_lat"), 0), 6),
                "สี": CLASS_COLORS.get(class_id, "#999999"),
            }
        )

    return pd.DataFrame(rows)


def _dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    if df is None or df.empty:
        return "".encode("utf-8-sig")
    return df.to_csv(index=False).encode("utf-8-sig")


def build_candidate_area_feature_collection(
    *,
    suitability_class: ee.Image,
    roi,
    min_class: int = 4,
    scale: int = 100,
    min_area_rai: float = 5.0,
    simplify_tolerance_m: int = 30,
    max_features: int = 500,
    is_whole_country: bool = False,
) -> ee.FeatureCollection:
    """
    แปลง raster suitability class เป็น polygon candidate areas

    แนวคิด:
    - Candidate = final class >= min_class
    - ใช้ reduceToVectors เพื่อแปลง raster เป็น polygon
    - ใส่ property area_rai และ centroid เพื่อเอาไปใช้ต่อใน QGIS / Excel
    """

    geometry = get_roi_geometry(roi)

    # สำหรับระดับประเทศ scale ละเอียดเกินไปจะช้า/หนักมาก
    if is_whole_country and scale < 500:
        scale = 500

    label = (
        suitability_class
        .updateMask(suitability_class.gte(min_class))
        .rename("class")
        .toInt()
    )

    vector_input = label.addBands(
        ee.Image.pixelArea().divide(1600).rename("pixel_area_rai")
    )

    fc = vector_input.reduceToVectors(
        reducer=ee.Reducer.sum(),
        geometry=geometry,
        scale=scale,
        geometryType="polygon",
        eightConnected=True,
        labelProperty="class",
        bestEffort=True,
        maxPixels=1e13,
        tileScale=4,
    )

    def decorate(feature):
        area_rai = feature.geometry().area(1).divide(1600)
        centroid = feature.geometry().centroid(1).coordinates()
        class_id = ee.Number(feature.get("class")).toInt()

        out = feature.set(
            {
                "class": class_id,
                "area_rai": area_rai,
                "centroid_lon": centroid.get(0),
                "centroid_lat": centroid.get(1),
                "exported_from": "Urban OS Suitability Analysis",
                "candidate_min_class": min_class,
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )

        if simplify_tolerance_m and simplify_tolerance_m > 0:
            out = out.setGeometry(out.geometry().simplify(simplify_tolerance_m))

        return out

    fc = (
        fc
        .map(decorate)
        .filter(ee.Filter.gte("area_rai", float(min_area_rai)))
        .sort("area_rai", False)
    )

    if max_features and max_features > 0:
        fc = fc.limit(int(max_features))

    return fc


def render_candidate_area_export_panel(
    *,
    roi,
    suitability_class: ee.Image | None,
    selected_province: str,
    selected_district: str,
    is_whole_country: bool = False,
) -> None:
    """
    แสดง Candidate Area Export Panel:
    - แปลง class 4-5 หรือ class 5 เป็น GeoJSON
    - Export CSV centroid/area summary
    """

    st.markdown("### 🟩 Candidate Area Export")
    st.caption(
        "แปลงพื้นที่เหมาะสมจาก Urban Suitability Class เป็น polygon สำหรับเปิดต่อใน QGIS / GIS software"
    )

    if suitability_class is None:
        st.info("ยังไม่มี raster ผลวิเคราะห์สำหรับ export ให้กด Run Suitability Analysis ก่อน")
        return

    with st.expander("⚙️ Candidate Export Settings", expanded=False):
        min_class = st.selectbox(
            "เลือก class ขั้นต่ำที่จะ export",
            options=[4, 5],
            index=0,
            format_func=lambda x: f"Class {x}: {CLASS_LABELS.get(x, '')}",
            key="candidate_export_min_class",
        )

        default_scale = 500 if is_whole_country else 100
        scale = st.selectbox(
            "Vectorization scale (เมตร)",
            options=[30, 50, 100, 250, 500, 1000],
            index=[30, 50, 100, 250, 500, 1000].index(default_scale),
            key="candidate_export_scale",
            help="scale ยิ่งละเอียด polygon ยิ่งเยอะและใช้เวลานาน สำหรับอำเภอแนะนำ 100m, จังหวัด 250m, ประเทศ 500–1000m",
        )

        min_area_rai = st.number_input(
            "กรอง polygon ที่เล็กกว่า (ไร่)",
            min_value=0.0,
            max_value=100000.0,
            value=5.0,
            step=5.0,
            key="candidate_export_min_area_rai",
        )

        simplify_tolerance_m = st.number_input(
            "Simplify geometry tolerance (เมตร)",
            min_value=0,
            max_value=1000,
            value=30,
            step=10,
            key="candidate_export_simplify_tolerance_m",
            help="ลดจำนวน vertex เพื่อให้ GeoJSON เบาลง ค่า 0 = ไม่ simplify",
        )

        max_features = st.number_input(
            "จำนวน polygon สูงสุดที่จะ export",
            min_value=10,
            max_value=10000,
            value=500,
            step=50,
            key="candidate_export_max_features",
        )

        if is_whole_country:
            st.warning(
                "กำลัง export ระดับประเทศ ระบบจะบังคับใช้ scale อย่างน้อย 500m "
                "เพื่อไม่ให้ Google Earth Engine หนักเกินไป"
            )

    col_a, col_b = st.columns([2, 1])

    with col_a:
        generate_clicked = st.button(
            "🧩 Generate Candidate GeoJSON",
            key="generate_candidate_geojson",
            use_container_width=True,
        )

    with col_b:
        clear_clicked = st.button(
            "🧹 Clear Candidate Export",
            key="clear_candidate_export",
            use_container_width=True,
        )

    if clear_clicked:
        for key in [
            "candidate_export_geojson_bytes",
            "candidate_export_csv_bytes",
            "candidate_export_df",
            "candidate_export_count",
            "candidate_export_settings",
        ]:
            st.session_state.pop(key, None)
        st.success("ล้าง Candidate Export แล้ว")

    if generate_clicked:
        with st.spinner("กำลังแปลง candidate raster เป็น polygon GeoJSON..."):
            try:
                fc = build_candidate_area_feature_collection(
                    suitability_class=suitability_class,
                    roi=roi,
                    min_class=int(min_class),
                    scale=int(scale),
                    min_area_rai=float(min_area_rai),
                    simplify_tolerance_m=int(simplify_tolerance_m),
                    max_features=int(max_features),
                    is_whole_country=is_whole_country,
                )

                feature_count = int(fc.size().getInfo())
                geojson_bytes = _feature_collection_to_geojson_bytes(fc)
                candidate_df = _feature_collection_to_dataframe(fc)
                csv_bytes = _dataframe_to_csv_bytes(candidate_df)

                st.session_state["candidate_export_geojson_bytes"] = geojson_bytes
                st.session_state["candidate_export_csv_bytes"] = csv_bytes
                st.session_state["candidate_export_df"] = candidate_df
                st.session_state["candidate_export_count"] = feature_count
                st.session_state["candidate_export_settings"] = {
                    "province": selected_province,
                    "district": selected_district,
                    "min_class": min_class,
                    "scale": scale,
                    "min_area_rai": min_area_rai,
                    "simplify_tolerance_m": simplify_tolerance_m,
                    "max_features": max_features,
                    "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }

                st.success(f"สร้าง Candidate GeoJSON สำเร็จ: {feature_count:,} polygon")

            except Exception as exc:
                st.error(f"สร้าง Candidate GeoJSON ไม่สำเร็จ: {exc}")
                st.caption(
                    "ถ้า error เพราะข้อมูลใหญ่เกินไป ให้เพิ่ม scale เป็น 250–500m, "
                    "เพิ่ม min area, หรือลดจำนวน max features"
                )

    geojson_bytes = st.session_state.get("candidate_export_geojson_bytes")
    csv_bytes = st.session_state.get("candidate_export_csv_bytes")
    candidate_df = st.session_state.get("candidate_export_df")
    feature_count = st.session_state.get("candidate_export_count")
    settings = st.session_state.get("candidate_export_settings") or {}

    if geojson_bytes and csv_bytes:
        st.success(
            f"Candidate Export พร้อมดาวน์โหลด: {int(feature_count or 0):,} polygon "
            f"| min class {settings.get('min_class')} | scale {settings.get('scale')}m"
        )

        if candidate_df is not None and not candidate_df.empty:
            st.dataframe(candidate_df.head(100), use_container_width=True)

        area_slug = "thailand" if is_whole_country else f"{selected_province}_{selected_district}"
        area_slug = (
            area_slug
            .replace(" ", "_")
            .replace("/", "_")
            .replace("\\", "_")
            .lower()
        )

        col1, col2 = st.columns(2)

        with col1:
            st.download_button(
                "⬇️ Download Candidate Areas GeoJSON",
                data=geojson_bytes,
                file_name=f"urban_os_candidate_areas_{area_slug}.geojson",
                mime="application/geo+json",
                use_container_width=True,
            )

        with col2:
            st.download_button(
                "⬇️ Download Candidate Areas CSV",
                data=csv_bytes,
                file_name=f"urban_os_candidate_areas_{area_slug}.csv",
                mime="text/csv",
                use_container_width=True,
            )

        st.caption(
            "GeoJSON นี้เป็น candidate จากผลวิเคราะห์ raster ไม่ใช่เขตพัฒนาอย่างเป็นทางการ "
            "ควรนำไปตรวจซ้ำใน QGIS และตรวจภาคสนามก่อนใช้ตัดสินใจจริง"
        )

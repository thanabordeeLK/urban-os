from __future__ import annotations

from datetime import datetime
import pandas as pd
import streamlit as st


def _fmt_number(value, digits: int = 0) -> str:
    try:
        return f"{float(value):,.{digits}f}"
    except Exception:
        return "0"



def dataframe_to_markdown_table(df: pd.DataFrame) -> str:
    """
    สร้าง Markdown table เองโดยไม่ใช้ pandas.to_markdown()
    เพื่อหลีกเลี่ยง dependency 'tabulate' บน Streamlit Cloud
    """
    if df is None or df.empty:
        return "_ไม่มีตารางสรุปพื้นที่_"

    safe_df = df.copy()

    def clean_cell(value) -> str:
        if pd.isna(value):
            return ""
        text = str(value)
        text = text.replace("|", "\\|")
        text = text.replace("\n", " ")
        return text

    columns = [clean_cell(c) for c in safe_df.columns]
    rows = []
    rows.append("| " + " | ".join(columns) + " |")
    rows.append("| " + " | ".join(["---"] * len(columns)) + " |")

    for _, row in safe_df.iterrows():
        rows.append("| " + " | ".join(clean_cell(row[col]) for col in safe_df.columns) + " |")

    return "\n".join(rows)


def _get_weight_text(weights: dict) -> str:
    if not weights:
        return "- ยังไม่มีค่าน้ำหนัก"

    lines = []
    for key, label in [
        ("slope", "Slope"),
        ("flood", "Flood Risk"),
        ("landcover", "Land Cover"),
        ("urban", "Urbanization"),
        ("road", "Road Accessibility"),
        ("facility", "Public Facility Proximity"),
        ("water", "Water Proximity"),
    ]:
        lines.append(f"- {label}: {weights.get(key, 0)}")
    return "\n".join(lines)


def build_validation_notes(suitability_config: dict) -> tuple[str, list[str], list[str]]:
    """
    สร้างระดับความน่าเชื่อถือเบื้องต้นของโมเดลจากข้อมูลที่เปิดใช้
    ไม่ใช่ค่าทางสถิติ แต่เป็น checklist เพื่อเตือนผู้ใช้ว่าข้อมูลใดครบ/ยังขาด
    """

    suitability_config = suitability_config or {}
    road_config = suitability_config.get("road_config", {}) or {}
    facility_config = suitability_config.get("facility_config", {}) or {}
    constraint_config = suitability_config.get("constraint_config", {}) or {}

    score = 40
    strengths = []
    gaps = []

    if road_config.get("enabled") and road_config.get("asset_ids"):
        score += 20
        strengths.append("มี Road Asset ใช้ประเมินการเข้าถึงถนน")
    else:
        gaps.append("ยังไม่มี/ยังไม่เปิดใช้ Road Asset จึงยังประเมิน accessibility ไม่เต็มรูปแบบ")

    if facility_config.get("enabled") and facility_config.get("asset_ids"):
        score += 10
        strengths.append("มี Facility Asset ใช้ประเมินการเข้าถึงบริการสาธารณะ")
    else:
        gaps.append("ยังไม่มี/ยังไม่เปิดใช้ Facility Asset จึงยังประเมินการเข้าถึงบริการสาธารณะไม่เต็มรูปแบบ")

    if constraint_config.get("use_wdpa") or constraint_config.get("asset_ids"):
        score += 20
        strengths.append("มี protected/forest constraints ใช้กันพื้นที่ควรหลีกเลี่ยง")
    else:
        gaps.append("ยังไม่มีชั้นข้อมูลป่า/พื้นที่คุ้มครองเป็น hard constraint")

    weights = suitability_config.get("weights", {}) or {}
    if any(float(v or 0) > 0 for v in weights.values()):
        score += 10
        strengths.append("มีการกำหนดน้ำหนักปัจจัยและ normalize ก่อนคำนวณ")
    else:
        gaps.append("ยังไม่ได้กำหนดน้ำหนักปัจจัยที่มีนัยสำคัญ")

    if suitability_config.get("show_factor_layers") is not None:
        score += 10
        strengths.append("สามารถตรวจสอบ factor layers เพื่ออธิบายเหตุผลของผลลัพธ์ได้")

    if score >= 80:
        level = "สูง"
    elif score >= 60:
        level = "ปานกลาง"
    else:
        level = "เบื้องต้น / ต้องตรวจสอบเพิ่ม"

    return level, strengths, gaps


def build_suitability_report_markdown(
    *,
    selected_province: str,
    selected_district: str,
    is_whole_country: bool,
    summary: dict,
    df: pd.DataFrame,
    suitability_config: dict,
) -> str:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    area_name = "ทั้งประเทศไทย" if is_whole_country else f"{selected_district}, {selected_province}"

    weights = (suitability_config or {}).get("weights", {}) or {}
    road_config = (suitability_config or {}).get("road_config", {}) or {}
    facility_config = (suitability_config or {}).get("facility_config", {}) or {}
    constraint_config = (suitability_config or {}).get("constraint_config", {}) or {}
    confidence_level, strengths, gaps = build_validation_notes(suitability_config)

    table_md = dataframe_to_markdown_table(df)

    strengths_md = "\n".join([f"- {x}" for x in strengths]) or "- ยังไม่มีจุดแข็งที่ระบบตรวจพบ"
    gaps_md = "\n".join([f"- {x}" for x in gaps]) or "- ยังไม่พบช่องว่างสำคัญจาก checklist เบื้องต้น"

    road_assets = road_config.get("asset_ids") or []
    facility_assets = facility_config.get("asset_ids") or []
    forest_assets = constraint_config.get("asset_ids") or []

    road_assets_md = "\n".join([f"- `{x}`" for x in road_assets]) or "- ยังไม่ได้ระบุ Road Asset"
    facility_assets_md = "\n".join([f"- `{x}`" for x in facility_assets]) or "- ยังไม่ได้ระบุ Facility Asset"
    forest_assets_md = "\n".join([f"- `{x}`" for x in forest_assets]) or "- ยังไม่ได้ระบุ Custom Forest/Constraint Asset"

    return f"""# Urban OS Suitability Analysis Report

วันที่สร้างรายงาน: {generated_at}

## 1. พื้นที่ศึกษา

- พื้นที่: {area_name}
- ระดับความน่าเชื่อถือของโมเดล: **{confidence_level}**

## 2. Executive Summary

- พื้นที่รวมที่คำนวณได้: **{_fmt_number(summary.get("total_rai", 0))} ไร่**
- พื้นที่เหมาะสมสูง–สูงมาก: **{_fmt_number(summary.get("development_candidate_rai", 0))} ไร่**
- สัดส่วนพื้นที่เหมาะสมสูง–สูงมาก: **{_fmt_number(summary.get("candidate_percent", 0), 1)}%**
- พื้นที่ควรหลีกเลี่ยง/จำกัด: **{_fmt_number(summary.get("restricted_rai", 0))} ไร่**

## 3. Suitability Class Area

{table_md}

## 4. Model Weights

{_get_weight_text(weights)}

## 5. Data / Constraint Inputs

### Road Accessibility

- เปิดใช้ถนนในสมการ: {road_config.get("enabled", False)}
- Buffer ถนน: {road_config.get("buffer_m", 0)} เมตร
- ระยะไกลสุดที่ใช้ประเมินถนน: {road_config.get("max_distance_m", 0)} เมตร

{road_assets_md}

### Public Facility Proximity

- เปิดใช้บริการสาธารณะในสมการ: {facility_config.get("enabled", False)}
- Buffer จุดบริการ: {facility_config.get("buffer_m", 0)} เมตร
- ระยะไกลสุดที่ใช้ประเมินบริการสาธารณะ: {facility_config.get("max_distance_m", 0)} เมตร

{facility_assets_md}

### Protected / Forest Constraints

- ใช้ WDPA: {constraint_config.get("use_wdpa", False)}
- Buffer รอบพื้นที่กันออก: {constraint_config.get("buffer_m", 0)} เมตร

{forest_assets_md}

## 6. Validation Notes

### จุดแข็งของผลวิเคราะห์

{strengths_md}

### ช่องว่างข้อมูล / สิ่งที่ควรตรวจสอบเพิ่ม

{gaps_md}

## 7. Planning Interpretation

พื้นที่ Class 4–5 ควรถูกพิจารณาเป็นพื้นที่ candidate สำหรับการวิเคราะห์ขั้นต่อไป ไม่ใช่พื้นที่อนุมัติพัฒนาโดยอัตโนมัติ  
พื้นที่ Class 1 ควรถูกจัดเป็นพื้นที่หลีกเลี่ยงหรือพื้นที่ที่ต้องตรวจสอบข้อจำกัดทางกฎหมาย สิ่งแวดล้อม และกายภาพอย่างเข้มงวด

## 8. Recommended Next Actions

1. ตรวจสอบพื้นที่ Class 4–5 เทียบกับถนนจริงและการเข้าถึงภาคสนาม
2. เติมชั้นข้อมูลป่าสงวน/อุทยาน/เขตห้ามล่าจากหน่วยงานไทย หากยังไม่มี
3. ตรวจสอบความครบถ้วนของ Facility Asset เช่น โรงพยาบาล โรงเรียน ศูนย์ราชการ ตลาด และสถานีขนส่ง
4. Export พื้นที่ candidate เป็น GeoJSON แล้วตรวจซ้ำใน QGIS
5. ตรวจสอบพื้นที่ด้วยภาพถ่ายดาวเทียมความละเอียดสูงและ field survey ก่อนใช้ประกอบการตัดสินใจจริง

---

หมายเหตุ: รายงานนี้เป็น decision-support output จาก Urban OS ไม่ใช่เอกสารรับรองทางกฎหมาย
"""


def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    if df is None or df.empty:
        return "".encode("utf-8-sig")
    return df.to_csv(index=False).encode("utf-8-sig")


def render_model_validation_panel(suitability_config: dict) -> None:
    confidence_level, strengths, gaps = build_validation_notes(suitability_config)

    with st.expander("🧪 Model Validation / Data Completeness", expanded=False):
        st.markdown(f"**ระดับความน่าเชื่อถือเบื้องต้น:** `{confidence_level}`")

        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown("**จุดแข็งที่ตรวจพบ**")
            if strengths:
                for item in strengths:
                    st.success(item)
            else:
                st.info("ยังไม่มีจุดแข็งที่ระบบตรวจพบ")

        with col_b:
            st.markdown("**ข้อมูลที่ยังควรเติม**")
            if gaps:
                for item in gaps:
                    st.warning(item)
            else:
                st.success("ไม่พบช่องว่างสำคัญจาก checklist เบื้องต้น")


def render_suitability_export_panel(
    *,
    selected_province: str,
    selected_district: str,
    is_whole_country: bool,
    summary: dict,
    df: pd.DataFrame,
    suitability_config: dict,
) -> None:
    """
    แสดงปุ่ม export รายงานและ CSV หลัง Suitability Analysis มีผลลัพธ์แล้ว
    """

    if df is None or df.empty:
        return

    render_model_validation_panel(suitability_config)

    st.markdown("### 📤 Export Suitability Output")

    report_md = build_suitability_report_markdown(
        selected_province=selected_province,
        selected_district=selected_district,
        is_whole_country=is_whole_country,
        summary=summary or {},
        df=df,
        suitability_config=suitability_config or {},
    )

    col1, col2 = st.columns(2)

    with col1:
        st.download_button(
            "⬇️ Download Area Summary CSV",
            data=dataframe_to_csv_bytes(df),
            file_name="urban_os_suitability_area_summary.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with col2:
        st.download_button(
            "⬇️ Download Planning Report Markdown",
            data=report_md.encode("utf-8"),
            file_name="urban_os_suitability_report.md",
            mime="text/markdown",
            use_container_width=True,
        )

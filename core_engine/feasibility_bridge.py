from __future__ import annotations

from datetime import datetime
import json
from typing import Any

import pandas as pd
import streamlit as st

from config.planning_standards import (
    get_standard_profile,
    get_density_reference,
    get_psa_residential_factors,
)

try:
    from llm.openai_client import ask_openai
except Exception:
    ask_openai = None


FEASIBILITY_SESSION_REPORT_KEY = "feasibility_bridge_report_md"
FEASIBILITY_SESSION_PAYLOAD_KEY = "feasibility_bridge_payload"
FEASIBILITY_SESSION_PRIORITY_DF_KEY = "feasibility_bridge_priority_df"


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _fmt(value: Any, digits: int = 0) -> str:
    try:
        return f"{float(value):,.{digits}f}"
    except Exception:
        return "-"


def _clean_cell(value: Any) -> str:
    if pd.isna(value):
        return ""
    text = str(value)
    text = text.replace("|", "\\|")
    text = text.replace("\n", " ")
    return text


def dataframe_to_markdown_table(df: pd.DataFrame, max_rows: int = 20) -> str:
    if df is None or df.empty:
        return "_ไม่มีข้อมูล_"

    safe_df = df.head(max_rows).copy()
    columns = [_clean_cell(c) for c in safe_df.columns]

    rows = []
    rows.append("| " + " | ".join(columns) + " |")
    rows.append("| " + " | ".join(["---"] * len(columns)) + " |")

    for _, row in safe_df.iterrows():
        rows.append("| " + " | ".join(_clean_cell(row[col]) for col in safe_df.columns) + " |")

    return "\n".join(rows)


def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    if df is None or df.empty:
        return "".encode("utf-8-sig")
    return df.to_csv(index=False).encode("utf-8-sig")


def _get_candidate_area_column(df: pd.DataFrame) -> str | None:
    for col in ["พื้นที่ (ไร่)", "area_rai", "area", "Area Rai"]:
        if col in df.columns:
            return col
    return None


def build_candidate_priority_dataframe(
    candidate_df: pd.DataFrame,
    top_n: int = 30,
    heat_penalty_enabled: bool = False,
) -> pd.DataFrame:
    """สร้างตารางจัดลำดับ candidate area เพื่อใช้ใน Feasibility Bridge."""

    if candidate_df is None or candidate_df.empty:
        return pd.DataFrame()

    df = candidate_df.copy()
    area_col = _get_candidate_area_column(df)

    if "class" not in df.columns:
        df["class"] = 0

    if area_col:
        df["_area_rai"] = df[area_col].apply(lambda x: _safe_float(x, 0))
    else:
        df["_area_rai"] = 0

    df["_class"] = df["class"].apply(lambda x: int(_safe_float(x, 0)))

    def tier(row) -> str:
        class_id = int(row["_class"])
        area_rai = float(row["_area_rai"])

        if class_id >= 5 and area_rai >= 100:
            return "A: ศักยภาพสูง / พิจารณาระยะสั้น"
        if class_id >= 5:
            return "B: เหมาะสมสูงมาก แต่ต้องตรวจขนาด/การรวมแปลง"
        if class_id >= 4 and area_rai >= 100:
            return "B: เหมาะสมสูง / พิจารณาระยะกลาง"
        if class_id >= 4:
            return "C: เหมาะสมสูงแต่ขนาดเล็ก / พิจารณาเป็นโครงข่ายย่อย"
        return "D: ไม่ใช่ candidate หลัก"

    def condition(row) -> str:
        class_id = int(row["_class"])
        if heat_penalty_enabled and class_id >= 4:
            return "ต้องตรวจ Heat Risk และกำหนด Green Infrastructure"
        if class_id >= 5:
            return "ตรวจ restrictive area, access, facility, field survey"
        if class_id >= 4:
            return "ตรวจความพร้อมโครงสร้างพื้นฐานและข้อจำกัดพื้นที่"
        return "สำรอง / ตรวจสอบเพิ่ม"

    df["ระดับความเป็นไปได้"] = df.apply(tier, axis=1)
    df["เงื่อนไขสำคัญ"] = df.apply(condition, axis=1)

    keep_cols = []
    for col in [
        "ลำดับ",
        "class",
        "ความหมาย",
        "พื้นที่ (ไร่)",
        "centroid_lon",
        "centroid_lat",
        "ระดับความเป็นไปได้",
        "เงื่อนไขสำคัญ",
    ]:
        if col in df.columns:
            keep_cols.append(col)

    if "ระดับความเป็นไปได้" not in keep_cols:
        keep_cols.append("ระดับความเป็นไปได้")
    if "เงื่อนไขสำคัญ" not in keep_cols:
        keep_cols.append("เงื่อนไขสำคัญ")

    df = df.sort_values(by=["_class", "_area_rai"], ascending=[False, False])
    out = df[keep_cols].head(top_n).reset_index(drop=True)

    return out


def _json_safe(value: Any) -> Any:
    if isinstance(value, pd.DataFrame):
        return value.to_dict(orient="records")
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    try:
        json.dumps(value)
        return value
    except Exception:
        return str(value)


def build_feasibility_payload(
    *,
    selected_province: str,
    selected_district: str,
    is_whole_country: bool,
    suitability_summary: dict,
    suitability_stats_df: pd.DataFrame,
    candidate_df: pd.DataFrame,
    suitability_config: dict,
    priority_df: pd.DataFrame,
    report_mode: str,
    feasibility_focus: list[str],
) -> dict:
    area_name = "ทั้งประเทศไทย" if is_whole_country else f"{selected_district}, {selected_province}"
    profile = get_standard_profile()
    weights_normalized = st.session_state.get("suitability_weights_normalized") or {}
    heat_penalty_enabled = bool((suitability_config or {}).get("heat_config", {}).get("enabled", False))

    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "area_name": area_name,
        "province": selected_province,
        "district": selected_district,
        "is_whole_country": is_whole_country,
        "planning_standard_profile": profile,
        "report_mode": report_mode,
        "feasibility_focus": feasibility_focus,
        "suitability_summary": suitability_summary or {},
        "suitability_stats": (
            suitability_stats_df.to_dict(orient="records")
            if suitability_stats_df is not None and not suitability_stats_df.empty
            else []
        ),
        "candidate_count": int(len(candidate_df)) if candidate_df is not None else 0,
        "candidate_priority": (
            priority_df.to_dict(orient="records")
            if priority_df is not None and not priority_df.empty
            else []
        ),
        "suitability_config": suitability_config or {},
        "weights_normalized": weights_normalized,
        "psa_factors": get_psa_residential_factors(),
        "density_reference": get_density_reference(),
        "heat_penalty_enabled": heat_penalty_enabled,
        "heat_image_count": st.session_state.get("suitability_heat_image_count"),
        "uhi_standalone_summary": st.session_state.get("uhi_heat_summary") or {},
    }

    return _json_safe(payload)


def build_deterministic_feasibility_report(payload: dict) -> str:
    profile = payload.get("planning_standard_profile", {})
    summary = payload.get("suitability_summary", {}) or {}
    area_name = payload.get("area_name", "-")
    heat_penalty_enabled = bool(payload.get("heat_penalty_enabled", False))
    candidate_count = int(payload.get("candidate_count", 0) or 0)

    priority_df = pd.DataFrame(payload.get("candidate_priority", []))
    stats_df = pd.DataFrame(payload.get("suitability_stats", []))

    focus_text = ", ".join(payload.get("feasibility_focus", [])) or "ทั่วไป"

    heat_text = (
        "เปิดใช้ Heat Penalty แล้ว จึงมีการหักคะแนนพื้นที่ร้อนจัดใน Suitability"
        if heat_penalty_enabled
        else "ยังไม่ได้เปิดใช้ Heat Penalty ใน Suitability ควรตรวจ UHI เพิ่มก่อนสรุปขั้นสุดท้าย"
    )

    candidate_rai = _safe_float(summary.get("development_candidate_rai"), 0)
    candidate_percent = _safe_float(summary.get("candidate_percent"), 0)
    restricted_rai = _safe_float(summary.get("restricted_rai"), 0)
    total_rai = _safe_float(summary.get("total_rai"), 0)

    if candidate_percent >= 25:
        diagnosis = "มีพื้นที่ศักยภาพค่อนข้างมาก ควรเข้าสู่การคัดกรองเชิงคุณภาพและ feasibility รายแปลง"
    elif candidate_percent >= 10:
        diagnosis = "มีพื้นที่ศักยภาพปานกลาง ควรเลือกเฉพาะ candidate ที่มี access และ facility พร้อม"
    elif candidate_percent > 0:
        diagnosis = "มีพื้นที่ศักยภาพจำกัด ต้องเข้มงวดเรื่องข้อจำกัดและต้นทุนโครงสร้างพื้นฐาน"
    else:
        diagnosis = "ยังไม่พบพื้นที่ศักยภาพชัดเจนจาก model ปัจจุบัน ควรตรวจข้อมูล input หรือปรับขอบเขตพื้นที่ศึกษา"

    density_reference = payload.get("density_reference", {}).get("เมืองขนาดเล็ก", {})

    return f"""# Standards-Based Feasibility Bridge Report

วันที่สร้างรายงาน: {payload.get("generated_at")}

## 1. Planning Standard Profile

- Profile: **{profile.get("profile_name_th", "-")}**
- พื้นที่ศึกษา: **{area_name}**
- รูปแบบรายงาน: **{payload.get("report_mode", "-")}**
- ประเด็นเน้นวิเคราะห์: **{focus_text}**

รายงานนี้เชื่อมผล **Suitability Analysis + Candidate Area Export + UHI/Heat Penalty + Planning Standards Preset** เพื่อใช้เป็นรายงานตั้งต้นด้านความเป็นไปได้ของพื้นที่พัฒนา

## 2. Executive Feasibility Summary

- พื้นที่รวมที่คำนวณได้: **{_fmt(total_rai)} ไร่**
- พื้นที่เหมาะสมสูง–สูงมาก: **{_fmt(candidate_rai)} ไร่**
- สัดส่วนพื้นที่เหมาะสมสูง–สูงมาก: **{_fmt(candidate_percent, 1)}%**
- พื้นที่ควรหลีกเลี่ยง/จำกัด: **{_fmt(restricted_rai)} ไร่**
- Candidate polygon ที่ export แล้ว: **{candidate_count:,} แปลง/กลุ่มพื้นที่**
- สถานะ UHI: **{heat_text}**

**ข้อวินิจฉัยเบื้องต้น:** {diagnosis}

## 3. Candidate Area Priority Table

{dataframe_to_markdown_table(priority_df, max_rows=20)}

## 4. Suitability Class Area

{dataframe_to_markdown_table(stats_df, max_rows=10)}

## 5. PSA / Standards-Based Screening

ใช้แนวคิด Potential Surface Analysis และ Restrictive Area / Veto เป็นแกนการคัดกรอง:

1. ตัดพื้นที่กันออกก่อน เช่น ป่า พื้นที่คุ้มครอง พื้นที่น้ำ พื้นที่เสี่ยงภัย และพื้นที่ที่มีข้อจำกัดทางกฎหมาย
2. ให้คะแนนพื้นที่ที่เหลือด้วยปัจจัยกายภาพ สิ่งแวดล้อม การเข้าถึง และบริการสาธารณะ
3. ตรวจพื้นที่ candidate ด้วยเงื่อนไขถนน บริการสาธารณะ ความร้อนเมือง และความพร้อมโครงสร้างพื้นฐาน
4. นำ candidate ที่ผ่านเข้าสู่การประเมินภาคสนามและการออกแบบ scenario

## 6. Planning Interpretation

พื้นที่ Class 4–5 ยังไม่ใช่พื้นที่อนุมัติพัฒนาโดยอัตโนมัติ แต่เป็น **พื้นที่ candidate** ที่ควรนำไปตรวจต่อในระดับรายละเอียด  
หากพื้นที่ candidate ซ้อนกับ Heat Risk สูง ต้องกำหนดมาตรการ Green Infrastructure เช่น ร่มเงา พื้นที่สีเขียว แนวระบายน้ำสีเขียว วัสดุลดความร้อน และการจำกัดความหนาแน่นบางส่วน

## 7. Density / Zoning Reference

ตัวอย่าง density reference สำหรับเมืองขนาดเล็ก:

{dataframe_to_markdown_table(pd.DataFrame([density_reference]), max_rows=1)}

ควรใช้ density reference นี้เป็นกรอบตรวจ capacity เบื้องต้น ไม่ใช่ตัวเลขบังคับตายตัว

## 8. Recommended Development Phasing

### ระยะสั้น
- เลือก candidate ระดับ A/B ที่มีถนนและบริการสาธารณะพร้อม
- ตรวจข้อจำกัดพื้นที่กันออกและสิทธิในที่ดิน
- ตรวจภาพถ่ายดาวเทียมและสำรวจภาคสนาม

### ระยะกลาง
- พัฒนา candidate ระดับ B/C ที่ต้องลงทุนโครงสร้างพื้นฐานเพิ่ม
- วาง green corridor และ blue-green infrastructure ในพื้นที่ Heat Risk สูง
- เชื่อมกับแผนถนน สาธารณูปโภค และบริการสาธารณะ

### ระยะยาว
- พื้นที่ที่มีศักยภาพแต่ยังไกลถนน/บริการ หรือมี heat/flood risk สูง
- ใช้เป็นพื้นที่สำรอง พื้นที่สีเขียว พื้นที่รองรับน้ำ หรือการพัฒนาแบบมีเงื่อนไข

## 9. Data Gaps / Field Survey Needed

- ตรวจสอบความถูกต้องของ Road Asset และลำดับชั้นถนน
- เพิ่ม/ตรวจ Public Facility Asset เช่น โรงพยาบาล โรงเรียน ตลาด ศูนย์ราชการ สถานีขนส่ง
- ตรวจแนวเขตป่าสงวน อุทยาน พื้นที่คุ้มครอง และพื้นที่กันออกจากหน่วยงานจริง
- ตรวจพื้นที่ Heat Hotspot กับสภาพผิวดินจริง
- ตรวจโครงสร้างพื้นฐาน น้ำ ไฟฟ้า ระบายน้ำ และความเสี่ยงน้ำท่วมซ้ำ

## 10. Feasibility Verdict

**ผลเบื้องต้น:** ใช้พื้นที่ Class 4–5 เป็น candidate สำหรับการศึกษาความเป็นไปได้ขั้นต่อไป โดยให้ความสำคัญกับ candidate ที่มีขนาดเพียงพอ เข้าถึงถนนและบริการสาธารณะได้ดี ไม่อยู่ในพื้นที่กันออก และมี Heat Risk ต่ำหรือสามารถลดผลกระทบด้วย Green Infrastructure ได้

---

หมายเหตุ: รายงานนี้เป็น decision-support output ไม่ใช่เอกสารรับรองทางกฎหมาย ต้องตรวจสอบกับผังเมืองรวม ข้อกำหนดพื้นที่ และข้อมูลราชการจริงก่อนใช้ตัดสินใจ
"""


def build_ai_feasibility_prompt(payload: dict) -> str:
    compact_payload = json.dumps(payload, ensure_ascii=False, indent=2, default=str)

    return f"""
คุณคือ Standards-Based Urban Feasibility Agent สำหรับระบบ Urban OS
ให้จัดทำรายงานความเป็นไปได้เชิงผังเมืองภาษาไทย โดยอ้างอิง planning standards profile และ evidence จากระบบ

ข้อกำหนด:
- ตอบแบบมืออาชีพ กระชับ ใช้ตัดสินใจได้
- แยกข้อมูลจริงจากระบบกับข้อเสนอเชิงวิเคราะห์
- ห้ามสรุปเกินข้อมูล ถ้าข้อมูลไม่พอให้ระบุ Data Gap
- ใช้แนวคิด Potential Surface Analysis, Restrictive Area/Veto, Accessibility, Community Utilities and Facilities, Density Reference
- ให้ข้อเสนอเป็น phasing: short / medium / long term
- ให้ feasibility verdict ชัดเจน

ข้อมูลจาก Urban OS:
{compact_payload}
"""


def generate_ai_feasibility_report(payload: dict) -> str:
    if ask_openai is None:
        return "ไม่สามารถเรียกใช้ OpenAI client ได้ใน runtime นี้"

    prompt = build_ai_feasibility_prompt(payload)
    system_prompt = (
        "You are an expert Thai urban planner and GIS feasibility analyst. "
        "Produce standards-based planning feasibility reports grounded in evidence."
    )

    return ask_openai(
        prompt=prompt,
        system_prompt=system_prompt,
        temperature=0.2,
    )


def render_feasibility_bridge_panel(
    *,
    selected_province: str,
    selected_district: str,
    is_whole_country: bool,
    suitability_summary: dict,
    suitability_stats_df: pd.DataFrame,
    suitability_config: dict,
) -> None:
    st.markdown("### 🔗 Standards-Based Feasibility Bridge")
    st.caption(
        "เชื่อม Candidate Area + Suitability + UHI + Planning Standards Preset "
        "เพื่อสร้างรายงานความเป็นไปได้เบื้องต้น"
    )

    candidate_df = st.session_state.get("candidate_export_df")

    if candidate_df is None or candidate_df.empty:
        st.info(
            "ยังไม่มี Candidate Area Export ให้กด Generate Candidate GeoJSON ก่อน "
            "แล้วจึงสร้าง Feasibility Report"
        )
        return

    heat_penalty_enabled = bool((suitability_config or {}).get("heat_config", {}).get("enabled", False))

    with st.expander("⚙️ Feasibility Bridge Settings", expanded=False):
        report_mode = st.selectbox(
            "รูปแบบรายงาน",
            ["Executive", "Technical", "Committee Brief"],
            index=0,
            key="feasibility_report_mode",
        )

        top_n = st.slider(
            "จำนวน candidate ที่ใช้จัดลำดับ",
            min_value=5,
            max_value=100,
            value=30,
            step=5,
            key="feasibility_top_n",
        )

        feasibility_focus = st.multiselect(
            "ประเด็นที่ต้องการเน้น",
            [
                "พื้นที่พัฒนาเมืองใหม่",
                "ที่อยู่อาศัย",
                "พาณิชยกรรมชุมชน",
                "โครงสร้างพื้นฐาน",
                "Green Infrastructure / UHI",
                "พื้นที่กันออก / สิ่งแวดล้อม",
                "การลงทุนระยะสั้น",
            ],
            default=[
                "พื้นที่พัฒนาเมืองใหม่",
                "โครงสร้างพื้นฐาน",
                "Green Infrastructure / UHI",
                "พื้นที่กันออก / สิ่งแวดล้อม",
            ],
            key="feasibility_focus",
        )

        use_ai_agent = st.checkbox(
            "ให้ GPT Planning Agent ช่วยเขียนรายงานเพิ่มเติม",
            value=False,
            key="feasibility_use_ai_agent",
            help="ต้องตั้งค่า OPENAI_API_KEY ใน Streamlit secrets ก่อน ถ้าไม่เปิด ระบบจะสร้างรายงาน deterministic จากข้อมูลในแอป",
        )

    priority_df = build_candidate_priority_dataframe(
        candidate_df=candidate_df,
        top_n=int(top_n),
        heat_penalty_enabled=heat_penalty_enabled,
    )

    st.markdown("#### Candidate Priority Preview")
    st.dataframe(priority_df, use_container_width=True, hide_index=True)

    col_run, col_clear = st.columns([2, 1])

    with col_run:
        run_clicked = st.button(
            "🧠 Generate Standards-Based Feasibility Report",
            key="generate_feasibility_bridge_report",
            use_container_width=True,
        )

    with col_clear:
        clear_clicked = st.button(
            "🧹 Clear Feasibility Report",
            key="clear_feasibility_bridge_report",
            use_container_width=True,
        )

    if clear_clicked:
        for key in [
            FEASIBILITY_SESSION_REPORT_KEY,
            FEASIBILITY_SESSION_PAYLOAD_KEY,
            FEASIBILITY_SESSION_PRIORITY_DF_KEY,
        ]:
            st.session_state.pop(key, None)
        st.success("ล้าง Feasibility Report แล้ว")

    if run_clicked:
        payload = build_feasibility_payload(
            selected_province=selected_province,
            selected_district=selected_district,
            is_whole_country=is_whole_country,
            suitability_summary=suitability_summary or {},
            suitability_stats_df=suitability_stats_df if suitability_stats_df is not None else pd.DataFrame(),
            candidate_df=candidate_df,
            suitability_config=suitability_config or {},
            priority_df=priority_df,
            report_mode=report_mode,
            feasibility_focus=feasibility_focus,
        )

        deterministic_report = build_deterministic_feasibility_report(payload)
        final_report = deterministic_report

        if use_ai_agent:
            with st.spinner("GPT Planning Agent กำลังเขียนรายงาน feasibility เพิ่มเติม..."):
                ai_report = generate_ai_feasibility_report(payload)

            final_report = (
                deterministic_report
                + "\n\n---\n\n"
                + "# GPT Planning Agent Supplement\n\n"
                + ai_report
            )

        st.session_state[FEASIBILITY_SESSION_REPORT_KEY] = final_report
        st.session_state[FEASIBILITY_SESSION_PAYLOAD_KEY] = payload
        st.session_state[FEASIBILITY_SESSION_PRIORITY_DF_KEY] = priority_df

        st.success("สร้าง Standards-Based Feasibility Report สำเร็จ")

    report_md = st.session_state.get(FEASIBILITY_SESSION_REPORT_KEY)
    payload = st.session_state.get(FEASIBILITY_SESSION_PAYLOAD_KEY)
    stored_priority_df = st.session_state.get(FEASIBILITY_SESSION_PRIORITY_DF_KEY)

    if report_md:
        st.markdown("#### Feasibility Report Preview")
        with st.expander("ดูรายงาน", expanded=True):
            st.markdown(report_md)

        area_slug = "thailand" if is_whole_country else f"{selected_province}_{selected_district}"
        area_slug = (
            area_slug
            .replace(" ", "_")
            .replace("/", "_")
            .replace("\\", "_")
            .lower()
        )

        col1, col2, col3 = st.columns(3)

        with col1:
            st.download_button(
                "⬇️ Download Feasibility Report MD",
                data=report_md.encode("utf-8"),
                file_name=f"urban_os_feasibility_report_{area_slug}.md",
                mime="text/markdown",
                use_container_width=True,
            )

        with col2:
            st.download_button(
                "⬇️ Download Feasibility Evidence JSON",
                data=json.dumps(payload or {}, ensure_ascii=False, indent=2, default=str).encode("utf-8"),
                file_name=f"urban_os_feasibility_evidence_{area_slug}.json",
                mime="application/json",
                use_container_width=True,
            )

        with col3:
            st.download_button(
                "⬇️ Download Candidate Priority CSV",
                data=dataframe_to_csv_bytes(stored_priority_df if stored_priority_df is not None else priority_df),
                file_name=f"urban_os_candidate_priority_{area_slug}.csv",
                mime="text/csv",
                use_container_width=True,
            )

        st.warning(
            "รายงานนี้เป็น feasibility bridge เบื้องต้น ไม่ใช่เอกสารอนุมัติทางกฎหมาย "
            "ต้องตรวจสอบกับผังเมืองรวม ข้อกำหนดพื้นที่ และ field survey อีกครั้ง"
        )

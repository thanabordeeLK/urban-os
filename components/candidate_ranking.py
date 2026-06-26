from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import pandas as pd
import streamlit as st


PRIORITY_RULES = [
    ("A", 80, "พื้นที่พร้อมพัฒนาระยะสั้น", "เหมาะสมสูงมาก ควรพิจารณาเป็นพื้นที่ลำดับต้น"),
    ("B", 65, "พื้นที่เหมาะสม / ระยะกลาง", "เหมาะสมสูง แต่ควรตรวจสอบโครงสร้างพื้นฐานและข้อจำกัดประกอบ"),
    ("C", 50, "พื้นที่มีศักยภาพแบบมีเงื่อนไข", "มีศักยภาพบางส่วน ควรตรวจสอบข้อจำกัดภาคสนามก่อนตัดสินใจ"),
    ("D", 0, "ไม่ใช่ candidate หลัก", "ยังไม่ควรจัดเป็นพื้นที่หลักในการพัฒนา"),
]


def _now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _safe_filename(value: str, default: str = "urban_os_candidate_ranking") -> str:
    import re

    value = str(value or default).strip()
    value = re.sub(r"[^0-9A-Za-zก-๙_\-]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(str(value).replace(",", ""))
    except Exception:
        return default


def _area_column(df: pd.DataFrame) -> str | None:
    candidates = [
        "พื้นที่ (ไร่)",
        "area_rai",
        "area",
        "Area Rai",
        "area rai",
    ]
    for col in candidates:
        if col in df.columns:
            return col
    return None


def _class_column(df: pd.DataFrame) -> str | None:
    candidates = [
        "class",
        "ระดับ",
        "Suitability Class",
        "suitability_class",
    ]
    for col in candidates:
        if col in df.columns:
            return col
    return None


def _centroid_columns(df: pd.DataFrame) -> tuple[str | None, str | None]:
    lon_candidates = ["centroid_lon", "lon", "longitude", "x"]
    lat_candidates = ["centroid_lat", "lat", "latitude", "y"]

    lon_col = next((col for col in lon_candidates if col in df.columns), None)
    lat_col = next((col for col in lat_candidates if col in df.columns), None)
    return lon_col, lat_col


def _priority_from_score(score: float) -> tuple[str, str, str]:
    for code, threshold, phase, recommendation in PRIORITY_RULES:
        if score >= threshold:
            return code, phase, recommendation
    return "D", "ไม่ใช่ candidate หลัก", "ยังไม่ควรจัดเป็นพื้นที่หลักในการพัฒนา"


def _score_area(area_rai: float, ideal_min: float, ideal_max: float) -> float:
    """
    0-20 คะแนนจากขนาดพื้นที่ candidate.
    ให้คะแนนสูงสุดเมื่ออยู่ในช่วง ideal_min-ideal_max
    """

    if area_rai <= 0:
        return 0.0

    if ideal_min <= area_rai <= ideal_max:
        return 20.0

    if area_rai < ideal_min:
        return max(0.0, min(20.0, (area_rai / max(ideal_min, 1)) * 20.0))

    # ใหญ่เกิน ideal_max ยังได้คะแนนดี แต่หักเล็กน้อยเพราะอาจจัดรูป/ลงทุนยาก
    over_ratio = area_rai / max(ideal_max, 1)
    return max(12.0, 20.0 - min(8.0, (over_ratio - 1.0) * 4.0))


def _score_data_readiness() -> tuple[float, list[str]]:
    """
    0-15 คะแนนจากความพร้อมของข้อมูลประกอบการตัดสินใจระดับระบบ
    """

    score = 0.0
    notes = []

    if st.session_state.get("suitability_stats_df") is not None:
        score += 4
        notes.append("มีผล Suitability")
    else:
        notes.append("ยังไม่มีผล Suitability")

    if st.session_state.get("uhi_lst_summary"):
        score += 3
        notes.append("มีผล UHI")
    else:
        notes.append("ยังไม่มีผล UHI")

    if st.session_state.get("import_wizard_last_postgis_import"):
        score += 3
        notes.append("มีชั้นข้อมูลนำเข้าใน PostGIS")
    elif st.session_state.get("import_wizard_last_geojson"):
        score += 2
        notes.append("มีชั้นข้อมูลนำเข้าใน session")
    else:
        notes.append("ยังไม่มีชั้นข้อมูลนำเข้า")

    if st.session_state.get("advanced_criteria_audit_rows"):
        score += 3
        notes.append("มี Advanced Criteria Audit")
    else:
        notes.append("ยังไม่มี Advanced Criteria Audit")

    if st.session_state.get("feasibility_payload") or st.session_state.get("feasibility_priority_df") is not None:
        score += 2
        notes.append("มี Feasibility Bridge")
    else:
        notes.append("ยังไม่มี Feasibility Bridge")

    return min(score, 15.0), notes


def _global_risk_adjustment() -> tuple[float, list[str]]:
    """
    ปรับคะแนนตามความเสี่ยงระดับพื้นที่วิเคราะห์ ไม่ใช่ราย candidate.
    """

    adjustment = 0.0
    notes: list[str] = []

    heat_summary = st.session_state.get("uhi_heat_summary") or {}
    hotspot_percent = _safe_float(heat_summary.get("hotspot_percent"), 0)
    if hotspot_percent >= 20:
        adjustment -= 8
        notes.append(f"Heat hotspot สูงมาก ({hotspot_percent:.1f}%)")
    elif hotspot_percent >= 10:
        adjustment -= 5
        notes.append(f"Heat hotspot ค่อนข้างสูง ({hotspot_percent:.1f}%)")
    elif hotspot_percent > 0:
        adjustment -= 2
        notes.append(f"มี Heat hotspot ({hotspot_percent:.1f}%)")

    summary = st.session_state.get("suitability_summary") or {}
    candidate_percent = _safe_float(summary.get("candidate_percent"), 0)
    if candidate_percent > 0 and candidate_percent < 5:
        adjustment -= 4
        notes.append(f"สัดส่วนพื้นที่เหมาะสมสูงมีน้อย ({candidate_percent:.1f}%)")
    elif candidate_percent >= 20:
        adjustment += 3
        notes.append(f"สัดส่วนพื้นที่เหมาะสมสูงค่อนข้างมาก ({candidate_percent:.1f}%)")

    return adjustment, notes


def build_candidate_ranking_dataframe(
    candidate_df: pd.DataFrame,
    *,
    ideal_min_area_rai: float = 10,
    ideal_max_area_rai: float = 300,
    top_n: int = 50,
) -> pd.DataFrame:
    if candidate_df is None or candidate_df.empty:
        return pd.DataFrame()

    df = candidate_df.copy()
    area_col = _area_column(df)
    class_col = _class_column(df)
    lon_col, lat_col = _centroid_columns(df)

    readiness_score, readiness_notes = _score_data_readiness()
    risk_adjust, risk_notes = _global_risk_adjustment()

    rows: list[dict] = []

    for idx, row in df.iterrows():
        class_id = int(_safe_float(row.get(class_col), 0)) if class_col else 0
        area_rai = _safe_float(row.get(area_col), 0) if area_col else 0

        suitability_score = max(0.0, min(45.0, (class_id / 5.0) * 45.0))
        area_score = _score_area(area_rai, ideal_min_area_rai, ideal_max_area_rai)

        # Candidate Export already filters suitable polygons, so this is a practical-readiness score.
        raw_total = suitability_score + area_score + readiness_score + risk_adjust
        readiness_total = max(0.0, min(100.0, raw_total))

        priority, phase, base_rec = _priority_from_score(readiness_total)

        constraint_notes: list[str] = []
        if area_rai < ideal_min_area_rai:
            constraint_notes.append("พื้นที่เล็กกว่าขนาดเป้าหมาย")
        elif area_rai > ideal_max_area_rai:
            constraint_notes.append("พื้นที่ใหญ่กว่าช่วงเหมาะสม ควรแบ่งเฟส")

        if risk_notes:
            constraint_notes.extend(risk_notes)

        if class_id < 4:
            constraint_notes.append("Suitability class ต่ำกว่า 4")

        recommendation = base_rec
        if priority == "A":
            recommendation += " เหมาะสำหรับ feasibility study ระยะสั้นและตรวจสอบกรรมสิทธิ์/สาธารณูปโภคทันที"
        elif priority == "B":
            recommendation += " เหมาะสำหรับแผนระยะกลางและการลงทุนโครงสร้างพื้นฐานเพิ่ม"
        elif priority == "C":
            recommendation += " ควรใช้เป็นพื้นที่สำรองหรือศึกษาข้อจำกัดเฉพาะจุด"
        else:
            recommendation += " ควรเก็บไว้เป็นข้อมูลอ้างอิง ไม่ควรเร่งลงทุน"

        rows.append(
            {
                "rank_score": round(readiness_total, 2),
                "priority": priority,
                "phase": phase,
                "suitability_class": class_id,
                "area_rai": round(area_rai, 2),
                "suitability_score_45": round(suitability_score, 2),
                "area_score_20": round(area_score, 2),
                "data_readiness_score_15": round(readiness_score, 2),
                "risk_adjustment": round(risk_adjust, 2),
                "constraint_notes": "; ".join(constraint_notes) if constraint_notes else "ไม่พบข้อจำกัดสำคัญจากข้อมูลระบบ",
                "recommendation": recommendation,
                "centroid_lon": _safe_float(row.get(lon_col), 0) if lon_col else None,
                "centroid_lat": _safe_float(row.get(lat_col), 0) if lat_col else None,
                "source_row": int(idx) + 1,
                "data_readiness_notes": "; ".join(readiness_notes),
            }
        )

    out = pd.DataFrame(rows)
    if out.empty:
        return out

    out = out.sort_values(
        by=["rank_score", "suitability_class", "area_rai"],
        ascending=[False, False, False],
    ).reset_index(drop=True)

    out.insert(0, "rank", range(1, len(out) + 1))

    top_n = int(max(1, min(top_n, 5000)))
    return out.head(top_n)


def build_candidate_ranking_markdown(
    *,
    ranking_df: pd.DataFrame,
    selected_province: str,
    selected_district: str,
    is_whole_country: bool,
    settings: dict,
) -> str:
    area_name = "ทั้งประเทศไทย" if is_whole_country else f"{selected_district}, {selected_province}"
    generated_at = _now_text()

    if ranking_df is None or ranking_df.empty:
        table_md = "_ยังไม่มีตารางจัดอันดับ candidate_"
    else:
        display_cols = [
            "rank",
            "priority",
            "phase",
            "rank_score",
            "suitability_class",
            "area_rai",
            "constraint_notes",
            "recommendation",
        ]
        display_cols = [c for c in display_cols if c in ranking_df.columns]
        try:
            table_md = ranking_df[display_cols].to_markdown(index=False)
        except Exception:
            table_md = ranking_df[display_cols].to_csv(index=False)

    return f"""# Candidate Area Ranking & Recommendation

วันที่จัดทำ: {generated_at}

## 1. พื้นที่ศึกษา
- พื้นที่: {area_name}
- จำนวน candidate ที่จัดอันดับ: {0 if ranking_df is None else len(ranking_df):,}
- Ideal area range: {settings.get("ideal_min_area_rai")}–{settings.get("ideal_max_area_rai")} ไร่

## 2. หลักการจัดอันดับ
ระบบจัดอันดับจากคะแนนรวม 100 คะแนน โดยใช้ข้อมูล:
- Suitability Class / Raw Candidate Class
- ขนาดพื้นที่ candidate
- ความพร้อมของข้อมูลประกอบ เช่น UHI, Imported Layer, Advanced Audit, Feasibility Bridge
- Risk adjustment จากภาพรวม เช่น Heat Hotspot และสัดส่วนพื้นที่เหมาะสมสูง

## 3. Priority Class
- **A**: พื้นที่พร้อมพัฒนาระยะสั้น
- **B**: พื้นที่เหมาะสม / ระยะกลาง
- **C**: พื้นที่มีศักยภาพแบบมีเงื่อนไข
- **D**: ไม่ใช่ candidate หลัก

## 4. Candidate Ranking Table

{table_md}

## 5. ข้อควรระวัง
- คะแนนนี้เป็นการจัดอันดับเบื้องต้นจากข้อมูลในระบบ Urban OS
- ควรตรวจสอบกรรมสิทธิ์ที่ดิน ราคาที่ดิน ผังเมืองตามกฎหมาย ข้อจำกัดสิ่งแวดล้อม และข้อมูลภาคสนามก่อนตัดสินใจ
- หากใช้ Imported session layer ควรนำเข้า PostGIS เพื่อให้ข้อมูลถาวรและตรวจสอบย้อนหลังได้
"""


def build_candidate_ranking_html(markdown_text: str) -> str:
    escaped = markdown_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    body = []
    for line in escaped.splitlines():
        if line.startswith("# "):
            body.append(f"<h1>{line[2:]}</h1>")
        elif line.startswith("## "):
            body.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("- "):
            body.append(f"<li>{line[2:]}</li>")
        elif line.startswith("|"):
            body.append(f"<pre class='table'>{line}</pre>")
        elif line.strip():
            body.append(f"<p>{line}</p>")
        else:
            body.append("")
    return f"""<!doctype html>
<html lang="th">
<head>
<meta charset="utf-8">
<title>Candidate Area Ranking</title>
<style>
body {{
  font-family: Arial, "Noto Sans Thai", sans-serif;
  margin: 0;
  background: #eef3f7;
  color: #172033;
  line-height: 1.55;
}}
.report {{
  max-width: 1160px;
  margin: 24px auto;
  background: white;
  padding: 34px 42px;
  border-radius: 12px;
  box-shadow: 0 8px 28px rgba(0,0,0,.12);
}}
h1 {{
  color: #0b3040;
  border-bottom: 4px solid #00bcd4;
  padding-bottom: 12px;
}}
h2 {{
  color: #0b3040;
  border-left: 6px solid #00bcd4;
  padding-left: 10px;
  margin-top: 30px;
}}
pre.table {{
  white-space: pre-wrap;
  background: #f6f8fa;
  border: 1px solid #d9e2ec;
  padding: 5px 8px;
  margin: 0;
  font-size: 12px;
}}
@media print {{
  body {{ background: white; }}
  .report {{ margin: 0; box-shadow: none; border-radius: 0; }}
}}
</style>
</head>
<body>
<div class="report">
{''.join(body)}
</div>
</body>
</html>"""


def _ranking_json_payload(ranking_df: pd.DataFrame, settings: dict) -> dict:
    return {
        "generated_at": _now_text(),
        "settings": settings,
        "rows": [] if ranking_df is None or ranking_df.empty else ranking_df.to_dict(orient="records"),
        "source": {
            "candidate_export_count": int(st.session_state.get("candidate_export_count") or 0),
            "candidate_export_settings": st.session_state.get("candidate_export_settings") or {},
            "suitability_summary": st.session_state.get("suitability_summary") or {},
            "uhi_heat_summary": st.session_state.get("uhi_heat_summary") or {},
            "imported_layer": {
                "name": st.session_state.get("import_wizard_last_layer_name", ""),
                "category": st.session_state.get("import_wizard_last_category", ""),
                "postgis_import": st.session_state.get("import_wizard_last_postgis_import") or {},
            },
        },
    }


def render_candidate_ranking_panel(
    *,
    selected_province: str,
    selected_district: str,
    is_whole_country: bool = False,
) -> None:
    st.markdown("### 🏆 Candidate Area Ranking & Recommendation")
    st.caption(
        "จัดอันดับพื้นที่ Candidate จาก Suitability, ขนาดพื้นที่, ความพร้อมข้อมูล และความเสี่ยงภาพรวม"
    )

    candidate_df = st.session_state.get("candidate_export_df")
    if candidate_df is None or candidate_df.empty:
        st.warning(
            "ยังไม่มี Candidate Area Export ให้ไปที่ Suitability Analysis แล้ว Generate Candidate GeoJSON/CSV ก่อน"
        )
        st.info(
            "Workflow: Run Suitability Analysis → Generate Candidate Area → กลับมาหน้านี้เพื่อจัดอันดับ"
        )
        return

    tab_settings, tab_ranking, tab_downloads, tab_method = st.tabs(
        ["⚙️ Settings", "🏆 Ranking", "⬇️ Downloads", "🧪 Method"]
    )

    with tab_settings:
        c1, c2, c3 = st.columns(3)
        with c1:
            ideal_min_area_rai = st.number_input(
                "Ideal min area (ไร่)",
                min_value=1.0,
                max_value=10000.0,
                value=float(st.session_state.get("ranking_ideal_min_area_rai", 10.0)),
                step=5.0,
                key="ranking_ideal_min_area_rai",
            )
        with c2:
            ideal_max_area_rai = st.number_input(
                "Ideal max area (ไร่)",
                min_value=1.0,
                max_value=100000.0,
                value=float(st.session_state.get("ranking_ideal_max_area_rai", 300.0)),
                step=10.0,
                key="ranking_ideal_max_area_rai",
            )
        with c3:
            top_n = st.number_input(
                "Top N",
                min_value=1,
                max_value=5000,
                value=int(st.session_state.get("ranking_top_n", min(len(candidate_df), 50))),
                step=10,
                key="ranking_top_n",
            )

        st.info(
            "คะแนนจัดอันดับเป็น heuristic เบื้องต้น เหมาะสำหรับช่วยคัดกรองพื้นที่ก่อนทำ feasibility study รายแปลง"
        )

    settings = {
        "ideal_min_area_rai": float(st.session_state.get("ranking_ideal_min_area_rai", 10.0)),
        "ideal_max_area_rai": float(st.session_state.get("ranking_ideal_max_area_rai", 300.0)),
        "top_n": int(st.session_state.get("ranking_top_n", min(len(candidate_df), 50))),
    }

    ranking_df = build_candidate_ranking_dataframe(
        candidate_df,
        ideal_min_area_rai=settings["ideal_min_area_rai"],
        ideal_max_area_rai=settings["ideal_max_area_rai"],
        top_n=settings["top_n"],
    )

    st.session_state["candidate_ranking_df"] = ranking_df
    st.session_state["candidate_ranking_settings"] = settings
    st.session_state["candidate_ranking_generated_at"] = _now_text()

    report_md = build_candidate_ranking_markdown(
        ranking_df=ranking_df,
        selected_province=selected_province,
        selected_district=selected_district,
        is_whole_country=is_whole_country,
        settings=settings,
    )
    report_html = build_candidate_ranking_html(report_md)
    payload = _ranking_json_payload(ranking_df, settings)
    st.session_state["candidate_ranking_report_md"] = report_md
    st.session_state["candidate_ranking_payload"] = payload

    with tab_ranking:
        if ranking_df.empty:
            st.warning("ไม่สามารถสร้าง ranking table ได้")
        else:
            top = ranking_df.iloc[0]
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Top Priority", str(top.get("priority", "-")))
            c2.metric("Top Score", f"{float(top.get('rank_score', 0)):,.1f}")
            c3.metric("Top Area", f"{float(top.get('area_rai', 0)):,.1f} ไร่")
            c4.metric("Candidates", f"{len(ranking_df):,}")

            st.dataframe(ranking_df, use_container_width=True, hide_index=True)

    with tab_downloads:
        base_name = _safe_filename(f"urban_os_candidate_ranking_{selected_province}_{selected_district}")
        c1, c2 = st.columns(2)
        with c1:
            st.download_button(
                "⬇️ Download Ranking CSV",
                data=ranking_df.to_csv(index=False).encode("utf-8-sig"),
                file_name=f"{base_name}.csv",
                mime="text/csv",
                use_container_width=True,
            )
            st.download_button(
                "⬇️ Download Ranking Markdown",
                data=report_md.encode("utf-8"),
                file_name=f"{base_name}.md",
                mime="text/markdown",
                use_container_width=True,
            )
        with c2:
            st.download_button(
                "⬇️ Download Ranking HTML",
                data=report_html.encode("utf-8"),
                file_name=f"{base_name}.html",
                mime="text/html",
                use_container_width=True,
            )
            st.download_button(
                "⬇️ Download Ranking JSON",
                data=json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
                file_name=f"{base_name}.json",
                mime="application/json",
                use_container_width=True,
            )

    with tab_method:
        st.markdown(
            """
            #### Scoring structure

            - Suitability score: 45 คะแนน
            - Area suitability score: 20 คะแนน
            - Data readiness score: 15 คะแนน
            - Risk adjustment: ปรับเพิ่ม/ลดจาก UHI และสัดส่วนพื้นที่เหมาะสมสูง

            #### Priority class

            - A ≥ 80: พื้นที่พร้อมพัฒนาระยะสั้น
            - B ≥ 65: พื้นที่เหมาะสม / ระยะกลาง
            - C ≥ 50: พื้นที่มีศักยภาพแบบมีเงื่อนไข
            - D < 50: ไม่ใช่ candidate หลัก

            #### Important note

            คะแนนนี้ใช้คัดกรองเบื้องต้น ไม่แทนการตรวจภาคสนาม ผังเมืองตามกฎหมาย ราคาที่ดิน กรรมสิทธิ์ และข้อจำกัดหน่วยงาน
            """
        )

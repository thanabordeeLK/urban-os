from __future__ import annotations

import html
import io
import json
from datetime import datetime
from typing import Any

import pandas as pd
import streamlit as st


def _now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _safe_filename(value: str, default: str = "urban_os_planning_report") -> str:
    import re

    value = str(value or default).strip()
    value = re.sub(r"[^0-9A-Za-zก-๙_\-]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or default


def _json_safe(value: Any) -> Any:
    if isinstance(value, pd.DataFrame):
        return value.to_dict(orient="records")
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            return str(value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _df_to_csv_bytes(df: pd.DataFrame | None) -> bytes:
    if df is None or df.empty:
        return "".encode("utf-8-sig")
    return df.to_csv(index=False).encode("utf-8-sig")


def _df_to_markdown(df: pd.DataFrame | None, max_rows: int = 50) -> str:
    if df is None or df.empty:
        return "_ไม่มีข้อมูลตาราง_"

    try:
        return df.head(max_rows).to_markdown(index=False)
    except Exception:
        # Fallback without requiring tabulate
        rows = df.head(max_rows).fillna("").astype(str).to_dict(orient="records")
        if not rows:
            return "_ไม่มีข้อมูลตาราง_"

        columns = list(rows[0].keys())
        lines = [
            "| " + " | ".join(columns) + " |",
            "| " + " | ".join(["---"] * len(columns)) + " |",
        ]
        for row in rows:
            lines.append("| " + " | ".join(str(row.get(col, "")) for col in columns) + " |")
        return "\n".join(lines)


def _dict_bullets(data: dict | None, *, prefix: str = "-") -> str:
    if not data:
        return "_ไม่มีข้อมูล_"

    lines = []
    for key, value in data.items():
        if isinstance(value, float):
            value_text = f"{value:,.2f}"
        else:
            value_text = str(value)
        lines.append(f"{prefix} **{key}**: {value_text}")
    return "\n".join(lines)


def _read_session_dataframe(key: str) -> pd.DataFrame | None:
    value = st.session_state.get(key)
    if isinstance(value, pd.DataFrame):
        return value
    return None


def _evidence_context(
    *,
    selected_province: str,
    selected_district: str,
    is_whole_country: bool,
    settings: dict,
) -> dict:
    suitability_df = _read_session_dataframe("suitability_stats_df")
    candidate_df = _read_session_dataframe("candidate_export_df")
    uhi_df = _read_session_dataframe("uhi_heat_area_df")

    evidence = {
        "generated_at": _now_text(),
        "report_settings": settings,
        "area": {
            "province": selected_province,
            "district": selected_district,
            "is_whole_country": is_whole_country,
            "area_name": "ทั้งประเทศไทย" if is_whole_country else f"{selected_district}, {selected_province}",
        },
        "suitability": {
            "has_result": suitability_df is not None and not suitability_df.empty,
            "summary": st.session_state.get("suitability_summary") or {},
            "stats": suitability_df,
            "weights_normalized": st.session_state.get("suitability_weights_normalized") or {},
            "last_config": st.session_state.get("suitability_last_config") or {},
            "advanced_metadata": st.session_state.get("suitability_advanced_metadata") or {},
        },
        "uhi": {
            "has_result": bool(st.session_state.get("uhi_lst_summary")),
            "settings": st.session_state.get("uhi_settings") or {},
            "lst_summary": st.session_state.get("uhi_lst_summary") or {},
            "heat_summary": st.session_state.get("uhi_heat_summary") or {},
            "heat_area": uhi_df,
            "image_count": int(st.session_state.get("uhi_image_count") or 0),
        },
        "candidate_areas": {
            "has_result": candidate_df is not None and not candidate_df.empty,
            "count": int(st.session_state.get("candidate_export_count") or (0 if candidate_df is None else len(candidate_df))),
            "settings": st.session_state.get("candidate_export_settings") or {},
            "table": candidate_df,
        },
        "candidate_ranking": {
            "has_result": st.session_state.get("candidate_ranking_df") is not None,
            "settings": st.session_state.get("candidate_ranking_settings") or {},
            "table": st.session_state.get("candidate_ranking_df"),
            "generated_at": st.session_state.get("candidate_ranking_generated_at", ""),
        },
        "ai_planning_recommendation": {
            "has_result": bool(st.session_state.get("ai_planning_recommendation_report_md")),
            "report_md": st.session_state.get("ai_planning_recommendation_report_md", ""),
            "payload": st.session_state.get("ai_planning_recommendation_payload") or {},
            "rule_table": st.session_state.get("ai_planning_rule_recommendation_df"),
        },
        "feasibility": {
            "payload": st.session_state.get("feasibility_payload") or {},
            "priority_table": st.session_state.get("feasibility_priority_df"),
            "ai_report": st.session_state.get("feasibility_ai_report", ""),
        },
        "advanced_audit": {
            "rows": st.session_state.get("advanced_criteria_audit_rows", []) or [],
        },
        "imported_layers": {
            "last_layer_name": st.session_state.get("import_wizard_last_layer_name", ""),
            "last_category": st.session_state.get("import_wizard_last_category", ""),
            "last_feature_count": len((st.session_state.get("import_wizard_last_geojson") or {}).get("features", []) or [])
            if isinstance(st.session_state.get("import_wizard_last_geojson"), dict)
            else 0,
            "last_postgis_import": st.session_state.get("import_wizard_last_postgis_import") or {},
            "overlay_meta": st.session_state.get("import_overlay_last_meta") or {},
        },
        "map_workspace": {
            "pane_count_label": st.session_state.get("map_pane_count_label", "1 หน้าจอ"),
            "sync_mode": st.session_state.get("map_sync_mode_label", "ไม่ซิงก์"),
            "height": st.session_state.get("map_panel_height", ""),
            "views": [
                {
                    "view": idx,
                    "layer": st.session_state.get(f"map_view_{idx}_layer_choice", ""),
                    "basemap": st.session_state.get(f"map_view_{idx}_basemap", ""),
                    "target_scale": st.session_state.get(f"map_view_{idx}_scale_label", ""),
                    "actual_scale": st.session_state.get(f"map_view_{idx}_actual_scale_label", ""),
                    "zoom": st.session_state.get(f"map_view_{idx}_zoom", ""),
                }
                for idx in [1, 2, 3]
            ],
        },
    }

    return evidence


def _summary_csv_dataframe(evidence: dict) -> pd.DataFrame:
    rows: list[dict] = []

    def add(section: str, metric: str, value: Any, note: str = ""):
        rows.append(
            {
                "section": section,
                "metric": metric,
                "value": _json_safe(value),
                "note": note,
            }
        )

    area = evidence.get("area", {})
    add("Area", "province", area.get("province", ""))
    add("Area", "district", area.get("district", ""))
    add("Area", "is_whole_country", area.get("is_whole_country", False))

    suit = evidence.get("suitability", {})
    add("Suitability", "has_result", suit.get("has_result", False))
    for key, value in (suit.get("summary") or {}).items():
        add("Suitability", key, value)

    uhi = evidence.get("uhi", {})
    add("UHI", "has_result", uhi.get("has_result", False))
    add("UHI", "image_count", uhi.get("image_count", 0))
    for key, value in (uhi.get("lst_summary") or {}).items():
        add("UHI LST", key, value)
    for key, value in (uhi.get("heat_summary") or {}).items():
        add("UHI Heat", key, value)

    cand = evidence.get("candidate_areas", {})
    add("Candidate", "has_result", cand.get("has_result", False))
    add("Candidate", "count", cand.get("count", 0))

    ranking = evidence.get("candidate_ranking", {})
    add("Candidate Ranking", "has_result", ranking.get("has_result", False))
    ranking_table = ranking.get("table")
    if ranking_table is not None and not getattr(ranking_table, "empty", True):
        add("Candidate Ranking", "top_priority", ranking_table.iloc[0].get("priority", ""))
        add("Candidate Ranking", "top_score", ranking_table.iloc[0].get("rank_score", ""))

    ai_rec = evidence.get("ai_planning_recommendation", {})
    add("AI Recommendation", "has_result", ai_rec.get("has_result", False))
    rule_table = ai_rec.get("rule_table")
    if rule_table is not None and not getattr(rule_table, "empty", True):
        add("AI Recommendation", "top_suggested_land_use", rule_table.iloc[0].get("suggested_land_use", ""))

    imported = evidence.get("imported_layers", {})
    add("Imported Layers", "last_layer_name", imported.get("last_layer_name", ""))
    add("Imported Layers", "last_category", imported.get("last_category", ""))
    add("Imported Layers", "last_feature_count", imported.get("last_feature_count", 0))
    add("Imported Layers", "last_postgis_table", (imported.get("last_postgis_import") or {}).get("full_table_name", ""))

    return pd.DataFrame(rows)


def _recommendations(evidence: dict) -> list[str]:
    recs: list[str] = []

    suit_summary = (evidence.get("suitability") or {}).get("summary") or {}
    candidate_percent = float(suit_summary.get("candidate_percent", 0) or 0)
    restricted_rai = float(suit_summary.get("restricted_rai", 0) or 0)

    if evidence.get("suitability", {}).get("has_result"):
        if candidate_percent >= 25:
            recs.append("จัดลำดับพื้นที่เหมาะสมสูง–สูงมากเป็นโซนพัฒนาเชิงยุทธศาสตร์ และตรวจสอบกรรมสิทธิ์/โครงสร้างพื้นฐานประกอบ")
        elif candidate_percent > 0:
            recs.append("ใช้พื้นที่เหมาะสมสูง–สูงมากเป็นพื้นที่ candidate เบื้องต้น แต่ควรตรวจสอบข้อจำกัดและบริการสาธารณะเพิ่มเติม")
        else:
            recs.append("ผล Suitability ยังไม่พบสัดส่วนพื้นที่เหมาะสมสูงมาก ควรปรับน้ำหนักปัจจัยหรือเติมข้อมูลถนน/บริการ/ข้อจำกัดให้ครบ")

        if restricted_rai > 0:
            recs.append("พื้นที่กันออก/พื้นที่จำกัดควรถูกใช้เป็น hard constraint ในการออกแบบผังและกำหนดแนวกันชน")

    heat_summary = (evidence.get("uhi") or {}).get("heat_summary") or {}
    hotspot_percent = float(heat_summary.get("hotspot_percent", 0) or 0)
    if evidence.get("uhi", {}).get("has_result"):
        if hotspot_percent >= 10:
            recs.append("พื้นที่ Heat Hotspot ควรถูกบูรณาการกับแนว Green Corridor, urban tree canopy และมาตรการลดอุณหภูมิผิวดิน")
        else:
            recs.append("ผล UHI ควรใช้ประกอบการกำหนดพื้นที่สีเขียวและวัสดุผิวเมือง แม้ hotspot ยังไม่สูงมาก")

    if evidence.get("candidate_areas", {}).get("has_result"):
        recs.append("นำ Candidate Areas ไปตรวจสอบภาคสนามและเปรียบเทียบกับแผนการลงทุนโครงสร้างพื้นฐานระยะสั้น–กลาง")

    ranking_table = (evidence.get("candidate_ranking") or {}).get("table")
    if ranking_table is not None and not getattr(ranking_table, "empty", True):
        top = ranking_table.iloc[0]
        recs.append(
            f"ใช้พื้นที่ Candidate อันดับ 1 Priority {top.get('priority')} "
            f"เป็นพื้นที่ตั้งต้นสำหรับ feasibility study โดยมีคะแนน {top.get('rank_score')}"
        )

    ai_rule_table = (evidence.get("ai_planning_recommendation") or {}).get("rule_table")
    if ai_rule_table is not None and not getattr(ai_rule_table, "empty", True):
        top = ai_rule_table.iloc[0]
        recs.append(
            f"ข้อเสนอแนะ AI ระบุให้พื้นที่อันดับ 1 เหมาะกับ {top.get('suggested_land_use')} "
            f"และควรดำเนินการแบบ {top.get('development_phase')}"
        )

    imported = evidence.get("imported_layers", {})
    if imported.get("last_feature_count", 0):
        recs.append("ชั้นข้อมูลที่นำเข้าควรถูกจัดเก็บถาวรใน PostGIS และระบุ metadata แหล่งที่มา/วันที่ปรับปรุงก่อนใช้ประกอบการตัดสินใจ")

    if not recs:
        recs.append("ควรรัน Suitability Analysis และ/หรือ UHI ก่อนสร้างรายงานฉบับใช้งานจริง")

    return recs


def _data_gaps(evidence: dict) -> list[str]:
    gaps: list[str] = []

    if not evidence.get("suitability", {}).get("has_result"):
        gaps.append("ยังไม่มีผล Suitability Analysis")
    if not evidence.get("candidate_areas", {}).get("has_result"):
        gaps.append("ยังไม่มี Candidate Area Export")
    if not evidence.get("uhi", {}).get("has_result"):
        gaps.append("ยังไม่มีผล Urban Heat Island / LST")
    if not evidence.get("imported_layers", {}).get("last_feature_count", 0) and not evidence.get("imported_layers", {}).get("last_postgis_import"):
        gaps.append("ยังไม่มีชั้นข้อมูล GIS ที่นำเข้าเองหรือบันทึกเข้า PostGIS")
    if not evidence.get("advanced_audit", {}).get("rows"):
        gaps.append("ยังไม่มี Advanced Criteria Score Audit")

    return gaps


def build_planning_report_markdown(evidence: dict) -> str:
    settings = evidence.get("report_settings", {})
    area = evidence.get("area", {})
    title = settings.get("title") or "Urban OS Planning Report"
    objective = settings.get("objective") or "สรุปผลวิเคราะห์เชิงพื้นที่เพื่อสนับสนุนการวางผังเมือง"
    prepared_by = settings.get("prepared_by") or "-"
    report_type = settings.get("report_type") or "Executive + Technical"

    lines: list[str] = [
        f"# {title}",
        "",
        f"วันที่จัดทำ: {evidence.get('generated_at')}",
        f"จัดทำโดย: {prepared_by}",
        f"รูปแบบรายงาน: {report_type}",
        "",
        "## 1. ข้อมูลพื้นที่ศึกษา",
        f"- พื้นที่: **{area.get('area_name', '-')}**",
        f"- จังหวัด: {area.get('province', '-')}",
        f"- อำเภอ: {area.get('district', '-')}",
        f"- วิเคราะห์ระดับประเทศ: {area.get('is_whole_country', False)}",
        "",
        "## 2. วัตถุประสงค์",
        objective,
        "",
    ]

    if settings.get("include_suitability", True):
        suitability = evidence.get("suitability", {})
        lines.extend(
            [
                "## 3. Suitability Analysis",
                f"- มีผลวิเคราะห์: {suitability.get('has_result', False)}",
                "",
                "### 3.1 Summary",
                _dict_bullets(suitability.get("summary") or {}),
                "",
                "### 3.2 Normalized Weights",
                _dict_bullets(suitability.get("weights_normalized") or {}),
                "",
                "### 3.3 Area Table",
                _df_to_markdown(suitability.get("stats")),
                "",
            ]
        )

    if settings.get("include_uhi", True):
        uhi = evidence.get("uhi", {})
        lines.extend(
            [
                "## 4. Urban Heat Island / LST",
                f"- มีผลวิเคราะห์: {uhi.get('has_result', False)}",
                f"- จำนวนภาพ Landsat: {uhi.get('image_count', 0):,}",
                "",
                "### 4.1 LST Summary",
                _dict_bullets(uhi.get("lst_summary") or {}),
                "",
                "### 4.2 Heat Risk Summary",
                _dict_bullets(uhi.get("heat_summary") or {}),
                "",
                "### 4.3 Heat Risk Area Table",
                _df_to_markdown(uhi.get("heat_area")),
                "",
            ]
        )

    if settings.get("include_candidate", True):
        candidate = evidence.get("candidate_areas", {})
        lines.extend(
            [
                "## 5. Candidate Areas",
                f"- มี Candidate Area: {candidate.get('has_result', False)}",
                f"- จำนวนพื้นที่ candidate: {candidate.get('count', 0):,}",
                "",
                _df_to_markdown(candidate.get("table"), max_rows=30),
                "",
            ]
        )

        ranking = evidence.get("candidate_ranking", {})
        lines.extend(
            [
                "## 5.1 Candidate Area Ranking",
                f"- มีผลจัดอันดับ: {ranking.get('has_result', False)}",
                f"- Generated at: {ranking.get('generated_at') or '-'}",
                "",
                _df_to_markdown(ranking.get("table"), max_rows=30),
                "",
            ]
        )

        ai_rec = evidence.get("ai_planning_recommendation", {})
        lines.extend(
            [
                "## 5.2 AI Planning Recommendation",
                f"- มีข้อเสนอแนะจาก Agent: {ai_rec.get('has_result', False)}",
                "",
                _df_to_markdown(ai_rec.get("rule_table"), max_rows=30),
                "",
            ]
        )
        if ai_rec.get("report_md"):
            lines.extend(
                [
                    "### 5.2.1 AI Recommendation Report",
                    ai_rec.get("report_md", ""),
                    "",
                ]
            )

    if settings.get("include_imported", True):
        imported = evidence.get("imported_layers", {})
        lines.extend(
            [
                "## 6. Imported Layers / PostGIS",
                f"- Last imported layer: {imported.get('last_layer_name') or '-'}",
                f"- Category: {imported.get('last_category') or '-'}",
                f"- Features in session: {imported.get('last_feature_count', 0):,}",
                f"- Last PostGIS table: {(imported.get('last_postgis_import') or {}).get('full_table_name', '-')}",
                "",
                "### 6.1 Overlay Metadata",
                _dict_bullets(imported.get("overlay_meta") or {}),
                "",
            ]
        )

    if settings.get("include_audit", True):
        audit_rows = (evidence.get("advanced_audit") or {}).get("rows") or []
        lines.extend(["## 7. Advanced Criteria / Score Audit", ""])
        if audit_rows:
            lines.append(_df_to_markdown(pd.DataFrame(audit_rows), max_rows=50))
        else:
            lines.append("_ยังไม่มี Advanced Criteria Score Audit_")
        lines.append("")

    if settings.get("include_map", True):
        map_ws = evidence.get("map_workspace", {})
        lines.extend(
            [
                "## 8. Map Workspace / Export Metadata",
                f"- Map panes: {map_ws.get('pane_count_label')}",
                f"- Sync mode: {map_ws.get('sync_mode')}",
                f"- Map height: {map_ws.get('height')}",
                "",
                _df_to_markdown(pd.DataFrame(map_ws.get("views") or []), max_rows=3),
                "",
            ]
        )

    lines.extend(
        [
            "## 9. ข้อเสนอเชิงผังเมืองเบื้องต้น",
            "",
        ]
    )
    for idx, rec in enumerate(_recommendations(evidence), start=1):
        lines.append(f"{idx}. {rec}")

    lines.extend(
        [
            "",
            "## 10. ข้อจำกัดและ Data Gaps",
            "",
        ]
    )
    gaps = _data_gaps(evidence)
    if gaps:
        for gap in gaps:
            lines.append(f"- {gap}")
    else:
        lines.append("- ไม่พบช่องว่างข้อมูลสำคัญจาก checklist เบื้องต้น")

    lines.extend(
        [
            "",
            "## 11. หมายเหตุการใช้งาน",
            "- รายงานนี้เป็นผลจากแบบจำลองเชิงพื้นที่เบื้องต้น ควรตรวจสอบร่วมกับข้อมูลภาคสนาม เอกสารทางกฎหมาย และหน่วยงานที่เกี่ยวข้อง",
            "- ค่า scale ของ web map เป็นค่าประมาณ ควรตรวจสอบซ้ำใน GIS layout หากใช้เป็นเอกสารทางราชการ",
            "- ชั้นข้อมูลนำเข้าจาก session อาจหายเมื่อ session สิ้นสุด ถ้าต้องการใช้งานถาวรควรเก็บใน PostGIS",
            "",
        ]
    )

    return "\n".join(lines)


def build_planning_report_html(markdown_text: str, evidence: dict) -> str:
    # Simple markdown-ish HTML renderer that keeps predictable styling without extra deps.
    escaped = html.escape(markdown_text)

    lines = escaped.splitlines()
    body_lines = []
    in_ul = False
    in_ol = False
    in_pre = False

    for raw in lines:
        line = raw.rstrip()

        if line.startswith("```"):
            if not in_pre:
                body_lines.append("<pre>")
                in_pre = True
            else:
                body_lines.append("</pre>")
                in_pre = False
            continue

        if in_pre:
            body_lines.append(line)
            continue

        if line.startswith("# "):
            body_lines.append(f"<h1>{line[2:]}</h1>")
        elif line.startswith("## "):
            body_lines.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("### "):
            body_lines.append(f"<h3>{line[4:]}</h3>")
        elif line.startswith("- "):
            if not in_ul:
                body_lines.append("<ul>")
                in_ul = True
            body_lines.append(f"<li>{line[2:]}</li>")
        elif re_match := __import__("re").match(r"^\d+\.\s+(.*)$", line):
            if not in_ol:
                body_lines.append("<ol>")
                in_ol = True
            body_lines.append(f"<li>{re_match.group(1)}</li>")
        else:
            if in_ul:
                body_lines.append("</ul>")
                in_ul = False
            if in_ol:
                body_lines.append("</ol>")
                in_ol = False

            if line.strip():
                if line.startswith("|"):
                    body_lines.append(f"<pre class='table'>{line}</pre>")
                else:
                    body_lines.append(f"<p>{line}</p>")
            else:
                body_lines.append("")

    if in_ul:
        body_lines.append("</ul>")
    if in_ol:
        body_lines.append("</ol>")

    title = html.escape(evidence.get("report_settings", {}).get("title", "Urban OS Planning Report"))

    return f"""<!doctype html>
<html lang="th">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
body {{
  font-family: Arial, "Noto Sans Thai", sans-serif;
  color: #172033;
  line-height: 1.55;
  margin: 0;
  background: #eef3f7;
}}
.report {{
  max-width: 1120px;
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
  margin-top: 32px;
  border-left: 6px solid #00bcd4;
  padding-left: 10px;
}}
h3 {{ color: #234b5f; }}
p, li {{ font-size: 14px; }}
pre.table {{
  white-space: pre-wrap;
  background: #f6f8fa;
  border: 1px solid #d9e2ec;
  padding: 6px 8px;
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
{''.join(body_lines)}
</div>
</body>
</html>"""


def render_planning_report_generator_panel(
    *,
    selected_province: str,
    selected_district: str,
    is_whole_country: bool = False,
) -> None:
    """
    Step 8.9: Planning Report Generator V2.
    """

    st.markdown("### 📄 Planning Report Generator V2")
    st.caption(
        "สร้างรายงานผังเมืองจากผล Suitability, UHI, Imported Layers, PostGIS, Candidate Areas และ Score Audit"
    )

    tab_settings, tab_preview, tab_downloads, tab_evidence = st.tabs(
        ["⚙️ Settings", "👁️ Preview", "⬇️ Downloads", "🧾 Evidence JSON"]
    )

    default_area = "ทั้งประเทศไทย" if is_whole_country else f"{selected_district}, {selected_province}"

    with tab_settings:
        c1, c2 = st.columns([1.4, 1.0])
        with c1:
            title = st.text_input(
                "Report title",
                value=f"รายงานวิเคราะห์ผังเมืองเชิงพื้นที่: {default_area}",
                key="report_v2_title",
            )
            objective = st.text_area(
                "วัตถุประสงค์รายงาน",
                value="สรุปผลวิเคราะห์เชิงพื้นที่เพื่อสนับสนุนการวางผังเมือง การจัดลำดับพื้นที่เหมาะสม และการพิจารณาข้อจำกัดเชิงพื้นที่",
                height=110,
                key="report_v2_objective",
            )
        with c2:
            prepared_by = st.text_input(
                "Prepared by",
                value=st.session_state.get("report_v2_prepared_by", ""),
                key="report_v2_prepared_by",
            )
            report_type = st.selectbox(
                "Report type",
                ["Executive + Technical", "Executive Brief", "Technical Appendix", "Committee Brief"],
                index=0,
                key="report_v2_type",
            )

        st.markdown("#### Included sections")
        cols = st.columns(3)
        with cols[0]:
            include_suitability = st.checkbox("Suitability", value=True, key="report_v2_include_suitability")
            include_uhi = st.checkbox("UHI / Heat", value=True, key="report_v2_include_uhi")
        with cols[1]:
            include_candidate = st.checkbox("Candidate Areas", value=True, key="report_v2_include_candidate")
            include_imported = st.checkbox("Imported / PostGIS Layers", value=True, key="report_v2_include_imported")
        with cols[2]:
            include_audit = st.checkbox("Advanced Audit", value=True, key="report_v2_include_audit")
            include_map = st.checkbox("Map Workspace Metadata", value=True, key="report_v2_include_map")

        st.info(
            "รายงานจะใช้ข้อมูลล่าสุดจาก session ของระบบ เช่น Suitability Summary, Candidate Export, UHI, Import Wizard และ Map Workspace"
        )

    settings = {
        "title": st.session_state.get("report_v2_title", f"รายงานวิเคราะห์ผังเมืองเชิงพื้นที่: {default_area}"),
        "objective": st.session_state.get("report_v2_objective", ""),
        "prepared_by": st.session_state.get("report_v2_prepared_by", ""),
        "report_type": st.session_state.get("report_v2_type", "Executive + Technical"),
        "include_suitability": bool(st.session_state.get("report_v2_include_suitability", True)),
        "include_uhi": bool(st.session_state.get("report_v2_include_uhi", True)),
        "include_candidate": bool(st.session_state.get("report_v2_include_candidate", True)),
        "include_imported": bool(st.session_state.get("report_v2_include_imported", True)),
        "include_audit": bool(st.session_state.get("report_v2_include_audit", True)),
        "include_map": bool(st.session_state.get("report_v2_include_map", True)),
    }

    evidence = _evidence_context(
        selected_province=selected_province,
        selected_district=selected_district,
        is_whole_country=is_whole_country,
        settings=settings,
    )
    report_md = build_planning_report_markdown(evidence)
    report_html = build_planning_report_html(report_md, evidence)
    summary_df = _summary_csv_dataframe(evidence)
    base_name = _safe_filename(f"urban_os_planning_report_{selected_province}_{selected_district}")

    with tab_preview:
        st.markdown("#### Report Preview")
        st.markdown(report_md)

    with tab_downloads:
        st.markdown("#### Download Report Outputs")

        c1, c2 = st.columns(2)
        with c1:
            st.download_button(
                "⬇️ Download Markdown Report",
                data=report_md.encode("utf-8"),
                file_name=f"{base_name}.md",
                mime="text/markdown",
                use_container_width=True,
            )
            st.download_button(
                "⬇️ Download Evidence JSON",
                data=json.dumps(_json_safe(evidence), ensure_ascii=False, indent=2).encode("utf-8"),
                file_name=f"{base_name}_evidence.json",
                mime="application/json",
                use_container_width=True,
            )
        with c2:
            st.download_button(
                "⬇️ Download HTML Report",
                data=report_html.encode("utf-8"),
                file_name=f"{base_name}.html",
                mime="text/html",
                use_container_width=True,
            )
            st.download_button(
                "⬇️ Download Summary CSV",
                data=_df_to_csv_bytes(summary_df),
                file_name=f"{base_name}_summary.csv",
                mime="text/csv",
                use_container_width=True,
            )

        st.success("สร้างไฟล์รายงาน V2 แล้ว สามารถนำ HTML ไปเปิดใน browser แล้ว Print / Save as PDF ได้")

    with tab_evidence:
        st.markdown("#### Evidence JSON")
        st.json(_json_safe(evidence))
        st.markdown("#### Summary CSV Preview")
        st.dataframe(summary_df, use_container_width=True, hide_index=True)

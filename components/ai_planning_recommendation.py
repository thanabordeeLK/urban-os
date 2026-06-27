from __future__ import annotations

import html
import json
from datetime import datetime
from typing import Any

import pandas as pd
import streamlit as st

try:
    from llm.openai_client import ask_openai
except Exception:
    ask_openai = None


def _now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _safe_filename(value: str, default: str = "urban_os_ai_planning_recommendation") -> str:
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


def _df_to_markdown(df: pd.DataFrame | None, max_rows: int = 10) -> str:
    if df is None or df.empty:
        return "_ไม่มีข้อมูล_"

    try:
        return df.head(max_rows).to_markdown(index=False)
    except Exception:
        return df.head(max_rows).to_csv(index=False)


def _df_to_csv_bytes(df: pd.DataFrame | None) -> bytes:
    if df is None or df.empty:
        return "".encode("utf-8-sig")
    return df.to_csv(index=False).encode("utf-8-sig")


def _get_ranking_df() -> pd.DataFrame | None:
    df = st.session_state.get("candidate_ranking_df")
    if isinstance(df, pd.DataFrame) and not df.empty:
        return df

    candidate_df = st.session_state.get("candidate_export_df")
    if isinstance(candidate_df, pd.DataFrame) and not candidate_df.empty:
        return candidate_df

    return None


def _priority_to_landuse(priority: str, area_rai: float, heat_note: str = "") -> str:
    priority = str(priority or "").upper().strip()

    if priority == "A":
        if area_rai >= 100:
            return "Mixed-use residential + community commercial + green infrastructure"
        return "Residential infill / community service hub / pilot development area"

    if priority == "B":
        return "Medium-term urban expansion / residential cluster / local commercial node"

    if priority == "C":
        return "Reserve area / low-density development / green buffer with conditional infrastructure"

    return "Conservation-supportive use / monitoring area / not recommended as primary urban expansion"


def _phase_strategy(priority: str) -> str:
    priority = str(priority or "").upper().strip()
    if priority == "A":
        return "Short term: สำรวจภาคสนาม ตรวจกรรมสิทธิ์ วางผังแนวถนนรอง และ feasibility study รายแปลง"
    if priority == "B":
        return "Medium term: เตรียมโครงสร้างพื้นฐาน น้ำ-ไฟ-ระบายน้ำ และจัดลำดับการลงทุน"
    if priority == "C":
        return "Long term / conditional: ใช้เป็นพื้นที่สำรองและตรวจข้อจำกัดเฉพาะจุดก่อนลงทุน"
    return "Monitoring: ยังไม่ควรเร่งพัฒนา ให้เก็บเป็นพื้นที่อ้างอิงหรือพื้นที่กันชน"


def _infra_requirements(priority: str, notes: str) -> list[str]:
    priority = str(priority or "").upper().strip()
    notes = str(notes or "")

    items = []

    if priority in {"A", "B"}:
        items.extend(
            [
                "ตรวจสอบความเชื่อมโยงถนนหลัก-ถนนรอง และกำหนด collector/local road hierarchy",
                "ประเมินระบบประปา ไฟฟ้า ระบายน้ำ และการจัดการน้ำเสียรองรับประชากรเป้าหมาย",
                "จัดวางบริการสาธารณะขั้นต่ำ เช่น โรงเรียน ศูนย์บริการชุมชน ตลาด และพื้นที่สีเขียว",
            ]
        )
    else:
        items.extend(
            [
                "ตรวจสอบข้อจำกัดทางกฎหมาย/สิ่งแวดล้อมก่อนกำหนดรูปแบบการใช้ประโยชน์",
                "วางมาตรการกันชนและระบบระบายน้ำตามสภาพพื้นที่",
            ]
        )

    if "Heat" in notes or "hotspot" in notes.lower():
        items.append("เพิ่มมาตรการลดความร้อนเมือง เช่น tree canopy, green corridor, cool pavement และพื้นที่ซึมน้ำ")

    if "เล็ก" in notes:
        items.append("รวมแปลงหรือเชื่อมพื้นที่ข้างเคียงเพื่อให้ได้ขนาดพื้นที่ที่เหมาะสมต่อโครงการ")
    if "ใหญ่" in notes:
        items.append("แบ่งเฟสการพัฒนาและกันพื้นที่เปิดโล่ง/ระบบนิเวศภายในโครงการ")

    return items


def _risk_notes(row: pd.Series, evidence: dict) -> list[str]:
    notes = []

    constraint_text = str(row.get("constraint_notes", "") or "")
    if constraint_text and constraint_text != "ไม่พบข้อจำกัดสำคัญจากข้อมูลระบบ":
        notes.append(constraint_text)

    heat_summary = evidence.get("uhi", {}).get("heat_summary", {}) or {}
    hotspot_percent = _safe_float(heat_summary.get("hotspot_percent"), 0)
    if hotspot_percent >= 10:
        notes.append(f"พื้นที่ศึกษาโดยรวมมี Heat Hotspot {hotspot_percent:.1f}% ควรระวังผลกระทบ UHI")
    elif hotspot_percent > 0:
        notes.append(f"มี Heat Hotspot {hotspot_percent:.1f}% ในพื้นที่ศึกษา ควรใช้ข้อมูล UHI ประกอบ")

    imported = evidence.get("imported_layers", {})
    if not imported.get("last_postgis_import") and imported.get("last_feature_count", 0):
        notes.append("ชั้นข้อมูลนำเข้ายังอยู่ใน session ควรนำเข้า PostGIS เพื่อความถาวร")

    if not notes:
        notes.append("ไม่พบ risk note สำคัญจากข้อมูลระบบ แต่ยังต้องตรวจสอบภาคสนามและข้อกฎหมาย")

    return notes


def _collect_evidence(
    *,
    selected_province: str,
    selected_district: str,
    is_whole_country: bool,
    top_n: int,
) -> dict:
    ranking_df = _get_ranking_df()
    if isinstance(ranking_df, pd.DataFrame):
        ranking_df = ranking_df.head(top_n).copy()

    evidence = {
        "generated_at": _now_text(),
        "area": {
            "province": selected_province,
            "district": selected_district,
            "is_whole_country": is_whole_country,
            "area_name": "ทั้งประเทศไทย" if is_whole_country else f"{selected_district}, {selected_province}",
        },
        "candidate_ranking": {
            "has_result": isinstance(ranking_df, pd.DataFrame) and not ranking_df.empty,
            "table": ranking_df,
            "settings": st.session_state.get("candidate_ranking_settings") or {},
            "generated_at": st.session_state.get("candidate_ranking_generated_at", ""),
        },
        "suitability": {
            "summary": st.session_state.get("suitability_summary") or {},
            "weights": st.session_state.get("suitability_weights_normalized") or {},
            "advanced_metadata": st.session_state.get("suitability_advanced_metadata") or {},
        },
        "uhi": {
            "lst_summary": st.session_state.get("uhi_lst_summary") or {},
            "heat_summary": st.session_state.get("uhi_heat_summary") or {},
            "settings": st.session_state.get("uhi_settings") or {},
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
        "advanced_audit": {
            "rows": st.session_state.get("advanced_criteria_audit_rows", []) or [],
        },
        "feasibility": {
            "report_md": st.session_state.get("feasibility_bridge_report_md", ""),
            "payload": st.session_state.get("feasibility_bridge_payload") or st.session_state.get("feasibility_payload") or {},
        },
    }
    return evidence


def build_rule_based_recommendations(evidence: dict) -> pd.DataFrame:
    ranking_df = evidence.get("candidate_ranking", {}).get("table")
    if ranking_df is None or getattr(ranking_df, "empty", True):
        return pd.DataFrame()

    rows = []
    for _, row in ranking_df.iterrows():
        rank = int(_safe_float(row.get("rank"), len(rows) + 1))
        priority = str(row.get("priority", "-"))
        area_rai = _safe_float(row.get("area_rai"), 0)
        score = _safe_float(row.get("rank_score"), 0)
        suitability_class = int(_safe_float(row.get("suitability_class"), 0))
        risk = _risk_notes(row, evidence)
        landuse = _priority_to_landuse(priority, area_rai, "; ".join(risk))
        phase = _phase_strategy(priority)
        infra = _infra_requirements(priority, "; ".join(risk))

        planning_strategy = []
        if priority == "A":
            planning_strategy.extend(
                [
                    "กำหนดเป็นพื้นที่นำร่องเพื่อทดสอบ feasibility รายแปลง",
                    "ออกแบบโครงข่ายถนนรองและพื้นที่สีเขียวก่อนกำหนดความหนาแน่น",
                    "จัดทำ concept plan 2–3 ทางเลือกเพื่อเปรียบเทียบการลงทุน",
                ]
            )
        elif priority == "B":
            planning_strategy.extend(
                [
                    "จัดเป็นพื้นที่พัฒนาระยะกลางและเตรียมงบโครงสร้างพื้นฐาน",
                    "เชื่อมกับศูนย์บริการ/ถนนหลักและกำหนด phasing ชัดเจน",
                ]
            )
        elif priority == "C":
            planning_strategy.extend(
                [
                    "ใช้เป็นพื้นที่สำรองและตรวจข้อจำกัดเฉพาะจุด",
                    "จำกัดความหนาแน่นหรือกำหนดเป็น low-impact development",
                ]
            )
        else:
            planning_strategy.extend(
                [
                    "ไม่ควรใช้เป็นพื้นที่พัฒนาเมืองหลักในรอบแผนนี้",
                    "ติดตามการเปลี่ยนแปลงข้อมูลและใช้เป็น buffer/green system ได้ตามความเหมาะสม",
                ]
            )

        rows.append(
            {
                "rank": rank,
                "priority": priority,
                "rank_score": round(score, 2),
                "suitability_class": suitability_class,
                "area_rai": round(area_rai, 2),
                "suggested_land_use": landuse,
                "development_phase": phase,
                "infrastructure_requirement": "; ".join(infra),
                "risk_constraint_notes": "; ".join(risk),
                "planning_strategy": "; ".join(planning_strategy),
                "executive_summary": (
                    f"Candidate อันดับ {rank} Priority {priority} คะแนน {score:.1f} "
                    f"เหมาะกับ {landuse} โดยควรดำเนินการแบบ {phase}"
                ),
            }
        )

    return pd.DataFrame(rows)


def build_ai_prompt(evidence: dict, rule_df: pd.DataFrame, focus: list[str], tone: str) -> str:
    compact = {
        "area": evidence.get("area"),
        "suitability": evidence.get("suitability"),
        "uhi": evidence.get("uhi"),
        "imported_layers": evidence.get("imported_layers"),
        "advanced_audit_rows": evidence.get("advanced_audit", {}).get("rows", [])[:20],
        "candidate_ranking": _json_safe(evidence.get("candidate_ranking", {}).get("table")),
        "rule_based_recommendations": _json_safe(rule_df),
        "focus": focus,
        "tone": tone,
    }

    payload = json.dumps(_json_safe(compact), ensure_ascii=False, indent=2)

    return f"""
โปรดเขียนข้อเสนอแนะเชิงผังเมืองภาษาไทยจากข้อมูล Urban OS ด้านล่าง

ข้อกำหนด:
- ห้ามอ้างว่าข้อมูลครบถ้า evidence ยังไม่ครบ
- แยกข้อเสนอเป็นราย Candidate ตาม rank
- ระบุ Suggested Land Use, Development Phase, Infrastructure Requirement, Risk / Constraint Notes, Planning Strategy
- สรุปสำหรับผู้บริหารตอนต้น
- ใช้ถ้อยคำแบบ {tone}
- ประเด็นที่ต้องเน้น: {", ".join(focus) if focus else "ภาพรวมผังเมือง"}

ข้อมูล evidence:
{payload}
"""


def call_ai_recommendation(evidence: dict, rule_df: pd.DataFrame, focus: list[str], tone: str) -> str:
    if ask_openai is None:
        return "ไม่สามารถเรียกใช้ OpenAI client ได้ใน runtime นี้"

    system_prompt = (
        "You are an expert Thai urban planner, GIS analyst, and planning policy advisor. "
        "Write practical, evidence-grounded planning recommendations. "
        "Do not invent facts beyond the supplied evidence."
    )
    prompt = build_ai_prompt(evidence, rule_df, focus, tone)

    return ask_openai(
        prompt=prompt,
        system_prompt=system_prompt,
        temperature=0.2,
    )


def build_recommendation_markdown(
    *,
    evidence: dict,
    rule_df: pd.DataFrame,
    ai_report: str = "",
    focus: list[str] | None = None,
    tone: str = "เชิงวิชาการ อ่านง่าย",
) -> str:
    area = evidence.get("area", {})
    generated_at = _now_text()

    if rule_df is None or rule_df.empty:
        table_text = "_ยังไม่มีตาราง recommendation_"
    else:
        display_cols = [
            "rank",
            "priority",
            "rank_score",
            "suggested_land_use",
            "development_phase",
            "risk_constraint_notes",
            "planning_strategy",
        ]
        display_cols = [col for col in display_cols if col in rule_df.columns]
        table_text = _df_to_markdown(rule_df[display_cols], max_rows=30)

    top_summary = ""
    if rule_df is not None and not rule_df.empty:
        top = rule_df.iloc[0]
        top_summary = (
            f"พื้นที่อันดับ 1 มี Priority **{top.get('priority')}** "
            f"คะแนน **{top.get('rank_score')}** และเสนอให้ใช้เป็น "
            f"**{top.get('suggested_land_use')}**"
        )
    else:
        top_summary = "ยังไม่มีผลจัดอันดับ candidate สำหรับสร้างข้อเสนอแนะรายพื้นที่"

    lines = [
        "# AI Planning Recommendation Agent",
        "",
        f"วันที่จัดทำ: {generated_at}",
        f"พื้นที่ศึกษา: {area.get('area_name', '-')}",
        f"Tone: {tone}",
        f"Focus: {', '.join(focus or []) if focus else '-'}",
        "",
        "## 1. Executive Summary",
        top_summary,
        "",
        "## 2. Rule-Based Candidate Recommendations",
        table_text,
        "",
    ]

    if ai_report:
        lines.extend(
            [
                "## 3. GPT Planning Agent Recommendation",
                ai_report,
                "",
            ]
        )

    lines.extend(
        [
            "## 4. Evidence Notes",
            f"- Candidate ranking available: {evidence.get('candidate_ranking', {}).get('has_result')}",
            f"- Suitability summary: {bool(evidence.get('suitability', {}).get('summary'))}",
            f"- UHI summary: {bool(evidence.get('uhi', {}).get('heat_summary'))}",
            f"- Imported layer features: {evidence.get('imported_layers', {}).get('last_feature_count', 0)}",
            f"- PostGIS import: {(evidence.get('imported_layers', {}).get('last_postgis_import') or {}).get('full_table_name', '-')}",
            "",
            "## 5. Limitation",
            "- ข้อเสนอแนะนี้เป็นการวิเคราะห์เบื้องต้นจากข้อมูลใน Urban OS",
            "- ต้องตรวจสอบภาคสนาม กรรมสิทธิ์ ราคาที่ดิน ผังเมืองตามกฎหมาย ข้อจำกัดสิ่งแวดล้อม และความเห็นของหน่วยงานที่เกี่ยวข้องก่อนตัดสินใจ",
            "",
        ]
    )

    return "\n".join(lines)


def build_html_report(markdown_text: str) -> str:
    escaped = html.escape(markdown_text)
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
<title>AI Planning Recommendation</title>
<style>
body {{
  font-family: Arial, "Noto Sans Thai", sans-serif;
  margin: 0;
  background: #eef3f7;
  color: #172033;
  line-height: 1.58;
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


def render_ai_planning_recommendation_panel(
    *,
    selected_province: str,
    selected_district: str,
    is_whole_country: bool = False,
) -> None:
    st.markdown("### 🤖 AI Planning Recommendation Agent")
    st.caption(
        "สร้างข้อเสนอแนะเชิงผังเมืองจาก Candidate Ranking, Suitability, UHI, Imported Layers และ Advanced Audit"
    )

    ranking_df = _get_ranking_df()
    if ranking_df is None or ranking_df.empty:
        st.warning(
            "ยังไม่มี Candidate Ranking หรือ Candidate Export ให้สร้าง Candidate Ranking ก่อนเพื่อให้ AI Agent วิเคราะห์รายพื้นที่ได้"
        )
        st.info("Workflow: Suitability Analysis → Candidate Area Export → Candidate Ranking → AI Recommendation")
        return

    tab_settings, tab_rule, tab_ai, tab_downloads, tab_evidence = st.tabs(
        ["⚙️ Settings", "🧭 Rule-Based", "🤖 GPT Agent", "⬇️ Downloads", "🧾 Evidence"]
    )

    with tab_settings:
        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            top_n = st.number_input(
                "จำนวน candidate ที่ให้ Agent วิเคราะห์",
                min_value=1,
                max_value=50,
                value=int(st.session_state.get("ai_rec_top_n", min(len(ranking_df), 10))),
                step=1,
                key="ai_rec_top_n",
            )
        with c2:
            tone = st.selectbox(
                "รูปแบบภาษา",
                ["เชิงวิชาการ อ่านง่าย", "สรุปผู้บริหาร", "เชิงเทคนิค GIS", "เชิงนโยบายและงบประมาณ"],
                index=0,
                key="ai_rec_tone",
            )
        with c3:
            include_gpt_default = bool(st.session_state.get("ai_rec_use_gpt", False))
            use_gpt = st.checkbox(
                "ใช้ GPT Planning Agent",
                value=include_gpt_default,
                key="ai_rec_use_gpt",
                help="ต้องตั้งค่า OPENAI_API_KEY ใน Streamlit secrets ก่อน",
            )

        focus = st.multiselect(
            "ประเด็นที่ต้องการเน้น",
            [
                "พื้นที่พัฒนาเมืองใหม่",
                "ที่อยู่อาศัย",
                "พาณิชยกรรมชุมชน",
                "โลจิสติกส์ / โครงข่ายคมนาคม",
                "Green Infrastructure / UHI",
                "พื้นที่กันออก / สิ่งแวดล้อม",
                "บริการสาธารณะ",
                "แผนลงทุนระยะสั้น",
                "ข้อจำกัดผังเมืองตามกฎหมาย",
            ],
            default=[
                "พื้นที่พัฒนาเมืองใหม่",
                "Green Infrastructure / UHI",
                "บริการสาธารณะ",
                "ข้อจำกัดผังเมืองตามกฎหมาย",
            ],
            key="ai_rec_focus",
        )

        st.info(
            "Rule-Based Recommendation ใช้งานได้ทันที ส่วน GPT Agent เป็น optional และจะไม่ทำงานถ้าไม่ได้ตั้งค่า OPENAI_API_KEY"
        )

    evidence = _collect_evidence(
        selected_province=selected_province,
        selected_district=selected_district,
        is_whole_country=is_whole_country,
        top_n=int(st.session_state.get("ai_rec_top_n", min(len(ranking_df), 10))),
    )
    rule_df = build_rule_based_recommendations(evidence)
    st.session_state["ai_planning_rule_recommendation_df"] = rule_df
    st.session_state["ai_planning_recommendation_evidence"] = _json_safe(evidence)

    with tab_rule:
        st.markdown("#### Rule-Based Recommendation")
        if rule_df.empty:
            st.warning("ไม่สามารถสร้าง recommendation table ได้")
        else:
            top = rule_df.iloc[0]
            c1, c2, c3 = st.columns(3)
            c1.metric("Top Priority", str(top.get("priority", "-")))
            c2.metric("Top Score", f"{_safe_float(top.get('rank_score'), 0):,.1f}")
            c3.metric("Top Land Use", str(top.get("suggested_land_use", "-"))[:40])
            st.dataframe(rule_df, use_container_width=True, hide_index=True)

    ai_report = st.session_state.get("ai_planning_gpt_report", "")
    with tab_ai:
        st.markdown("#### GPT Planning Agent")
        if not st.session_state.get("ai_rec_use_gpt", False):
            st.info("ยังไม่ได้เปิดใช้ GPT Planning Agent ใช้ Rule-Based Recommendation ได้ทันที")
        else:
            if ask_openai is None:
                st.error("ไม่พบ llm.openai_client.ask_openai")
            if st.button("🤖 Generate GPT Planning Recommendation", use_container_width=True, key="ai_rec_generate_gpt"):
                with st.spinner("กำลังให้ GPT Planning Agent วิเคราะห์ข้อมูล..."):
                    ai_report = call_ai_recommendation(
                        evidence=evidence,
                        rule_df=rule_df,
                        focus=st.session_state.get("ai_rec_focus", []),
                        tone=st.session_state.get("ai_rec_tone", "เชิงวิชาการ อ่านง่าย"),
                    )
                    st.session_state["ai_planning_gpt_report"] = ai_report

        if ai_report:
            st.markdown(ai_report)

    report_md = build_recommendation_markdown(
        evidence=evidence,
        rule_df=rule_df,
        ai_report=st.session_state.get("ai_planning_gpt_report", ""),
        focus=st.session_state.get("ai_rec_focus", []),
        tone=st.session_state.get("ai_rec_tone", "เชิงวิชาการ อ่านง่าย"),
    )
    report_html = build_html_report(report_md)
    payload = {
        "generated_at": _now_text(),
        "settings": {
            "top_n": st.session_state.get("ai_rec_top_n"),
            "tone": st.session_state.get("ai_rec_tone"),
            "focus": st.session_state.get("ai_rec_focus", []),
            "use_gpt": st.session_state.get("ai_rec_use_gpt", False),
        },
        "rule_based": [] if rule_df.empty else rule_df.to_dict(orient="records"),
        "gpt_report": st.session_state.get("ai_planning_gpt_report", ""),
        "evidence": _json_safe(evidence),
    }

    st.session_state["ai_planning_recommendation_report_md"] = report_md
    st.session_state["ai_planning_recommendation_payload"] = payload

    with tab_downloads:
        base_name = _safe_filename(f"urban_os_ai_planning_recommendation_{selected_province}_{selected_district}")
        c1, c2 = st.columns(2)
        with c1:
            st.download_button(
                "⬇️ Download Recommendation CSV",
                data=_df_to_csv_bytes(rule_df),
                file_name=f"{base_name}.csv",
                mime="text/csv",
                use_container_width=True,
            )
            st.download_button(
                "⬇️ Download Recommendation Markdown",
                data=report_md.encode("utf-8"),
                file_name=f"{base_name}.md",
                mime="text/markdown",
                use_container_width=True,
            )
        with c2:
            st.download_button(
                "⬇️ Download Recommendation HTML",
                data=report_html.encode("utf-8"),
                file_name=f"{base_name}.html",
                mime="text/html",
                use_container_width=True,
            )
            st.download_button(
                "⬇️ Download Recommendation JSON",
                data=json.dumps(_json_safe(payload), ensure_ascii=False, indent=2).encode("utf-8"),
                file_name=f"{base_name}.json",
                mime="application/json",
                use_container_width=True,
            )

    with tab_evidence:
        st.markdown("#### Evidence JSON")
        st.json(_json_safe(evidence))
        st.markdown("#### Prompt Preview")
        with st.container():
            st.text_area(
                "Prompt ที่จะส่งให้ GPT Agent",
                value=build_ai_prompt(
                    evidence=evidence,
                    rule_df=rule_df,
                    focus=st.session_state.get("ai_rec_focus", []),
                    tone=st.session_state.get("ai_rec_tone", "เชิงวิชาการ อ่านง่าย"),
                ),
                height=260,
                key="ai_rec_prompt_preview",
            )

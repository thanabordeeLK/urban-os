from __future__ import annotations

import math
from typing import Any

import streamlit as st

from services.spatial_db_service import (
    fetch_postgis_records_by_roi,
    summarize_postgis_numeric_by_roi,
)


def _to_float(value, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        if isinstance(value, str) and not value.strip():
            return default
        return float(value)
    except Exception:
        return default


def _score_from_capacity_value(value) -> int:
    """
    Convert source values into 1-5 score.
    If the database already stores 1-5, keep it.
    If it stores percent 0-100, convert into 1-5.
    """

    v = _to_float(value, 3.0)

    if 1 <= v <= 5:
        return int(round(v))

    if 0 <= v <= 100:
        return int(max(1, min(5, math.ceil(v / 20))))

    return int(max(1, min(5, round(v))))


def _avg(values: list[float], default: float = 3.0) -> float:
    clean = [float(v) for v in values if v is not None]
    if not clean:
        return default
    return sum(clean) / len(clean)


def _contains_any(text: Any, needles: list[str]) -> bool:
    text = str(text or "").lower()
    return any(str(n or "").lower().strip() and str(n or "").lower().strip() in text for n in needles)


def _score_limit_lte(target: float, allowed: float) -> float:
    """
    Higher is better when target <= allowed.
    """

    target = _to_float(target, 0)
    allowed = _to_float(allowed, 0)

    if target <= 0 or allowed <= 0:
        return 3.0

    ratio = target / allowed
    if ratio <= 0.80:
        return 5.0
    if ratio <= 1.00:
        return 4.0
    if ratio <= 1.15:
        return 3.0
    if ratio <= 1.30:
        return 2.0
    return 1.0


def _score_min_gte(target: float, required: float) -> float:
    """
    Higher is better when target >= required.
    """

    target = _to_float(target, 0)
    required = _to_float(required, 0)

    if target <= 0 or required <= 0:
        return 3.0

    ratio = target / required
    if ratio >= 1.20:
        return 5.0
    if ratio >= 1.00:
        return 4.0
    if ratio >= 0.85:
        return 3.0
    if ratio >= 0.70:
        return 2.0
    return 1.0


def _score_buffer_rule(text: Any) -> float:
    value = str(text or "").lower()
    if not value.strip():
        return 5.0
    if any(word in value for word in ["prohibit", "not allowed", "ห้าม", "ไม่อนุญาต"]):
        return 1.0
    if any(word in value for word in ["condition", "review", "buffer", "เงื่อนไข", "ทบทวน", "กันชน"]):
        return 3.0
    return 4.0


def _field_input(label: str, default: str, key: str, disabled: bool = False) -> str:
    return st.text_input(label, value=default, key=key, disabled=disabled)


def _safe_set_state(key: str, value) -> None:
    st.session_state[key] = value


def render_advanced_criteria_postgis_autofill(roi=None) -> None:
    """
    Optional helper to pull advanced criteria values from PostGIS and write them into
    the existing manual widgets. It does not force any criterion to be enabled.
    """

    st.markdown("#### 🔌 Advanced Criteria Data Source: Manual / PostGIS")
    st.caption(
        "ใช้ส่วนนี้เพื่อดึงค่าเริ่มต้นจาก PostGIS เข้าช่องคะแนนด้านล่าง "
        "หากไม่กดดึงข้อมูล ระบบยังใช้ค่าที่กรอกมือเหมือนเดิม"
    )

    data_source = st.selectbox(
        "Advanced Criteria source helper",
        ["Manual only", "PostGIS auto-fill"],
        index=0,
        key="advanced_criteria_source_helper",
    )

    if data_source != "PostGIS auto-fill":
        st.info("ขณะนี้ใช้ Manual only: ทุกคะแนนด้านล่างจะมาจากค่าที่ผู้ใช้กรอกเอง")
        return

    st.markdown("**Population Capacity จาก PostGIS**")
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        pop_table = st.text_input("Population table", "urban_os.population_registry", key="pg_pop_table")
        pop_geom = st.text_input("Population geom", "geom", key="pg_pop_geom")
        pop_current_field = st.text_input("Current population field", "registered_population", key="pg_pop_current_field")
    with col_p2:
        pop_capacity_table = st.text_input("Capacity table", "urban_os.household_statistics", key="pg_pop_capacity_table")
        pop_capacity_field = st.text_input("Planned capacity field", "planned_population_capacity", key="pg_pop_capacity_field")
        pop_where = st.text_input("Population filter SQL", "", key="pg_pop_where")

    if st.button("ดึง Population Capacity จาก PostGIS", use_container_width=True, key="pg_pull_population"):
        try:
            pop_summary = summarize_postgis_numeric_by_roi(
                table_name=pop_table,
                geom_col=pop_geom,
                numeric_columns=[pop_current_field],
                where_sql=pop_where,
                roi=roi,
                agg="sum",
            )
            cap_summary = summarize_postgis_numeric_by_roi(
                table_name=pop_capacity_table,
                geom_col=pop_geom,
                numeric_columns=[pop_capacity_field],
                where_sql=pop_where,
                roi=roi,
                agg="sum",
            )
            _safe_set_state("suit_current_population", int(_to_float(pop_summary.get(pop_current_field), 0)))
            _safe_set_state("suit_population_capacity", int(_to_float(cap_summary.get(pop_capacity_field), 0)))
            st.success("ดึง Population Capacity แล้ว ระบบจะใช้ค่าใน widget หลัง rerun")
            st.rerun()
        except Exception as exc:
            st.warning(f"ดึง Population Capacity ไม่สำเร็จ: {exc}")

    st.markdown("**Infrastructure Capacity จาก PostGIS**")
    col_i1, col_i2 = st.columns(2)
    with col_i1:
        infra_table = st.text_input("Infrastructure table", "urban_os.infrastructure_capacity", key="pg_infra_table")
        infra_geom = st.text_input("Infrastructure geom", "geom", key="pg_infra_geom")
        infra_where = st.text_input("Infrastructure filter SQL", "", key="pg_infra_where")
    with col_i2:
        st.caption("field default: water_capacity, wastewater_capacity, electricity_capacity, solid_waste_capacity, drainage_capacity")

    if st.button("ดึง Infrastructure Capacity จาก PostGIS", use_container_width=True, key="pg_pull_infra"):
        try:
            fields = [
                "water_capacity",
                "wastewater_capacity",
                "electricity_capacity",
                "solid_waste_capacity",
                "drainage_capacity",
            ]
            summary = summarize_postgis_numeric_by_roi(
                table_name=infra_table,
                geom_col=infra_geom,
                numeric_columns=fields,
                where_sql=infra_where,
                roi=roi,
                agg="avg",
            )
            mapping = {
                "suit_infra_water": "water_capacity",
                "suit_infra_wastewater": "wastewater_capacity",
                "suit_infra_electricity": "electricity_capacity",
                "suit_infra_solid_waste": "solid_waste_capacity",
                "suit_infra_drainage": "drainage_capacity",
            }
            for widget_key, field in mapping.items():
                _safe_set_state(widget_key, _score_from_capacity_value(summary.get(field)))
            st.success("ดึง Infrastructure Capacity แล้ว")
            st.rerun()
        except Exception as exc:
            st.warning(f"ดึง Infrastructure Capacity ไม่สำเร็จ: {exc}")

    st.markdown("**Service Coverage / Hazard / Equity จาก PostGIS**")
    col_s, col_h, col_e = st.columns(3)

    with col_s:
        service_table = st.text_input("Service table", "urban_os.service_areas", key="pg_service_table")
        service_type_field = st.text_input("Service type field", "facility_type", key="pg_service_type_field")
        service_score_field = st.text_input("Service score field", "coverage_score", key="pg_service_score_field")
        service_geom = st.text_input("Service geom", "geom", key="pg_service_geom")
        if st.button("ดึง Service Coverage", use_container_width=True, key="pg_pull_service"):
            try:
                rows = fetch_postgis_records_by_roi(
                    table_name=service_table,
                    geom_col=service_geom,
                    fields=[service_type_field, service_score_field],
                    roi=roi,
                    limit=1000,
                )
                buckets = {
                    "suit_svc_health": [],
                    "suit_svc_education": [],
                    "suit_svc_park": [],
                    "suit_svc_market": [],
                    "suit_svc_police": [],
                    "suit_svc_fire": [],
                    "suit_svc_transport": [],
                }
                for row in rows:
                    typ = str(row.get(service_type_field, "")).lower()
                    score = _score_from_capacity_value(row.get(service_score_field, 3))
                    if any(k in typ for k in ["health", "hospital", "clinic", "สาธารณสุข", "โรงพยาบาล"]):
                        buckets["suit_svc_health"].append(score)
                    if any(k in typ for k in ["school", "education", "college", "การศึกษา", "โรงเรียน"]):
                        buckets["suit_svc_education"].append(score)
                    if any(k in typ for k in ["park", "recreation", "สวน", "นันทนาการ"]):
                        buckets["suit_svc_park"].append(score)
                    if any(k in typ for k in ["market", "commercial", "retail", "ตลาด", "พาณิชย์"]):
                        buckets["suit_svc_market"].append(score)
                    if any(k in typ for k in ["police", "ตำรวจ"]):
                        buckets["suit_svc_police"].append(score)
                    if any(k in typ for k in ["fire", "emergency", "ดับเพลิง", "ฉุกเฉิน"]):
                        buckets["suit_svc_fire"].append(score)
                    if any(k in typ for k in ["transport", "station", "bus", "rail", "ขนส่ง", "สถานี"]):
                        buckets["suit_svc_transport"].append(score)
                for key, values in buckets.items():
                    if values:
                        _safe_set_state(key, int(round(_avg(values))))
                st.success("ดึง Service Coverage แล้ว")
                st.rerun()
            except Exception as exc:
                st.warning(f"ดึง Service Coverage ไม่สำเร็จ: {exc}")

    with col_h:
        hazard_table = st.text_input("Hazard table", "urban_os.hazard_zones", key="pg_hazard_table")
        hazard_type_field = st.text_input("Hazard type field", "hazard_type", key="pg_hazard_type_field")
        hazard_risk_field = st.text_input("Risk level field", "risk_level", key="pg_hazard_risk_field")
        hazard_geom = st.text_input("Hazard geom", "geom", key="pg_hazard_geom")
        if st.button("ดึง Hazard Risk", use_container_width=True, key="pg_pull_hazard"):
            try:
                rows = fetch_postgis_records_by_roi(
                    table_name=hazard_table,
                    geom_col=hazard_geom,
                    fields=[hazard_type_field, hazard_risk_field],
                    roi=roi,
                    limit=1000,
                )
                buckets = {
                    "suit_hazard_flood": [],
                    "suit_hazard_landslide": [],
                    "suit_hazard_erosion": [],
                    "suit_hazard_wildfire": [],
                    "suit_hazard_earthquake": [],
                    "suit_hazard_stormwater": [],
                }
                for row in rows:
                    typ = str(row.get(hazard_type_field, "")).lower()
                    risk = _score_from_capacity_value(row.get(hazard_risk_field, 3))
                    if any(k in typ for k in ["flood", "น้ำท่วม"]):
                        buckets["suit_hazard_flood"].append(risk)
                    if any(k in typ for k in ["landslide", "ดินถล่ม"]):
                        buckets["suit_hazard_landslide"].append(risk)
                    if any(k in typ for k in ["erosion", "กัดเซาะ", "พังทลาย"]):
                        buckets["suit_hazard_erosion"].append(risk)
                    if any(k in typ for k in ["wildfire", "fire", "ไฟป่า"]):
                        buckets["suit_hazard_wildfire"].append(risk)
                    if any(k in typ for k in ["earthquake", "fault", "แผ่นดินไหว", "รอยเลื่อน"]):
                        buckets["suit_hazard_earthquake"].append(risk)
                    if any(k in typ for k in ["stormwater", "drainage", "น้ำหลาก", "ระบายน้ำ"]):
                        buckets["suit_hazard_stormwater"].append(risk)
                for key, values in buckets.items():
                    if values:
                        _safe_set_state(key, int(round(_avg(values))))
                st.success("ดึง Hazard Risk แล้ว")
                st.rerun()
            except Exception as exc:
                st.warning(f"ดึง Hazard Risk ไม่สำเร็จ: {exc}")

    with col_e:
        equity_table = st.text_input("Socioeconomic table", "urban_os.socioeconomic", key="pg_equity_table")
        equity_score_field = st.text_input("Equity score field", "equity_score", key="pg_equity_score_field")
        equity_geom = st.text_input("Equity geom", "geom", key="pg_equity_geom")
        if st.button("ดึง Equity Score", use_container_width=True, key="pg_pull_equity"):
            try:
                summary = summarize_postgis_numeric_by_roi(
                    table_name=equity_table,
                    geom_col=equity_geom,
                    numeric_columns=[equity_score_field],
                    roi=roi,
                    agg="avg",
                )
                score = _score_from_capacity_value(summary.get(equity_score_field, 3))
                for key in [
                    "suit_equity_access",
                    "suit_equity_benefit",
                    "suit_equity_vulnerable",
                    "suit_equity_land_tenure",
                    "suit_equity_displacement",
                ]:
                    _safe_set_state(key, score)
                st.success("ดึง Equity Score แล้ว")
                st.rerun()
            except Exception as exc:
                st.warning(f"ดึง Equity Score ไม่สำเร็จ: {exc}")


def render_zoning_compliance_controls(*, roi=None, use_zoning_compliance: bool = False) -> dict:
    """
    Render detailed zoning/legal controls.
    Every rule has its own checkbox. Unchecked rules do not affect the zoning score.
    """

    source_type = st.selectbox(
        "Zoning criteria source",
        ["Manual", "PostGIS planning_controls"],
        index=0,
        key="suit_zoning_source_type",
        disabled=not use_zoning_compliance,
    )

    proposed_use = st.text_input(
        "Proposed use / ประเภทการใช้ประโยชน์ที่ต้องการตรวจ",
        value=st.session_state.get("suit_zoning_proposed_use", ""),
        key="suit_zoning_proposed_use",
        disabled=not use_zoning_compliance,
        placeholder="เช่น residential, commercial, industrial หรือที่อยู่อาศัย",
    )

    enabled = {
        "permitted_use": st.checkbox("ตรวจ permitted_use", value=False, key="suit_check_permitted_use", disabled=not use_zoning_compliance),
        "prohibited_use": st.checkbox("ตรวจ prohibited_use", value=False, key="suit_check_prohibited_use", disabled=not use_zoning_compliance),
        "far": st.checkbox("ตรวจ FAR", value=False, key="suit_check_far", disabled=not use_zoning_compliance),
        "bcr": st.checkbox("ตรวจ BCR", value=False, key="suit_check_bcr", disabled=not use_zoning_compliance),
        "osr": st.checkbox("ตรวจ OSR", value=False, key="suit_check_osr", disabled=not use_zoning_compliance),
        "height_limit_m": st.checkbox("ตรวจ height_limit_m", value=False, key="suit_check_height", disabled=not use_zoning_compliance),
        "buffer_rule": st.checkbox("ตรวจ buffer_rule", value=False, key="suit_check_buffer_rule", disabled=not use_zoning_compliance),
    }

    target_col1, target_col2 = st.columns(2)
    with target_col1:
        target_far = st.number_input("FAR ที่เสนอ", min_value=0.0, value=0.0, step=0.1, key="suit_target_far", disabled=not (use_zoning_compliance and enabled["far"]))
        target_bcr = st.number_input("BCR ที่เสนอ", min_value=0.0, value=0.0, step=0.05, key="suit_target_bcr", disabled=not (use_zoning_compliance and enabled["bcr"]))
    with target_col2:
        target_osr = st.number_input("OSR ที่เสนอ", min_value=0.0, value=0.0, step=0.05, key="suit_target_osr", disabled=not (use_zoning_compliance and enabled["osr"]))
        target_height = st.number_input("ความสูงอาคารที่เสนอ (เมตร)", min_value=0.0, value=0.0, step=1.0, key="suit_target_height_m", disabled=not (use_zoning_compliance and enabled["height_limit_m"]))

    scores = {
        "permitted_use": 3.0,
        "prohibited_use": 3.0,
        "far": 3.0,
        "bcr": 3.0,
        "osr": 3.0,
        "height_limit_m": 3.0,
        "buffer_rule": 3.0,
    }

    if source_type == "Manual":
        st.caption("Manual mode: กำหนดคะแนนแต่ละข้อเอง โดยข้อที่ไม่ติ๊กจะไม่ถูกนำไปเฉลี่ย")
        manual_options = {
            "ผ่าน / เหมาะสม": 5.0,
            "มีเงื่อนไข / ต้องทบทวน": 3.0,
            "ไม่ผ่าน / จำกัด": 1.0,
        }
        for rule in enabled:
            if enabled[rule]:
                label = st.selectbox(
                    f"คะแนน {rule}",
                    list(manual_options.keys()),
                    index=1,
                    key=f"suit_manual_score_{rule}",
                    disabled=not use_zoning_compliance,
                )
                scores[rule] = manual_options[label]
    else:
        st.caption("PostGIS mode: ดึงข้อมูลจาก planning_controls ที่ intersect กับ ROI แล้วประเมินคะแนนเฉพาะข้อที่ติ๊ก")
        col_a, col_b = st.columns(2)
        with col_a:
            table_name = st.text_input("planning_controls table", "urban_os.planning_controls", key="pg_zoning_table", disabled=not use_zoning_compliance)
            geom_col = st.text_input("planning_controls geom", "geom", key="pg_zoning_geom", disabled=not use_zoning_compliance)
            where_sql = st.text_input("planning_controls filter SQL", "", key="pg_zoning_where", disabled=not use_zoning_compliance)
        with col_b:
            permitted_field = st.text_input("permitted_use field", "permitted_use", key="pg_zoning_permitted_field", disabled=not use_zoning_compliance)
            prohibited_field = st.text_input("prohibited_use field", "prohibited_use", key="pg_zoning_prohibited_field", disabled=not use_zoning_compliance)
            buffer_field = st.text_input("buffer_rule field", "buffer_rule", key="pg_zoning_buffer_field", disabled=not use_zoning_compliance)

        col_c, col_d = st.columns(2)
        with col_c:
            far_field = st.text_input("far field", "far", key="pg_zoning_far_field", disabled=not use_zoning_compliance)
            bcr_field = st.text_input("bcr field", "bcr", key="pg_zoning_bcr_field", disabled=not use_zoning_compliance)
        with col_d:
            osr_field = st.text_input("osr field", "osr", key="pg_zoning_osr_field", disabled=not use_zoning_compliance)
            height_field = st.text_input("height_limit_m field", "height_limit_m", key="pg_zoning_height_field", disabled=not use_zoning_compliance)

        if st.button("ประเมิน Zoning จาก PostGIS", use_container_width=True, key="pg_evaluate_zoning", disabled=not use_zoning_compliance):
            try:
                fields = list(dict.fromkeys([permitted_field, prohibited_field, far_field, bcr_field, osr_field, height_field, buffer_field]))
                rows = fetch_postgis_records_by_roi(
                    table_name=table_name,
                    geom_col=geom_col,
                    fields=fields,
                    where_sql=where_sql,
                    roi=roi,
                    limit=500,
                )

                if not rows:
                    st.warning("ไม่พบ planning_controls ที่ตัดกับ ROI")
                else:
                    needles = [proposed_use] if proposed_use else []
                    permitted_scores = []
                    prohibited_scores = []
                    far_scores = []
                    bcr_scores = []
                    osr_scores = []
                    height_scores = []
                    buffer_scores = []

                    for row in rows:
                        if needles:
                            permitted_scores.append(5.0 if _contains_any(row.get(permitted_field), needles) else 3.0)
                            prohibited_scores.append(1.0 if _contains_any(row.get(prohibited_field), needles) else 5.0)

                        far_scores.append(_score_limit_lte(target_far, row.get(far_field)))
                        bcr_scores.append(_score_limit_lte(target_bcr, row.get(bcr_field)))
                        osr_scores.append(_score_min_gte(target_osr, row.get(osr_field)))
                        height_scores.append(_score_limit_lte(target_height, row.get(height_field)))
                        buffer_scores.append(_score_buffer_rule(row.get(buffer_field)))

                    if enabled["permitted_use"] and permitted_scores:
                        scores["permitted_use"] = round(_avg(permitted_scores), 2)
                    if enabled["prohibited_use"] and prohibited_scores:
                        scores["prohibited_use"] = round(_avg(prohibited_scores), 2)
                    if enabled["far"] and far_scores:
                        scores["far"] = round(_avg(far_scores), 2)
                    if enabled["bcr"] and bcr_scores:
                        scores["bcr"] = round(_avg(bcr_scores), 2)
                    if enabled["osr"] and osr_scores:
                        scores["osr"] = round(_avg(osr_scores), 2)
                    if enabled["height_limit_m"] and height_scores:
                        scores["height_limit_m"] = round(_avg(height_scores), 2)
                    if enabled["buffer_rule"] and buffer_scores:
                        scores["buffer_rule"] = round(_avg(buffer_scores), 2)

                    st.session_state["suit_zoning_postgis_scores"] = scores
                    st.success(f"ประเมิน zoning จาก PostGIS แล้ว: {len(rows)} records")
                    st.rerun()

            except Exception as exc:
                st.warning(f"ประเมิน Zoning จาก PostGIS ไม่สำเร็จ: {exc}")

        scores = st.session_state.get("suit_zoning_postgis_scores", scores)

    active_scores = [scores[k] for k, v in enabled.items() if v]
    if use_zoning_compliance and active_scores:
        zoning_score = round(_avg(active_scores), 2)
        st.metric("Zoning criteria score", f"{zoning_score:.2f}/5")
    elif use_zoning_compliance:
        zoning_score = 3.0
        st.info("ยังไม่ได้ติ๊ก criteria รายข้อ: zoning score เป็นกลาง 3 และจะมีผลตามน้ำหนักถ้าเปิด master checkbox")
    else:
        zoning_score = 3.0

    if zoning_score >= 4:
        level = "permitted"
    elif zoning_score >= 3:
        level = "conditional"
    elif zoning_score >= 2:
        level = "restricted"
    else:
        level = "prohibited"

    return {
        "enabled": bool(use_zoning_compliance),
        "source_type": source_type,
        "level": level,
        "score_override": zoning_score,
        "criteria_enabled": enabled,
        "criteria_scores": scores,
        "target_values": {
            "proposed_use": proposed_use,
            "far": target_far,
            "bcr": target_bcr,
            "osr": target_osr,
            "height_limit_m": target_height,
        },
        "applied_last": True,
    }



def _geometry_score_config_ui(
    *,
    label: str,
    key_prefix: str,
    default_table: str,
    default_score_field: str,
    default_buffer_m: int = 0,
    default_invert: bool = False,
    enabled_dependency: bool = True,
) -> dict:
    use_geom = st.checkbox(
        f"ใช้ PostGIS Geometry Score Map: {label}",
        value=False,
        key=f"{key_prefix}_geom_enabled",
        disabled=not enabled_dependency,
        help="ถ้าเปิด ระบบจะสร้าง raster score จาก geometry และ score_field โดยตรง แทนค่า manual/auto-fill",
    )

    col1, col2 = st.columns(2)
    with col1:
        table_name = st.text_input(
            f"{label} table",
            default_table,
            key=f"{key_prefix}_geom_table",
            disabled=not (enabled_dependency and use_geom),
        )
        geom_col = st.text_input(
            f"{label} geom",
            "geom",
            key=f"{key_prefix}_geom_col",
            disabled=not (enabled_dependency and use_geom),
        )
        score_field = st.text_input(
            f"{label} score field",
            default_score_field,
            key=f"{key_prefix}_score_field",
            disabled=not (enabled_dependency and use_geom),
        )
    with col2:
        where_sql = st.text_input(
            f"{label} filter SQL",
            "",
            key=f"{key_prefix}_geom_where",
            disabled=not (enabled_dependency and use_geom),
        )
        buffer_m = st.number_input(
            f"{label} buffer for point/line (m)",
            min_value=0,
            max_value=10000,
            value=int(default_buffer_m),
            step=50,
            key=f"{key_prefix}_geom_buffer_m",
            disabled=not (enabled_dependency and use_geom),
        )
        limit = st.number_input(
            f"{label} feature limit",
            min_value=1,
            max_value=50000,
            value=5000,
            step=500,
            key=f"{key_prefix}_geom_limit",
            disabled=not (enabled_dependency and use_geom),
        )

    reducer = st.selectbox(
        f"{label} overlap reducer",
        ["mean", "max", "min", "first"],
        index=0,
        key=f"{key_prefix}_geom_reducer",
        disabled=not (enabled_dependency and use_geom),
    )

    invert_score = False
    if default_invert:
        invert_score = st.checkbox(
            f"{label}: invert score/risk 1-5",
            value=True,
            key=f"{key_prefix}_geom_invert",
            disabled=not (enabled_dependency and use_geom),
        )

    default_score = st.slider(
        f"{label} default score outside geometry",
        1.0,
        5.0,
        3.0,
        0.5,
        key=f"{key_prefix}_geom_default_score",
        disabled=not (enabled_dependency and use_geom),
    )

    return {
        "enabled": bool(enabled_dependency and use_geom),
        "table_name": table_name,
        "geom_col": geom_col,
        "score_field": score_field,
        "where_sql": where_sql,
        "buffer_m": buffer_m,
        "limit": limit,
        "reducer": reducer,
        "invert_score": invert_score,
        "default_score": default_score,
    }


def render_postgis_geometry_score_controls(
    *,
    use_population_capacity: bool,
    use_infrastructure_capacity: bool,
    use_service_coverage: bool,
    use_multi_hazard: bool,
    use_socioeconomic_equity: bool,
    use_zoning_compliance: bool,
) -> dict:
    """
    Step 8.7.4:
    Per-factor PostGIS geometry scoring configs.
    """

    st.markdown("#### 🗺️ Auto Criteria Score from PostGIS Geometry")
    st.caption(
        "สร้าง score map จาก geometry โดยตรง: polygon/line/point ที่มี field คะแนน 1-5 "
        "จะถูกแปลงเป็น raster suitability. ถ้าไม่ติ๊ก factor นั้นจะใช้ manual/auto-fill score"
    )

    configs = {
        "population_capacity": _geometry_score_config_ui(
            label="Population Capacity",
            key_prefix="pg_geom_population",
            default_table="urban_os.population_registry",
            default_score_field="population_capacity_score",
            enabled_dependency=use_population_capacity,
        ),
        "infrastructure_capacity": _geometry_score_config_ui(
            label="Infrastructure Capacity",
            key_prefix="pg_geom_infrastructure",
            default_table="urban_os.infrastructure_capacity",
            default_score_field="capacity_score",
            enabled_dependency=use_infrastructure_capacity,
        ),
        "service_coverage": _geometry_score_config_ui(
            label="Service Coverage",
            key_prefix="pg_geom_service",
            default_table="urban_os.service_areas",
            default_score_field="coverage_score",
            enabled_dependency=use_service_coverage,
        ),
        "multi_hazard": _geometry_score_config_ui(
            label="Multi-Hazard Risk",
            key_prefix="pg_geom_hazard",
            default_table="urban_os.hazard_zones",
            default_score_field="risk_level",
            default_invert=True,
            enabled_dependency=use_multi_hazard,
        ),
        "socioeconomic_equity": _geometry_score_config_ui(
            label="Socioeconomic / Equity",
            key_prefix="pg_geom_equity",
            default_table="urban_os.socioeconomic",
            default_score_field="equity_score",
            enabled_dependency=use_socioeconomic_equity,
        ),
        "zoning_compliance": _geometry_score_config_ui(
            label="Zoning / Legal Compliance",
            key_prefix="pg_geom_zoning",
            default_table="urban_os.planning_controls",
            default_score_field="zoning_score",
            enabled_dependency=use_zoning_compliance,
        ),
    }

    active = [k for k, v in configs.items() if v.get("enabled")]
    if active:
        st.success("เปิด Geometry Score Map: " + ", ".join(active))
    else:
        st.info("ยังไม่ได้เปิด Geometry Score Map: ทุกปัจจัยยังใช้ manual/auto-fill score")

    return configs

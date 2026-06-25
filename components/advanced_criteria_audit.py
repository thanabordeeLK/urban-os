from __future__ import annotations

import csv
import io
import json
from datetime import datetime
from typing import Any

import streamlit as st


FACTOR_LABELS = {
    "population_capacity": "Population Capacity",
    "infrastructure_capacity": "Infrastructure Capacity",
    "service_coverage": "Service Coverage",
    "multi_hazard": "Multi-Hazard Safety",
    "socioeconomic_equity": "Socioeconomic / Equity",
    "zoning_compliance": "Zoning / Legal Compliance",
}

SCORE_KEYS = {
    "population_capacity": "population_score",
    "infrastructure_capacity": "infrastructure_score",
    "service_coverage": "service_coverage_score",
    "multi_hazard": "multi_hazard_safety_score",
    "socioeconomic_equity": "socioeconomic_equity_score",
    "zoning_compliance": "zoning_score",
}


def _safe_get(d: dict | None, *keys, default=None):
    value = d or {}
    for key in keys:
        if not isinstance(value, dict):
            return default
        value = value.get(key)
    return default if value is None else value


def _status_for_factor(
    *,
    factor_key: str,
    factor_config: dict,
    normalized_weight: float,
    metadata: dict,
) -> tuple[str, str]:
    geometry_meta = _safe_get(metadata, "geometry_scoring", factor_key, default={}) or {}
    enabled = bool(factor_config.get("enabled", False))

    if not enabled or normalized_weight <= 0:
        return "No effect", "Not enabled or normalized weight is 0"

    if bool(geometry_meta.get("enabled", False)):
        if bool(geometry_meta.get("used_geometry", False)):
            if factor_key == "multi_hazard" and geometry_meta.get("invert_score"):
                return "OK - PostGIS Geometry Score (Inverted)", "Geometry score is active; hazard risk was inverted to suitability"
            return "OK - PostGIS Geometry Score", "Geometry score is active"

        error = str(geometry_meta.get("error") or "")
        feature_count = int(geometry_meta.get("feature_count", 0) or 0)

        if feature_count <= 0:
            return "Fallback Score 3", "Geometry scoring was enabled but no features intersected the ROI"
        if error:
            return "Error / Fallback", error
        return "Fallback Score 3", "Geometry scoring was enabled but did not create a score image"

    # Geometry disabled, factor may still be manual or auto-fill.
    return "Manual / Auto-fill", "Uses current widget values or PostGIS auto-fill values"


def build_advanced_criteria_audit_rows(
    *,
    suitability_config: dict | None = None,
    metadata: dict | None = None,
    normalized_weights: dict | None = None,
) -> list[dict]:
    suitability_config = suitability_config or {}
    metadata = metadata or {}
    normalized_weights = normalized_weights or {}

    advanced_config = suitability_config.get("advanced_config", {}) or {}

    rows = []
    for factor_key, label in FACTOR_LABELS.items():
        factor_config = advanced_config.get(factor_key, {}) or {}
        geometry_meta = _safe_get(metadata, "geometry_scoring", factor_key, default={}) or {}
        normalized_weight = float(normalized_weights.get(factor_key, 0) or 0)
        score_value = metadata.get(SCORE_KEYS.get(factor_key, ""), None)

        status, note = _status_for_factor(
            factor_key=factor_key,
            factor_config=factor_config,
            normalized_weight=normalized_weight,
            metadata=metadata,
        )

        source_type = "Not enabled"
        if bool(factor_config.get("enabled", False)):
            if bool(geometry_meta.get("enabled", False)):
                source_type = "PostGIS Geometry"
            else:
                source_type = "Manual / Auto-fill"

        row = {
            "factor": label,
            "factor_key": factor_key,
            "enabled": bool(factor_config.get("enabled", False)),
            "source": source_type,
            "status": status,
            "score": score_value,
            "normalized_weight": round(normalized_weight, 4),
            "table_name": geometry_meta.get("table_name", ""),
            "score_field": geometry_meta.get("score_field", ""),
            "feature_count": geometry_meta.get("feature_count", ""),
            "used_geometry": bool(geometry_meta.get("used_geometry", False)),
            "fallback_or_error": geometry_meta.get("error", ""),
            "note": note,
        }

        if factor_key == "zoning_compliance":
            criteria_enabled = metadata.get("zoning_criteria_enabled", {}) or {}
            criteria_scores = metadata.get("zoning_criteria_scores", {}) or {}
            row["zoning_checked_rules"] = ", ".join(
                [key for key, value in criteria_enabled.items() if value]
            )
            row["zoning_rule_scores"] = json.dumps(criteria_scores, ensure_ascii=False)
            row["zoning_source_type"] = metadata.get("zoning_source_type", "")

        rows.append(row)

    return rows


def _rows_to_csv_bytes(rows: list[dict]) -> bytes:
    if not rows:
        return b""

    fieldnames = sorted({key for row in rows for key in row.keys()})
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buf.getvalue().encode("utf-8-sig")


def _build_methodology_markdown(rows: list[dict], metadata: dict, normalized_weights: dict) -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        "# Advanced Criteria Score Audit",
        "",
        f"Generated: {timestamp}",
        "",
        "## Summary",
        "",
        "This audit explains whether each advanced planning criterion used manual values, PostGIS auto-fill values, PostGIS geometry scoring, or fallback values.",
        "",
        "## Normalized Weights",
        "",
    ]

    for key, value in (normalized_weights or {}).items():
        lines.append(f"- **{key}**: {value}")

    lines.extend(["", "## Factor Audit", ""])

    for row in rows:
        lines.extend([
            f"### {row.get('factor')}",
            f"- Enabled: `{row.get('enabled')}`",
            f"- Source: `{row.get('source')}`",
            f"- Status: `{row.get('status')}`",
            f"- Score: `{row.get('score')}`",
            f"- Normalized weight: `{row.get('normalized_weight')}`",
            f"- Table: `{row.get('table_name')}`",
            f"- Score field: `{row.get('score_field')}`",
            f"- Feature count: `{row.get('feature_count')}`",
            f"- Note: {row.get('note')}",
            "",
        ])

        if row.get("factor_key") == "zoning_compliance":
            lines.extend([
                "- Zoning checked rules: `" + str(row.get("zoning_checked_rules", "")) + "`",
                "- Zoning source type: `" + str(row.get("zoning_source_type", "")) + "`",
                "",
            ])

    lines.extend([
        "## Interpretation",
        "",
        "- `OK - PostGIS Geometry Score` means the factor produced a spatial score image from PostGIS geometry.",
        "- `Manual / Auto-fill` means the factor used current widget values or values pulled into widgets from PostGIS.",
        "- `Fallback Score 3` means geometry scoring was enabled but no usable geometry was found, so the model used a neutral score.",
        "- `No effect` means the factor is not enabled or its normalized weight is zero.",
        "- Zoning / Legal Compliance remains intentionally optional and last in the criteria chain.",
    ])

    return "\n".join(lines)


def render_advanced_criteria_score_audit(
    *,
    suitability_config: dict | None = None,
) -> None:
    """
    Render Step 8.7.5 audit panel.
    """

    metadata = st.session_state.get("suitability_advanced_metadata", {}) or {}
    normalized_weights = st.session_state.get("suitability_weights_normalized", {}) or {}

    with st.expander("🧪 Advanced Criteria Score Audit & Validation", expanded=False):
        if not metadata:
            st.info(
                "ยังไม่มี Advanced Criteria metadata ให้ตรวจสอบ กด Run Suitability Analysis ก่อน "
                "หรือเปิด Advanced Planning Criteria แล้วรันโมเดลอีกครั้ง"
            )
            return

        rows = build_advanced_criteria_audit_rows(
            suitability_config=suitability_config,
            metadata=metadata,
            normalized_weights=normalized_weights,
        )

        ok_count = sum(1 for row in rows if str(row.get("status", "")).startswith("OK"))
        fallback_count = sum(1 for row in rows if "Fallback" in str(row.get("status", "")))
        manual_count = sum(1 for row in rows if row.get("status") == "Manual / Auto-fill")
        no_effect_count = sum(1 for row in rows if row.get("status") == "No effect")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Geometry OK", ok_count)
        c2.metric("Manual / Auto-fill", manual_count)
        c3.metric("Fallback / Error", fallback_count)
        c4.metric("No effect", no_effect_count)

        try:
            import pandas as pd

            df = pd.DataFrame(rows)
            st.dataframe(
                df[
                    [
                        "factor",
                        "source",
                        "status",
                        "score",
                        "normalized_weight",
                        "table_name",
                        "score_field",
                        "feature_count",
                        "note",
                    ]
                ],
                use_container_width=True,
            )
        except Exception:
            st.json(rows)

        zoning_rows = [row for row in rows if row.get("factor_key") == "zoning_compliance"]
        if zoning_rows:
            zoning = zoning_rows[0]
            st.markdown("#### ⚖️ Zoning / Legal Compliance Audit")
            st.caption(
                "Zoning ยังเป็นปัจจัยท้ายสุดและจะไม่มีผลถ้ายังไม่เปิด master checkbox หรือ normalized weight เป็น 0"
            )
            st.write(
                {
                    "source": zoning.get("source"),
                    "status": zoning.get("status"),
                    "checked_rules": zoning.get("zoning_checked_rules", ""),
                    "score": zoning.get("score"),
                    "normalized_weight": zoning.get("normalized_weight"),
                }
            )

        json_payload = {
            "metadata": metadata,
            "normalized_weights": normalized_weights,
            "rows": rows,
            "generated_at": datetime.now().isoformat(),
        }
        csv_bytes = _rows_to_csv_bytes(rows)
        md_text = _build_methodology_markdown(rows, metadata, normalized_weights)

        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.download_button(
                "Download Score Audit JSON",
                data=json.dumps(json_payload, ensure_ascii=False, indent=2).encode("utf-8"),
                file_name="advanced_criteria_score_audit.json",
                mime="application/json",
                use_container_width=True,
            )
        with col_b:
            st.download_button(
                "Download Score Audit CSV",
                data=csv_bytes,
                file_name="advanced_criteria_score_audit.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with col_c:
            st.download_button(
                "Download Methodology Markdown",
                data=md_text.encode("utf-8"),
                file_name="advanced_criteria_methodology.md",
                mime="text/markdown",
                use_container_width=True,
            )

        st.session_state["advanced_criteria_audit_rows"] = rows
        st.session_state["advanced_criteria_audit_json"] = json_payload

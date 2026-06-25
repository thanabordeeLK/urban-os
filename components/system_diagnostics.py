from __future__ import annotations

import json
import platform
import sys
from datetime import datetime
from typing import Any

import pandas as pd
import streamlit as st


SENSITIVE_KEYWORDS = [
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "authorization",
    "credential",
    "private",
    "client_secret",
]


SUITABILITY_KEYS = [
    "suitability_run_active",
    "suitability_final_class",
    "suitability_raw_score",
    "suitability_weights_normalized",
    "suitability_stats_df",
    "suitability_summary",
    "suitability_config_signature",
    "suitability_heat_risk",
    "suitability_heat_score",
    "suitability_heat_lst",
    "suitability_heat_image_count",
        "suitability_advanced_metadata",
        "advanced_criteria_source_helper",
]

UHI_KEYS = [
    "uhi_run_active",
    "uhi_lst_image",
    "uhi_heat_risk_image",
    "uhi_image_count",
    "uhi_settings",
    "uhi_lst_summary",
    "uhi_heat_area_df",
    "uhi_heat_summary",
    "uhi_config_signature",
]

CANDIDATE_KEYS = [
    "candidate_export_geojson_bytes",
    "candidate_export_csv_bytes",
    "candidate_export_df",
    "candidate_export_count",
    "candidate_export_settings",
]

FEASIBILITY_KEYS = [
    "feasibility_report_md",
    "feasibility_evidence_json",
    "feasibility_candidate_priority_df",
    "feasibility_generated_at",
]

MULTI_AGENT_KEYS = [
    "multi_agent_run_active",
    "multi_agent_results",
    "multi_agent_report",
    "multi_agent_settings",
    "multi_agent_evidence",
]

SPATIAL_DB_KEYS = [
    "spatial_db_registry",
    "spatial_db_preview_geojson",
    "spatial_db_tables_df",
    "spatial_db_preview_table_name",
    "spatial_db_preview_geom_col",
    "spatial_db_preview_where_sql",
    "spatial_db_preview_limit",
]

MAP_KEYS = [
    "urban_os_map_refresh_token",
    "map_center",
    "map_zoom",
    "last_map_center",
    "last_map_zoom",
    "last_clicked",
    "last_object_clicked",
    "last_active_drawing",
    "all_drawings",
]


def _is_sensitive_key(key: str) -> bool:
    key_lower = str(key).lower()
    return any(word in key_lower for word in SENSITIVE_KEYWORDS)


def _safe_value(value: Any) -> Any:
    """
    Convert objects in session_state into JSON-safe preview values.
    Never serialize Earth Engine objects or large binary payloads directly.
    """

    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        if isinstance(value, str) and len(value) > 500:
            return value[:500] + "...[truncated]"
        return value

    if isinstance(value, bytes):
        return f"<bytes: {len(value):,} bytes>"

    if isinstance(value, pd.DataFrame):
        return {
            "type": "DataFrame",
            "rows": int(len(value)),
            "columns": list(value.columns),
        }

    if isinstance(value, dict):
        safe_dict = {}
        for k, v in list(value.items())[:50]:
            if _is_sensitive_key(str(k)):
                safe_dict[k] = "***REDACTED***"
            else:
                safe_dict[k] = _safe_value(v)
        if len(value) > 50:
            safe_dict["__truncated__"] = f"{len(value) - 50} more keys"
        return safe_dict

    if isinstance(value, (list, tuple, set)):
        items = list(value)
        return [_safe_value(v) for v in items[:50]] + (
            [f"...{len(items) - 50} more items"] if len(items) > 50 else []
        )

    return f"<{type(value).__name__}>"


def _session_key_exists(key: str) -> bool:
    return key in st.session_state and st.session_state.get(key) is not None


def _status_icon(value: bool) -> str:
    return "✅" if value else "⚠️"


def _render_status_table(rows: list[dict]) -> None:
    df = pd.DataFrame(rows)
    if df.empty:
        st.info("ยังไม่มีสถานะให้แสดง")
        return
    st.dataframe(df, use_container_width=True, hide_index=True)


def _has_secret_section(section: str) -> bool:
    try:
        return section in st.secrets
    except Exception:
        return False


def _sanitize_session_state() -> dict:
    output = {}
    for key, value in st.session_state.items():
        if _is_sensitive_key(key):
            output[key] = "***REDACTED***"
        else:
            output[key] = _safe_value(value)
    return output


def _clear_keys(keys: list[str]) -> None:
    for key in keys:
        st.session_state.pop(key, None)


def render_system_diagnostics_panel(
    *,
    roi,
    selected_province: str,
    selected_district: str,
    is_whole_country: bool,
) -> None:
    st.markdown("## 🧪 System Stability & Diagnostic Center")
    st.caption(
        "ตรวจสุขภาพ Urban OS, ดูสถานะ runtime, source config, cache และปุ่มล้างสถานะเมื่อแผนที่หรือผลวิเคราะห์ค้าง"
    )

    area_name = "Thailand" if is_whole_country else f"{selected_district}, {selected_province}"
    st.info(f"พื้นที่ทำงานปัจจุบัน: {area_name}")

    tab_overview, tab_runtime, tab_sources, tab_cache, tab_config = st.tabs(
        [
            "Overview",
            "Runtime",
            "Data Sources",
            "Cache / Reset",
            "Config JSON",
        ]
    )

    with tab_overview:
        st.markdown("### ✅ System Health Overview")

        rows = [
            {
                "หมวด": "ROI",
                "สถานะ": _status_icon(roi is not None),
                "รายละเอียด": "โหลดพื้นที่วิเคราะห์แล้ว" if roi is not None else "ยังไม่พบ ROI",
            },
            {
                "หมวด": "Map",
                "สถานะ": _status_icon(True),
                "รายละเอียด": f"map_refresh_token = {st.session_state.get('urban_os_map_refresh_token', 0)}",
            },
            {
                "หมวด": "Suitability",
                "สถานะ": _status_icon(_session_key_exists("suitability_final_class")),
                "รายละเอียด": "มีผล Urban Suitability Class" if _session_key_exists("suitability_final_class") else "ยังไม่มีผล Suitability",
            },
            {
                "หมวด": "UHI",
                "สถานะ": _status_icon(_session_key_exists("uhi_heat_risk_image") or _session_key_exists("suitability_heat_risk")),
                "รายละเอียด": "มี Heat Risk layer" if (_session_key_exists("uhi_heat_risk_image") or _session_key_exists("suitability_heat_risk")) else "ยังไม่มี Heat Risk layer",
            },
            {
                "หมวด": "Candidate Export",
                "สถานะ": _status_icon(_session_key_exists("candidate_export_df")),
                "รายละเอียด": f"candidate_count = {st.session_state.get('candidate_export_count', 0)}",
            },
            {
                "หมวด": "Spatial Database",
                "สถานะ": _status_icon(bool(st.session_state.get("spatial_db_registry")) or _has_secret_section("postgis")),
                "รายละเอียด": (
                    f"registry = {len(st.session_state.get('spatial_db_registry', []))} layer(s), "
                    f"postgis_secret = {_has_secret_section('postgis')}"
                ),
            },
            {
                "หมวด": "OpenAI / Agent",
                "สถานะ": _status_icon(_has_secret_section("openai") or "OPENAI_API_KEY" in st.secrets if hasattr(st, "secrets") else False),
                "รายละเอียด": "ใช้เฉพาะตอนเปิด GPT Planning Agent",
            },
        ]

        _render_status_table(rows)

        if st.button("🔄 Force Map Refresh", use_container_width=True):
            st.session_state["urban_os_map_refresh_token"] = int(
                st.session_state.get("urban_os_map_refresh_token", 0)
            ) + 1
            st.success("เพิ่ม map_refresh_token แล้ว กด rerun/เปลี่ยนโหมดหรือกด Run ใหม่เพื่อโหลดแผนที่")
            st.rerun()

    with tab_runtime:
        st.markdown("### 🖥️ Runtime Status")

        col1, col2, col3 = st.columns(3)
        col1.metric("Python", sys.version.split()[0])
        col2.metric("Platform", platform.system())
        col3.metric("Session keys", len(st.session_state.keys()))

        rows = [
            {
                "รายการ": "Current datetime",
                "ค่า": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            },
            {
                "รายการ": "Province",
                "ค่า": selected_province,
            },
            {
                "รายการ": "District",
                "ค่า": selected_district,
            },
            {
                "รายการ": "Whole country",
                "ค่า": str(is_whole_country),
            },
            {
                "รายการ": "Map refresh token",
                "ค่า": str(st.session_state.get("urban_os_map_refresh_token", 0)),
            },
            {
                "รายการ": "Suitability signature exists",
                "ค่า": str("suitability_config_signature" in st.session_state),
            },
            {
                "รายการ": "UHI signature exists",
                "ค่า": str("uhi_config_signature" in st.session_state),
            },
        ]
        _render_status_table(rows)

        st.markdown("### 🌎 Earth Engine quick test")
        st.caption("กดเท่านั้นเมื่ออยากทดสอบ GEE เพราะมีการเรียก getInfo() เล็กน้อย")

        if st.button("Test Earth Engine", use_container_width=True):
            try:
                import ee

                value = ee.Number(1).getInfo()
                st.success(f"Earth Engine OK: {value}")
            except Exception as exc:
                st.error(f"Earth Engine test failed: {exc}")

        st.markdown("### 🗄️ PostGIS quick test")
        if st.button("Test PostGIS from Diagnostics", use_container_width=True):
            try:
                from services.spatial_db_service import test_postgis_connection

                info = test_postgis_connection()
                st.success("PostGIS OK")
                st.json(_safe_value(info))
            except Exception as exc:
                st.error(f"PostGIS test failed: {exc}")

    with tab_sources:
        st.markdown("### 🧭 Active Data Source Status")

        suitability_weights = st.session_state.get("suitability_weights_normalized", {}) or {}

        rows = []
        for key, label in [
            ("slope", "Slope"),
            ("flood", "Flood Risk"),
            ("landcover", "Land Cover"),
            ("urban", "Urbanization"),
            ("road", "Road Accessibility"),
            ("facility", "Public Facility"),
            ("heat", "Urban Heat Risk"),
            ("water", "Water Proximity"),
        ]:
            rows.append(
                {
                    "Factor": label,
                    "Normalized weight": suitability_weights.get(key, "-"),
                    "Session status": "active" if key in suitability_weights else "-",
                }
            )

        _render_status_table(rows)

        st.markdown("### 🗂️ Registries")

        registry_rows = [
            {
                "Registry": "Spatial DB Registry",
                "Count": len(st.session_state.get("spatial_db_registry", []) or []),
            },
            {
                "Registry": "Local/GEE Registry",
                "Count": len(st.session_state.get("local_data_registry", []) or []),
            },
        ]
        _render_status_table(registry_rows)

        spatial_registry = st.session_state.get("spatial_db_registry", []) or []
        if spatial_registry:
            st.markdown("#### Spatial DB Registry")
            st.dataframe(spatial_registry, use_container_width=True, hide_index=True)

        local_registry = st.session_state.get("local_data_registry", []) or []
        if local_registry:
            st.markdown("#### Local / GEE Registry")
            st.dataframe(local_registry, use_container_width=True, hide_index=True)

    with tab_cache:
        st.markdown("### 🧹 Cache / Reset Actions")
        st.warning("ปุ่มในหน้านี้ใช้ล้างสถานะ runtime เฉพาะใน session ปัจจุบัน ไม่ได้ลบไฟล์หรือฐานข้อมูลจริง")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Reset Map Cache", use_container_width=True):
                st.session_state["urban_os_map_refresh_token"] = int(
                    st.session_state.get("urban_os_map_refresh_token", 0)
                ) + 1
                for key in MAP_KEYS:
                    if key != "urban_os_map_refresh_token":
                        st.session_state.pop(key, None)
                st.success("Reset map cache แล้ว")
                st.rerun()

            if st.button("Clear Suitability Cache", use_container_width=True):
                _clear_keys(SUITABILITY_KEYS)
                st.session_state["urban_os_map_refresh_token"] = int(
                    st.session_state.get("urban_os_map_refresh_token", 0)
                ) + 1
                st.success("Clear Suitability cache แล้ว")
                st.rerun()

            if st.button("Clear UHI Cache", use_container_width=True):
                _clear_keys(UHI_KEYS)
                st.session_state["urban_os_map_refresh_token"] = int(
                    st.session_state.get("urban_os_map_refresh_token", 0)
                ) + 1
                st.success("Clear UHI cache แล้ว")
                st.rerun()

        with col2:
            if st.button("Clear Candidate Export", use_container_width=True):
                _clear_keys(CANDIDATE_KEYS)
                st.success("Clear Candidate Export แล้ว")
                st.rerun()

            if st.button("Clear Feasibility Bridge", use_container_width=True):
                _clear_keys(FEASIBILITY_KEYS)
                st.success("Clear Feasibility Bridge แล้ว")
                st.rerun()

            if st.button("Clear Multi-Agent Cache", use_container_width=True):
                _clear_keys(MULTI_AGENT_KEYS)
                st.success("Clear Multi-Agent cache แล้ว")
                st.rerun()

        st.markdown("### 🧨 Emergency reset")
        if st.button("Clear All Analysis Runtime Cache", use_container_width=True):
            _clear_keys(
                SUITABILITY_KEYS
                + UHI_KEYS
                + CANDIDATE_KEYS
                + FEASIBILITY_KEYS
                + MULTI_AGENT_KEYS
            )
            st.session_state["urban_os_map_refresh_token"] = int(
                st.session_state.get("urban_os_map_refresh_token", 0)
            ) + 1
            st.success("ล้าง analysis runtime cache ทั้งหมดแล้ว")
            st.rerun()

    with tab_config:
        st.markdown("### 🧾 Current Config JSON")
        st.caption("ข้อมูลนี้ถูก sanitize แล้ว ไม่แสดง secret/password/token")

        snapshot = {
            "generated_at": datetime.now().isoformat(),
            "area": {
                "province": selected_province,
                "district": selected_district,
                "is_whole_country": is_whole_country,
            },
            "session_state": _sanitize_session_state(),
        }

        st.download_button(
            "Download Diagnostics JSON",
            data=json.dumps(snapshot, ensure_ascii=False, indent=2, default=str).encode("utf-8"),
            file_name="urban_os_diagnostics_snapshot.json",
            mime="application/json",
            use_container_width=True,
        )

        with st.expander("Show sanitized session_state", expanded=False):
            st.json(snapshot)

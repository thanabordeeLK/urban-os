from __future__ import annotations

import json
from typing import Any

import folium
import streamlit as st

try:
    from services.spatial_db_service import fetch_postgis_geojson, get_roi_bbox_4326
except Exception:
    fetch_postgis_geojson = None
    get_roi_bbox_4326 = None


SESSION_GEOJSON_KEY = "import_wizard_last_geojson"
POSTGIS_RESULT_KEY = "import_wizard_last_postgis_import"


SOURCE_SESSION_LAST = "Session: Last Imported Layer"
SOURCE_POSTGIS_LAST = "PostGIS: Last Imported Table"
SOURCE_POSTGIS_CUSTOM = "PostGIS: Custom Table"


def _features(geojson: dict) -> list[dict]:
    return (geojson or {}).get("features", []) or []


def _geometry_type_summary(geojson: dict) -> str:
    counts: dict[str, int] = {}
    for feat in _features(geojson):
        geom_type = ((feat.get("geometry") or {}).get("type")) or "Unknown"
        counts[geom_type] = counts.get(geom_type, 0) + 1
    return ", ".join(f"{key}: {value}" for key, value in counts.items()) if counts else "-"


def _property_keys(geojson: dict, limit: int = 200) -> list[str]:
    keys: list[str] = []
    for feat in _features(geojson)[:limit]:
        for key in (feat.get("properties") or {}).keys():
            if key not in keys:
                keys.append(key)
    return keys


def _safe_table_name_from_last_result() -> str:
    result = st.session_state.get(POSTGIS_RESULT_KEY) or {}
    return str(result.get("full_table_name") or result.get("table_name") or "")


def _safe_geom_col_from_last_result() -> str:
    result = st.session_state.get(POSTGIS_RESULT_KEY) or {}
    return str(result.get("geom_col") or "geom")


def _get_overlay_geojson(roi=None) -> tuple[dict | None, dict]:
    """
    Resolve overlay source into GeoJSON + metadata.
    """

    source = st.session_state.get("import_overlay_source", SOURCE_SESSION_LAST)

    if source == SOURCE_SESSION_LAST:
        geojson = st.session_state.get(SESSION_GEOJSON_KEY)
        return geojson, {
            "source": source,
            "feature_count": len(_features(geojson or {})),
            "geometry": _geometry_type_summary(geojson or {}),
            "table_name": "",
        }

    if source in {SOURCE_POSTGIS_LAST, SOURCE_POSTGIS_CUSTOM}:
        if fetch_postgis_geojson is None:
            raise RuntimeError("PostGIS fetch service ยังไม่พร้อมใช้งาน")

        if source == SOURCE_POSTGIS_LAST:
            table_name = _safe_table_name_from_last_result()
            geom_col = _safe_geom_col_from_last_result()
        else:
            table_name = str(st.session_state.get("import_overlay_custom_table", "") or "").strip()
            geom_col = str(st.session_state.get("import_overlay_custom_geom_col", "geom") or "geom").strip()

        if not table_name:
            raise ValueError("ยังไม่มี PostGIS table สำหรับ overlay")

        where_sql = str(st.session_state.get("import_overlay_where_sql", "") or "").strip()
        limit = int(st.session_state.get("import_overlay_limit", 5000) or 5000)
        clip_to_roi = bool(st.session_state.get("import_overlay_clip_to_roi", True))

        bbox = None
        if clip_to_roi and get_roi_bbox_4326 is not None:
            bbox = get_roi_bbox_4326(roi)

        geojson = fetch_postgis_geojson(
            table_name=table_name,
            geom_col=geom_col,
            where_sql=where_sql,
            bbox_4326=bbox,
            limit=limit,
        )
        return geojson, {
            "source": source,
            "feature_count": len(_features(geojson or {})),
            "geometry": _geometry_type_summary(geojson or {}),
            "table_name": table_name,
            "geom_col": geom_col,
            "clip_to_roi": clip_to_roi,
            "limit": limit,
        }

    return None, {"source": source, "feature_count": 0, "geometry": "-"}


def _build_tooltip(geojson: dict):
    raw = str(st.session_state.get("import_overlay_tooltip_fields", "") or "").strip()
    if not raw:
        return None

    requested = [item.strip() for item in raw.replace("\n", ",").split(",") if item.strip()]
    if not requested:
        return None

    existing = set(_property_keys(geojson))
    fields = [field for field in requested if field in existing]
    if not fields:
        return None

    try:
        return folium.GeoJsonTooltip(fields=fields, aliases=fields, localize=True)
    except Exception:
        return None


def add_imported_layer_overlays(Map, roi=None):
    """
    Add imported GIS layer overlay to the Folium map when enabled.
    """

    if Map is None:
        return Map

    if not st.session_state.get("import_overlay_enabled", False):
        return Map

    try:
        geojson, meta = _get_overlay_geojson(roi=roi)
    except Exception as exc:
        st.session_state["import_overlay_last_error"] = str(exc)
        return Map

    if not geojson or not _features(geojson):
        st.session_state["import_overlay_last_error"] = "ไม่พบ feature สำหรับ overlay"
        st.session_state["import_overlay_last_meta"] = meta
        return Map

    color = st.session_state.get("import_overlay_color", "#00F2FE")
    fill_color = st.session_state.get("import_overlay_fill_color", color)
    weight = int(st.session_state.get("import_overlay_weight", 3) or 3)
    opacity = float(st.session_state.get("import_overlay_opacity", 0.85) or 0.85)
    fill_opacity = float(st.session_state.get("import_overlay_fill_opacity", 0.25) or 0.25)
    layer_name = st.session_state.get("import_overlay_layer_name", "Imported Layer Overlay")

    tooltip = _build_tooltip(geojson)

    try:
        folium.GeoJson(
            geojson,
            name=layer_name,
            style_function=lambda feature: {
                "color": color,
                "weight": weight,
                "opacity": opacity,
                "fillColor": fill_color,
                "fillOpacity": fill_opacity,
            },
            tooltip=tooltip,
            show=True,
        ).add_to(Map)

        st.session_state["import_overlay_last_error"] = ""
        st.session_state["import_overlay_last_meta"] = meta
    except Exception as exc:
        st.session_state["import_overlay_last_error"] = str(exc)

    return Map


def render_imported_layer_overlay_panel(roi=None) -> None:
    """
    UI controls for imported layer overlay.
    """

    st.markdown("#### 🧩 Imported Layer Overlay")
    st.caption(
        "เปิดชั้นข้อมูลที่ import แล้วให้แสดงทับบน Map Workspace เพื่อเทียบกับ Suitability, UHI, Zoning หรือแผนที่อื่น"
    )

    session_geojson = st.session_state.get(SESSION_GEOJSON_KEY)
    last_pg_result = st.session_state.get(POSTGIS_RESULT_KEY) or {}

    c1, c2 = st.columns([1.0, 1.2])
    with c1:
        enabled = st.checkbox(
            "Enable imported layer overlay",
            value=bool(st.session_state.get("import_overlay_enabled", False)),
            key="import_overlay_enabled",
        )

        source_options = [SOURCE_SESSION_LAST, SOURCE_POSTGIS_LAST, SOURCE_POSTGIS_CUSTOM]
        default_source = st.session_state.get("import_overlay_source", SOURCE_SESSION_LAST)
        if default_source not in source_options:
            default_source = SOURCE_SESSION_LAST

        source = st.selectbox(
            "Overlay source",
            source_options,
            index=source_options.index(default_source),
            key="import_overlay_source",
        )

        st.text_input(
            "Layer name on map",
            value=st.session_state.get("import_overlay_layer_name", "Imported Layer Overlay"),
            key="import_overlay_layer_name",
        )

    with c2:
        if source == SOURCE_SESSION_LAST:
            if session_geojson:
                st.success(
                    f"Session layer พร้อมใช้งาน: {len(_features(session_geojson)):,} features / {_geometry_type_summary(session_geojson)}"
                )
                keys = _property_keys(session_geojson)
                if keys:
                    st.caption("Available fields: " + ", ".join(keys[:12]) + (" ..." if len(keys) > 12 else ""))
            else:
                st.warning("ยังไม่มี Last Imported Layer ใน session ให้ upload ไฟล์ก่อน")

        elif source == SOURCE_POSTGIS_LAST:
            if last_pg_result:
                st.success(f"Last PostGIS table: {last_pg_result.get('full_table_name')}")
                st.caption(f"geom: {last_pg_result.get('geom_col', 'geom')}")
            else:
                st.warning("ยังไม่มีผล Import to PostGIS ล่าสุด ให้ import เข้า PostGIS ก่อน")

        else:
            st.text_input(
                "Custom PostGIS table",
                value=st.session_state.get("import_overlay_custom_table", ""),
                placeholder="public.roads_imported",
                key="import_overlay_custom_table",
            )
            st.text_input(
                "Custom geometry column",
                value=st.session_state.get("import_overlay_custom_geom_col", "geom"),
                key="import_overlay_custom_geom_col",
            )

    st.markdown("##### Style")
    s1, s2, s3 = st.columns(3)
    with s1:
        st.color_picker(
            "Line color",
            value=st.session_state.get("import_overlay_color", "#00F2FE"),
            key="import_overlay_color",
        )
        st.slider(
            "Line weight",
            min_value=1,
            max_value=10,
            value=int(st.session_state.get("import_overlay_weight", 3) or 3),
            key="import_overlay_weight",
        )
    with s2:
        st.color_picker(
            "Fill color",
            value=st.session_state.get("import_overlay_fill_color", "#00F2FE"),
            key="import_overlay_fill_color",
        )
        st.slider(
            "Line opacity",
            min_value=0.05,
            max_value=1.0,
            value=float(st.session_state.get("import_overlay_opacity", 0.85) or 0.85),
            step=0.05,
            key="import_overlay_opacity",
        )
    with s3:
        st.slider(
            "Fill opacity",
            min_value=0.0,
            max_value=1.0,
            value=float(st.session_state.get("import_overlay_fill_opacity", 0.25) or 0.25),
            step=0.05,
            key="import_overlay_fill_opacity",
        )
        st.text_input(
            "Tooltip fields, comma separated",
            value=st.session_state.get("import_overlay_tooltip_fields", ""),
            placeholder="name,type,score",
            key="import_overlay_tooltip_fields",
        )

    if source in {SOURCE_POSTGIS_LAST, SOURCE_POSTGIS_CUSTOM}:
        st.markdown("##### PostGIS filter")
        p1, p2 = st.columns(2)
        with p1:
            st.checkbox(
                "Clip to current ROI bbox",
                value=bool(st.session_state.get("import_overlay_clip_to_roi", True)),
                key="import_overlay_clip_to_roi",
            )
            st.number_input(
                "Fetch limit",
                min_value=1,
                max_value=50000,
                value=int(st.session_state.get("import_overlay_limit", 5000) or 5000),
                step=500,
                key="import_overlay_limit",
            )
        with p2:
            st.text_area(
                "Optional safe WHERE filter",
                value=st.session_state.get("import_overlay_where_sql", ""),
                placeholder="category = 'road'",
                height=80,
                key="import_overlay_where_sql",
            )

    st.info(
        "หลังเปิด overlay ให้ดูผลบนแผนที่อ้างอิงด้านล่าง หรือกลับไปหน้าอื่น เช่น Suitability Analysis / Urban Heat Island "
        "ชั้นข้อมูล overlay จะถูกวางทับบน Map Workspace ตามค่า session ปัจจุบัน"
    )

    meta = st.session_state.get("import_overlay_last_meta")
    err = st.session_state.get("import_overlay_last_error", "")

    if enabled:
        if err:
            st.warning(f"Overlay status: {err}")
        if meta:
            st.caption("Last overlay metadata")
            st.json(meta)

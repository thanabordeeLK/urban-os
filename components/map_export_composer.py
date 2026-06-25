from __future__ import annotations

import io
import json
import re
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st


WGS84_PRJ = """GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]]"""


def _safe_filename(value: str, default: str = "urban_os_export") -> str:
    value = str(value or default).strip()
    value = re.sub(r"[^0-9A-Za-zก-๙_\-]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or default


def _sanitize_field_name(name: str, existing: set[str]) -> str:
    """
    Shapefile DBF field names should be <= 10 chars.
    """

    base = re.sub(r"[^0-9A-Za-z_]+", "_", str(name or "field")).strip("_")
    if not base:
        base = "field"
    base = base[:10]

    candidate = base
    i = 1
    while candidate.lower() in existing:
        suffix = str(i)
        candidate = f"{base[:10-len(suffix)]}{suffix}"
        i += 1

    existing.add(candidate.lower())
    return candidate


def _infer_dbf_type(values: list[Any]) -> tuple[str, int, int]:
    """
    Returns pyshp field type, size, decimal.
    """

    clean = [v for v in values if v is not None]
    if not clean:
        return "C", 254, 0

    if all(isinstance(v, bool) for v in clean):
        return "L", 1, 0

    if all(isinstance(v, int) and not isinstance(v, bool) for v in clean):
        return "N", 18, 0

    if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in clean):
        return "F", 18, 6

    return "C", 254, 0


def _flatten_props(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return json.dumps(value, ensure_ascii=False)


def _iter_polygon_parts(geometry: dict) -> list[list[list[float]]]:
    """
    Convert GeoJSON Polygon / MultiPolygon into pyshp parts.
    pyshp expects parts as rings.
    """

    if not geometry:
        return []

    geom_type = geometry.get("type")
    coords = geometry.get("coordinates") or []

    parts: list[list[list[float]]] = []

    if geom_type == "Polygon":
        for ring in coords:
            if ring:
                parts.append(ring)

    elif geom_type == "MultiPolygon":
        for polygon in coords:
            for ring in polygon:
                if ring:
                    parts.append(ring)

    return parts


def _geojson_feature_collection_from_roi(roi) -> dict:
    """
    Convert current ROI to a GeoJSON FeatureCollection.
    """

    if roi is None:
        return {"type": "FeatureCollection", "features": []}

    try:
        geom = roi.geometry().getInfo() if hasattr(roi, "geometry") else roi.getInfo()
    except Exception:
        geom = None

    if not geom:
        return {"type": "FeatureCollection", "features": []}

    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": geom,
                "properties": {
                    "source": "roi_boundary",
                    "created_by": "Urban OS",
                },
            }
        ],
    }


def _load_candidate_geojson_from_session() -> dict | None:
    data = st.session_state.get("candidate_export_geojson_bytes")
    if not data:
        return None
    try:
        if isinstance(data, bytes):
            return json.loads(data.decode("utf-8"))
        if isinstance(data, str):
            return json.loads(data)
    except Exception:
        return None
    return None


def _geojson_to_bytes(geojson: dict) -> bytes:
    return json.dumps(geojson or {"type": "FeatureCollection", "features": []}, ensure_ascii=False, indent=2).encode("utf-8")


def _geojson_to_shapefile_zip_bytes(
    geojson: dict,
    *,
    layer_name: str = "urban_os_layer",
) -> tuple[bytes | None, str | None]:
    """
    Convert Polygon/MultiPolygon GeoJSON FeatureCollection to zipped Shapefile.

    Requires pyshp (`pip install pyshp`).
    """

    try:
        import shapefile  # pyshp
    except Exception as exc:
        return None, f"ไม่พบ library pyshp/shapefile: {exc}"

    features = (geojson or {}).get("features", []) or []
    polygon_features = []
    for feat in features:
        geom = feat.get("geometry") or {}
        if geom.get("type") in {"Polygon", "MultiPolygon"}:
            polygon_features.append(feat)

    if not polygon_features:
        return None, "ไม่มี Polygon/MultiPolygon สำหรับสร้าง Shapefile"

    # Collect fields
    prop_keys = []
    for feat in polygon_features:
        for key in (feat.get("properties") or {}).keys():
            if key not in prop_keys:
                prop_keys.append(key)

    if not prop_keys:
        prop_keys = ["name"]

    field_name_map = {}
    used_names: set[str] = set()
    for key in prop_keys:
        field_name_map[key] = _sanitize_field_name(key, used_names)

    safe_layer = _safe_filename(layer_name)

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        shp_base = tmp / safe_layer

        writer = shapefile.Writer(str(shp_base), shapeType=shapefile.POLYGON)
        writer.autoBalance = 1

        for key in prop_keys:
            values = [_flatten_props((feat.get("properties") or {}).get(key)) for feat in polygon_features]
            f_type, size, decimal = _infer_dbf_type(values)
            writer.field(field_name_map[key], f_type, size=size, decimal=decimal)

        for feat in polygon_features:
            geom = feat.get("geometry") or {}
            parts = _iter_polygon_parts(geom)
            if not parts:
                continue

            writer.poly(parts)

            props = feat.get("properties") or {}
            row = []
            for key in prop_keys:
                value = _flatten_props(props.get(key))
                if value is None:
                    value = ""
                row.append(value)
            writer.record(*row)

        writer.close()

        (tmp / f"{safe_layer}.prj").write_text(WGS84_PRJ, encoding="utf-8")
        (tmp / f"{safe_layer}.cpg").write_text("UTF-8", encoding="utf-8")
        (tmp / f"{safe_layer}_field_mapping.json").write_text(
            json.dumps(field_name_map, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as z:
            for file in tmp.iterdir():
                z.write(file, file.name)

        return zip_buf.getvalue(), None


def _render_html_export(Map, base_name: str) -> None:
    try:
        html = Map.get_root().render()
        st.download_button(
            "⬇️ Export Current Interactive Map HTML",
            data=html.encode("utf-8"),
            file_name=f"{base_name}_interactive_map.html",
            mime="text/html",
            use_container_width=True,
        )
    except Exception as exc:
        st.warning(f"ไม่สามารถสร้าง HTML map ได้: {exc}")


def _workspace_summary_markdown(
    *,
    selected_province: str,
    selected_district: str,
    is_whole_country: bool,
) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pane_label = st.session_state.get("map_pane_count_label", "1 หน้าจอ")
    height = st.session_state.get("map_panel_height", "")

    lines = [
        "# Urban OS Map Workspace Export Summary",
        "",
        f"Generated: {now}",
        "",
        "## Area",
        f"- Province: `{selected_province}`",
        f"- District: `{selected_district}`",
        f"- Whole country: `{is_whole_country}`",
        "",
        "## Layout",
        f"- Map Views: `{pane_label}`",
        f"- Map height: `{height}`",
        "",
        "## Map View Settings",
    ]

    for idx in [1, 2, 3]:
        lines.extend(
            [
                f"### Map View {idx}",
                f"- Layer / analysis: `{st.session_state.get(f'map_view_{idx}_layer_choice', '')}`",
                f"- Basemap: `{st.session_state.get(f'map_view_{idx}_basemap', '')}`",
                f"- Scale: `{st.session_state.get(f'map_view_{idx}_scale_label', '')}`",
                f"- Apply scale to zoom: `{st.session_state.get(f'map_view_{idx}_apply_scale', '')}`",
                "",
            ]
        )

    lines.extend(
        [
            "## Notes",
            "- Web-map scale is approximate and depends on browser, DPI and export size.",
            "- For official cartographic production, verify scale again in QGIS/ArcGIS layout.",
        ]
    )

    return "\n".join(lines)


def render_map_export_composer(
    *,
    Map,
    roi=None,
    selected_province: str = "",
    selected_district: str = "",
    is_whole_country: bool = False,
) -> None:
    """
    Step 8.7.6: Map Export Composer + GIS Export
    """

    with st.expander("🖨️ Map Export Composer / GIS Export", expanded=False):
        st.caption(
            "ส่งออกแผนที่และข้อมูล GIS สำหรับนำไปใช้ต่อใน QGIS, ArcGIS, GeoLibre, GeoServer หรือรายงาน"
        )

        base_name = _safe_filename(
            f"urban_os_{selected_province or 'thailand'}_{selected_district or 'area'}"
        )

        tab_map, tab_gis, tab_report = st.tabs(
            ["🗺️ Map Export", "🧩 GIS Export", "📝 Layout Summary"]
        )

        with tab_map:
            st.markdown("#### Interactive HTML Map")
            st.caption("ส่งออกแผนที่แบบ interactive HTML จาก current map layer stack")
            _render_html_export(Map, base_name)

        with tab_gis:
            st.markdown("#### Shapefile / GeoJSON Export")

            source = st.selectbox(
                "เลือกชุดข้อมูล GIS ที่ต้องการ export",
                [
                    "ROI Boundary",
                    "Candidate Areas จาก Candidate Export",
                ],
                key="gis_export_source",
            )

            if source == "ROI Boundary":
                geojson = _geojson_feature_collection_from_roi(roi)
                export_name = f"{base_name}_roi_boundary"
            else:
                geojson = _load_candidate_geojson_from_session()
                export_name = f"{base_name}_candidate_areas"

            if not geojson:
                st.warning(
                    "ยังไม่มี Candidate Areas GeoJSON ใน session ให้ไปที่ Candidate Area Export แล้วกด Generate Candidate GeoJSON ก่อน"
                )
            else:
                feature_count = len((geojson or {}).get("features", []) or [])
                st.metric("Feature count", feature_count)

                col1, col2 = st.columns(2)
                with col1:
                    st.download_button(
                        "⬇️ Download GeoJSON",
                        data=_geojson_to_bytes(geojson),
                        file_name=f"{export_name}.geojson",
                        mime="application/geo+json",
                        use_container_width=True,
                    )

                with col2:
                    shp_zip, error = _geojson_to_shapefile_zip_bytes(
                        geojson,
                        layer_name=export_name,
                    )
                    if shp_zip:
                        st.download_button(
                            "⬇️ Download Shapefile ZIP",
                            data=shp_zip,
                            file_name=f"{export_name}_shapefile.zip",
                            mime="application/zip",
                            use_container_width=True,
                        )
                    else:
                        st.warning(error or "ไม่สามารถสร้าง Shapefile ได้")

                st.info(
                    "หมายเหตุ: Shapefile รองรับ field name ไม่เกิน 10 ตัวอักษร จึงมีไฟล์ field_mapping.json แนบใน zip"
                )

        with tab_report:
            st.markdown("#### Map Workspace Summary")
            md = _workspace_summary_markdown(
                selected_province=selected_province,
                selected_district=selected_district,
                is_whole_country=is_whole_country,
            )
            st.download_button(
                "⬇️ Download Map Layout Summary Markdown",
                data=md.encode("utf-8"),
                file_name=f"{base_name}_map_workspace_summary.md",
                mime="text/markdown",
                use_container_width=True,
            )
            st.code(md, language="markdown")

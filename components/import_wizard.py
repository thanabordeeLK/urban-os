from __future__ import annotations

import io
import json
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from components.imported_layer_overlay import render_imported_layer_overlay_panel

try:
    from services.spatial_db_service import import_geojson_to_postgis, test_postgis_connection
except Exception:
    import_geojson_to_postgis = None
    test_postgis_connection = None

try:
    from components.map_export_composer import _geojson_to_shapefile_zip_bytes
except Exception:
    _geojson_to_shapefile_zip_bytes = None


IMPORT_REGISTRY_KEY = "import_wizard_registry"
LAST_IMPORT_KEY = "import_wizard_last_geojson"

CATEGORY_OPTIONS = {
    "roads": "🛣️ Roads / Transport",
    "public_facilities": "🏥 Public Facilities / POI",
    "protected_forest": "🌲 Protected / Forest",
    "zoning": "🧩 Zoning / Land Use",
    "hazard": "⚠️ Hazard / Risk Area",
    "candidate_area": "🟢 Candidate Area",
    "parcels": "📐 Parcels / Land Plots",
    "buildings": "🏢 Buildings",
    "water": "💧 Water / Waterways",
    "custom": "🧪 Custom Overlay",
}


def _now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _safe_filename(name: str, default: str = "urban_os_import") -> str:
    import re

    name = str(name or default).strip()
    name = re.sub(r"[^0-9A-Za-zก-๙_\\-]+", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return name or default


def _geojson_bytes(geojson: dict) -> bytes:
    return json.dumps(
        geojson or {"type": "FeatureCollection", "features": []},
        ensure_ascii=False,
        indent=2,
    ).encode("utf-8")


def _features(geojson: dict) -> list[dict]:
    return (geojson or {}).get("features", []) or []


def _flatten_props(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return json.dumps(value, ensure_ascii=False)


def _geometry_type_summary(geojson: dict) -> str:
    counts = {}
    for feat in _features(geojson):
        gtype = ((feat.get("geometry") or {}).get("type")) or "Unknown"
        counts[gtype] = counts.get(gtype, 0) + 1
    return ", ".join(f"{k}: {v}" for k, v in counts.items()) if counts else "-"


def _properties_dataframe(geojson: dict, max_rows: int = 500) -> pd.DataFrame:
    rows = []
    for idx, feat in enumerate(_features(geojson)[:max_rows], start=1):
        props = {k: _flatten_props(v) for k, v in (feat.get("properties") or {}).items()}
        props["_feature_id"] = idx
        props["_geometry_type"] = (feat.get("geometry") or {}).get("type", "")
        rows.append(props)
    return pd.DataFrame(rows)


def _bbox_from_geojson(geojson: dict):
    xs, ys = [], []

    def collect(coords):
        if coords is None:
            return
        if isinstance(coords, (list, tuple)) and coords and isinstance(coords[0], (int, float)):
            if len(coords) >= 2:
                xs.append(float(coords[0]))
                ys.append(float(coords[1]))
            return
        if isinstance(coords, (list, tuple)):
            for item in coords:
                collect(item)

    for feat in _features(geojson):
        collect((feat.get("geometry") or {}).get("coordinates"))

    if not xs or not ys:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def _preview_geojson_map(geojson: dict, height: int = 460) -> None:
    bbox = _bbox_from_geojson(geojson)
    if bbox:
        minx, miny, maxx, maxy = bbox
        center = [(miny + maxy) / 2, (minx + maxx) / 2]
    else:
        center = [15.87, 100.99]

    m = folium.Map(location=center, zoom_start=11, tiles="OpenStreetMap")

    try:
        folium.GeoJson(
            geojson,
            name="Imported Layer",
            style_function=lambda feature: {
                "color": "#00F2FE",
                "weight": 3,
                "fillColor": "#00F2FE",
                "fillOpacity": 0.22,
            },
        ).add_to(m)
        if bbox:
            m.fit_bounds([[miny, minx], [maxy, maxx]])
    except Exception as exc:
        st.warning(f"ไม่สามารถ preview geometry ได้: {exc}")

    st_folium(m, height=height, use_container_width=True)


def _read_geojson(uploaded_file) -> dict:
    obj = json.loads(uploaded_file.getvalue().decode("utf-8-sig"))
    if obj.get("type") == "FeatureCollection":
        return obj
    if obj.get("type") == "Feature":
        return {"type": "FeatureCollection", "features": [obj]}
    if obj.get("type") in {"Point", "LineString", "Polygon", "MultiPoint", "MultiLineString", "MultiPolygon"}:
        return {"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": obj, "properties": {}}]}
    raise ValueError("ไม่ใช่ GeoJSON ที่รองรับ")


def _read_shapefile_zip(uploaded_file, encoding: str = "utf-8") -> dict:
    try:
        import shapefile
    except Exception as exc:
        raise RuntimeError(f"ไม่พบ pyshp/shapefile: {exc}")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        with zipfile.ZipFile(io.BytesIO(uploaded_file.getvalue())) as z:
            z.extractall(tmp)

        shp_files = list(tmp.rglob("*.shp"))
        if not shp_files:
            raise ValueError("ไม่พบไฟล์ .shp ใน ZIP")

        reader = shapefile.Reader(str(shp_files[0]), encoding=encoding)
        fields = [field[0] for field in reader.fields[1:]]
        features = []

        for sr in reader.iterShapeRecords():
            props = {key: _flatten_props(value) for key, value in zip(fields, sr.record)}
            features.append({"type": "Feature", "geometry": sr.shape.__geo_interface__, "properties": props})

        return {"type": "FeatureCollection", "features": features}


def _parse_kml_coordinates(text: str) -> list[list[float]]:
    coords = []
    for part in (text or "").strip().split():
        values = part.split(",")
        if len(values) >= 2:
            try:
                coords.append([float(values[0]), float(values[1])])
            except Exception:
                pass
    return coords


def _read_kml_or_kmz(uploaded_file) -> dict:
    name = uploaded_file.name.lower()
    raw = uploaded_file.getvalue()

    if name.endswith(".kmz"):
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            kml_names = [n for n in z.namelist() if n.lower().endswith(".kml")]
            if not kml_names:
                raise ValueError("ไม่พบไฟล์ .kml ใน KMZ")
            kml_text = z.read(kml_names[0]).decode("utf-8-sig", errors="ignore")
    else:
        kml_text = raw.decode("utf-8-sig", errors="ignore")

    root = ET.fromstring(kml_text)
    ns = {"kml": "http://www.opengis.net/kml/2.2"}

    def find_text(node, paths):
        for path in paths:
            found = node.find(path, ns)
            if found is not None and found.text:
                return found.text
        return ""

    features = []
    for pm in root.findall(".//kml:Placemark", ns):
        props = {"name": find_text(pm, ["kml:name"]), "description": find_text(pm, ["kml:description"])}
        point_text = find_text(pm, [".//kml:Point/kml:coordinates"])
        line_text = find_text(pm, [".//kml:LineString/kml:coordinates"])
        poly_text = find_text(pm, [".//kml:Polygon//kml:outerBoundaryIs//kml:LinearRing/kml:coordinates"])

        geom = None
        if point_text:
            coords = _parse_kml_coordinates(point_text)
            if coords:
                geom = {"type": "Point", "coordinates": coords[0]}
        elif line_text:
            coords = _parse_kml_coordinates(line_text)
            if coords:
                geom = {"type": "LineString", "coordinates": coords}
        elif poly_text:
            coords = _parse_kml_coordinates(poly_text)
            if coords:
                if coords[0] != coords[-1]:
                    coords.append(coords[0])
                geom = {"type": "Polygon", "coordinates": [coords]}

        if geom:
            features.append({"type": "Feature", "geometry": geom, "properties": props})

    return {"type": "FeatureCollection", "features": features}


def _read_csv_preview(uploaded_file) -> pd.DataFrame:
    raw = uploaded_file.getvalue()
    try:
        return pd.read_csv(io.BytesIO(raw))
    except Exception:
        return pd.read_csv(io.BytesIO(raw), encoding="tis-620")


def _csv_to_geojson(df: pd.DataFrame, lon_col: str, lat_col: str) -> dict:
    features = []
    for _, row in df.iterrows():
        try:
            lon = float(row[lon_col])
            lat = float(row[lat_col])
        except Exception:
            continue

        props = {}
        for col in df.columns:
            value = row[col]
            if pd.isna(value):
                value = None
            props[col] = _flatten_props(value)

        features.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]}, "properties": props})
    return {"type": "FeatureCollection", "features": features}


def _guess_lon_lat_columns(columns: list[str]):
    lower = {str(c).lower(): c for c in columns}
    lon_candidates = ["lon", "lng", "longitude", "x", "xcoord", "x_coord", "easting"]
    lat_candidates = ["lat", "latitude", "y", "ycoord", "y_coord", "northing"]
    lon_col = next((lower[k] for k in lon_candidates if k in lower), None)
    lat_col = next((lower[k] for k in lat_candidates if k in lower), None)
    return lon_col, lat_col


def _register_imported_layer(layer_info: dict) -> None:
    registry = st.session_state.get(IMPORT_REGISTRY_KEY, []) or []
    registry.append(layer_info)
    st.session_state[IMPORT_REGISTRY_KEY] = registry


def _registry_df() -> pd.DataFrame:
    return pd.DataFrame(st.session_state.get(IMPORT_REGISTRY_KEY, []) or [])


def _registry_json_bytes() -> bytes:
    return json.dumps(
        {"exported_from": "Urban OS Import Wizard", "exported_at": _now_text(), "items": st.session_state.get(IMPORT_REGISTRY_KEY, []) or []},
        ensure_ascii=False,
        indent=2,
    ).encode("utf-8")


def _render_geojson_downloads(geojson: dict, export_name: str) -> None:
    col1, col2 = st.columns(2)
    with col1:
        st.download_button("⬇️ Download GeoJSON", data=_geojson_bytes(geojson), file_name=f"{export_name}.geojson", mime="application/geo+json", use_container_width=True)
    with col2:
        if _geojson_to_shapefile_zip_bytes:
            shp_zip, error = _geojson_to_shapefile_zip_bytes(geojson, layer_name=export_name)
            if shp_zip:
                st.download_button("⬇️ Download Shapefile ZIP", data=shp_zip, file_name=f"{export_name}_shapefile.zip", mime="application/zip", use_container_width=True)
            else:
                st.warning(error or "ไม่สามารถสร้าง Shapefile ได้")


def _ogr2ogr_command(file_name: str, table_name: str) -> str:
    table_name = _safe_filename(table_name or "imported_layer")
    return "\\n".join([
        '# ตัวอย่างคำสั่งนำเข้า PostGIS ด้วย ogr2ogr',
        'ogr2ogr -f "PostgreSQL" \\\\',
        '  PG:"host=<HOST> port=5432 dbname=<DB> user=<USER> password=<PASSWORD>" \\\\',
        f'  "{file_name}" \\\\',
        f'  -nln public.{table_name} \\\\',
        '  -lco GEOMETRY_NAME=geom \\\\',
        '  -lco FID=id \\\\',
        '  -nlt PROMOTE_TO_MULTI \\\\',
        '  -t_srs EPSG:4326 \\\\',
        '  -overwrite',
    ])




def _render_direct_postgis_import() -> None:
    st.markdown("#### Direct Import to PostGIS / Supabase PostGIS")
    st.caption("นำ Last Imported Layer เข้า PostGIS โดยตรงจากข้อมูลที่ preview แล้ว")

    geojson = st.session_state.get(LAST_IMPORT_KEY)
    if not geojson:
        st.warning("ยังไม่มี Last Imported Layer ให้กลับไป Upload & Preview ก่อน")
        return

    if import_geojson_to_postgis is None:
        st.error("ไม่พบ service import_geojson_to_postgis ตรวจสอบ services/spatial_db_service.py")
        return

    with st.container():
        c0, c1, c2 = st.columns([1, 1, 1])
        with c0:
            if st.button("Test PostGIS Connection", key="import_pg_test_connection", use_container_width=True):
                try:
                    info = test_postgis_connection() if test_postgis_connection else {}
                    st.success("เชื่อมต่อ PostGIS สำเร็จ")
                    st.json(info)
                except Exception as exc:
                    st.error(f"เชื่อมต่อ PostGIS ไม่สำเร็จ: {exc}")

        feature_count = len(_features(geojson))
        c1.metric("Ready features", f"{feature_count:,}")
        c2.metric("Geometry", _geometry_type_summary(geojson))

    default_layer = st.session_state.get("import_wizard_last_layer_name", "imported_layer")
    default_category = st.session_state.get("import_wizard_last_category", "custom")

    col1, col2, col3 = st.columns(3)
    with col1:
        schema_name = st.text_input("Schema", value="public", key="direct_pg_schema")
        table_name = st.text_input(
            "Target table",
            value=_safe_filename(default_layer),
            key="direct_pg_table",
        )
    with col2:
        geom_col = st.text_input("Geometry column", value="geom", key="direct_pg_geom_col")
        mode = st.selectbox("Import mode", ["append", "overwrite"], index=0, key="direct_pg_mode")
    with col3:
        create_attrs = st.checkbox("Create attribute columns", value=True, key="direct_pg_create_attrs")
        create_index = st.checkbox("Create spatial index", value=True, key="direct_pg_create_index")

    max_features = st.number_input(
        "Max features to import",
        min_value=1,
        max_value=200000,
        value=min(max(feature_count, 1), 50000),
        step=100,
        key="direct_pg_max_features",
    )

    st.warning(
        "โหมด overwrite จะ DROP TABLE เดิมก่อนสร้างใหม่ ควรใช้เมื่อแน่ใจแล้วเท่านั้น"
    )

    confirm = st.checkbox(
        "ยืนยันว่าต้องการนำเข้า PostGIS",
        value=False,
        key="direct_pg_confirm",
    )

    if st.button("🐘 Import Last Layer to PostGIS", key="direct_pg_import_button", use_container_width=True):
        if not confirm:
            st.error("กรุณาติ๊กยืนยันก่อน import")
            return

        try:
            with st.spinner("กำลัง import เข้า PostGIS..."):
                result = import_geojson_to_postgis(
                    geojson=geojson,
                    schema_name=schema_name,
                    table_name=table_name,
                    geom_col=geom_col,
                    layer_name=default_layer,
                    category=default_category,
                    source_file=st.session_state.get("import_wizard_last_source_file", ""),
                    mode=mode,
                    create_attribute_columns=create_attrs,
                    create_spatial_index=create_index,
                    max_features=int(max_features),
                )

            st.session_state["import_wizard_last_postgis_import"] = result
            st.success(
                f"Import สำเร็จ: {result.get('inserted', 0):,} features → {result.get('full_table_name')}"
            )
            st.json(result)

        except Exception as exc:
            st.error(f"Import เข้า PostGIS ไม่สำเร็จ: {exc}")

    last_result = st.session_state.get("import_wizard_last_postgis_import")
    if last_result:
        st.markdown("#### Last PostGIS Import Result")
        st.json(last_result)


def render_import_wizard(*, roi=None, selected_province: str = "", selected_district: str = "", is_whole_country: bool = False) -> None:
    st.markdown("### 📥 Import Wizard")
    st.caption("นำเข้าข้อมูล GIS จาก Shapefile ZIP, GeoJSON, KML/KMZ หรือ CSV พิกัด X,Y เพื่อ preview, จัดหมวดหมู่, export ต่อ และเตรียมส่งเข้า PostGIS")

    area_name = "ทั้งประเทศไทย" if is_whole_country else f"{selected_district}, {selected_province}"
    st.info(f"พื้นที่ทำงานปัจจุบัน: {area_name}")

    tab_upload, tab_registry, tab_overlay, tab_postgis = st.tabs(["📤 Upload & Preview", "📋 Imported Registry", "🧩 Overlay", "🐘 PostGIS Import Guide"])

    with tab_upload:
        uploaded = st.file_uploader(
            "Upload GIS file",
            type=["zip", "geojson", "json", "kml", "kmz", "csv"],
            help="Shapefile ต้อง zip เป็นชุดไฟล์ .shp/.shx/.dbf/.prj",
            key="import_wizard_file",
        )

        if uploaded is None:
            st.info("อัปโหลดไฟล์ Shapefile ZIP / GeoJSON / KML / KMZ / CSV เพื่อเริ่มนำเข้า")
        else:
            file_name = uploaded.name
            suffix = Path(file_name).suffix.lower()

            category = st.selectbox("จัดหมวดหมู่ชั้นข้อมูล", list(CATEGORY_OPTIONS.keys()), format_func=lambda key: CATEGORY_OPTIONS.get(key, key), index=list(CATEGORY_OPTIONS.keys()).index("custom"), key="import_wizard_category")
            layer_name = st.text_input("ชื่อชั้นข้อมูล", value=Path(file_name).stem, key="import_wizard_layer_name")

            encoding = "utf-8"
            if suffix == ".zip":
                encoding = st.selectbox("Shapefile DBF encoding", ["utf-8", "cp874", "tis-620", "latin1"], index=0, key="import_shp_encoding")

            geojson = None
            try:
                if suffix in {".geojson", ".json"}:
                    geojson = _read_geojson(uploaded)
                elif suffix == ".zip":
                    geojson = _read_shapefile_zip(uploaded, encoding=encoding)
                elif suffix in {".kml", ".kmz"}:
                    geojson = _read_kml_or_kmz(uploaded)
                elif suffix == ".csv":
                    df_csv = _read_csv_preview(uploaded)
                    st.markdown("#### CSV Column Mapping")
                    st.dataframe(df_csv.head(30), use_container_width=True)
                    columns = list(df_csv.columns)
                    guess_lon, guess_lat = _guess_lon_lat_columns(columns)
                    c1, c2 = st.columns(2)
                    with c1:
                        lon_col = st.selectbox("Longitude / X column", columns, index=columns.index(guess_lon) if guess_lon in columns else 0, key="csv_lon_col")
                    with c2:
                        lat_col = st.selectbox("Latitude / Y column", columns, index=columns.index(guess_lat) if guess_lat in columns else min(1, len(columns) - 1), key="csv_lat_col")
                    geojson = _csv_to_geojson(df_csv, lon_col=lon_col, lat_col=lat_col)
                else:
                    st.error("ชนิดไฟล์ยังไม่รองรับ")
            except Exception as exc:
                st.error(f"อ่านไฟล์ไม่สำเร็จ: {exc}")

            if geojson:
                feature_count = len(_features(geojson))
                geom_summary = _geometry_type_summary(geojson)
                bbox = _bbox_from_geojson(geojson)
                export_name = _safe_filename(f"urban_os_import_{layer_name}")

                st.session_state[LAST_IMPORT_KEY] = geojson
                st.session_state["import_wizard_last_layer_name"] = layer_name
                st.session_state["import_wizard_last_category"] = category
                st.session_state["import_wizard_last_source_file"] = file_name

                st.markdown("#### Import Summary")
                c1, c2, c3 = st.columns(3)
                c1.metric("Features", f"{feature_count:,}")
                c2.metric("Geometry", geom_summary)
                c3.metric("Category", CATEGORY_OPTIONS.get(category, category))

                if bbox:
                    st.caption(f"BBOX EPSG:4326 ≈ {bbox}")

                if feature_count == 0:
                    st.warning("ไม่พบ feature ในไฟล์นี้")
                else:
                    st.markdown("#### Attribute Preview")
                    st.dataframe(_properties_dataframe(geojson), use_container_width=True)
                    st.markdown("#### Geometry Preview")
                    _preview_geojson_map(geojson)
                    st.markdown("#### Export Converted Data")
                    _render_geojson_downloads(geojson, export_name)

                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("➕ Add to Imported Registry", key="add_import_to_registry", use_container_width=True):
                            _register_imported_layer({
                                "id": f"import_{int(datetime.now().timestamp())}",
                                "layer_name": layer_name,
                                "category": category,
                                "category_label": CATEGORY_OPTIONS.get(category, category),
                                "source_file": file_name,
                                "feature_count": feature_count,
                                "geometry_summary": geom_summary,
                                "bbox": bbox,
                                "created_at": _now_text(),
                                "note": "Stored in Streamlit session. Download GeoJSON/Shapefile for permanent use.",
                            })
                            st.success("เพิ่มเข้า Imported Registry แล้ว")
                    with c2:
                        st.download_button(
                            "⬇️ Download Import Metadata JSON",
                            data=json.dumps({"layer_name": layer_name, "category": category, "source_file": file_name, "feature_count": feature_count, "geometry_summary": geom_summary, "bbox": bbox, "created_at": _now_text()}, ensure_ascii=False, indent=2).encode("utf-8"),
                            file_name=f"{export_name}_metadata.json",
                            mime="application/json",
                            use_container_width=True,
                        )

    with tab_registry:
        st.markdown("#### Imported Registry")
        df = _registry_df()
        if df.empty:
            st.info("ยังไม่มี imported layer ใน registry")
        else:
            st.dataframe(df, use_container_width=True)
            c1, c2 = st.columns(2)
            with c1:
                st.download_button("⬇️ Download Imported Registry JSON", data=_registry_json_bytes(), file_name="urban_os_imported_registry.json", mime="application/json", use_container_width=True)
            with c2:
                if st.button("🧹 Clear Imported Registry", use_container_width=True):
                    st.session_state[IMPORT_REGISTRY_KEY] = []
                    st.success("ล้าง Imported Registry แล้ว")

        last_geojson = st.session_state.get(LAST_IMPORT_KEY)
        if last_geojson:
            st.markdown("#### Last Imported Layer")
            st.caption(st.session_state.get("import_wizard_last_layer_name", ""))
            _render_geojson_downloads(last_geojson, _safe_filename(f"urban_os_last_import_{st.session_state.get('import_wizard_last_layer_name','layer')}"))

    with tab_overlay:
        render_imported_layer_overlay_panel(roi=roi)

    with tab_postgis:
        _render_direct_postgis_import()

        st.divider()
        st.markdown("#### PostGIS Import Guide / Fallback")
        table_name = st.text_input("Target table name", value=_safe_filename(st.session_state.get("import_wizard_last_layer_name", "imported_layer")), key="postgis_import_table_name")
        source_path = st.text_input("Source file path for ogr2ogr", value=f"{_safe_filename(st.session_state.get('import_wizard_last_layer_name','imported_layer'))}.geojson", key="postgis_import_source_path")
        command = _ogr2ogr_command(source_path, table_name)
        st.code(command, language="bash")
        st.download_button("⬇️ Download ogr2ogr Import Command", data=command.encode("utf-8"), file_name=f"{_safe_filename(table_name)}_ogr2ogr_import.sh", mime="text/x-shellscript", use_container_width=True)
        st.info("เวอร์ชันนี้ยังไม่เขียนเข้า PostGIS โดยตรง เพื่อความปลอดภัยของ credential. ขั้นถัดไปสามารถทำ Import to PostGIS แบบกดปุ่มได้")

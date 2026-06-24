from __future__ import annotations

import json

import streamlit as st

from components.postgis_schema_generator import render_postgis_schema_generator_panel

from services.spatial_db_service import (
    fetch_postgis_geojson,
    geojson_properties_dataframe,
    get_roi_bbox_4326,
    list_postgis_tables,
    test_postgis_connection,
)


DB_LAYER_CATEGORIES = {
    "roads": "Roads / Transport Network",
    "public_facilities": "Public Facilities / POI",
    "protected_forest": "Protected / Forest Constraint",
    "zoning": "Zoning / Land Use Plan",
    "parcels": "Parcels / Land Plots",
    "buildings": "Buildings / Built-up",
    "water": "Water / Waterways",
    "custom": "Custom / Other",
}


def get_spatial_db_registry() -> list[dict]:
    if "spatial_db_registry" not in st.session_state:
        st.session_state["spatial_db_registry"] = []
    return st.session_state["spatial_db_registry"]


def add_spatial_db_registry_item(item: dict) -> None:
    registry = get_spatial_db_registry()
    # update by layer_name
    layer_name = item.get("layer_name")
    registry = [x for x in registry if x.get("layer_name") != layer_name]
    registry.append(item)
    st.session_state["spatial_db_registry"] = registry


def get_spatial_db_layers_by_category(category: str) -> list[dict]:
    registry = get_spatial_db_registry()
    return [item for item in registry if item.get("category") == category and item.get("enabled", True)]


def render_spatial_database_connector(
    *,
    roi,
    is_whole_country: bool,
    selected_province: str,
    selected_district: str,
) -> None:
    st.markdown("## 🗄️ Spatial Database Bridge")
    st.caption(
        "เชื่อม Urban OS กับฐานข้อมูลพื้นที่ของหน่วยงาน เช่น PostGIS/Supabase PostGIS "
        "เพื่อลดการกรอก GEE Asset ID ทีละชั้นข้อมูล"
    )

    area_name = "Thailand" if is_whole_country else f"{selected_district}, {selected_province}"
    st.info(f"พื้นที่ทำงานปัจจุบัน: {area_name}")

    tab_overview, tab_connect, tab_preview, tab_registry, tab_schema = st.tabs(
        [
            "Overview",
            "PostGIS Connection",
            "Table Preview",
            "DB Layer Registry",
            "Schema Generator",
        ]
    )

    with tab_overview:
        st.markdown(
            """
            ### แนวทางการใช้ฐานข้อมูลกับ Urban OS

            โครงสร้างที่แนะนำ:

            ```text
            GEE = Raster / Remote Sensing / DEM / Flood / LST / Land Cover
            PostGIS = Roads / POI / Zoning / Parcels / Buildings / Local Constraints
            Urban OS = Dashboard + Suitability + Report + AI Planning Agent
            ```

            สำหรับข้อมูลขนาดเล็กถึงระดับอำเภอ/จังหวัด ระบบสามารถดึงจาก PostGIS แล้วแปลงเป็น
            `ee.FeatureCollection` เพื่อใช้คำนวณใน GEE ได้

            สำหรับข้อมูลใหญ่มาก เช่น ถนนทั้งประเทศ อาคารทั้งประเทศ หรือแปลงที่ดินจำนวนมาก
            ควรทำอย่างใดอย่างหนึ่ง:

            - clip ตาม ROI ก่อน
            - ทำ materialized view รายจังหวัด/อำเภอ
            - sync ไปเป็น GEE Asset อัตโนมัติ
            - หรือคำนวณระยะ/overlay ใน PostGIS แทน
            """
        )

        st.warning(
            "ห้ามใส่รหัสผ่านฐานข้อมูลใน GitHub ให้เก็บใน Streamlit Secrets เท่านั้น"
        )

        with st.expander("ตัวอย่าง Streamlit Secrets", expanded=False):
            st.code(
                """
[postgis]
host = "db.example.com"
port = 5432
database = "urban_os"
user = "urban_reader"
password = "your-password"
                """.strip(),
                language="toml",
            )
            st.caption("หรือใช้ url = postgresql+psycopg2://user:password@host:5432/database")

    with tab_connect:
        st.markdown("### 🔌 Test PostGIS Connection")

        if st.button("Test connection", use_container_width=True):
            try:
                info = test_postgis_connection()
                st.success("เชื่อมต่อ PostGIS สำเร็จ")
                st.json(info)
            except Exception as exc:
                st.error(f"เชื่อมต่อไม่สำเร็จ: {exc}")

        st.markdown("### 📚 Spatial Tables")

        if st.button("List spatial tables", use_container_width=True):
            try:
                tables_df = list_postgis_tables(limit=200)
                if tables_df.empty:
                    st.warning("ไม่พบ spatial table ใน geometry_columns")
                else:
                    st.dataframe(tables_df, use_container_width=True, hide_index=True)
                    st.session_state["spatial_db_tables_df"] = tables_df
            except Exception as exc:
                st.error(f"โหลดรายชื่อตารางไม่สำเร็จ: {exc}")

    with tab_preview:
        st.markdown("### 🔎 Preview PostGIS Table by Current ROI")

        bbox = get_roi_bbox_4326(roi)
        if bbox:
            st.caption(f"ROI bbox EPSG:4326: {bbox}")
        else:
            st.warning("ไม่สามารถอ่าน bbox จาก ROI ได้ ระบบจะไม่กรองพื้นที่จาก ROI")

        table_name = st.text_input(
            "Table name",
            value="public.roads",
            key="spatial_db_preview_table_name",
            help="ใช้รูปแบบ table หรือ schema.table เช่น public.roads",
        )
        geom_col = st.text_input(
            "Geometry column",
            value="geom",
            key="spatial_db_preview_geom_col",
        )
        where_sql = st.text_input(
            "Optional filter",
            value="",
            key="spatial_db_preview_where_sql",
            placeholder="เช่น road_class IN ('primary','secondary')",
            help="เว้นว่างได้ ห้ามใส่ ; หรือคำสั่งแก้ไขฐานข้อมูล",
        )
        limit = st.number_input(
            "Feature limit",
            min_value=1,
            max_value=50000,
            value=5000,
            step=500,
            key="spatial_db_preview_limit",
        )

        if st.button("Fetch preview by ROI", use_container_width=True):
            try:
                geojson = fetch_postgis_geojson(
                    table_name=table_name,
                    geom_col=geom_col,
                    where_sql=where_sql,
                    bbox_4326=bbox,
                    limit=int(limit),
                )
                features = geojson.get("features", []) or []
                st.success(f"โหลดข้อมูลสำเร็จ: {len(features):,} features")
                st.session_state["spatial_db_preview_geojson"] = geojson

                df = geojson_properties_dataframe(geojson, max_rows=100)
                if not df.empty:
                    st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                    st.info("ไม่มี property preview หรือไม่พบ feature ใน ROI")

                st.download_button(
                    "Download preview GeoJSON",
                    data=json.dumps(geojson, ensure_ascii=False).encode("utf-8"),
                    file_name="urban_os_postgis_preview.geojson",
                    mime="application/geo+json",
                    use_container_width=True,
                )
            except Exception as exc:
                st.error(f"โหลด preview ไม่สำเร็จ: {exc}")

    with tab_registry:
        st.markdown("### 🧾 Register PostGIS Layer")

        layer_name = st.text_input(
            "Layer name",
            value="roads_from_postgis",
            key="spatial_db_register_layer_name",
        )

        category_label = st.selectbox(
            "Category",
            list(DB_LAYER_CATEGORIES.values()),
            index=0,
            key="spatial_db_register_category_label",
        )
        category = next(
            key for key, value in DB_LAYER_CATEGORIES.items() if value == category_label
        )

        table_name_reg = st.text_input(
            "PostGIS table",
            value=st.session_state.get("spatial_db_preview_table_name", "public.roads"),
            key="spatial_db_register_table_name",
        )
        geom_col_reg = st.text_input(
            "Geometry column",
            value=st.session_state.get("spatial_db_preview_geom_col", "geom"),
            key="spatial_db_register_geom_col",
        )
        where_sql_reg = st.text_input(
            "Filter SQL",
            value=st.session_state.get("spatial_db_preview_where_sql", ""),
            key="spatial_db_register_where_sql",
        )
        limit_reg = st.number_input(
            "Limit",
            min_value=1,
            max_value=50000,
            value=int(st.session_state.get("spatial_db_preview_limit", 5000)),
            step=500,
            key="spatial_db_register_limit",
        )
        enabled = st.checkbox(
            "Enabled",
            value=True,
            key="spatial_db_register_enabled",
        )

        if st.button("Add to Spatial DB Registry", use_container_width=True):
            item = {
                "layer_name": layer_name,
                "category": category,
                "category_label": category_label,
                "source_type": "postgis",
                "table_name": table_name_reg,
                "geom_col": geom_col_reg,
                "where_sql": where_sql_reg,
                "limit": int(limit_reg),
                "enabled": bool(enabled),
            }
            add_spatial_db_registry_item(item)
            st.success(f"เพิ่ม {layer_name} เข้า Spatial DB Registry แล้ว")

        registry = get_spatial_db_registry()
        if registry:
            st.dataframe(registry, use_container_width=True, hide_index=True)
            st.download_button(
                "Download Spatial DB Registry JSON",
                data=json.dumps(registry, ensure_ascii=False, indent=2).encode("utf-8"),
                file_name="urban_os_spatial_db_registry.json",
                mime="application/json",
                use_container_width=True,
            )

            if st.button("Clear Spatial DB Registry", use_container_width=True):
                st.session_state["spatial_db_registry"] = []
                st.rerun()
        else:
            st.info("ยังไม่มีรายการใน Spatial DB Registry")

    with tab_schema:
        render_postgis_schema_generator_panel()


from __future__ import annotations

import streamlit as st

from services.postgis_schema_generator import (
    TABLES,
    build_csv_templates_zip,
    build_data_dictionary_csv,
    build_ogr2ogr_examples,
    build_postgis_schema_sql,
    validate_schema_name,
)


def render_postgis_schema_generator_panel() -> None:
    st.markdown("### 🧱 PostGIS Schema Generator")
    st.caption("สร้าง SQL schema และ template ข้อมูลมาตรฐานสำหรับ Urban OS Spatial Database")

    with st.expander("แนวคิดโครงสร้างฐานข้อมูล", expanded=False):
        st.markdown("- GEE ใช้กับ raster / remote sensing / DEM / Flood / LST / Land Cover")
        st.markdown("- PostGIS ใช้กับข้อมูลท้องถิ่น เช่น ถนน อาคาร POI ผังสี แปลงที่ดิน พื้นที่กันออก")
        st.markdown("- Urban OS เชื่อมข้อมูล วิเคราะห์ suitability และสร้างรายงาน")

    col_a, col_b = st.columns(2)
    with col_a:
        schema_name = st.text_input("Schema name", value="urban_os", key="schema_generator_schema_name")
        srid = st.number_input("SRID", min_value=4326, max_value=999999, value=4326, step=1, key="schema_generator_srid")
    with col_b:
        include_drop = st.checkbox("Include DROP SCHEMA CASCADE", value=False, key="schema_generator_include_drop")
        include_sample_data = st.checkbox("Include sample urban_layers registry", value=True, key="schema_generator_include_sample_data")
        include_views = st.checkbox("Include useful views", value=True, key="schema_generator_include_views")
        include_comments = st.checkbox("Include table/column comments", value=True, key="schema_generator_include_comments")

    try:
        validate_schema_name(schema_name)
        schema_sql = build_postgis_schema_sql(
            schema_name=schema_name,
            srid=int(srid),
            include_drop=include_drop,
            include_sample_data=include_sample_data,
            include_views=include_views,
            include_comments=include_comments,
        )
        ogr_examples = build_ogr2ogr_examples(schema_name=schema_name)
        valid = True
    except Exception as exc:
        st.error(f"Schema setting ไม่ถูกต้อง: {exc}")
        schema_sql = ""
        ogr_examples = ""
        valid = False

    st.markdown("### 📚 ตารางมาตรฐานที่สร้าง")
    table_rows = [
        {"table": table_name, "description": spec.get("description"), "geometry": spec.get("geometry") or "-", "columns": len(spec.get("columns", []))}
        for table_name, spec in TABLES.items()
    ]
    st.dataframe(table_rows, use_container_width=True, hide_index=True)

    st.markdown("### 📤 Downloads")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.download_button("Download schema SQL", data=schema_sql.encode("utf-8"), file_name="urban_os_postgis_schema.sql", mime="text/sql", use_container_width=True, disabled=not valid)
    with col2:
        st.download_button("Download CSV templates ZIP", data=build_csv_templates_zip(), file_name="urban_os_csv_templates.zip", mime="application/zip", use_container_width=True)
    with col3:
        st.download_button("Download data dictionary CSV", data=build_data_dictionary_csv(), file_name="urban_os_data_dictionary.csv", mime="text/csv", use_container_width=True)

    with st.expander("🧾 Show schema SQL", expanded=False):
        st.code(schema_sql, language="sql")

    with st.expander("🚚 Show ogr2ogr import examples", expanded=False):
        st.code(ogr_examples, language="bash")

    st.warning("ควรสร้าง database user แบบ read-only สำหรับ Streamlit และห้าม commit connection string หรือ password ขึ้น GitHub")

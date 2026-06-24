
from __future__ import annotations

import csv
import io
import re
import zipfile
from datetime import datetime

SAFE_SCHEMA_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

TABLES = {
    "urban_layers": {
        "description": "บัญชีรายการชั้นข้อมูลเมือง",
        "geometry": None,
        "columns": [
            ("layer_id", "text", "รหัสชั้นข้อมูล"),
            ("layer_name", "text", "ชื่อชั้นข้อมูล"),
            ("category", "text", "หมวดข้อมูล"),
            ("source_type", "text", "ชนิดแหล่งข้อมูล"),
            ("table_name", "text", "ชื่อตาราง"),
            ("geom_col", "text", "ชื่อ geometry column"),
            ("srid", "integer", "SRID"),
            ("enabled", "boolean", "เปิดใช้งาน"),
            ("description", "text", "คำอธิบาย"),
        ],
    },
    "roads": {
        "description": "โครงข่ายถนนและคมนาคม",
        "geometry": "MULTILINESTRING",
        "columns": [
            ("road_id", "text", "รหัสถนน"),
            ("name", "text", "ชื่อถนน"),
            ("road_class", "text", "ระดับถนน"),
            ("width_m", "numeric", "ความกว้างเมตร"),
            ("surface", "text", "วัสดุผิวทาง"),
            ("lanes", "integer", "จำนวนช่องจราจร"),
            ("source", "text", "แหล่งข้อมูล"),
        ],
    },
    "public_facilities": {
        "description": "บริการสาธารณะและจุดบริการเมือง",
        "geometry": "MULTIPOINT",
        "columns": [
            ("facility_id", "text", "รหัสบริการ"),
            ("name", "text", "ชื่อสถานที่"),
            ("facility_type", "text", "ประเภทบริการ"),
            ("service_level", "text", "ระดับบริการ"),
            ("owner_agency", "text", "หน่วยงานเจ้าของ"),
            ("capacity", "numeric", "ศักยภาพบริการ"),
            ("source", "text", "แหล่งข้อมูล"),
        ],
    },
    "protected_areas": {
        "description": "พื้นที่อนุรักษ์ พื้นที่กันออก และข้อจำกัดการพัฒนา",
        "geometry": "MULTIPOLYGON",
        "columns": [
            ("protected_id", "text", "รหัสพื้นที่"),
            ("name", "text", "ชื่อพื้นที่"),
            ("category", "text", "ประเภทพื้นที่"),
            ("legal_status", "text", "สถานะกฎหมาย"),
            ("buffer_m", "numeric", "ระยะกันชนเมตร"),
            ("restriction_level", "text", "ระดับข้อจำกัด"),
            ("source", "text", "แหล่งข้อมูล"),
        ],
    },
    "zoning": {
        "description": "ผังสีและการใช้ประโยชน์ที่ดิน",
        "geometry": "MULTIPOLYGON",
        "columns": [
            ("zone_id", "text", "รหัสพื้นที่ผัง"),
            ("zone_code", "text", "รหัสผังสี"),
            ("zone_name", "text", "ชื่อประเภทการใช้ประโยชน์ที่ดิน"),
            ("landuse_type", "text", "กลุ่มการใช้ประโยชน์"),
            ("far", "numeric", "FAR"),
            ("bcr", "numeric", "BCR"),
            ("osr", "numeric", "OSR"),
            ("note", "text", "หมายเหตุ"),
            ("source", "text", "แหล่งข้อมูล"),
        ],
    },
    "parcels": {
        "description": "แปลงที่ดิน",
        "geometry": "MULTIPOLYGON",
        "columns": [
            ("parcel_id", "text", "รหัสแปลง"),
            ("land_no", "text", "เลขที่ดิน"),
            ("parcel_no", "text", "เลขแปลง"),
            ("area_rai", "numeric", "พื้นที่ไร่"),
            ("ownership_type", "text", "ประเภทกรรมสิทธิ์"),
            ("source", "text", "แหล่งข้อมูล"),
        ],
    },
    "buildings": {
        "description": "อาคารและสิ่งปลูกสร้าง",
        "geometry": "MULTIPOLYGON",
        "columns": [
            ("building_id", "text", "รหัสอาคาร"),
            ("name", "text", "ชื่ออาคาร"),
            ("use_type", "text", "ประเภทการใช้ประโยชน์"),
            ("floors", "integer", "จำนวนชั้น"),
            ("height_m", "numeric", "ความสูงเมตร"),
            ("construction_year", "integer", "ปีที่ก่อสร้าง"),
            ("source", "text", "แหล่งข้อมูล"),
        ],
    },
    "waterways": {
        "description": "ลำน้ำ แหล่งน้ำ และโครงข่ายน้ำ",
        "geometry": "MULTILINESTRING",
        "columns": [
            ("water_id", "text", "รหัสแหล่งน้ำ"),
            ("name", "text", "ชื่อแหล่งน้ำ"),
            ("water_type", "text", "ประเภทแหล่งน้ำ"),
            ("seasonal", "boolean", "ตามฤดูกาล"),
            ("buffer_m", "numeric", "ระยะกันชนเมตร"),
            ("source", "text", "แหล่งข้อมูล"),
        ],
    },
    "candidate_areas": {
        "description": "พื้นที่ candidate จาก Urban OS",
        "geometry": "MULTIPOLYGON",
        "columns": [
            ("candidate_id", "text", "รหัส candidate"),
            ("project_id", "text", "รหัสโครงการ"),
            ("suitability_class", "integer", "ระดับ suitability"),
            ("area_rai", "numeric", "พื้นที่ไร่"),
            ("heat_risk_class", "integer", "ระดับ Heat Risk"),
            ("feasibility_level", "text", "ระดับความเป็นไปได้"),
            ("priority_phase", "text", "ระยะพัฒนา"),
            ("note", "text", "หมายเหตุ"),
        ],
    },
    "uhi_hotspots": {
        "description": "พื้นที่ Heat Hotspot / UHI",
        "geometry": "MULTIPOLYGON",
        "columns": [
            ("hotspot_id", "text", "รหัส hotspot"),
            ("analysis_date", "date", "วันที่วิเคราะห์"),
            ("lst_mean_c", "numeric", "LST เฉลี่ย C"),
            ("lst_max_c", "numeric", "LST สูงสุด C"),
            ("heat_risk_class", "integer", "ระดับความร้อน"),
            ("area_rai", "numeric", "พื้นที่ไร่"),
            ("recommendation", "text", "แนวทางลดความร้อน"),
        ],
    },
    "planning_projects": {
        "description": "รายการโครงการวิเคราะห์หรือจัดทำผัง",
        "geometry": "MULTIPOLYGON",
        "columns": [
            ("project_id", "text", "รหัสโครงการ"),
            ("project_name", "text", "ชื่อโครงการ"),
            ("province", "text", "จังหวัด"),
            ("district", "text", "อำเภอ"),
            ("planning_standard_profile", "text", "profile มาตรฐาน"),
            ("created_by", "text", "ผู้สร้าง"),
            ("created_at_text", "text", "วันเวลาที่สร้าง"),
            ("description", "text", "คำอธิบาย"),
        ],
    },
}


def validate_schema_name(schema_name: str) -> str:
    schema_name = str(schema_name or "urban_os").strip()
    if not SAFE_SCHEMA_RE.match(schema_name):
        raise ValueError("ชื่อ schema ใช้ได้เฉพาะตัวอักษร ตัวเลข และ underscore และต้องไม่ขึ้นต้นด้วยตัวเลข")
    return schema_name


def quoted_cols(cols: list[str]) -> str:
    return ", ".join([f'"{c}"' for c in cols])


def build_postgis_schema_sql(schema_name: str = "urban_os", srid: int = 4326, include_drop: bool = False, include_sample_data: bool = True, include_views: bool = True, include_comments: bool = True) -> str:
    schema_name = validate_schema_name(schema_name)
    srid = int(srid or 4326)
    lines = [
        "-- Urban OS PostGIS Schema Template",
        f"-- Generated at: {datetime.now().isoformat(timespec='seconds')}",
        "CREATE EXTENSION IF NOT EXISTS postgis;",
        f'CREATE SCHEMA IF NOT EXISTS "{schema_name}";',
        "",
    ]

    if include_drop:
        lines += [
            "-- WARNING: destructive reset",
            f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE;',
            f'CREATE SCHEMA "{schema_name}";',
            "",
        ]

    for table_name, spec in TABLES.items():
        full_table = f'"{schema_name}"."{table_name}"'
        lines.append(f"-- {table_name}: {spec['description']}")
        lines.append(f"CREATE TABLE IF NOT EXISTS {full_table} (")
        cols = ['    "id" bigserial PRIMARY KEY']
        for col_name, col_type, _comment in spec["columns"]:
            cols.append(f'    "{col_name}" {col_type}')
        cols += ['    "created_at" timestamptz DEFAULT now()', '    "updated_at" timestamptz DEFAULT now()']
        if spec.get("geometry"):
            cols.append(f'    "geom" geometry({spec["geometry"]}, {srid})')
        lines.append(",\n".join(cols))
        lines.append(");")

        if spec.get("geometry"):
            lines.append(f'CREATE INDEX IF NOT EXISTS "{table_name}_geom_gix" ON {full_table} USING GIST ("geom");')

        for col_name, _col_type, _comment in spec["columns"]:
            if col_name.endswith("_id") or col_name in ["category", "road_class", "facility_type", "zone_code", "landuse_type", "heat_risk_class", "suitability_class"]:
                lines.append(f'CREATE INDEX IF NOT EXISTS "{table_name}_{col_name}_idx" ON {full_table} ("{col_name}");')

        if include_comments:
            desc = spec["description"].replace("'", "''")
            lines.append(f"COMMENT ON TABLE {full_table} IS '{desc}';")
            for col_name, _col_type, col_comment in spec["columns"]:
                comment = col_comment.replace("'", "''")
                lines.append(f'COMMENT ON COLUMN {full_table}."{col_name}" IS \'{comment}\';')

        lines.append("")

    if include_views:
        lines += [
            "-- Useful views for Urban OS",
            f'CREATE OR REPLACE VIEW "{schema_name}"."v_enabled_layers" AS SELECT layer_id, layer_name, category, source_type, table_name, geom_col, srid, enabled, description FROM "{schema_name}"."urban_layers" WHERE enabled IS TRUE;',
            f'CREATE OR REPLACE VIEW "{schema_name}"."v_development_candidates_high" AS SELECT * FROM "{schema_name}"."candidate_areas" WHERE suitability_class >= 4;',
            f'CREATE OR REPLACE VIEW "{schema_name}"."v_heat_hotspots_high" AS SELECT * FROM "{schema_name}"."uhi_hotspots" WHERE heat_risk_class >= 4;',
            "",
        ]

    if include_sample_data:
        lines.append("-- Sample data for urban_layers registry")
        for table_name, spec in TABLES.items():
            if table_name == "urban_layers":
                continue
            cols = ["layer_id", "layer_name", "category", "source_type", "table_name", "geom_col", "srid", "enabled", "description"]
            vals = [f"{table_name}_default", table_name, table_name, "postgis", f"{schema_name}.{table_name}", "geom" if spec.get("geometry") else "", str(srid), "true", spec["description"]]
            sql_vals = []
            for value in vals:
                if value == "true":
                    sql_vals.append("true")
                elif str(value).isdigit():
                    sql_vals.append(str(value))
                else:
                    sql_vals.append("'" + str(value).replace("'", "''") + "'")
            lines.append(f'INSERT INTO "{schema_name}"."urban_layers" ({quoted_cols(cols)}) VALUES ({", ".join(sql_vals)}) ON CONFLICT DO NOTHING;')
        lines.append("")

    lines += [
        "-- Recommended read-only role",
        "-- CREATE ROLE urban_reader LOGIN PASSWORD 'change-me';",
        f'-- GRANT USAGE ON SCHEMA "{schema_name}" TO urban_reader;',
        f'-- GRANT SELECT ON ALL TABLES IN SCHEMA "{schema_name}" TO urban_reader;',
        f'-- ALTER DEFAULT PRIVILEGES IN SCHEMA "{schema_name}" GRANT SELECT ON TABLES TO urban_reader;',
        "",
    ]
    return "\n".join(lines)


def build_data_dictionary_csv() -> bytes:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["table_name", "description", "column_name", "data_type", "column_description", "geometry_type"])
    for table_name, spec in TABLES.items():
        for col_name, col_type, col_comment in spec["columns"]:
            writer.writerow([table_name, spec["description"], col_name, col_type, col_comment, spec.get("geometry") or ""])
    return output.getvalue().encode("utf-8-sig")


def build_csv_templates_zip() -> bytes:
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as z:
        for table_name, spec in TABLES.items():
            output = io.StringIO()
            writer = csv.writer(output)
            headers = [col_name for col_name, _col_type, _comment in spec["columns"]]
            if spec.get("geometry"):
                headers += ["lon", "lat", "wkt_geom"]
            writer.writerow(headers)
            writer.writerow(["" for _ in headers])
            z.writestr(f"{table_name}_template.csv", output.getvalue())
        z.writestr("data_dictionary.csv", build_data_dictionary_csv().decode("utf-8-sig"))
        z.writestr("README_IMPORT.md", "Urban OS CSV templates for PostGIS import. Use lon/lat for point layers or wkt_geom for line/polygon layers.")
    mem.seek(0)
    return mem.getvalue()


def build_ogr2ogr_examples(schema_name: str = "urban_os") -> str:
    schema_name = validate_schema_name(schema_name)
    return "\n".join([
        "# ตัวอย่างคำสั่ง ogr2ogr สำหรับนำข้อมูลเข้า PostGIS",
        "",
        "## Shapefile ถนน",
        f'ogr2ogr -f "PostgreSQL" PG:"host=<HOST> dbname=<DB> user=<USER> password=<PASSWORD>" roads.shp -nln {schema_name}.roads -nlt PROMOTE_TO_MULTI -lco GEOMETRY_NAME=geom -t_srs EPSG:4326 -append',
        "",
        "## GeoPackage บริการสาธารณะ",
        f'ogr2ogr -f "PostgreSQL" PG:"host=<HOST> dbname=<DB> user=<USER> password=<PASSWORD>" public_facilities.gpkg public_facilities -nln {schema_name}.public_facilities -nlt PROMOTE_TO_MULTI -lco GEOMETRY_NAME=geom -t_srs EPSG:4326 -append',
        "",
        "## GeoJSON zoning",
        f'ogr2ogr -f "PostgreSQL" PG:"host=<HOST> dbname=<DB> user=<USER> password=<PASSWORD>" zoning.geojson -nln {schema_name}.zoning -nlt PROMOTE_TO_MULTI -lco GEOMETRY_NAME=geom -t_srs EPSG:4326 -append',
    ])

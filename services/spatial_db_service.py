from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

import ee
import pandas as pd
import streamlit as st


SAFE_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)?$")
DANGEROUS_SQL_RE = re.compile(
    r"(;|--|/\*|\*/|\bdrop\b|\bdelete\b|\bupdate\b|\binsert\b|\balter\b|\bcreate\b|\bgrant\b|\brevoke\b|\btruncate\b)",
    re.IGNORECASE,
)


@dataclass
class SpatialDBLayerConfig:
    source_type: str = "postgis"
    table_name: str = ""
    geom_col: str = "geom"
    where_sql: str = ""
    limit: int = 5000


def _quote_identifier(identifier: str) -> str:
    """
    Quote schema/table/column identifiers after strict validation.

    Accepted:
    - roads
    - public.roads

    Rejected:
    - roads; drop table ...
    - public.roads where ...
    """

    identifier = str(identifier or "").strip()
    if not SAFE_IDENTIFIER_RE.match(identifier):
        raise ValueError(
            f"Invalid SQL identifier: {identifier}. ใช้ได้เฉพาะชื่อแบบ table หรือ schema.table"
        )

    return ".".join(f'"{part}"' for part in identifier.split("."))


def _validate_where_sql(where_sql: str) -> str:
    """
    Optional WHERE clause fragment for advanced users.
    This is intentionally conservative.
    """

    where_sql = str(where_sql or "").strip()
    if not where_sql:
        return ""

    if DANGEROUS_SQL_RE.search(where_sql):
        raise ValueError("WHERE filter มีคำสั่ง SQL ที่เสี่ยงเกินไป ระบบไม่อนุญาตให้ใช้")

    return where_sql


def get_postgis_url_from_secrets(section: str = "postgis") -> str:
    """
    Read PostGIS connection from Streamlit secrets.

    Supported formats:

    [postgis]
    url = "postgresql+psycopg2://user:password@host:5432/database"

    or

    [postgis]
    host = "..."
    port = 5432
    database = "urban_os"
    user = "..."
    password = "..."
    """

    if section not in st.secrets:
        raise RuntimeError(
            f"ไม่พบ st.secrets['{section}'] กรุณาตั้งค่า connection ใน Streamlit Secrets ก่อน"
        )

    cfg = st.secrets[section]

    if "url" in cfg:
        return str(cfg["url"])

    host = cfg.get("host")
    port = int(cfg.get("port", 5432))
    database = cfg.get("database") or cfg.get("dbname")
    user = cfg.get("user")
    password = cfg.get("password")

    missing = [
        name
        for name, value in {
            "host": host,
            "database": database,
            "user": user,
            "password": password,
        }.items()
        if not value
    ]
    if missing:
        raise RuntimeError(f"PostGIS secrets ไม่ครบ: {', '.join(missing)}")

    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"


@st.cache_resource(show_spinner=False)
def get_postgis_engine(section: str = "postgis"):
    try:
        from sqlalchemy import create_engine
    except Exception as exc:
        raise RuntimeError(
            "ยังไม่ได้ติดตั้ง SQLAlchemy/psycopg2 กรุณาเพิ่ม sqlalchemy และ psycopg2-binary ใน requirements.txt"
        ) from exc

    url = get_postgis_url_from_secrets(section)
    return create_engine(url, pool_pre_ping=True)


def test_postgis_connection(section: str = "postgis") -> dict:
    from sqlalchemy import text

    engine = get_postgis_engine(section)

    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT
                    current_database() AS database_name,
                    current_schema() AS schema_name,
                    postgis_full_version() AS postgis_version
                """
            )
        ).mappings().first()

    return dict(row or {})


def list_postgis_tables(section: str = "postgis", limit: int = 100) -> pd.DataFrame:
    """
    List spatial tables detected from geometry_columns.
    """

    from sqlalchemy import text

    engine = get_postgis_engine(section)

    sql = text(
        """
        SELECT
            f_table_schema AS schema_name,
            f_table_name AS table_name,
            f_geometry_column AS geom_col,
            type AS geometry_type,
            srid
        FROM geometry_columns
        ORDER BY f_table_schema, f_table_name
        LIMIT :limit
        """
    )

    with engine.connect() as conn:
        rows = conn.execute(sql, {"limit": int(limit)}).mappings().all()

    return pd.DataFrame([dict(row) for row in rows])


def get_roi_bbox_4326(roi) -> tuple[float, float, float, float] | None:
    """
    Convert current GEE ROI to bbox in EPSG:4326.

    Returns:
        minx, miny, maxx, maxy
    """

    if roi is None:
        return None

    try:
        geometry = roi.geometry() if hasattr(roi, "geometry") else ee.Geometry(roi)
        coords = geometry.bounds(maxError=1).coordinates().getInfo()[0]
        xs = [float(pt[0]) for pt in coords]
        ys = [float(pt[1]) for pt in coords]
        return min(xs), min(ys), max(xs), max(ys)
    except Exception:
        return None


def fetch_postgis_geojson(
    *,
    table_name: str,
    geom_col: str = "geom",
    where_sql: str = "",
    bbox_4326: tuple[float, float, float, float] | None = None,
    limit: int = 5000,
    section: str = "postgis",
) -> dict:
    """
    Fetch PostGIS features as GeoJSON FeatureCollection.

    Geometry is transformed to EPSG:4326 because Earth Engine expects lon/lat GeoJSON.
    """

    from sqlalchemy import text

    table_sql = _quote_identifier(table_name)
    geom_sql = _quote_identifier(geom_col)
    where_sql = _validate_where_sql(where_sql)

    limit = int(max(1, min(int(limit or 5000), 50000)))

    where_parts = [f"{geom_sql} IS NOT NULL"]

    params: dict[str, Any] = {"limit": limit}

    if bbox_4326:
        minx, miny, maxx, maxy = bbox_4326
        where_parts.append(
            f"ST_Intersects(ST_Transform({geom_sql}, 4326), ST_MakeEnvelope(:minx, :miny, :maxx, :maxy, 4326))"
        )
        params.update({"minx": minx, "miny": miny, "maxx": maxx, "maxy": maxy})

    if where_sql:
        where_parts.append(f"({where_sql})")

    where_clause = " AND ".join(where_parts)

    sql = text(
        f"""
        WITH src AS (
            SELECT *
            FROM {table_sql}
            WHERE {where_clause}
            LIMIT :limit
        ),
        features AS (
            SELECT jsonb_build_object(
                'type', 'Feature',
                'geometry', ST_AsGeoJSON(ST_Transform({geom_sql}, 4326))::jsonb,
                'properties', to_jsonb(src) - '{geom_col}'
            ) AS feature
            FROM src
        )
        SELECT jsonb_build_object(
            'type', 'FeatureCollection',
            'features', COALESCE(jsonb_agg(feature), '[]'::jsonb)
        ) AS geojson
        FROM features
        """
    )

    engine = get_postgis_engine(section)

    with engine.connect() as conn:
        value = conn.execute(sql, params).scalar()

    if value is None:
        return {"type": "FeatureCollection", "features": []}

    if isinstance(value, str):
        return json.loads(value)

    return value


def geojson_to_ee_feature_collection(
    geojson: dict,
    *,
    max_features: int = 5000,
) -> ee.FeatureCollection:
    """
    Convert a GeoJSON FeatureCollection into ee.FeatureCollection.

    Use this only for ROI-sized layers. Very large national layers should be:
    - uploaded/synced to GEE Asset, or
    - processed in PostGIS instead of being sent to GEE each run.
    """

    features = (geojson or {}).get("features", []) or []
    max_features = int(max(1, min(max_features, 50000)))

    if len(features) > max_features:
        features = features[:max_features]

    if not features:
        return ee.FeatureCollection([])

    return ee.FeatureCollection(features)


def fetch_postgis_as_ee_feature_collection(
    *,
    roi,
    table_name: str,
    geom_col: str = "geom",
    where_sql: str = "",
    limit: int = 5000,
    section: str = "postgis",
) -> tuple[ee.FeatureCollection, dict]:
    """
    Fetch PostGIS table within current ROI and return ee.FeatureCollection + metadata.
    """

    bbox = get_roi_bbox_4326(roi)
    geojson = fetch_postgis_geojson(
        table_name=table_name,
        geom_col=geom_col,
        where_sql=where_sql,
        bbox_4326=bbox,
        limit=limit,
        section=section,
    )

    fc = geojson_to_ee_feature_collection(geojson, max_features=limit)

    metadata = {
        "source_type": "postgis",
        "table_name": table_name,
        "geom_col": geom_col,
        "feature_count": len(geojson.get("features", []) or []),
        "bbox_4326": bbox,
        "limit": limit,
    }

    return fc, metadata


def geojson_properties_dataframe(geojson: dict, max_rows: int = 100) -> pd.DataFrame:
    rows = []
    for feature in (geojson or {}).get("features", [])[:max_rows]:
        props = feature.get("properties", {}) or {}
        rows.append(props)
    return pd.DataFrame(rows)



def count_postgis_features_by_roi(
    *,
    table_name: str,
    geom_col: str = "geom",
    where_sql: str = "",
    roi=None,
    section: str = "postgis",
) -> int:
    """
    Count PostGIS features intersecting the current GEE ROI bbox.
    Used by Planning Standards Preset V2 to estimate city size from buildings.
    """

    from sqlalchemy import text

    table_sql = _quote_identifier(table_name)
    geom_sql = _quote_identifier(geom_col)
    where_sql = _validate_where_sql(where_sql)

    bbox_4326 = get_roi_bbox_4326(roi)
    where_parts = [f"{geom_sql} IS NOT NULL"]
    params = {}

    if bbox_4326:
        minx, miny, maxx, maxy = bbox_4326
        where_parts.append(
            f"ST_Intersects(ST_Transform({geom_sql}, 4326), ST_MakeEnvelope(:minx, :miny, :maxx, :maxy, 4326))"
        )
        params.update({"minx": minx, "miny": miny, "maxx": maxx, "maxy": maxy})

    if where_sql:
        where_parts.append(f"({where_sql})")

    sql = text(f"SELECT COUNT(*) FROM {table_sql} WHERE {' AND '.join(where_parts)}")

    engine = get_postgis_engine(section)

    with engine.connect() as conn:
        return int(conn.execute(sql, params).scalar() or 0)



def summarize_postgis_numeric_by_roi(
    *,
    table_name: str,
    geom_col: str = "geom",
    numeric_columns: list[str] | tuple[str, ...],
    where_sql: str = "",
    roi=None,
    agg: str = "avg",
    section: str = "postgis",
) -> dict:
    """
    Summarize numeric PostGIS fields intersecting the current ROI bbox.

    agg:
    - avg
    - sum
    - max
    - min
    """

    from sqlalchemy import text

    table_sql = _quote_identifier(table_name)
    geom_sql = _quote_identifier(geom_col)
    where_sql = _validate_where_sql(where_sql)

    agg = str(agg or "avg").lower().strip()
    if agg not in {"avg", "sum", "max", "min"}:
        agg = "avg"

    cols = [str(c or "").strip() for c in (numeric_columns or []) if str(c or "").strip()]
    if not cols:
        raise ValueError("numeric_columns is empty")

    select_parts = []
    for col in cols:
        col_sql = _quote_identifier(col)
        select_parts.append(f"{agg.upper()}({col_sql})::float AS {col_sql}")

    where_parts = [f"{geom_sql} IS NOT NULL"]
    params: dict[str, Any] = {}

    bbox_4326 = get_roi_bbox_4326(roi)
    if bbox_4326:
        minx, miny, maxx, maxy = bbox_4326
        where_parts.append(
            f"ST_Intersects(ST_Transform({geom_sql}, 4326), ST_MakeEnvelope(:minx, :miny, :maxx, :maxy, 4326))"
        )
        params.update({"minx": minx, "miny": miny, "maxx": maxx, "maxy": maxy})

    if where_sql:
        where_parts.append(f"({where_sql})")

    sql = text(f"SELECT {', '.join(select_parts)} FROM {table_sql} WHERE {' AND '.join(where_parts)}")

    engine = get_postgis_engine(section)
    with engine.connect() as conn:
        row = conn.execute(sql, params).mappings().first()

    if not row:
        return {col: None for col in cols}

    return {col: row.get(col) for col in cols}


def fetch_postgis_records_by_roi(
    *,
    table_name: str,
    geom_col: str = "geom",
    fields: list[str] | tuple[str, ...],
    where_sql: str = "",
    roi=None,
    limit: int = 500,
    section: str = "postgis",
) -> list[dict]:
    """
    Fetch selected non-geometry fields from PostGIS features intersecting ROI.
    Used for planning_controls, service_areas, hazard_zones, socioeconomic, etc.
    """

    from sqlalchemy import text

    table_sql = _quote_identifier(table_name)
    geom_sql = _quote_identifier(geom_col)
    where_sql = _validate_where_sql(where_sql)

    fields = [str(f or "").strip() for f in (fields or []) if str(f or "").strip()]
    if not fields:
        raise ValueError("fields is empty")

    field_sql_parts = []
    for field in fields:
        field_sql_parts.append(_quote_identifier(field))

    limit = int(max(1, min(int(limit or 500), 5000)))

    where_parts = [f"{geom_sql} IS NOT NULL"]
    params: dict[str, Any] = {"limit": limit}

    bbox_4326 = get_roi_bbox_4326(roi)
    if bbox_4326:
        minx, miny, maxx, maxy = bbox_4326
        where_parts.append(
            f"ST_Intersects(ST_Transform({geom_sql}, 4326), ST_MakeEnvelope(:minx, :miny, :maxx, :maxy, 4326))"
        )
        params.update({"minx": minx, "miny": miny, "maxx": maxx, "maxy": maxy})

    if where_sql:
        where_parts.append(f"({where_sql})")

    sql = text(
        f"SELECT {', '.join(field_sql_parts)} FROM {table_sql} "
        f"WHERE {' AND '.join(where_parts)} LIMIT :limit"
    )

    engine = get_postgis_engine(section)
    with engine.connect() as conn:
        rows = list(conn.execute(sql, params).mappings())

    return [dict(row) for row in rows]


# ---------------------------------------------------------
# Import Wizard -> PostGIS writer
# ---------------------------------------------------------
def _safe_pg_identifier(name: str, default: str = "field") -> str:
    """
    Convert arbitrary text to a safe PostgreSQL identifier.
    """

    name = str(name or default).strip().lower()
    name = re.sub(r"[^a-z0-9_]+", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")

    if not name:
        name = default

    if name[0].isdigit():
        name = f"f_{name}"

    return name[:50]


def _safe_pg_column_name(name: str, used: set[str]) -> str:
    base = _safe_pg_identifier(name, "field")
    candidate = base
    i = 1
    while candidate in used or candidate in {
        "id",
        "geom",
        "properties",
        "layer_name",
        "category",
        "source_file",
        "imported_at",
    }:
        suffix = f"_{i}"
        candidate = f"{base[:50-len(suffix)]}{suffix}"
        i += 1
    used.add(candidate)
    return candidate


def _infer_pg_type(values: list[Any]) -> str:
    clean = [v for v in values if v is not None and v != ""]
    if not clean:
        return "TEXT"

    if all(isinstance(v, bool) for v in clean):
        return "BOOLEAN"

    if all(isinstance(v, int) and not isinstance(v, bool) for v in clean):
        return "BIGINT"

    if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in clean):
        return "DOUBLE PRECISION"

    return "TEXT"


def _coerce_value_for_pg(value: Any, pg_type: str):
    if value is None:
        return None

    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False)

    if pg_type == "BOOLEAN":
        if isinstance(value, bool):
            return value
        if str(value).strip().lower() in {"true", "t", "1", "yes", "y"}:
            return True
        if str(value).strip().lower() in {"false", "f", "0", "no", "n"}:
            return False
        return None

    if pg_type == "BIGINT":
        try:
            return int(value)
        except Exception:
            return None

    if pg_type == "DOUBLE PRECISION":
        try:
            return float(value)
        except Exception:
            return None

    return str(value)


def import_geojson_to_postgis(
    *,
    geojson: dict,
    table_name: str,
    schema_name: str = "public",
    geom_col: str = "geom",
    layer_name: str = "",
    category: str = "",
    source_file: str = "",
    mode: str = "append",
    create_attribute_columns: bool = True,
    create_spatial_index: bool = True,
    section: str = "postgis",
    max_features: int = 50000,
) -> dict:
    """
    Import a GeoJSON FeatureCollection into PostGIS.

    The import table stores:
    - id
    - geom geometry(GEOMETRY,4326)
    - properties jsonb
    - metadata columns
    - optional flattened attribute columns

    mode:
    - append
    - overwrite
    """

    from sqlalchemy import text

    features = (geojson or {}).get("features", []) or []
    max_features = int(max(1, min(int(max_features or 50000), 200000)))
    features = features[:max_features]

    if not features:
        raise ValueError("GeoJSON ไม่มี features สำหรับ import")

    schema_name = _safe_pg_identifier(schema_name, "public")
    table_name = _safe_pg_identifier(table_name, "imported_layer")
    geom_col = _safe_pg_identifier(geom_col, "geom")

    mode = str(mode or "append").lower().strip()
    if mode not in {"append", "overwrite"}:
        mode = "append"

    # Attribute field mapping
    prop_keys: list[str] = []
    for feat in features:
        for key in (feat.get("properties") or {}).keys():
            if key not in prop_keys:
                prop_keys.append(key)

    used_cols: set[str] = set()
    attr_map: dict[str, str] = {}
    attr_types: dict[str, str] = {}

    if create_attribute_columns:
        for key in prop_keys:
            col = _safe_pg_column_name(key, used_cols)
            values = [(feat.get("properties") or {}).get(key) for feat in features[:500]]
            pg_type = _infer_pg_type(values)
            attr_map[key] = col
            attr_types[col] = pg_type

    schema_sql = _quote_identifier(schema_name)
    table_sql = f'{schema_sql}.{_quote_identifier(table_name)}'
    geom_sql = _quote_identifier(geom_col)

    engine = get_postgis_engine(section)

    inserted = 0
    skipped = 0

    with engine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_sql}"))

        if mode == "overwrite":
            conn.execute(text(f"DROP TABLE IF EXISTS {table_sql} CASCADE"))

        base_cols = f"""
            id BIGSERIAL PRIMARY KEY,
            {geom_sql} geometry(GEOMETRY, 4326),
            properties JSONB,
            layer_name TEXT,
            category TEXT,
            source_file TEXT,
            imported_at TIMESTAMPTZ DEFAULT NOW()
        """

        conn.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS {table_sql} (
                    {base_cols}
                )
                """
            )
        )

        # Add attribute columns when needed. Use IF NOT EXISTS for append mode.
        for col, pg_type in attr_types.items():
            conn.execute(
                text(
                    f"ALTER TABLE {table_sql} ADD COLUMN IF NOT EXISTS {_quote_identifier(col)} {pg_type}"
                )
            )

        insert_cols = [geom_col, "properties", "layer_name", "category", "source_file"]
        insert_exprs = [
            "ST_SetSRID(ST_GeomFromGeoJSON(:geom_json), 4326)",
            "CAST(:properties AS JSONB)",
            ":layer_name",
            ":category",
            ":source_file",
        ]

        for _, col in attr_map.items():
            insert_cols.append(col)
            insert_exprs.append(f":attr_{col}")

        col_sql = ", ".join(_quote_identifier(c) for c in insert_cols)
        val_sql = ", ".join(insert_exprs)

        insert_sql = text(f"INSERT INTO {table_sql} ({col_sql}) VALUES ({val_sql})")

        for feat in features:
            geom = feat.get("geometry")
            if not geom:
                skipped += 1
                continue

            props = feat.get("properties") or {}

            params: dict[str, Any] = {
                "geom_json": json.dumps(geom, ensure_ascii=False),
                "properties": json.dumps(props, ensure_ascii=False),
                "layer_name": str(layer_name or ""),
                "category": str(category or ""),
                "source_file": str(source_file or ""),
            }

            for original_key, col in attr_map.items():
                pg_type = attr_types.get(col, "TEXT")
                params[f"attr_{col}"] = _coerce_value_for_pg(props.get(original_key), pg_type)

            conn.execute(insert_sql, params)
            inserted += 1

        if create_spatial_index:
            idx_name = _safe_pg_identifier(f"idx_{schema_name}_{table_name}_{geom_col}_gist", "idx_geom")[:60]
            conn.execute(
                text(
                    f"CREATE INDEX IF NOT EXISTS {_quote_identifier(idx_name)} "
                    f"ON {table_sql} USING GIST ({geom_sql})"
                )
            )

        conn.execute(text(f"ANALYZE {table_sql}"))

    return {
        "schema_name": schema_name,
        "table_name": table_name,
        "full_table_name": f"{schema_name}.{table_name}",
        "geom_col": geom_col,
        "inserted": inserted,
        "skipped": skipped,
        "mode": mode,
        "attribute_columns": attr_map,
        "attribute_types": attr_types,
        "spatial_index": bool(create_spatial_index),
        "section": section,
    }

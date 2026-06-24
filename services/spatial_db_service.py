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

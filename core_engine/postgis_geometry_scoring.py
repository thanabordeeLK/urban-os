from __future__ import annotations

import ee

from services.gee_service import safe_clip
from services.spatial_db_service import fetch_postgis_as_ee_feature_collection


def _constant_score(score: float, name: str, roi=None, is_whole_country: bool = False) -> ee.Image:
    try:
        value = float(score)
    except Exception:
        value = 3.0
    value = max(1.0, min(5.0, value))
    img = ee.Image(value).rename(name).toFloat()
    if roi is not None:
        img = safe_clip(img, roi, is_whole_country)
    return img


def get_postgis_score_image(
    *,
    roi,
    config: dict | None,
    image_name: str,
    is_whole_country: bool = False,
    default_score: float = 3.0,
    invert_score: bool = False,
) -> tuple[ee.Image, dict]:
    """
    Build a 1-5 suitability score image directly from PostGIS geometry.

    Expected score field:
    - numeric 1-5, or percent 0-100
    - for hazard risk fields set invert_score=True: risk 5 => suitability 1
    """

    cfg = config or {}
    meta = {
        "enabled": bool(cfg.get("enabled", False)),
        "source_type": "postgis_geometry",
        "table_name": cfg.get("table_name", ""),
        "score_field": cfg.get("score_field", ""),
        "feature_count": 0,
        "used_geometry": False,
        "error": None,
    }

    if not bool(cfg.get("enabled", False)):
        return _constant_score(default_score, image_name, roi, is_whole_country), meta

    table_name = str(cfg.get("table_name", "") or "").strip()
    geom_col = str(cfg.get("geom_col", "geom") or "geom").strip()
    score_field = str(cfg.get("score_field", "") or "").strip()
    where_sql = str(cfg.get("where_sql", "") or "").strip()
    limit = int(cfg.get("limit", 5000) or 5000)
    buffer_m = float(cfg.get("buffer_m", 0) or 0)
    reducer_name = str(cfg.get("reducer", "mean") or "mean").lower().strip()
    default_score = float(cfg.get("default_score", default_score) or default_score)

    if not table_name or not score_field:
        meta["error"] = "Missing table_name or score_field"
        return _constant_score(default_score, image_name, roi, is_whole_country), meta

    try:
        fc, source_meta = fetch_postgis_as_ee_feature_collection(
            roi=roi,
            table_name=table_name,
            geom_col=geom_col,
            where_sql=where_sql,
            limit=limit,
        )
        meta.update(source_meta)
        meta["score_field"] = score_field
        feature_count = int(source_meta.get("feature_count", 0) or 0)
        meta["feature_count"] = feature_count

        if feature_count <= 0:
            meta["error"] = "No features intersect ROI"
            return _constant_score(default_score, image_name, roi, is_whole_country), meta

        if buffer_m > 0:
            fc = fc.map(lambda f: f.buffer(buffer_m))

        if reducer_name == "max":
            reducer = ee.Reducer.max()
        elif reducer_name == "min":
            reducer = ee.Reducer.min()
        elif reducer_name == "first":
            reducer = ee.Reducer.first()
        else:
            reducer = ee.Reducer.mean()

        raw = fc.reduceToImage(properties=[score_field], reducer=reducer).rename(image_name).toFloat()

        # If field is 0-100, convert to 1-5; if already 1-5, keep it.
        img = raw.where(raw.gt(5), raw.divide(20).ceil()).clamp(1, 5).unmask(default_score)

        if invert_score:
            img = ee.Image(6).subtract(img).clamp(1, 5)

        img = safe_clip(img.rename(image_name).toFloat(), roi, is_whole_country)

        meta["used_geometry"] = True
        meta["buffer_m"] = buffer_m
        meta["reducer"] = reducer_name
        meta["invert_score"] = bool(invert_score)
        meta["default_score"] = default_score
        return img, meta

    except Exception as exc:
        meta["error"] = str(exc)
        return _constant_score(default_score, image_name, roi, is_whole_country), meta

from __future__ import annotations

import ee

from services.gee_service import safe_clip
from core_engine.postgis_geometry_scoring import get_postgis_score_image


def _clamp_score(value, default: float = 3.0) -> float:
    try:
        score = float(value)
    except Exception:
        score = default
    return max(1.0, min(5.0, score))


def score_population_capacity(current_population: int, population_capacity: int) -> float:
    """
    Population Capacity Score

    utilization = current population / planned capacity

    <= 60%  = 5
    <= 80%  = 4
    <= 100% = 3
    <= 120% = 2
    > 120%  = 1
    """

    current_population = max(int(current_population or 0), 0)
    population_capacity = max(int(population_capacity or 0), 0)

    if population_capacity <= 0:
        return 3.0

    utilization = current_population / population_capacity

    if utilization <= 0.60:
        return 5.0
    if utilization <= 0.80:
        return 4.0
    if utilization <= 1.00:
        return 3.0
    if utilization <= 1.20:
        return 2.0
    return 1.0


def score_infrastructure_capacity(scores: dict | None = None) -> float:
    """
    Infrastructure Capacity Score from 1-5 component scores.
    Components may include water, wastewater, electricity, solid_waste, drainage.
    """

    scores = scores or {}
    values = []
    for key in ["water", "wastewater", "electricity", "solid_waste", "drainage"]:
        values.append(_clamp_score(scores.get(key, 3.0), default=3.0))

    if not values:
        return 3.0

    return round(sum(values) / len(values), 2)


def score_zoning_compliance(
    level: str = "neutral",
    criteria_enabled: dict | None = None,
    criteria_scores: dict | None = None,
    score_override: float | None = None,
) -> float:
    """
    Zoning / Legal Compliance Score.

    Step 8.7.3:
    - Every planning-control subcriterion can be toggled individually.
    - Unchecked subcriteria do not affect the zoning score.
    - If no subcriteria are checked, fallback to level mapping or neutral score.
    - This factor remains intentionally last and optional.
    """

    if score_override is not None:
        return _clamp_score(score_override, default=3.0)

    criteria_enabled = criteria_enabled or {}
    criteria_scores = criteria_scores or {}

    active_scores = []
    for key, enabled in criteria_enabled.items():
        if enabled:
            active_scores.append(_clamp_score(criteria_scores.get(key, 3.0), default=3.0))

    if active_scores:
        return round(sum(active_scores) / len(active_scores), 2)

    level = str(level or "neutral").lower().strip()

    mapping = {
        "permitted": 5.0,
        "compatible": 5.0,
        "conditional": 3.0,
        "needs_review": 3.0,
        "neutral": 3.0,
        "unknown": 3.0,
        "restricted": 2.0,
        "prohibited": 1.0,
        "not_allowed": 1.0,
    }

    return mapping.get(level, 3.0)


def score_service_coverage(scores: dict | None = None) -> float:
    """
    Service Coverage Score by Type.
    Components may include health, education, park, market, police, fire, transport.
    """

    scores = scores or {}
    keys = ["health", "education", "park", "market", "police", "fire", "transport"]
    values = [_clamp_score(scores.get(key, 3.0), default=3.0) for key in keys]
    return round(sum(values) / len(values), 2)


def score_multi_hazard_safety(risks: dict | None = None) -> float:
    """
    Multi-Hazard Safety Score.
    User inputs risk levels 1-5. Suitability is inverted:
    risk 1 = suitability 5, risk 5 = suitability 1.
    """

    risks = risks or {}
    keys = ["flood", "landslide", "erosion", "wildfire", "earthquake", "stormwater"]
    risk_values = [_clamp_score(risks.get(key, 3.0), default=3.0) for key in keys]
    avg_risk = sum(risk_values) / len(risk_values)
    return round(6.0 - avg_risk, 2)


def score_socioeconomic_equity(scores: dict | None = None) -> float:
    """
    Socioeconomic / Equity Score.
    A higher score means the area is more appropriate or higher priority from
    equity, community benefit, and access-improvement perspectives.
    """

    scores = scores or {}
    keys = ["access_equity", "community_benefit", "vulnerable_priority", "land_tenure_readiness", "displacement_safety"]
    values = [_clamp_score(scores.get(key, 3.0), default=3.0) for key in keys]
    return round(sum(values) / len(values), 2)


def constant_score_image(score: float, name: str, roi=None, is_whole_country: bool = False) -> ee.Image:
    image = ee.Image(_clamp_score(score)).rename(name).toFloat()
    if roi is not None:
        image = safe_clip(image, roi, is_whole_country)
    return image


def _score_image_from_manual_or_geometry(
    *,
    roi,
    is_whole_country: bool,
    manual_score: float,
    image_name: str,
    config: dict | None,
    invert_score: bool = False,
) -> tuple[ee.Image, dict]:
    cfg = config or {}
    geom_cfg = cfg.get("geometry_scoring", {}) or {}

    if bool(cfg.get("enabled", False)) and bool(geom_cfg.get("enabled", False)):
        return get_postgis_score_image(
            roi=roi,
            config=geom_cfg,
            image_name=image_name,
            is_whole_country=is_whole_country,
            default_score=manual_score,
            invert_score=invert_score,
        )

    return (
        constant_score_image(manual_score, image_name, roi=roi, is_whole_country=is_whole_country),
        {
            "enabled": False,
            "source_type": "manual_or_neutral",
            "used_geometry": False,
            "score_field": None,
            "feature_count": 0,
            "error": None,
        },
    )


def get_advanced_planning_scores(
    *,
    roi,
    is_whole_country: bool = False,
    advanced_config: dict | None = None,
) -> dict:
    """
    Step 8.7.2 Phase A:
    - Population Capacity
    - Infrastructure Capacity
    - Zoning / Legal Compliance

    These are active scoring factors but intentionally optional.
    If a factor is not enabled, the image is neutral 3 and its weight should be zeroed by suitability.py.
    """

    cfg = advanced_config or {}

    pop_cfg = cfg.get("population_capacity", {}) or {}
    infra_cfg = cfg.get("infrastructure_capacity", {}) or {}
    service_cfg = cfg.get("service_coverage", {}) or {}
    hazard_cfg = cfg.get("multi_hazard", {}) or {}
    equity_cfg = cfg.get("socioeconomic_equity", {}) or {}
    zoning_cfg = cfg.get("zoning_compliance", {}) or {}

    pop_score_value = score_population_capacity(
        current_population=int(pop_cfg.get("current_population", 0) or 0),
        population_capacity=int(pop_cfg.get("population_capacity", 0) or 0),
    )

    infra_score_value = score_infrastructure_capacity(
        scores=infra_cfg.get("scores", {}) or {}
    )

    service_score_value = score_service_coverage(
        scores=service_cfg.get("scores", {}) or {}
    )

    hazard_score_value = score_multi_hazard_safety(
        risks=hazard_cfg.get("risks", {}) or {}
    )

    equity_score_value = score_socioeconomic_equity(
        scores=equity_cfg.get("scores", {}) or {}
    )

    zoning_score_value = score_zoning_compliance(
        level=zoning_cfg.get("level", "neutral"),
        criteria_enabled=zoning_cfg.get("criteria_enabled", {}) or {},
        criteria_scores=zoning_cfg.get("criteria_scores", {}) or {},
        score_override=zoning_cfg.get("score_override", None),
    )

    population_img, population_geom_meta = _score_image_from_manual_or_geometry(
        roi=roi,
        is_whole_country=is_whole_country,
        manual_score=pop_score_value,
        image_name="Population_Capacity_Suitability",
        config=pop_cfg,
    )
    infrastructure_img, infrastructure_geom_meta = _score_image_from_manual_or_geometry(
        roi=roi,
        is_whole_country=is_whole_country,
        manual_score=infra_score_value,
        image_name="Infrastructure_Capacity_Suitability",
        config=infra_cfg,
    )
    service_img, service_geom_meta = _score_image_from_manual_or_geometry(
        roi=roi,
        is_whole_country=is_whole_country,
        manual_score=service_score_value,
        image_name="Service_Coverage_Suitability",
        config=service_cfg,
    )
    hazard_img, hazard_geom_meta = _score_image_from_manual_or_geometry(
        roi=roi,
        is_whole_country=is_whole_country,
        manual_score=hazard_score_value,
        image_name="Multi_Hazard_Safety_Suitability",
        config=hazard_cfg,
        invert_score=bool((hazard_cfg.get("geometry_scoring", {}) or {}).get("invert_score", True)),
    )
    equity_img, equity_geom_meta = _score_image_from_manual_or_geometry(
        roi=roi,
        is_whole_country=is_whole_country,
        manual_score=equity_score_value,
        image_name="Socioeconomic_Equity_Suitability",
        config=equity_cfg,
    )
    zoning_img, zoning_geom_meta = _score_image_from_manual_or_geometry(
        roi=roi,
        is_whole_country=is_whole_country,
        manual_score=zoning_score_value,
        image_name="Zoning_Legal_Compliance_Suitability",
        config=zoning_cfg,
    )

    return {
        "population_capacity": population_img,
        "infrastructure_capacity": infrastructure_img,
        "service_coverage": service_img,
        "multi_hazard": hazard_img,
        "socioeconomic_equity": equity_img,
        "zoning_compliance": zoning_img,
        "metadata": {
            "population_score": pop_score_value,
            "infrastructure_score": infra_score_value,
            "service_coverage_score": service_score_value,
            "multi_hazard_safety_score": hazard_score_value,
            "socioeconomic_equity_score": equity_score_value,
            "zoning_score": zoning_score_value,
            "zoning_source_type": zoning_cfg.get("source_type", "Manual"),
            "zoning_criteria_enabled": zoning_cfg.get("criteria_enabled", {}) or {},
            "zoning_criteria_scores": zoning_cfg.get("criteria_scores", {}) or {},
            "geometry_scoring": {
                "population_capacity": population_geom_meta,
                "infrastructure_capacity": infrastructure_geom_meta,
                "service_coverage": service_geom_meta,
                "multi_hazard": hazard_geom_meta,
                "socioeconomic_equity": equity_geom_meta,
                "zoning_compliance": zoning_geom_meta,
            },
            "population_enabled": bool(pop_cfg.get("enabled", False)),
            "infrastructure_enabled": bool(infra_cfg.get("enabled", False)),
            "service_coverage_enabled": bool(service_cfg.get("enabled", False)),
            "multi_hazard_enabled": bool(hazard_cfg.get("enabled", False)),
            "socioeconomic_equity_enabled": bool(equity_cfg.get("enabled", False)),
            "zoning_enabled": bool(zoning_cfg.get("enabled", False)),
            "note": (
                "Zoning / Legal Compliance is intentionally optional. "
                "When unchecked, its weight is zero and it does not affect the final class."
            ),
        },
    }

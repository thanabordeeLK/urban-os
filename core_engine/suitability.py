import streamlit as st
import ee
import pandas as pd

from config.datasets import DATASET_CATALOG
from components.map_renderer import add_custom_legend
from services.gee_service import safe_clip


# ---------------------------------------------------------
# Dataset fallback
# ---------------------------------------------------------
FALLBACK_DATASET_CATALOG = {
    "copernicus_dem": {"id": "COPERNICUS/DEM/GLO30"},
    "global_flood_db": {"id": "GLOBAL_FLOOD_DB/MODIS_EVENTS/V1"},
    "esa_worldcover": {"id": "ESA/WorldCover/v200"},
    "ghsl_smod": {"id": "JRC/GHSL/P2023A/GHS_SMOD_V2-0/2030"},
    "wdpa_polygons": {"id": "WCMC/WDPA/current/polygons"},
}


# ---------------------------------------------------------
# Suitability visualization
# คะแนนทุกชั้นใช้หลักเดียวกัน:
# 1 = ต่ำมาก / จำกัด
# 5 = สูงมาก / เหมาะสมมาก
# ---------------------------------------------------------
SUITABILITY_VIS = {
    "min": 1,
    "max": 5,
    "palette": [
        "d7191c",  # 1 very low / restricted
        "fdae61",  # 2 low
        "ffffbf",  # 3 moderate
        "a6d96a",  # 4 high
        "1a9641",  # 5 very high
    ],
}


SUITABILITY_LEGEND = {
    "1: ควรหลีกเลี่ยง / จำกัดการพัฒนา": "d7191c",
    "2: เหมาะสมน้อย": "fdae61",
    "3: เหมาะสมปานกลาง / มีเงื่อนไข": "ffffbf",
    "4: เหมาะสมสูง": "a6d96a",
    "5: เหมาะสมสูงมาก": "1a9641",
}


FACTOR_SCORE_LEGEND = {
    "1: ไม่เหมาะสม / เสี่ยงสูง": "d7191c",
    "2: เหมาะสมน้อย": "fdae61",
    "3: ปานกลาง": "ffffbf",
    "4: เหมาะสม": "a6d96a",
    "5: เหมาะสมมาก": "1a9641",
}


DEFAULT_WEIGHTS = {
    "slope": 0.20,
    "flood": 0.25,
    "landcover": 0.25,
    "urban": 0.20,
    "water": 0.10,
}


CLASS_LABELS = {
    1: "ควรหลีกเลี่ยง / จำกัดการพัฒนา",
    2: "เหมาะสมน้อย",
    3: "เหมาะสมปานกลาง / มีเงื่อนไข",
    4: "เหมาะสมสูง",
    5: "เหมาะสมสูงมาก",
}


CLASS_COLORS = {
    1: "#d7191c",
    2: "#fdae61",
    3: "#ffffbf",
    4: "#a6d96a",
    5: "#1a9641",
}

# ---------------------------------------------------------
# Display / analysis consistency
# ---------------------------------------------------------
# ใช้ค่าคงที่นี้เพื่อให้ผล final class ไม่เปลี่ยนตามระดับซูมของแผนที่
# หมายเหตุ: สำหรับระดับประเทศไม่บังคับ reproject เพื่อไม่ให้ GEE หนักเกินไป
ANALYSIS_SCALE_M = 30


def lock_display_projection(image: ee.Image, reference_image: ee.Image, is_whole_country: bool = False) -> ee.Image:
    """
    ทำให้ raster ที่แสดงผลบนแผนที่ใช้ projection/scale คงที่
    ลดอาการสีหรือ class ดูเปลี่ยนเมื่อ zoom in/out จาก GEE tile pyramid

    ใช้กับระดับจังหวัด/อำเภอ/ROI เป็นหลัก
    ไม่บังคับกับทั้งประเทศ เพราะจะคำนวณหนักเกินจำเป็น
    """
    if is_whole_country:
        return image

    try:
        return image.reproject(reference_image.projection())
    except Exception:
        return image


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------
def get_dataset_id(key: str) -> str:
    """
    ดึง dataset id จาก config.datasets.DATASET_CATALOG
    ถ้าไม่มีให้ใช้ fallback
    """
    if key in DATASET_CATALOG and "id" in DATASET_CATALOG[key]:
        return DATASET_CATALOG[key]["id"]

    return FALLBACK_DATASET_CATALOG[key]["id"]


def get_roi_geometry(roi):
    """
    คืน geometry สำหรับ reduceRegion
    รองรับทั้ง ee.FeatureCollection / ee.Feature / ee.Geometry
    """
    try:
        return roi.geometry()
    except Exception:
        return roi


def normalize_weights(weights: dict | None) -> dict:
    """
    ปรับน้ำหนักให้รวมเป็น 1.0 อัตโนมัติ
    ถ้าผู้ใช้ตั้งทุกค่าเป็น 0 ให้ใช้ default
    """
    if not weights:
        weights = DEFAULT_WEIGHTS.copy()

    clean_weights = {
        "slope": float(weights.get("slope", 0)),
        "flood": float(weights.get("flood", 0)),
        "landcover": float(weights.get("landcover", 0)),
        "urban": float(weights.get("urban", 0)),
        "water": float(weights.get("water", 0)),
    }

    total = sum(clean_weights.values())

    if total <= 0:
        return DEFAULT_WEIGHTS.copy()

    return {key: value / total for key, value in clean_weights.items()}


def classify_weighted_score(weighted_score: ee.Image) -> ee.Image:
    """
    แปลงคะแนน weighted score 1–5 ให้เป็น class 1–5
    เพื่อให้สีบนแผนที่ตรงกับ legend แบบชัดเจน

    ช่วงคะแนน:
    1.0–1.8 = class 1
    1.8–2.6 = class 2
    2.6–3.4 = class 3
    3.4–4.2 = class 4
    4.2–5.0 = class 5
    """

    score_class = (
        ee.Image(1)
        .where(weighted_score.gte(1.8), 2)
        .where(weighted_score.gte(2.6), 3)
        .where(weighted_score.gte(3.4), 4)
        .where(weighted_score.gte(4.2), 5)
        .rename("Suitability_Class")
        .toInt()
    )

    return score_class


# ---------------------------------------------------------
# Factor 1: Slope suitability
# ---------------------------------------------------------
def get_slope_score(roi, is_whole_country: bool = False) -> ee.Image:
    """
    Slope Suitability

    0–5°     = 5 เหมาะสมมาก
    5–10°    = 4
    10–15°   = 3
    15–20°   = 2
    >20°     = 1 จำกัด
    """

    dem = (
        ee.ImageCollection(get_dataset_id("copernicus_dem"))
        .select("DEM")
        .mosaic()
    )

    dem = safe_clip(dem, roi, is_whole_country)

    slope = ee.Terrain.slope(dem)

    slope_score = (
        ee.Image(1)
        .where(slope.lt(20), 2)
        .where(slope.lt(15), 3)
        .where(slope.lt(10), 4)
        .where(slope.lt(5), 5)
        .rename("Slope_Suitability")
        .toInt()
    )

    return slope_score


# ---------------------------------------------------------
# Factor 2: Flood suitability
# ---------------------------------------------------------
def get_flood_score(roi, is_whole_country: bool = False) -> ee.Image:
    """
    Flood Suitability

    ไม่พบประวัติน้ำท่วม = 5
    ท่วม 1–2 ครั้ง       = 3
    ท่วมมากกว่า 2 ครั้ง = 1 จำกัด
    """

    flood_history = (
        ee.ImageCollection(get_dataset_id("global_flood_db"))
        .filterBounds(roi)
        .select("flooded")
        .sum()
    )

    flood_history = safe_clip(flood_history, roi, is_whole_country)

    flood_score = (
        ee.Image(5)
        .where(flood_history.gt(0), 3)
        .where(flood_history.gt(2), 1)
        .rename("Flood_Suitability")
        .toInt()
    )

    return flood_score


# ---------------------------------------------------------
# Factor 3: Land cover compatibility
# ---------------------------------------------------------
def get_landcover_score(roi, is_whole_country: bool = False):
    """
    Land Cover Compatibility จาก ESA WorldCover

    แนวคิด:
    - พื้นที่พุ่มไม้/ดินโล่ง เหมาะต่อการพัฒนาใหม่มากกว่า
    - พื้นที่เกษตรมี trade-off
    - ป่า น้ำ พื้นที่ชุ่มน้ำ และเมืองเดิม เป็น hard constraint สำหรับโมเดลขยายเมือง
    """

    esa_lc = (
        ee.ImageCollection(get_dataset_id("esa_worldcover"))
        .first()
        .select("Map")
    )

    esa_lc = safe_clip(esa_lc, roi, is_whole_country)

    lc_score = esa_lc.remap(
        # ESA classes
        [10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 100],
        # Suitability scores
        [1, 5, 4, 3, 1, 5, 1, 1, 1, 1, 2],
    ).rename("LandCover_Suitability").toInt()

    return lc_score, esa_lc


# ---------------------------------------------------------
# Factor 4: Urbanization / built-up pressure
# ---------------------------------------------------------
def get_urban_score(roi, is_whole_country: bool = False) -> ee.Image:
    """
    Urbanization Suitability จาก GHSL SMOD

    แนวคิด:
    - ชานเมือง / กึ่งเมือง เหมาะกับการขยายเมืองมากกว่า
    - ศูนย์กลางเมืองหนาแน่นและน้ำ ไม่เหมาะสำหรับพื้นที่พัฒนาใหม่
    """

    smod = (
        ee.Image(get_dataset_id("ghsl_smod"))
        .select("smod_code")
    )

    smod = safe_clip(smod, roi, is_whole_country)

    urban_score = smod.remap(
        # GHSL SMOD classes
        [10, 11, 12, 13, 21, 22, 23, 30],
        # Suitability scores
        [1, 2, 3, 3, 5, 5, 4, 1],
        2,
    ).rename("Urbanization_Suitability").toInt()

    return urban_score


# ---------------------------------------------------------
# Factor 5: Water proximity
# ---------------------------------------------------------
def get_water_proximity_score(
    roi,
    esa_lc: ee.Image,
    is_whole_country: bool = False,
) -> ee.Image:
    """
    Water Proximity Suitability

    0–50m       = 1 buffer/riparian zone ควรจำกัด
    50–1,000m   = 5 amenity สูง
    1,000–3,000m = 3
    >3,000m     = 2
    """

    # ใช้เฉพาะกลุ่มน้ำที่มีขนาดพอสมควร เพื่อลด noise จาก pixel น้ำเล็ก ๆ
    # ที่มักทำให้เกิดวงกลม suitability หลอกเมื่อซูมเข้า
    water_mask = esa_lc.eq(80).selfMask()
    water_connected = water_mask.connectedPixelCount(100, True)
    clean_water_mask = water_mask.updateMask(water_connected.gte(20)).unmask(0)

    # ESA WorldCover resolution ประมาณ 10m
    # ใช้ max distance 300 pixels ≈ 3,000m
    dist_to_water = (
        clean_water_mask
        .fastDistanceTransform(300)
        .sqrt()
        .multiply(10)
        .rename("Distance_To_Water_Meter")
    )

    dist_to_water = safe_clip(dist_to_water, roi, is_whole_country)

    water_score = (
        ee.Image(2)
        .where(dist_to_water.lt(3000), 3)
        .where(dist_to_water.lt(1000), 5)
        .where(dist_to_water.lt(50), 1)
        .rename("Water_Proximity_Suitability")
        .toInt()
    )

    return water_score



# ---------------------------------------------------------
# Hard constraint: Protected / forest reserve areas
# ---------------------------------------------------------
def _merge_feature_collections(collections: list[ee.FeatureCollection]) -> ee.FeatureCollection:
    """
    รวม FeatureCollection หลายชุดให้เป็นชุดเดียว
    """
    if not collections:
        return ee.FeatureCollection([])

    merged = ee.FeatureCollection(collections[0])
    for fc in collections[1:]:
        merged = merged.merge(fc)

    return merged


def get_protected_area_constraint(
    roi,
    is_whole_country: bool = False,
    constraint_config: dict | None = None,
) -> tuple[ee.Image, ee.FeatureCollection]:
    """
    สร้าง raster mask สำหรับพื้นที่ที่ต้องกันออกจากการพัฒนา เช่น
    - WDPA protected areas
    - ป่าสงวน / ป่าอนุรักษ์ / ชั้นข้อมูลท้องถิ่นที่ผู้ใช้อัปโหลดเป็น GEE Asset

    ผลลัพธ์:
    - 1 = restricted / ห้ามหรือควรจำกัดการพัฒนา
    - 0 = ไม่ใช่พื้นที่กันออกจากชุดข้อมูลนี้
    """

    constraint_config = constraint_config or {}
    use_wdpa = bool(constraint_config.get("use_wdpa", True))
    asset_ids = constraint_config.get("asset_ids") or []
    buffer_m = float(constraint_config.get("buffer_m", 0) or 0)

    collections = []

    if use_wdpa:
        try:
            wdpa = (
                ee.FeatureCollection(get_dataset_id("wdpa_polygons"))
                .filterBounds(get_roi_geometry(roi))
            )
            collections.append(wdpa)
        except Exception:
            pass

    for asset_id in asset_ids:
        asset_id = str(asset_id).strip()
        if not asset_id:
            continue

        try:
            fc = ee.FeatureCollection(asset_id).filterBounds(get_roi_geometry(roi))
            collections.append(fc)
        except Exception:
            # ปล่อยให้ GEE raise ตอน evaluate/render ดีกว่าไม่ให้แอปล้มตั้งแต่สร้าง object
            pass

    protected_fc = _merge_feature_collections(collections)

    if buffer_m > 0:
        protected_fc = protected_fc.map(lambda f: f.buffer(buffer_m))

    protected_mask = (
        ee.Image(0)
        .byte()
        .paint(protected_fc, 1)
        .unmask(0)
        .rename("Protected_Forest_Constraint")
        .toInt()
    )

    protected_mask = safe_clip(protected_mask, roi, is_whole_country)

    return protected_mask, protected_fc


# ---------------------------------------------------------
# Build suitability model
# ---------------------------------------------------------
def build_suitability_model(
    roi,
    weights: dict | None = None,
    is_whole_country: bool = False,
    constraint_config: dict | None = None,
) -> dict:
    """
    สร้าง Suitability Model หลัก

    Returns:
        dict:
            raw_score
            final_class
            slope
            flood
            landcover
            urban
            water
            protected_constraint
            hard_restricted
    """

    weights = normalize_weights(weights)

    slope_score = get_slope_score(roi, is_whole_country)
    flood_score = get_flood_score(roi, is_whole_country)
    lc_score, esa_lc = get_landcover_score(roi, is_whole_country)
    urban_score = get_urban_score(roi, is_whole_country)
    water_score = get_water_proximity_score(roi, esa_lc, is_whole_country)
    protected_constraint, protected_fc = get_protected_area_constraint(
        roi=roi,
        is_whole_country=is_whole_country,
        constraint_config=constraint_config,
    )

    raw_score = (
        slope_score.multiply(weights["slope"])
        .add(flood_score.multiply(weights["flood"]))
        .add(lc_score.multiply(weights["landcover"]))
        .add(urban_score.multiply(weights["urban"]))
        .add(water_score.multiply(weights["water"]))
        .rename("Suitability_Raw_Score")
    )

    final_class = classify_weighted_score(raw_score)

    # Hard constraints:
    # - land cover score = 1 เช่น ป่า น้ำ เมืองเดิม พื้นที่ชุ่มน้ำ
    # - flood score = 1 เช่น ท่วมซ้ำมากกว่า 2 ครั้ง
    # - protected/forest reserve constraint = 1 เช่น อุทยาน ป่าสงวน ป่าอนุรักษ์ หรือชั้นข้อมูลที่ผู้ใช้กำหนด
    hard_restricted = (
        lc_score.eq(1)
        .Or(flood_score.eq(1))
        .Or(protected_constraint.eq(1))
        .rename("Hard_Restricted")
    )

    # ไม่ mask ทิ้ง แต่บังคับให้เป็น class 1 เพื่อให้เห็นเป็นสีแดงบนแผนที่
    final_class = (
        final_class
        .where(hard_restricted, 1)
        .rename("Urban_Suitability_Class")
        .toInt()
    )

    # ล็อก projection ของผลลัพธ์ให้คงที่ตาม ESA WorldCover
    # เพื่อให้การแสดงผลไม่ดูเปลี่ยนเมื่อ zoom in/out
    final_class = lock_display_projection(final_class, esa_lc, is_whole_country)
    raw_score = lock_display_projection(raw_score, esa_lc, is_whole_country)

    slope_score = lock_display_projection(slope_score, esa_lc, is_whole_country)
    flood_score = lock_display_projection(flood_score, esa_lc, is_whole_country)
    lc_score = lock_display_projection(lc_score, esa_lc, is_whole_country)
    urban_score = lock_display_projection(urban_score, esa_lc, is_whole_country)
    water_score = lock_display_projection(water_score, esa_lc, is_whole_country)
    protected_constraint = lock_display_projection(protected_constraint, esa_lc, is_whole_country)

    final_class = safe_clip(final_class, roi, is_whole_country)
    raw_score = safe_clip(raw_score, roi, is_whole_country)

    return {
        "weights": weights,
        "raw_score": raw_score,
        "final_class": final_class,
        "slope": slope_score,
        "flood": flood_score,
        "landcover": lc_score,
        "urban": urban_score,
        "water": water_score,
        "protected_constraint": protected_constraint,
        "protected_fc": protected_fc,
        "hard_restricted": hard_restricted,
    }


# ---------------------------------------------------------
# Area statistics
# ---------------------------------------------------------
def calculate_suitability_area_statistics(
    suitability_class: ee.Image,
    roi,
    is_whole_country: bool = False,
) -> tuple[pd.DataFrame, dict]:
    """
    คำนวณพื้นที่แต่ละระดับ suitability เป็นไร่
    """

    geometry = get_roi_geometry(roi)
    scale = 1000 if is_whole_country else 100

    area_rai = ee.Image.pixelArea().divide(1600).rename("area_rai")
    class_band = suitability_class.rename("class").toInt()

    grouped = (
        area_rai
        .addBands(class_band)
        .reduceRegion(
            reducer=ee.Reducer.sum().group(
                groupField=1,
                groupName="class",
            ),
            geometry=geometry,
            scale=scale,
            maxPixels=1e13,
            bestEffort=True,
            tileScale=4,
        )
        .getInfo()
    )

    groups = grouped.get("groups", []) if grouped else []

    rows = []

    for group in groups:
        class_id = int(group.get("class"))
        area = float(group.get("sum", 0))

        rows.append(
            {
                "ระดับ": class_id,
                "ความหมาย": CLASS_LABELS.get(class_id, "ไม่ทราบระดับ"),
                "พื้นที่ (ไร่)": round(area, 2),
                "สี": CLASS_COLORS.get(class_id, "#999999"),
            }
        )

    df = pd.DataFrame(rows)

    if df.empty:
        summary = {
            "total_rai": 0,
            "high_rai": 0,
            "very_high_rai": 0,
            "development_candidate_rai": 0,
            "restricted_rai": 0,
            "candidate_percent": 0,
        }

        return df, summary

    df = df.sort_values("ระดับ").reset_index(drop=True)

    total_rai = float(df["พื้นที่ (ไร่)"].sum())

    def area_of(class_id: int) -> float:
        matched = df.loc[df["ระดับ"] == class_id, "พื้นที่ (ไร่)"]
        if matched.empty:
            return 0.0
        return float(matched.iloc[0])

    high_rai = area_of(4)
    very_high_rai = area_of(5)
    development_candidate_rai = high_rai + very_high_rai
    restricted_rai = area_of(1)

    candidate_percent = (
        development_candidate_rai / total_rai * 100
        if total_rai > 0
        else 0
    )

    summary = {
        "total_rai": round(total_rai, 2),
        "high_rai": round(high_rai, 2),
        "very_high_rai": round(very_high_rai, 2),
        "development_candidate_rai": round(development_candidate_rai, 2),
        "restricted_rai": round(restricted_rai, 2),
        "candidate_percent": round(candidate_percent, 2),
    }

    return df, summary


def render_suitability_summary(df: pd.DataFrame, summary: dict) -> None:
    """
    แสดงผลสรุปใน Sidebar
    """

    st.sidebar.markdown("<hr style='border-color: #1E293B;'>", unsafe_allow_html=True)
    st.sidebar.markdown("### 📊 Suitability Summary")

    if df.empty:
        st.sidebar.warning("ไม่พบข้อมูลพื้นที่สำหรับคำนวณ Suitability")
        return

    st.sidebar.metric(
        "พื้นที่เหมาะสมสูง–สูงมาก",
        f"{summary.get('development_candidate_rai', 0):,.0f} ไร่",
        f"{summary.get('candidate_percent', 0):.1f}%",
    )

    st.sidebar.metric(
        "พื้นที่ควรหลีกเลี่ยง/จำกัด",
        f"{summary.get('restricted_rai', 0):,.0f} ไร่",
    )

    display_df = df[["ระดับ", "ความหมาย", "พื้นที่ (ไร่)"]].copy()
    st.sidebar.dataframe(display_df, use_container_width=True)


# ---------------------------------------------------------
# Add layers to map
# ---------------------------------------------------------
def add_suitability_layers(
    Map,
    roi,
    weights: dict | None = None,
    show_factors: bool = False,
    is_whole_country: bool = False,
    calculate_stats: bool = True,
    constraint_config: dict | None = None,
):
    """
    เพิ่ม Suitability Layer ลงบนแผนที่
    """

    with st.spinner("กำลังคำนวณ Suitability Analysis..."):
        result = build_suitability_model(
            roi=roi,
            weights=weights,
            is_whole_country=is_whole_country,
            constraint_config=constraint_config,
        )

        final_class = result["final_class"]

        Map.addLayer(
            final_class,
            SUITABILITY_VIS,
            "Urban Suitability Class",
            opacity=0.92,
        )

        st.info(
            "หมายเหตุ: แผนที่หลักคือ Urban Suitability Class เท่านั้น "
            "ถ้าเปิด Factor Layers สีที่เห็นจะเป็นการซ้อนหลายชั้นข้อมูล ไม่ควรใช้แทนผล final class"
        )

        add_custom_legend(
            Map=Map,
            title="Urban Suitability Score",
            legend_dict=SUITABILITY_LEGEND,
            position="bottomright",
        )

        if show_factors:
            Map.addLayer(
                result["slope"],
                SUITABILITY_VIS,
                "Factor: Slope Suitability",
                shown=False,
                opacity=0.35,
            )
            Map.addLayer(
                result["flood"],
                SUITABILITY_VIS,
                "Factor: Flood Suitability",
                shown=False,
                opacity=0.35,
            )
            Map.addLayer(
                result["landcover"],
                SUITABILITY_VIS,
                "Factor: Land Cover Suitability",
                shown=False,
                opacity=0.35,
            )
            Map.addLayer(
                result["urban"],
                SUITABILITY_VIS,
                "Factor: Urbanization Suitability",
                shown=False,
                opacity=0.35,
            )
            Map.addLayer(
                result["water"],
                SUITABILITY_VIS,
                "Factor: Water Proximity Suitability",
                shown=False,
                opacity=0.35,
            )
            Map.addLayer(
                result["protected_constraint"].selfMask(),
                {"min": 1, "max": 1, "palette": ["8b0000"]},
                "Hard Constraint: Protected / Forest Reserve",
                shown=False,
                opacity=0.70,
            )

        try:
            if calculate_stats or "suitability_stats_df" not in st.session_state:
                df, summary = calculate_suitability_area_statistics(
                    suitability_class=final_class,
                    roi=roi,
                    is_whole_country=is_whole_country,
                )

                st.session_state["suitability_stats_df"] = df
                st.session_state["suitability_summary"] = summary
            else:
                df = st.session_state.get("suitability_stats_df")
                summary = st.session_state.get("suitability_summary", {})

            if df is not None:
                render_suitability_summary(df, summary)

        except Exception as exc:
            st.sidebar.warning(f"คำนวณสรุปพื้นที่ Suitability ไม่สำเร็จ: {exc}")

    return Map


# ---------------------------------------------------------
# Methodology
# ---------------------------------------------------------
def render_suitability_methodology():
    """
    แสดงคำอธิบาย methodology ของ Suitability Analysis
    """

    with st.expander("📘 Methodology: Suitability Analysis", expanded=False):
        st.markdown(
            """
            โมเดลนี้เป็น **Development Suitability Analysis v1** สำหรับประเมินพื้นที่เหมาะสมต่อการพัฒนาเมืองใหม่หรือการขยายตัวของเมือง

            ### ปัจจัยที่ใช้

            #### 1. Slope Suitability
            พื้นที่ราบเหมาะต่อการพัฒนามากกว่า เพราะลดต้นทุนการปรับพื้นที่ งานดิน ฐานราก และความเสี่ยงดินถล่ม

            - 0–5° = 5 เหมาะสมมาก
            - 5–10° = 4
            - 10–15° = 3
            - 15–20° = 2
            - มากกว่า 20° = 1 ควรจำกัด

            #### 2. Flood Suitability
            พื้นที่ที่มีประวัติน้ำท่วมซ้ำจะถูกลดคะแนน

            - ไม่พบประวัติน้ำท่วม = 5
            - ท่วม 1–2 ครั้ง = 3
            - ท่วมมากกว่า 2 ครั้ง = 1 ควรจำกัด

            #### 3. Land Cover Compatibility
            ใช้ ESA WorldCover เพื่อประเมินความเข้ากันได้ของการใช้ที่ดิน

            - พุ่มไม้ / ดินโล่ง = คะแนนสูง
            - ทุ่งหญ้า = คะแนนค่อนข้างสูง
            - เกษตรกรรม = คะแนนปานกลาง เพราะมี trade-off ด้านความมั่นคงอาหาร
            - ป่า น้ำ พื้นที่ชุ่มน้ำ เมืองเดิม = คะแนนต่ำหรือควรจำกัด

            #### 4. Protected / Forest Reserve Constraint
            ชั้นข้อมูลพื้นที่คุ้มครอง เช่น WDPA, ป่าสงวน, ป่าอนุรักษ์ หรือชั้นข้อมูล GEE Asset ที่ผู้ใช้เพิ่ม จะถูกใช้เป็น **Hard Constraint** และบังคับเป็น class 1 เพื่อกันออกจากพื้นที่เสนอพัฒนา

            #### 5. Urbanization Suitability
            ใช้ GHSL SMOD เพื่อดูบริบทความเป็นเมือง

            - พื้นที่ชานเมืองหรือกึ่งเมืองได้คะแนนสูง
            - ศูนย์กลางเมืองหนาแน่นได้คะแนนต่ำ เพราะเป็นพื้นที่พัฒนาแล้ว
            - พื้นที่ชนบทมากได้คะแนนต่ำกว่า เพราะอาจขาดโครงสร้างพื้นฐาน

            #### 6. Water Proximity Suitability
            พื้นที่ใกล้น้ำในระยะเหมาะสมมีคุณค่าด้านภูมิทัศน์และ amenity แต่พื้นที่ชิดลำน้ำเกินไปควรจำกัด

            - 0–50 เมตร = 1 buffer/riparian zone
            - 50–1,000 เมตร = 5
            - 1,000–3,000 เมตร = 3
            - มากกว่า 3,000 เมตร = 2

            ### การรวมคะแนน

            ระบบรวมคะแนนด้วย weighted overlay:

            ```text
            Suitability Score =
            slope × weight
            + flood × weight
            + landcover × weight
            + urbanization × weight
            + water proximity × weight
            ```

            จากนั้น classify เป็น 5 ระดับ:

            - 1 = ควรหลีกเลี่ยง / จำกัดการพัฒนา
            - 2 = เหมาะสมน้อย
            - 3 = เหมาะสมปานกลาง / มีเงื่อนไข
            - 4 = เหมาะสมสูง
            - 5 = เหมาะสมสูงมาก

            ### ข้อจำกัด

            - Copernicus DEM เป็น DSM อาจรวมความสูงต้นไม้และอาคาร
            - ESA WorldCover อาจจำแนกสวนไม้ยืนต้นกับป่าธรรมชาติคลาดเคลื่อนในประเทศไทย
            - Global Flood Database ไม่เหมาะกับน้ำท่วมฉับพลันระดับชุมชนหรือระบบระบายน้ำเมือง
            - WDPA เป็นฐานข้อมูลระดับโลก จึงควรตรวจสอบซ้ำกับข้อมูลทางกฎหมายของไทย เช่น ป่าสงวนแห่งชาติ อุทยานแห่งชาติ เขตห้ามล่าสัตว์ป่า และพื้นที่ ส.ป.ก.
            - หากใช้ชั้นข้อมูลป่าสงวน/ป่าอนุรักษ์จากหน่วยงานไทย ควรอัปโหลดเป็น GEE Asset แล้วใส่ Asset ID ใน Sidebar
            - โมเดล v1 ยังไม่มี Road Accessibility ซึ่งควรเพิ่มใน v2
            - ผลลัพธ์นี้เป็น decision-support layer ไม่ใช่คำตัดสินทางกฎหมาย
            """
        )

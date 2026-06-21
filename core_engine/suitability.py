import streamlit as st
import ee


SUITABILITY_VIS = {
    "min": 1,
    "max": 5,
    "palette": [
        "#d7191c",  # very low
        "#fdae61",  # low
        "#ffffbf",  # moderate
        "#a6d96a",  # high
        "#1a9641",  # very high
    ],
}


def normalize_weights(weights: dict) -> dict:
    total = sum(weights.values())
    if total == 0:
        return weights
    return {k: v / total for k, v in weights.items()}


def get_slope_score(roi):
    dem = (
        ee.ImageCollection("COPERNICUS/DEM/GLO30")
        .select("DEM")
        .mosaic()
        .clip(roi)
    )

    slope = ee.Terrain.slope(dem)

    slope_score = (
        ee.Image(1)
        .where(slope.lt(20), 2)
        .where(slope.lt(15), 3)
        .where(slope.lt(10), 4)
        .where(slope.lt(5), 5)
        .rename("slope_suitability")
    )

    return slope_score


def get_flood_score(roi):
    flood_history = (
        ee.ImageCollection("GLOBAL_FLOOD_DB/MODIS_EVENTS/V1")
        .filterBounds(roi)
        .select("flooded")
        .sum()
        .clip(roi)
    )

    flood_score = (
        ee.Image(5)
        .where(flood_history.gt(0), 2)
        .where(flood_history.gt(2), 1)
        .rename("flood_suitability")
    )

    return flood_score


def get_landcover_score(roi):
    esa_lc = (
        ee.ImageCollection("ESA/WorldCover/v200")
        .first()
        .select("Map")
        .clip(roi)
    )

    lc_score = esa_lc.remap(
        [10, 20, 30, 40, 50, 60, 80, 90, 95],
        [1, 5, 4, 3, 1, 5, 1, 1, 1],
    ).rename("lc_suitability")

    return lc_score, esa_lc


def get_urban_score(roi):
    smod = (
        ee.Image("JRC/GHSL/P2023A/GHS_SMOD_V2-0/2030")
        .select("smod_code")
        .clip(roi)
    )

    urban_score = smod.remap(
        [10, 11, 12, 13, 21, 22, 23, 30],
        [1, 2, 3, 3, 5, 5, 4, 1],
    ).rename("urban_suitability")

    return urban_score


def get_water_proximity_score(roi, esa_lc):
    water_mask = esa_lc.eq(80)

    dist_to_water = (
        water_mask
        .Not()
        .fastDistanceTransform(5000)
        .sqrt()
        .multiply(30)
        .rename("distance_to_water")
    )

    water_score = (
        ee.Image(2)
        .where(dist_to_water.lt(3000), 3)
        .where(dist_to_water.lt(1000), 5)
        .where(dist_to_water.lt(50), 1)
        .rename("water_prox_suitability")
    )

    return water_score


def build_suitability_model(roi, weights: dict):
    weights = normalize_weights(weights)

    slope_score = get_slope_score(roi)
    flood_score = get_flood_score(roi)
    lc_score, esa_lc = get_landcover_score(roi)
    urban_score = get_urban_score(roi)
    water_score = get_water_proximity_score(roi, esa_lc)

    final_suitability = (
        slope_score.multiply(weights["slope"])
        .add(flood_score.multiply(weights["flood"]))
        .add(lc_score.multiply(weights["landcover"]))
        .add(urban_score.multiply(weights["urban"]))
        .add(water_score.multiply(weights["water"]))
        .rename("urban_suitability_score")
    )

    restricted_mask = (
        lc_score.neq(1)
        .And(flood_score.neq(1))
    )

    final_suitability_masked = final_suitability.updateMask(restricted_mask)

    return {
        "final": final_suitability_masked,
        "slope": slope_score,
        "flood": flood_score,
        "landcover": lc_score,
        "urban": urban_score,
        "water": water_score,
    }


def add_suitability_layers(Map, roi, weights, show_factors=False):
    with st.spinner("กำลังคำนวณ Suitability Analysis..."):
        result = build_suitability_model(roi, weights)

        Map.addLayer(
            result["final"],
            SUITABILITY_VIS,
            "Urban Suitability Score",
            opacity=0.75,
        )

        if show_factors:
            factor_vis = {
                "min": 1,
                "max": 5,
                "palette": ["#d7191c", "#fdae61", "#ffffbf", "#a6d96a", "#1a9641"],
            }

            Map.addLayer(result["slope"], factor_vis, "Factor: Slope Suitability", opacity=0.55)
            Map.addLayer(result["flood"], factor_vis, "Factor: Flood Suitability", opacity=0.55)
            Map.addLayer(result["landcover"], factor_vis, "Factor: Land Cover Suitability", opacity=0.55)
            Map.addLayer(result["urban"], factor_vis, "Factor: Urbanization Suitability", opacity=0.55)
            Map.addLayer(result["water"], factor_vis, "Factor: Water Proximity Suitability", opacity=0.55)

        try:
            Map.add_legend(
                title="Suitability Score",
                legend_dict={
                    "ต่ำมาก / ควรหลีกเลี่ยง": "d7191c",
                    "ต่ำ / ควรควบคุม": "fdae61",
                    "ปานกลาง / มีเงื่อนไข": "ffffbf",
                    "สูง / เหมาะสม": "a6d96a",
                    "สูงมาก / เหมาะสมมาก": "1a9641",
                },
            )
        except Exception:
            pass

    return Map


def render_suitability_methodology():
    with st.expander("📘 Methodology: Suitability Analysis"):
        st.markdown(
            """
            โมเดลนี้เป็น **Development Suitability Analysis v1** สำหรับประเมินพื้นที่เหมาะสมต่อการขยายเมืองหรือพัฒนาเมืองใหม่

            ### ปัจจัยที่ใช้

            1. **Slope Suitability**  
            พื้นที่ลาดชันต่ำเหมาะต่อการพัฒนามากกว่า เพราะลดต้นทุนงานดิน ฐานราก และความเสี่ยงดินถล่ม

            2. **Flood Suitability**  
            พื้นที่ที่มีประวัติน้ำท่วมบ่อยจะถูกลดคะแนน

            3. **Land Cover Compatibility**  
            พื้นที่โล่ง พุ่มไม้ หรือดินเปล่ามีคะแนนสูงกว่า ส่วนป่า น้ำ พื้นที่ชุ่มน้ำ และพื้นที่เมืองเดิมจะถูกจำกัด

            4. **Urbanization Suitability**  
            พื้นที่ชานเมืองหรือกึ่งเมืองมีคะแนนสูง เพราะมักใกล้โครงสร้างพื้นฐานเดิม

            5. **Water Proximity Suitability**  
            พื้นที่ใกล้น้ำในระยะเหมาะสมมีคุณค่าด้าน amenity แต่พื้นที่ชิดลำน้ำเกินไปถูกลดคะแนนเพราะเสี่ยงต่อ erosion และข้อจำกัด buffer

            ### ข้อจำกัดสำคัญ

            - Copernicus DEM เป็น DSM อาจรวมความสูงต้นไม้และอาคาร
            - ESA WorldCover อาจแยกสวนยาง/สวนผลไม้/ป่าธรรมชาติในไทยคลาดเคลื่อน
            - Global Flood Database ไม่เหมาะกับน้ำท่วมฉับพลันระดับซอยหรือระบบระบายน้ำเมือง
            - ยังไม่มี Road Accessibility ซึ่งควรเพิ่มจาก OSMnx หรือ road shapefile ในขั้นต่อไป
            """
        )

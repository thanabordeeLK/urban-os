from __future__ import annotations

import streamlit as st

from config.planning_standards_v2 import (
    CITY_SIZE_PROFILES,
    FUTURE_FACTORS_V2,
    PRESET_V2_WEIGHTS,
    classify_city_size,
    estimate_households_from_buildings,
    estimate_population_from_buildings,
    get_city_profile,
    get_city_size_label,
    get_objective_label,
    get_preset_v2_weights,
    normalize_weights,
)


def _try_count_gee_features(asset_id: str, roi) -> int | None:
    if not asset_id or roi is None:
        return None
    try:
        import ee

        geom = roi.geometry() if hasattr(roi, "geometry") else ee.Geometry(roi)
        return int(ee.FeatureCollection(asset_id).filterBounds(geom).size().getInfo())
    except Exception as exc:
        st.warning(f"นับจำนวนอาคารจาก GEE Asset ไม่สำเร็จ: {exc}")
        return None


def _try_count_postgis_features(table_name: str, geom_col: str, where_sql: str, roi) -> int | None:
    if not table_name:
        return None
    try:
        from services.spatial_db_service import count_postgis_features_by_roi

        return int(
            count_postgis_features_by_roi(
                table_name=table_name,
                geom_col=geom_col or "geom",
                where_sql=where_sql or "",
                roi=roi,
            )
        )
    except Exception as exc:
        st.warning(f"นับจำนวนอาคารจาก PostGIS ไม่สำเร็จ: {exc}")
        return None


def apply_preset_v2_to_session(weights: dict, city_profile: dict) -> None:
    key_map = {
        "slope": "suit_w_slope",
        "flood": "suit_w_flood",
        "landcover": "suit_w_landcover",
        "urban": "suit_w_urban",
        "road": "suit_w_road",
        "facility": "suit_w_facility",
        "heat": "suit_w_heat",
        "water": "suit_w_water",
    }
    for factor, widget_key in key_map.items():
        st.session_state[widget_key] = float(weights.get(factor, 0.0))

    st.session_state["suit_road_max_distance_m"] = int(city_profile.get("road_max_distance_m", 5000))
    st.session_state["suit_facility_max_distance_m"] = int(city_profile.get("facility_max_distance_m", 10000))
    st.session_state["planning_standard_v2_applied"] = True


def render_planning_standards_v2_panel(roi=None) -> dict:
    """
    Render Planning Standards Preset V2 inside Suitability sidebar.
    Returns selected profile metadata.
    """

    result = {}

    with st.expander("📘 Planning Standards Preset V2", expanded=False):
        st.caption(
            "เลือกเกณฑ์ตามขนาดเมืองและเป้าหมายการวิเคราะห์ ระบบจะตั้งค่าน้ำหนักเริ่มต้นให้อัตโนมัติ"
        )

        objective_options = list(PRESET_V2_WEIGHTS.keys())
        objective_label_map = {key: get_objective_label(key) for key in objective_options}

        objective_label = st.selectbox(
            "เป้าหมายการวิเคราะห์",
            list(objective_label_map.values()),
            index=0,
            key="v2_objective_label",
        )
        objective = next(key for key, label in objective_label_map.items() if label == objective_label)

        st.markdown("#### 🏙️ ประเมินขนาดเมือง")

        city_size_mode = st.radio(
            "วิธีเลือกขนาดเมือง",
            ["Auto จากจำนวนอาคาร/ครัวเรือน/ประชากร", "เลือกเอง"],
            index=0,
            key="v2_city_size_mode",
        )

        building_source = st.selectbox(
            "แหล่งข้อมูลจำนวนอาคาร",
            ["Manual", "GEE FeatureCollection", "PostGIS table"],
            index=0,
            key="v2_building_count_source",
        )

        building_count = int(st.session_state.get("v2_building_count", 0) or 0)

        if building_source == "Manual":
            building_count = int(
                st.number_input(
                    "จำนวนอาคารในขอบเขตพื้นที่",
                    min_value=0,
                    value=int(building_count or 0),
                    step=100,
                    key="v2_building_count_manual",
                )
            )
            st.session_state["v2_building_count"] = building_count

        elif building_source == "GEE FeatureCollection":
            asset_id = st.text_input(
                "GEE Asset ID อาคาร",
                value=st.session_state.get("v2_building_gee_asset_id", ""),
                key="v2_building_gee_asset_id",
                placeholder="projects/.../assets/buildings หรือ users/.../buildings",
            )
            if st.button("นับอาคารจาก GEE ตาม ROI", use_container_width=True, key="v2_count_buildings_gee"):
                count = _try_count_gee_features(asset_id, roi)
                if count is not None:
                    st.session_state["v2_building_count"] = count
                    building_count = count
                    st.success(f"นับอาคารได้ {count:,} หลัง/feature")

        else:
            col_a, col_b = st.columns(2)
            with col_a:
                table_name = st.text_input(
                    "PostGIS building table",
                    value=st.session_state.get("v2_building_db_table", "urban_os.buildings"),
                    key="v2_building_db_table",
                )
            with col_b:
                geom_col = st.text_input(
                    "Geometry column",
                    value=st.session_state.get("v2_building_db_geom_col", "geom"),
                    key="v2_building_db_geom_col",
                )
            where_sql = st.text_input(
                "Filter SQL",
                value=st.session_state.get("v2_building_db_where", ""),
                key="v2_building_db_where",
                placeholder="เช่น use_type IN ('residential','mixed_use')",
            )
            if st.button("นับอาคารจาก PostGIS ตาม ROI", use_container_width=True, key="v2_count_buildings_postgis"):
                count = _try_count_postgis_features(table_name, geom_col, where_sql, roi)
                if count is not None:
                    st.session_state["v2_building_count"] = count
                    building_count = count
                    st.success(f"นับอาคารได้ {count:,} หลัง/feature")

        household_per_building = st.number_input(
            "อัตราครัวเรือนต่ออาคาร",
            min_value=0.1,
            max_value=20.0,
            value=float(st.session_state.get("v2_household_per_building", 1.15)),
            step=0.05,
            key="v2_household_per_building",
            help="ค่าเริ่มต้นใช้ประมาณการเบื้องต้น สามารถปรับตามข้อมูลทะเบียน/สำรวจจริง",
        )

        persons_per_household = st.number_input(
            "คนต่อครัวเรือน",
            min_value=1.0,
            max_value=10.0,
            value=float(st.session_state.get("v2_persons_per_household", 2.7)),
            step=0.1,
            key="v2_persons_per_household",
        )

        estimated_households = estimate_households_from_buildings(building_count, household_per_building)
        estimated_population = estimate_population_from_buildings(
            building_count,
            household_per_building,
            persons_per_household,
        )

        registered_population = int(
            st.number_input(
                "ประชากรทะเบียนราษฎรในขอบเขตพื้นที่ ถ้ามี",
                min_value=0,
                value=int(st.session_state.get("v2_registered_population", 0) or 0),
                step=100,
                key="v2_registered_population",
                help="ถ้ามีข้อมูลจริง ให้ใส่ค่านี้ ระบบจะใช้แทนประชากรประมาณการ",
            )
        )

        population_for_class = registered_population if registered_population > 0 else estimated_population

        if city_size_mode == "เลือกเอง":
            city_size_label_map = {key: value["label_th"] for key, value in CITY_SIZE_PROFILES.items()}
            selected_label = st.selectbox(
                "เลือกขนาดเมือง",
                list(city_size_label_map.values()),
                index=0,
                key="v2_city_size_manual_label",
            )
            city_size = next(key for key, label in city_size_label_map.items() if label == selected_label)
        else:
            city_size = classify_city_size(
                building_count=building_count,
                household_count=estimated_households,
                population=population_for_class,
            )

        city_profile = get_city_profile(city_size)
        weights = get_preset_v2_weights(objective, city_size)
        norm_weights = normalize_weights(weights)

        st.markdown("#### 📊 ผลประเมินเบื้องต้น")
        c1, c2, c3 = st.columns(3)
        c1.metric("อาคาร", f"{building_count:,}")
        c2.metric("ครัวเรือนประมาณการ", f"{estimated_households:,}")
        c3.metric("ประชากรที่ใช้จัดชั้น", f"{population_for_class:,}")

        st.success(f"ขนาดเมืองที่ใช้: {get_city_size_label(city_size)}")
        st.caption(city_profile.get("density_note", ""))

        st.markdown("#### ⚖️ น้ำหนัก Preset V2 ที่จะนำไปใช้")
        st.json(norm_weights)

        st.markdown("#### 🔜 ปัจจัยที่ควรเพิ่มในขั้นถัดไป")
        st.caption(
            "แสดงเป็นข้อความธรรมดาเพื่อหลีกเลี่ยงปัญหา nested expander ของ Streamlit "
            "เพราะ panel นี้อยู่ภายใน expander หลักอยู่แล้ว"
        )
        for key, desc in FUTURE_FACTORS_V2.items():
            st.markdown(f"- **{key}**: {desc}")

        if st.button("📘 Apply Planning Standards Preset V2", use_container_width=True, key="apply_planning_standards_v2"):
            apply_preset_v2_to_session(weights, city_profile)
            st.session_state["planning_standard_v2_profile"] = {
                "objective": objective,
                "objective_label": get_objective_label(objective),
                "city_size": city_size,
                "city_size_label": get_city_size_label(city_size),
                "building_count": building_count,
                "estimated_households": estimated_households,
                "population_for_class": population_for_class,
                "weights": weights,
                "normalized_weights": norm_weights,
                "road_max_distance_m": city_profile.get("road_max_distance_m"),
                "facility_max_distance_m": city_profile.get("facility_max_distance_m"),
            }
            st.success("ใช้ Planning Standards Preset V2 แล้ว")
            st.rerun()

        result = {
            "objective": objective,
            "objective_label": get_objective_label(objective),
            "city_size": city_size,
            "city_size_label": get_city_size_label(city_size),
            "building_count": building_count,
            "estimated_households": estimated_households,
            "population_for_class": population_for_class,
            "weights": weights,
            "normalized_weights": norm_weights,
            "city_profile": city_profile,
        }

    return result

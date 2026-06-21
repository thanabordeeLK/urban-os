import streamlit as st
import geemap.foliumap as geemap
import ee
import folium
from streamlit_folium import st_folium


# ---------------------------------------------------------
# Basemap config แบบใช้ Tile URL ตรง
# ---------------------------------------------------------
BASEMAPS = {
    "OpenStreetMap": {
        "tiles": "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        "attr": "© OpenStreetMap contributors",
        "name": "OpenStreetMap",
    },
    "Esri Satellite": {
        "tiles": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        "attr": "Tiles © Esri — Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community",
        "name": "Esri Satellite",
    },
    "Esri Topographic": {
        "tiles": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}",
        "attr": "Tiles © Esri — Source: Esri, HERE, Garmin, FAO, NOAA, USGS",
        "name": "Esri Topographic",
    },
    "CartoDB Positron": {
        "tiles": "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
        "attr": "© OpenStreetMap contributors © CARTO",
        "name": "CartoDB Positron",
    },
    "CartoDB Dark": {
        "tiles": "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
        "attr": "© OpenStreetMap contributors © CARTO",
        "name": "CartoDB Dark",
    },
}


BASEMAP_ALIASES = {
    "OSM": "OpenStreetMap",
    "ROADMAP": "OpenStreetMap",
    "TERRAIN": "Esri Topographic",
    "SATELLITE": "Esri Satellite",
    "HYBRID": "Esri Satellite",
    "OpenStreetMap": "OpenStreetMap",
    "Esri Satellite": "Esri Satellite",
    "Esri Topographic": "Esri Topographic",
    "CartoDB Positron": "CartoDB Positron",
    "CartoDB Dark": "CartoDB Dark",
}


def resolve_basemap_name(basemap_choice: str) -> str:
    if not basemap_choice:
        return "OpenStreetMap"

    return BASEMAP_ALIASES.get(basemap_choice, "OpenStreetMap")


def add_custom_basemap(Map, basemap_choice: str):
    basemap_name = resolve_basemap_name(basemap_choice)
    basemap = BASEMAPS.get(basemap_name, BASEMAPS["OpenStreetMap"])

    try:
        folium.TileLayer(
            tiles=basemap["tiles"],
            attr=basemap["attr"],
            name=basemap["name"],
            overlay=False,
            control=False,
            show=True,
        ).add_to(Map)

    except Exception as e:
        st.warning(
            f"โหลด Basemap '{basemap_choice}' ไม่สำเร็จ "
            f"จึงใช้ OpenStreetMap แทน: {e}"
        )

        fallback = BASEMAPS["OpenStreetMap"]

        folium.TileLayer(
            tiles=fallback["tiles"],
            attr=fallback["attr"],
            name=fallback["name"],
            overlay=False,
            control=False,
            show=True,
        ).add_to(Map)

    return Map


def get_area_key(selected_province: str, selected_district: str) -> str:
    """
    ใช้ตรวจว่าผู้ใช้เปลี่ยนพื้นที่วิเคราะห์หรือไม่
    """
    return f"{selected_province}::{selected_district}"


def get_roi_center(roi):
    """
    ดึง centroid ของ ROI จาก Earth Engine แล้วแปลงเป็น lat/lon
    """

    try:
        if roi is None:
            return 15.87, 100.99

        geom = roi.geometry()
        centroid = geom.centroid(maxError=100)
        coords = centroid.coordinates().getInfo()

        lon = coords[0]
        lat = coords[1]

        return lat, lon

    except Exception as e:
        st.warning(f"ไม่สามารถคำนวณจุดกึ่งกลางพื้นที่ได้: {e}")
        return 15.87, 100.99


def get_roi_bounds(roi):
    """
    ดึง bounding box ของ ROI สำหรับใช้ fit_bounds

    Folium ต้องการรูปแบบ:
    [[south, west], [north, east]]
    """

    try:
        if roi is None:
            return None

        bounds_geom = roi.geometry().bounds(maxError=100)
        coords = bounds_geom.coordinates().getInfo()

        # coords ปกติจะเป็น polygon:
        # [[[lon, lat], [lon, lat], ...]]
        ring = coords[0]

        lons = [pt[0] for pt in ring]
        lats = [pt[1] for pt in ring]

        west = min(lons)
        east = max(lons)
        south = min(lats)
        north = max(lats)

        return [[south, west], [north, east]]

    except Exception as e:
        st.warning(f"ไม่สามารถคำนวณขอบเขตพื้นที่ได้: {e}")
        return None


def initialize_or_update_map_view(
    roi,
    is_whole_country: bool,
    selected_province: str,
    selected_district: str,
):
    """
    จัดการ center/zoom/bounds ของแผนที่

    หลักการ:
    - ถ้าเปลี่ยนจังหวัด/อำเภอ → fit bounds ให้ขอบเขตเต็มจอ
    - ถ้าแค่เปิด/ปิด layer → ใช้ตำแหน่งล่าสุด ไม่เด้งกลับ
    """

    area_key = get_area_key(selected_province, selected_district)
    previous_area_key = st.session_state.get("urban_os_area_key")
    area_changed = previous_area_key != area_key

    if area_changed or "urban_os_map_center" not in st.session_state:
        lat, lon = get_roi_center(roi)
        roi_bounds = get_roi_bounds(roi)

        if is_whole_country:
            zoom = 6
        else:
            zoom = 10

        st.session_state["urban_os_area_key"] = area_key
        st.session_state["urban_os_map_center"] = [lat, lon]
        st.session_state["urban_os_map_zoom"] = zoom
        st.session_state["urban_os_roi_bounds"] = roi_bounds
        st.session_state["urban_os_should_fit_bounds"] = True
    else:
        st.session_state["urban_os_should_fit_bounds"] = False

    center = st.session_state.get("urban_os_map_center", [15.87, 100.99])
    zoom = st.session_state.get("urban_os_map_zoom", 6)
    bounds = st.session_state.get("urban_os_roi_bounds")
    should_fit_bounds = st.session_state.get("urban_os_should_fit_bounds", False)

    return center, zoom, bounds, should_fit_bounds


def create_base_map(
    basemap_choice: str = "OpenStreetMap",
    roi=None,
    is_whole_country: bool = False,
    selected_province: str = "",
    selected_district: str = "",
):
    """
    สร้างแผนที่ฐาน

    จุดสำคัญ:
    - ถ้าเปลี่ยนพื้นที่ จะ fit bounds
    - ถ้าเปิด/ปิด layer จะรักษา viewport เดิม
    """

    center, zoom, bounds, should_fit_bounds = initialize_or_update_map_view(
        roi=roi,
        is_whole_country=is_whole_country,
        selected_province=selected_province,
        selected_district=selected_district,
    )

    Map = geemap.Map(
        location=center,
        zoom_start=zoom,
        ee_initialize=False,
        tiles=None,
    )

    add_custom_basemap(Map, basemap_choice)

    # fit ขอบเขตพื้นที่ให้เต็มจอ เฉพาะตอนเปลี่ยนพื้นที่เท่านั้น
    if should_fit_bounds and bounds is not None:
        try:
            Map.fit_bounds(bounds)
        except Exception:
            pass

    Map.basemap_choice = resolve_basemap_name(basemap_choice)
    Map.area_key = get_area_key(selected_province, selected_district)

    return Map


def add_boundary(Map, roi, is_whole_country: bool = False):
    """
    เพิ่มขอบเขตพื้นที่วิเคราะห์

    ไม่สั่ง center/zoom ที่นี่
    เพราะ create_base_map() จัดการ fit bounds แล้ว
    """

    try:
        if roi is None:
            st.warning("ไม่พบ ROI สำหรับพื้นที่ที่เลือก")
            return Map

        if not is_whole_country:
            boundary_style = roi.style(
                color="#00F2FE",
                fillColor="00000000",
                width=3,
            )

            Map.addLayer(
                boundary_style,
                {},
                "ขอบเขตพื้นที่วิเคราะห์",
            )

    except Exception as e:
        st.warning(f"ไม่สามารถแสดงขอบเขตพื้นที่ได้: {e}")

    return Map


def render_map(Map, height: int = 850):
    """
    แสดงผลแผนที่หลัก และบันทึกตำแหน่ง zoom/pan ล่าสุดไว้ใน session_state
    """

    with st.spinner("กำลังเรนเดอร์แผนที่..."):
        try:
            basemap_choice = getattr(Map, "basemap_choice", "OpenStreetMap")
            area_key = getattr(Map, "area_key", "default_area")

            # key เปลี่ยนเมื่อเปลี่ยนพื้นที่หรือเปลี่ยน basemap
            # แต่ไม่เปลี่ยนเมื่อเปิด/ปิด layer
            clean_basemap = basemap_choice.replace(" ", "_")
            clean_area_key = area_key.replace(" ", "_").replace("::", "_")

            map_key = f"urban_os_map_{clean_area_key}_{clean_basemap}"

            map_data = st_folium(
                Map,
                height=height,
                use_container_width=True,
                returned_objects=["center", "zoom"],
                key=map_key,
            )

            if map_data:
                center = map_data.get("center")
                zoom = map_data.get("zoom")

                if center and "lat" in center and "lng" in center:
                    st.session_state["urban_os_map_center"] = [
                        center["lat"],
                        center["lng"],
                    ]

                if zoom is not None:
                    st.session_state["urban_os_map_zoom"] = zoom

        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการโหลดแผนที่: {e}")

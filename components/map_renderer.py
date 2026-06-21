import streamlit as st
import geemap.foliumap as geemap
import ee
import folium
from streamlit_folium import st_folium


# ---------------------------------------------------------
# Basemap config แบบใช้ Tile URL ตรง
# เสถียรกว่า geemap.add_basemap บน Streamlit Cloud
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
    """
    แปลงชื่อ basemap จาก sidebar ให้เป็นชื่อที่ระบบรองรับจริง
    """
    if not basemap_choice:
        return "OpenStreetMap"

    return BASEMAP_ALIASES.get(basemap_choice, "OpenStreetMap")


def add_custom_basemap(Map, basemap_choice: str):
    """
    เพิ่ม basemap ด้วย folium.TileLayer โดยตรง
    """

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


def get_area_key(selected_province: str, selected_district: str) -> str:
    """
    สร้าง key สำหรับตรวจว่าผู้ใช้เปลี่ยนพื้นที่วิเคราะห์หรือไม่
    """
    return f"{selected_province}::{selected_district}"


def initialize_or_update_map_view(
    roi,
    is_whole_country: bool,
    selected_province: str,
    selected_district: str,
):
    """
    จัดการ center/zoom ของแผนที่

    หลักการ:
    - ถ้าเปลี่ยนจังหวัด/อำเภอ → center ไปพื้นที่ใหม่
    - ถ้าแค่เปิด/ปิด layer → ใช้ center/zoom ล่าสุด ไม่เด้งกลับ
    """

    area_key = get_area_key(selected_province, selected_district)

    previous_area_key = st.session_state.get("urban_os_area_key")

    area_changed = previous_area_key != area_key

    if area_changed or "urban_os_map_center" not in st.session_state:
        lat, lon = get_roi_center(roi)

        if is_whole_country:
            zoom = 6
        else:
            zoom = 10

        st.session_state["urban_os_area_key"] = area_key
        st.session_state["urban_os_map_center"] = [lat, lon]
        st.session_state["urban_os_map_zoom"] = zoom

    center = st.session_state.get("urban_os_map_center", [15.87, 100.99])
    zoom = st.session_state.get("urban_os_map_zoom", 6)

    return center, zoom


def create_base_map(
    basemap_choice: str = "OpenStreetMap",
    roi=None,
    is_whole_country: bool = False,
    selected_province: str = "",
    selected_district: str = "",
):
    """
    สร้างแผนที่ฐานแบบเสถียรสำหรับ Streamlit Cloud

    จุดสำคัญ:
    - ใช้ session_state เก็บ center/zoom
    - ไม่ reset viewport ทุกครั้งที่เปิดปิด layer
    """

    center, zoom = initialize_or_update_map_view(
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

    Map.basemap_choice = resolve_basemap_name(basemap_choice)

    return Map


def add_boundary(Map, roi, is_whole_country: bool = False):
    """
    เพิ่มขอบเขตพื้นที่วิเคราะห์

    หมายเหตุ:
    - ไม่สั่ง center/zoom ที่นี่แล้ว
    - เพราะ center/zoom ถูกจัดการใน create_base_map()
    - เพื่อป้องกันการเด้งกลับเวลาเปิดปิด layer
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

            # key ไม่ควรเปลี่ยนตาม layer checkbox
            # แต่เปลี่ยนตาม basemap เพื่อให้ basemap refresh ได้จริง
            map_key = f"urban_os_map_{basemap_choice.replace(' ', '_')}"

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

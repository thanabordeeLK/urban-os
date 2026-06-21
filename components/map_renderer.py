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


# เผื่อ sidebar หรือไฟล์เก่ายังส่งชื่อแบบเดิมมา
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
    ไม่ใช้ geemap.add_basemap() เพื่อลดปัญหา Streamlit Cloud ไม่เปลี่ยนแผนที่ฐาน
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


def create_base_map(basemap_choice: str = "OpenStreetMap"):
    """
    สร้างแผนที่ฐานแบบเสถียรสำหรับ Streamlit Cloud

    จุดสำคัญ:
    - ใช้ geemap.Map เพื่อให้ addLayer ของ Earth Engine ยังทำงานได้
    - แต่ basemap ใช้ folium.TileLayer ตรง เพื่อให้เปลี่ยน basemap ได้จริง
    """

    Map = geemap.Map(
        location=[15.87, 100.99],
        zoom_start=6,
        ee_initialize=False,
        tiles=None,
    )

    add_custom_basemap(Map, basemap_choice)

    # เก็บชื่อ basemap ไว้ใช้ทำ key ตอน render
    Map.basemap_choice = resolve_basemap_name(basemap_choice)

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


def add_boundary(Map, roi, is_whole_country: bool = False):
    """
    เพิ่มขอบเขตพื้นที่วิเคราะห์ และสั่ง zoom/center ไปยังพื้นที่นั้น
    """

    try:
        if roi is None:
            st.warning("ไม่พบ ROI สำหรับพื้นที่ที่เลือก")
            return Map

        lat, lon = get_roi_center(roi)

        if is_whole_country:
            zoom_level = 6
        else:
            zoom_level = 10

        # ใช้ location/zoom_start ของ folium โดยตรง
        Map.location = [lat, lon]
        Map.options["zoom"] = zoom_level

        try:
            Map.setCenter(lon, lat, zoom_level)
        except Exception:
            pass

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
    แสดงผลแผนที่หลัก

    ใช้ key ที่เปลี่ยนตาม basemap เพื่อบังคับให้ Streamlit/Folium render ใหม่จริง
    """

    with st.spinner("กำลังเรนเดอร์แผนที่..."):
        try:
            basemap_choice = getattr(Map, "basemap_choice", "OpenStreetMap")
            map_key = f"urban_os_map_{basemap_choice.replace(' ', '_')}"

            st_folium(
                Map,
                height=height,
                use_container_width=True,
                returned_objects=[],
                key=map_key,
            )

        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการโหลดแผนที่: {e}")

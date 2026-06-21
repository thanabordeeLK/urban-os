import streamlit as st
import geemap.foliumap as geemap
import ee
from streamlit_folium import st_folium


BASEMAP_ALIASES = {
    "OSM": "OpenStreetMap",
    "ROADMAP": "OpenStreetMap",
    "SATELLITE": "Esri.WorldImagery",
    "HYBRID": "Esri.WorldImagery",
    "TERRAIN": "Esri.WorldTopoMap",
    "OpenStreetMap": "OpenStreetMap",
    "Esri Satellite": "Esri.WorldImagery",
    "Esri WorldImagery": "Esri.WorldImagery",
    "Esri Topographic": "Esri.WorldTopoMap",
    "CartoDB Positron": "CartoDB.Positron",
    "CartoDB Dark": "CartoDB.DarkMatter",
}


def create_base_map(basemap_choice: str = "OSM"):
    """
    สร้างแผนที่ฐานแบบเสถียรสำหรับ Streamlit Cloud

    หมายเหตุ:
    - Google HYBRID / SATELLITE บางครั้งไม่เสถียรใน geemap + folium
    - จึง map ไปใช้ Esri.WorldImagery แทน
    """

    Map = geemap.Map(
        center=[15.87, 100.99],
        zoom=6,
        ee_initialize=False,
    )

    basemap_name = BASEMAP_ALIASES.get(basemap_choice, "OpenStreetMap")

    try:
        Map.add_basemap(basemap_name)
    except Exception as e:
        st.warning(f"โหลด Basemap '{basemap_choice}' ไม่สำเร็จ ใช้ OpenStreetMap แทน")
        Map.add_basemap("OpenStreetMap")

    return Map


def get_roi_center(roi):
    """
    ดึง centroid ของ ROI จาก Earth Engine แล้วแปลงเป็น lat/lon
    ใช้แทน Map.centerObject() เพื่อให้ Streamlit Cloud center ได้เสถียรกว่า
    """

    try:
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
            Map.setCenter(lon, lat, 6)
        else:
            Map.setCenter(lon, lat, 10)

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
    ปิด returned_objects เพื่อลดปัญหาจอดำและลด memory
    """

    with st.spinner("กำลังเรนเดอร์แผนที่..."):
        try:
            st_folium(
                Map,
                height=height,
                use_container_width=True,
                returned_objects=[],
            )
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการโหลดแผนที่: {e}")

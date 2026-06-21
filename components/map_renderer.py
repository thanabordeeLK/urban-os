import streamlit as st
import geemap.foliumap as geemap
import ee
from streamlit_folium import st_folium

from config.settings import DEFAULT_CENTER, DEFAULT_ZOOM


def create_base_map(basemap_choice: str):
    """สร้างแผนที่หลัก"""
    Map = geemap.Map(
        center=DEFAULT_CENTER,
        zoom=DEFAULT_ZOOM,
        ee_initialize=False,
    )
    Map.add_basemap(basemap_choice)
    return Map


def add_boundary(Map, roi, is_whole_country: bool) -> None:
    """เพิ่มขอบเขตพื้นที่วิเคราะห์บนแผนที่"""
    if not is_whole_country:
        Map.centerObject(roi)
        Map.addLayer(
            ee.Image().paint(roi, 0, 2),
            {"palette": ["00F2FE"]},
            "Boundary",
        )


def render_map(Map, height: int = 850) -> None:
    """
    แสดงแผนที่ด้วย streamlit-folium

    returned_objects=[] ช่วยลดการ sync object กลับมาใน Streamlit
    และช่วยลดอาการแผนที่ดำ/ค้างเมื่อ layer เยอะ
    """
    with st.spinner("กำลังเรนเดอร์แผนที่..."):
        try:
            st_folium(
                Map,
                height=height,
                use_container_width=True,
                returned_objects=[],
            )
        except Exception as exc:
            st.error(f"เกิดข้อผิดพลาดในการโหลดแผนที่: {exc}")

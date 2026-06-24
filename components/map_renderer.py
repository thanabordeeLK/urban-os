import streamlit as st
import geemap.foliumap as geemap
import folium
from streamlit_folium import st_folium
from html import escape
from branca.element import MacroElement, Template


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


# รองรับชื่อเก่าที่เคยใช้ใน sidebar
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


# ---------------------------------------------------------
# Basemap utilities
# ---------------------------------------------------------
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
    ไม่ใช้ geemap.add_basemap() เพื่อลดปัญหา Streamlit Cloud
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


# ---------------------------------------------------------
# ROI utilities
# ---------------------------------------------------------
def get_area_key(selected_province: str, selected_district: str) -> str:
    """
    ใช้ตรวจว่าผู้ใช้เปลี่ยนพื้นที่วิเคราะห์หรือไม่
    """
    province = selected_province or ""
    district = selected_district or ""
    return f"{province}::{district}"


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

        # กันกรณีขอบเขตเล็กผิดปกติ
        if west == east or south == north:
            return None

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

        zoom = 6 if is_whole_country else 10

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


# ---------------------------------------------------------
# Map creation
# ---------------------------------------------------------
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


# ---------------------------------------------------------
# Custom legend
# ---------------------------------------------------------
def add_custom_legend(
    Map,
    title: str,
    legend_dict: dict,
    position: str = "bottomright",
):
    """
    เพิ่ม legend แบบ HTML ผ่าน branca MacroElement
    วิธีนี้เสถียรกว่า folium.Element() บน Streamlit Cloud / st_folium

    Args:
        Map: folium/geemap map object
        title: ชื่อหัวข้อ legend
        legend_dict: {"ชื่อรายการ": "รหัสสี hex"}
        position: bottomright, bottomleft, topright, topleft
    """

    if not legend_dict:
        return Map

    position_styles = {
        "bottomright": "bottom: 28px; right: 18px;",
        "bottomleft": "bottom: 28px; left: 18px;",
        "topright": "top: 18px; right: 18px;",
        "topleft": "top: 18px; left: 18px;",
    }

    pos_style = position_styles.get(position, position_styles["bottomright"])

    rows = ""

    for label, color in legend_dict.items():
        safe_label = escape(str(label))
        safe_color = str(color).replace("#", "").strip()

        if not safe_color:
            safe_color = "999999"

        rows += f"""
        <div style="display:flex; align-items:center; margin-bottom:6px;">
            <span style="
                display:inline-block;
                width:18px;
                height:14px;
                min-width:18px;
                margin-right:8px;
                background-color:#{safe_color};
                border:1px solid #333333;
            "></span>
            <span style="
                color:#111111 !important;
                font-size:12px;
                font-weight:600;
                line-height:1.25;
                white-space:normal;
            ">
                {safe_label}
            </span>
        </div>
        """

    legend_html = f"""
    {{% macro html(this, kwargs) %}}

    <div id="urban-os-custom-legend" style="
        position: fixed;
        {pos_style}
        z-index: 999999;
        background-color: rgba(255,255,255,0.96);
        padding: 10px 12px;
        border: 1px solid #777777;
        border-radius: 8px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.35);
        max-width: 300px;
        max-height: 380px;
        overflow-y: auto;
        font-family: Arial, sans-serif;
    ">
        <div style="
            color:#000000 !important;
            font-weight:700;
            font-size:13px;
            margin-bottom:8px;
            border-bottom:1px solid #dddddd;
            padding-bottom:5px;
        ">
            {escape(title)}
        </div>

        {rows}
    </div>

    {{% endmacro %}}
    """

    try:
        legend = MacroElement()
        legend._template = Template(legend_html)
        Map.get_root().add_child(legend)

    except Exception as e:
        st.warning(f"ไม่สามารถเพิ่มคำอธิบายสัญลักษณ์ได้: {e}")

    return Map


# ---------------------------------------------------------
# Render map
# ---------------------------------------------------------
def render_map(Map, height: int = 850):
    """
    แสดงผลแผนที่หลัก และบันทึกตำแหน่ง zoom/pan ล่าสุดไว้ใน session_state
    """

    with st.spinner("กำลังเรนเดอร์แผนที่..."):
        try:
            basemap_choice = getattr(Map, "basemap_choice", "OpenStreetMap")
            area_key = getattr(Map, "area_key", "default_area")

            # key เปลี่ยนเมื่อเปลี่ยนพื้นที่ / basemap / analysis layer version
            # เดิม key ไม่เปลี่ยนตอนคำนวณ layer ใหม่ ทำให้ streamlit-folium บางครั้งยังแสดง map เก่า
            # จึงเพิ่ม refresh token เฉพาะเมื่อผู้ใช้กด Run หรือ config วิเคราะห์เปลี่ยน
            clean_basemap = basemap_choice.replace(" ", "_")
            clean_area_key = (
                area_key.replace(" ", "_")
                .replace("::", "_")
                .replace("/", "_")
                .replace("\\", "_")
            )

            map_refresh_token = st.session_state.get("urban_os_map_refresh_token", 0)
            map_key = f"urban_os_map_{clean_area_key}_{clean_basemap}_{map_refresh_token}"

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

import copy
import math

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
# Map scale / export helpers
# ---------------------------------------------------------
def estimate_leaflet_zoom_from_scale(
    scale_denominator: int | float | None,
    latitude: float = 15.0,
) -> int | None:
    """
    Approximate Leaflet/Web Mercator zoom from representative fraction.

    resolution(m/px) ≈ scale_denominator × 0.00028

    This is an export-planning approximation, not a legal cartographic scale guarantee.
    """

    try:
        denominator = float(scale_denominator or 0)
        lat = float(latitude or 0)
    except Exception:
        return None

    if denominator <= 0:
        return None

    target_resolution = denominator * 0.00028
    if target_resolution <= 0:
        return None

    earth_resolution_z0 = 156543.03392 * math.cos(math.radians(lat))
    if earth_resolution_z0 <= 0:
        earth_resolution_z0 = 156543.03392

    zoom = math.log2(earth_resolution_z0 / target_resolution)
    return int(max(0, min(22, round(zoom))))


def add_export_scale_overlay(Map, scale_label: str = "", paper_preset: str = ""):
    """
    Add a small visual export-scale label on the map.
    """

    if not scale_label or scale_label.startswith("Auto"):
        return Map

    try:
        safe_scale = escape(str(scale_label))
        safe_paper = escape(str(paper_preset or ""))

        html = f"""
        {{% macro html(this, kwargs) %}}
        <div style="
            position: fixed;
            left: 18px;
            bottom: 28px;
            z-index: 9999;
            background: rgba(255,255,255,0.92);
            color: #111;
            border: 1px solid rgba(0,0,0,0.25);
            border-radius: 8px;
            padding: 8px 10px;
            font-size: 12px;
            font-weight: 700;
            box-shadow: 0 2px 8px rgba(0,0,0,0.18);
        ">
            🧭 Export scale {safe_scale}
            <div style="font-size:11px; font-weight:500; margin-top:2px;">
                {safe_paper}
            </div>
        </div>
        {{% endmacro %}}
        """

        macro = MacroElement()
        macro._template = Template(html)
        Map.get_root().add_child(macro)
    except Exception:
        pass

    return Map


def clone_map_for_panel(Map):
    """
    Try to clone the map so comparison panes can have independent layer controls.
    """

    try:
        return copy.deepcopy(Map)
    except Exception:
        return Map


# ---------------------------------------------------------
# Map creation
# ---------------------------------------------------------
def create_base_map(
    basemap_choice: str = "OpenStreetMap",
    roi=None,
    is_whole_country: bool = False,
    selected_province: str = "",
    selected_district: str = "",
    target_scale_denominator: int | None = None,
    apply_scale_to_zoom: bool = False,
    export_scale_label: str = "",
    export_paper_preset: str = "",
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

    if apply_scale_to_zoom and target_scale_denominator:
        approx_zoom = estimate_leaflet_zoom_from_scale(
            target_scale_denominator,
            latitude=center[0] if center else 15.0,
        )
        if approx_zoom is not None:
            zoom = approx_zoom
            should_fit_bounds = False

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
    Map.export_scale_label = export_scale_label
    Map.export_paper_preset = export_paper_preset

    add_export_scale_overlay(
        Map,
        scale_label=export_scale_label,
        paper_preset=export_paper_preset,
    )

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
def render_map(Map, height: int = 850, key_suffix: str = "", panel_title: str = ""):
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
            suffix = str(key_suffix or "").replace(" ", "_").replace("/", "_")
            if suffix:
                map_key = f"urban_os_map_{clean_area_key}_{clean_basemap}_{map_refresh_token}_{suffix}"
            else:
                map_key = f"urban_os_map_{clean_area_key}_{clean_basemap}_{map_refresh_token}"

            if panel_title:
                st.markdown(f"**{panel_title}**")

            export_scale_label = getattr(Map, "export_scale_label", "")
            export_paper_preset = getattr(Map, "export_paper_preset", "")
            if export_scale_label and not str(export_scale_label).startswith("Auto"):
                st.caption(
                    f"🧭 Export scale target: {export_scale_label} "
                    f"{('· ' + export_paper_preset) if export_paper_preset else ''}"
                )

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



def render_map_workspace(Map, layout_config: dict | None = None):
    """
    Render map as 1 / 2 / 3 comparison panes.
    """

    layout_config = layout_config or {}
    pane_count = int(layout_config.get("pane_count", 1) or 1)
    pane_count = max(1, min(3, pane_count))
    height = int(layout_config.get("height", 850) or 850)

    if pane_count <= 1:
        render_map(Map, height=height, key_suffix="single")
        return

    st.info(
        "โหมดเปรียบเทียบแผนที่: แต่ละหน้าจอใช้ชุดชั้นข้อมูลเดียวกัน "
        "แต่สามารถเปิด/ปิด Layer Control ในแต่ละ pane แยกกัน เพื่อเทียบข้อมูลคนละชุดได้"
    )

    cols = st.columns(pane_count)

    for idx, col in enumerate(cols, start=1):
        with col:
            panel_map = clone_map_for_panel(Map)
            render_map(
                panel_map,
                height=height,
                key_suffix=f"compare_{idx}",
                panel_title=f"Map View {idx}",
            )

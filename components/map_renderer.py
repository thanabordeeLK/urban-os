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
# Workspace layer styles
# ---------------------------------------------------------
WORKSPACE_SCORE_VIS = {
    "min": 1,
    "max": 5,
    "palette": ["d7191c", "fdae61", "ffffbf", "a6d96a", "1a9641"],
}

WORKSPACE_RAW_SCORE_VIS = {
    "min": 1,
    "max": 5,
    "palette": ["d7191c", "fdae61", "ffffbf", "a6d96a", "1a9641"],
}

WORKSPACE_HEAT_RISK_VIS = {
    "min": 1,
    "max": 5,
    "palette": ["2c7bb6", "abd9e9", "ffffbf", "fdae61", "d7191c"],
}

WORKSPACE_LST_VIS = {
    "min": 22,
    "max": 45,
    "palette": ["08306b", "2171b5", "6baed6", "ffffbf", "fdae61", "f46d43", "a50026"],
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

# ---------------------------------------------------------
# Map View synchronization helpers
# ---------------------------------------------------------
def _normalize_sync_mode(sync_mode_label: str | None) -> str:
    mapping = {
        "ไม่ซิงก์": "off",
        "ซิงก์ตาม Map View 1": "master_1",
        "ซิงก์ตาม Map View 2": "master_2",
        "ซิงก์ตาม Map View 3": "master_3",
        "ซิงก์ทุก View (ล่าสุด)": "latest",
    }
    return mapping.get(sync_mode_label or "ไม่ซิงก์", "off")


def _sync_master_view_idx(sync_mode: str) -> int | None:
    if sync_mode == "master_1":
        return 1
    if sync_mode == "master_2":
        return 2
    if sync_mode == "master_3":
        return 3
    return None


def _center_to_list(center) -> list[float] | None:
    if isinstance(center, dict) and "lat" in center and "lng" in center:
        try:
            return [float(center["lat"]), float(center["lng"])]
        except Exception:
            return None

    if isinstance(center, (list, tuple)) and len(center) >= 2:
        try:
            return [float(center[0]), float(center[1])]
        except Exception:
            return None

    return None


def _viewport_changed(
    old_center,
    old_zoom,
    new_center,
    new_zoom,
    tolerance: float = 0.000001,
) -> bool:
    old_c = _center_to_list(old_center)
    new_c = _center_to_list(new_center)

    if old_c is None or new_c is None:
        return True

    if abs(old_c[0] - new_c[0]) > tolerance or abs(old_c[1] - new_c[1]) > tolerance:
        return True

    try:
        if old_zoom is None and new_zoom is not None:
            return True
        if old_zoom is not None and new_zoom is None:
            return True
        if old_zoom is not None and new_zoom is not None and int(old_zoom) != int(new_zoom):
            return True
    except Exception:
        return True

    return False


def _apply_viewport_to_map(Map, center=None, zoom=None, lock_zoom: bool = True):
    """
    Apply center/zoom to an existing Folium/geemap map before st_folium renders it.
    """

    center_list = _center_to_list(center)
    if center_list is not None:
        try:
            Map.location = center_list
        except Exception:
            pass
        try:
            Map.options["center"] = center_list
        except Exception:
            pass

    if lock_zoom and zoom is not None:
        try:
            zoom_int = int(zoom)
            Map.options["zoom"] = zoom_int
            Map.options["zoom_start"] = zoom_int
            Map.zoom_start = zoom_int
        except Exception:
            pass

    return Map


def _get_sync_config(layout_config: dict | None = None) -> dict:
    layout_config = layout_config or {}
    mode_label = layout_config.get("sync_mode_label", st.session_state.get("map_sync_mode_label", "ไม่ซิงก์"))
    sync_mode = _normalize_sync_mode(mode_label)

    return {
        "mode_label": mode_label,
        "mode": sync_mode,
        "master_view_idx": _sync_master_view_idx(sync_mode),
        "lock_zoom": bool(layout_config.get("sync_lock_zoom", st.session_state.get("map_sync_lock_zoom", True))),
    }


def _sync_should_write(view_idx: int | None, sync_config: dict) -> bool:
    if not view_idx:
        return False

    mode = sync_config.get("mode", "off")
    if mode == "off":
        return False

    if mode == "latest":
        return True

    master_idx = sync_config.get("master_view_idx")
    return master_idx == view_idx


def _sync_should_apply(view_idx: int | None, sync_config: dict) -> bool:
    if not view_idx:
        return False

    mode = sync_config.get("mode", "off")
    if mode == "off":
        return False

    center = st.session_state.get("map_sync_center")
    if center is None:
        return False

    if mode == "latest":
        return True

    # In master mode, do not force the master to its previous value;
    # let the master view be freely panned/zoomed and push its viewport to others.
    master_idx = sync_config.get("master_view_idx")
    return master_idx is not None and view_idx != master_idx


def _sync_apply_to_map(Map, view_idx: int | None, sync_config: dict):
    if not _sync_should_apply(view_idx, sync_config):
        return Map

    return _apply_viewport_to_map(
        Map,
        center=st.session_state.get("map_sync_center"),
        zoom=st.session_state.get("map_sync_zoom"),
        lock_zoom=bool(sync_config.get("lock_zoom", True)),
    )


def _sync_update_from_map_data(view_idx: int | None, sync_config: dict, map_data: dict | None):
    if not map_data or not _sync_should_write(view_idx, sync_config):
        return

    center = _center_to_list(map_data.get("center"))
    zoom = map_data.get("zoom")

    if center is None:
        return

    old_center = st.session_state.get("map_sync_center")
    old_zoom = st.session_state.get("map_sync_zoom")

    if _viewport_changed(old_center, old_zoom, center, zoom):
        st.session_state["map_sync_center"] = center
        st.session_state["map_sync_zoom"] = zoom
        st.session_state["map_sync_source_view"] = view_idx
        st.session_state["map_sync_token"] = int(st.session_state.get("map_sync_token", 0)) + 1


def render_map(
    Map,
    height: int = 850,
    key_suffix: str = "",
    panel_title: str = "",
    view_idx: int | None = None,
    sync_config: dict | None = None,
):
    """
    แสดงผลแผนที่หลัก และบันทึกตำแหน่ง zoom/pan ล่าสุดไว้ใน session_state
    """

    sync_config = sync_config or {"mode": "off"}

    with st.spinner("กำลังเรนเดอร์แผนที่..."):
        try:
            Map = _sync_apply_to_map(Map, view_idx=view_idx, sync_config=sync_config)

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
            if (sync_config or {}).get("mode") != "off":
                map_refresh_token = f"{map_refresh_token}_sync{st.session_state.get('map_sync_token', 0)}"
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
                    if view_idx:
                        st.session_state[f"map_view_{view_idx}_center"] = [
                            center["lat"],
                            center["lng"],
                        ]

                if zoom is not None:
                    st.session_state["urban_os_map_zoom"] = zoom
                    if view_idx:
                        st.session_state[f"map_view_{view_idx}_zoom"] = zoom

                _sync_update_from_map_data(
                    view_idx=view_idx,
                    sync_config=sync_config,
                    map_data=map_data,
                )

        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการโหลดแผนที่: {e}")





def _map_scale_options() -> list[str]:
    return [
        "Auto / ตาม zoom",
        "1 : 500",
        "1 : 1,000",
        "1 : 2,000",
        "1 : 5,000",
        "1 : 10,000",
        "1 : 25,000",
        "1 : 50,000",
        "1 : 100,000",
        "1 : 250,000",
    ]


def _scale_denominator(scale_label: str):
    return {
        "Auto / ตาม zoom": None,
        "1 : 500": 500,
        "1 : 1,000": 1000,
        "1 : 2,000": 2000,
        "1 : 5,000": 5000,
        "1 : 10,000": 10000,
        "1 : 25,000": 25000,
        "1 : 50,000": 50000,
        "1 : 100,000": 100000,
        "1 : 250,000": 250000,
    }.get(scale_label)



def _render_main_map_workspace_controls(layout_config: dict | None = None) -> dict:
    """
    Main-screen controls for workspace layout only.

    Export scale is controlled per Map View to avoid duplicate controls and to
    allow View 1 / View 2 / View 3 to use different scales.
    """

    layout_config = layout_config or {}

    st.markdown("### 🖥️ Map Workspace")
    with st.container():
        c1, c2, c3, c4 = st.columns([1.35, 1.0, 1.55, 2.0])

        pane_options = ["1 หน้าจอ", "2 หน้าจอ", "3 หน้าจอ"]
        current_pane_label = st.session_state.get("map_pane_count_label", "1 หน้าจอ")
        pane_index = pane_options.index(current_pane_label) if current_pane_label in pane_options else 0

        with c1:
            pane_label = st.radio(
                "จำนวน Map View",
                pane_options,
                index=pane_index,
                horizontal=True,
                key="map_pane_count_label",
            )

        with c2:
            height = st.number_input(
                "Map height",
                min_value=450,
                max_value=1200,
                value=int(st.session_state.get("map_panel_height", layout_config.get("height", 850)) or 850),
                step=50,
                key="map_panel_height",
            )

        with c3:
            sync_options = [
                "ไม่ซิงก์",
                "ซิงก์ตาม Map View 1",
                "ซิงก์ตาม Map View 2",
                "ซิงก์ตาม Map View 3",
                "ซิงก์ทุก View (ล่าสุด)",
            ]
            current_sync = st.session_state.get("map_sync_mode_label", "ไม่ซิงก์")
            sync_index = sync_options.index(current_sync) if current_sync in sync_options else 0
            sync_mode_label = st.selectbox(
                "🔒 Sync Map Views",
                sync_options,
                index=sync_index,
                key="map_sync_mode_label",
                help="ล็อกตำแหน่ง pan/zoom เพื่อเปรียบเทียบข้อมูลหลาย Map View ในพื้นที่เดียวกัน",
            )
            sync_lock_zoom = st.checkbox(
                "ล็อก zoom ด้วย",
                value=bool(st.session_state.get("map_sync_lock_zoom", True)),
                key="map_sync_lock_zoom",
            )

        with c4:
            source_view = st.session_state.get("map_sync_source_view")
            sync_center = st.session_state.get("map_sync_center")
            sync_zoom = st.session_state.get("map_sync_zoom")
            if sync_mode_label != "ไม่ซิงก์" and sync_center:
                st.caption(
                    f"Sync active · source View {source_view or '-'} · "
                    f"zoom {sync_zoom if sync_zoom is not None else '-'}"
                )
            else:
                st.caption(
                    "ปรับ Scale และการทำงาน/ผลวิเคราะห์ได้แยกกันในแต่ละ Map View ด้านล่าง"
                )

            if st.button("Reset Sync Viewport", key="reset_map_sync_viewport"):
                for key in [
                    "map_sync_center",
                    "map_sync_zoom",
                    "map_sync_source_view",
                    "map_sync_token",
                ]:
                    st.session_state.pop(key, None)
                st.success("Reset sync viewport แล้ว")

    pane_count = {"1 หน้าจอ": 1, "2 หน้าจอ": 2, "3 หน้าจอ": 3}.get(pane_label, 1)

    return {
        "pane_count": pane_count,
        "height": int(height),
        "sync_mode_label": sync_mode_label,
        "sync_lock_zoom": bool(sync_lock_zoom),
        # kept for backward compatibility only; not shown as top controls
        "paper_preset": st.session_state.get("map_export_paper_preset", "Screen / Dashboard"),
    }


def _workspace_layer_options() -> list[str]:
    return [
        "Current Mode Layers",
        "Boundary Only",
        "Suitability: Final Class",
        "Suitability: Raw Score",
        "Advanced: Population Capacity",
        "Advanced: Infrastructure Capacity",
        "Advanced: Service Coverage",
        "Advanced: Multi-Hazard Safety",
        "Advanced: Socioeconomic / Equity",
        "Advanced: Zoning / Legal Compliance",
        "UHI: Heat Risk",
        "UHI: Land Surface Temperature",
    ]


def _add_workspace_result_layer(Map, layer_choice: str):
    """
    Add one result/analysis layer from session_state to a specific Map View.
    """

    if layer_choice == "Suitability: Final Class":
        img = st.session_state.get("suitability_final_class")
        if img is not None:
            Map.addLayer(img, WORKSPACE_SCORE_VIS, "Suitability Final Class", opacity=0.92)
        else:
            st.warning("ยังไม่มี Suitability Final Class: กด Run Suitability Analysis ก่อน")

    elif layer_choice == "Suitability: Raw Score":
        img = st.session_state.get("suitability_raw_score")
        if img is not None:
            Map.addLayer(img, WORKSPACE_RAW_SCORE_VIS, "Suitability Raw Score", opacity=0.75)
        else:
            st.warning("ยังไม่มี Suitability Raw Score")

    elif layer_choice == "Advanced: Population Capacity":
        img = st.session_state.get("suitability_advanced_population_capacity")
        if img is not None:
            Map.addLayer(img, WORKSPACE_SCORE_VIS, "Population Capacity Score", opacity=0.75)
        else:
            st.info("ยังไม่มี layer Population Capacity แยกใน session นี้")

    elif layer_choice == "Advanced: Infrastructure Capacity":
        img = st.session_state.get("suitability_advanced_infrastructure_capacity")
        if img is not None:
            Map.addLayer(img, WORKSPACE_SCORE_VIS, "Infrastructure Capacity Score", opacity=0.75)
        else:
            st.info("ยังไม่มี layer Infrastructure Capacity แยกใน session นี้")

    elif layer_choice == "Advanced: Service Coverage":
        img = st.session_state.get("suitability_advanced_service_coverage")
        if img is not None:
            Map.addLayer(img, WORKSPACE_SCORE_VIS, "Service Coverage Score", opacity=0.75)
        else:
            st.info("ยังไม่มี layer Service Coverage แยกใน session นี้")

    elif layer_choice == "Advanced: Multi-Hazard Safety":
        img = st.session_state.get("suitability_advanced_multi_hazard")
        if img is not None:
            Map.addLayer(img, WORKSPACE_SCORE_VIS, "Multi-Hazard Safety Score", opacity=0.75)
        else:
            st.info("ยังไม่มี layer Multi-Hazard แยกใน session นี้")

    elif layer_choice == "Advanced: Socioeconomic / Equity":
        img = st.session_state.get("suitability_advanced_socioeconomic_equity")
        if img is not None:
            Map.addLayer(img, WORKSPACE_SCORE_VIS, "Socioeconomic / Equity Score", opacity=0.75)
        else:
            st.info("ยังไม่มี layer Socioeconomic / Equity แยกใน session นี้")

    elif layer_choice == "Advanced: Zoning / Legal Compliance":
        img = st.session_state.get("suitability_advanced_zoning_compliance")
        if img is not None:
            Map.addLayer(img, WORKSPACE_SCORE_VIS, "Zoning / Legal Compliance Score", opacity=0.75)
        else:
            st.info("ยังไม่มี layer Zoning / Legal Compliance แยกใน session นี้")

    elif layer_choice == "UHI: Heat Risk":
        img = st.session_state.get("suitability_heat_risk") or st.session_state.get("uhi_heat_risk")
        if img is not None:
            Map.addLayer(img, WORKSPACE_HEAT_RISK_VIS, "Heat Risk", opacity=0.75)
        else:
            st.warning("ยังไม่มี Heat Risk layer: รัน UHI หรือ Suitability Heat Penalty ก่อน")

    elif layer_choice == "UHI: Land Surface Temperature":
        img = st.session_state.get("suitability_heat_lst") or st.session_state.get("uhi_lst")
        if img is not None:
            Map.addLayer(img, WORKSPACE_LST_VIS, "Land Surface Temperature", opacity=0.75)
        else:
            st.warning("ยังไม่มี LST layer: รัน UHI ก่อน")

    return Map



def _apply_scale_to_existing_map(Map, scale_label: str, apply_scale: bool):
    """
    Apply an approximate zoom level to an already-built map.

    Needed for Current Mode Layers, because that pane clones the current mode map
    instead of rebuilding it from scratch.
    """

    if not apply_scale:
        return Map

    scale_denom = _scale_denominator(scale_label)
    if not scale_denom:
        return Map

    try:
        center = getattr(Map, "location", None) or st.session_state.get("urban_os_map_center", [15.0, 100.0])
        lat = center[0] if isinstance(center, (list, tuple)) and center else 15.0
        approx_zoom = estimate_leaflet_zoom_from_scale(scale_denom, latitude=lat)

        if approx_zoom is not None:
            try:
                Map.options["zoom"] = approx_zoom
            except Exception:
                pass
            try:
                Map.options["zoom_start"] = approx_zoom
            except Exception:
                pass
            try:
                Map.zoom_start = approx_zoom
            except Exception:
                pass
    except Exception:
        pass

    return Map


def _create_independent_view_map(
    *,
    original_map,
    view_config: dict,
    roi=None,
    is_whole_country: bool = False,
    selected_province: str = "",
    selected_district: str = "",
):
    """
    Build a map for one pane. If the pane uses Current Mode Layers, clone the
    original map. Otherwise create a fresh base map and add only the selected result layer.
    """

    layer_choice = view_config.get("layer_choice", "Current Mode Layers")
    scale_label = view_config.get("scale_label", "Auto / ตาม zoom")
    scale_denom = _scale_denominator(scale_label)
    apply_scale = bool(view_config.get("apply_scale_to_zoom", False))
    paper_preset = view_config.get("paper_preset", "Screen / Dashboard")
    basemap_choice = view_config.get("basemap_choice", getattr(original_map, "basemap_choice", "OpenStreetMap"))

    if layer_choice == "Current Mode Layers":
        panel_map = clone_map_for_panel(original_map)
        panel_map = _apply_scale_to_existing_map(
            panel_map,
            scale_label=scale_label,
            apply_scale=apply_scale,
        )
        panel_map.export_scale_label = scale_label
        panel_map.export_paper_preset = paper_preset
        add_export_scale_overlay(panel_map, scale_label=scale_label, paper_preset=paper_preset)
        return panel_map

    panel_map = create_base_map(
        basemap_choice=basemap_choice,
        roi=roi,
        is_whole_country=is_whole_country,
        selected_province=selected_province,
        selected_district=selected_district,
        target_scale_denominator=scale_denom,
        apply_scale_to_zoom=apply_scale,
        export_scale_label=scale_label,
        export_paper_preset=paper_preset,
    )

    add_boundary(panel_map, roi=roi, is_whole_country=is_whole_country)

    if layer_choice != "Boundary Only":
        _add_workspace_result_layer(panel_map, layer_choice)

    return panel_map


def _render_view_controls(
    *,
    idx: int,
    default_basemap: str,
    global_scale_label: str,
    global_paper_preset: str,
    global_apply_scale: bool,
) -> dict:
    """
    Controls displayed directly above each Map View.
    """

    st.markdown(f"#### Map View {idx}")

    c1, c2 = st.columns(2)
    with c1:
        layer_choice = st.selectbox(
            "การทำงาน / ผลวิเคราะห์",
            _workspace_layer_options(),
            index=0,
            key=f"map_view_{idx}_layer_choice",
            help="เลือกเฉพาะ Map View นี้ ไม่กระทบ Map View อื่น",
        )
        basemap_choice = st.selectbox(
            "Basemap",
            list(BASEMAPS.keys()),
            index=list(BASEMAPS.keys()).index(default_basemap) if default_basemap in BASEMAPS else 0,
            key=f"map_view_{idx}_basemap",
        )

    with c2:
        scale_options = _map_scale_options()
        scale_index = scale_options.index(global_scale_label) if global_scale_label in scale_options else 0
        scale_label = st.selectbox(
            "Scale ของ View นี้",
            scale_options,
            index=scale_index,
            key=f"map_view_{idx}_scale_label",
        )
        apply_scale = st.checkbox(
            "ใช้ scale นี้กับ zoom",
            value=bool(global_apply_scale),
            key=f"map_view_{idx}_apply_scale",
        )

    return {
        "layer_choice": layer_choice,
        "basemap_choice": basemap_choice,
        "scale_label": scale_label,
        "apply_scale_to_zoom": apply_scale,
        "paper_preset": global_paper_preset,
    }


def render_map_workspace(
    Map,
    layout_config: dict | None = None,
    *,
    roi=None,
    is_whole_country: bool = False,
    selected_province: str = "",
    selected_district: str = "",
):
    """
    Render map workspace with on-screen controls and independent pane content.

    - 1 / 2 / 3 Map Views are selectable directly above the maps.
    - Export scale can be changed directly above the maps.
    - Each Map View can choose its own analysis/result layer and basemap.
    """

    layout_config = _render_main_map_workspace_controls(layout_config)
    pane_count = int(layout_config.get("pane_count", 1) or 1)
    pane_count = max(1, min(3, pane_count))
    height = int(layout_config.get("height", 850) or 850)
    sync_config = _get_sync_config(layout_config)

    if pane_count > 1:
        if sync_config.get("mode") == "off":
            st.info(
                "เลือกการทำงาน/ผลวิเคราะห์ของแต่ละ Map View ได้แยกกัน เช่น View 1 = Suitability, "
                "View 2 = Heat Risk, View 3 = Boundary Only"
            )
        else:
            st.info(
                "Sync Map Views เปิดอยู่: เลื่อน/ซูม view ต้นแบบ แล้ว view อื่นจะตามตำแหน่งเดียวกันหลัง rerun"
            )

    cols = st.columns(pane_count)

    for idx, col in enumerate(cols, start=1):
        with col:
            view_config = _render_view_controls(
                idx=idx,
                default_basemap=getattr(Map, "basemap_choice", "OpenStreetMap"),
                global_scale_label=st.session_state.get(f"map_view_{idx}_scale_label", "1 : 2,000"),
                global_paper_preset=layout_config.get("paper_preset", "Screen / Dashboard"),
                global_apply_scale=bool(st.session_state.get(f"map_view_{idx}_apply_scale", True)),
            )
            panel_map = _create_independent_view_map(
                original_map=Map,
                view_config=view_config,
                roi=roi,
                is_whole_country=is_whole_country,
                selected_province=selected_province,
                selected_district=selected_district,
            )
            scale_key = str(view_config.get("scale_label", "")).replace(" ", "").replace(":", "_").replace(",", "")
            layer_key = str(view_config.get("layer_choice", "")).replace(" ", "_").replace("/", "_")
            basemap_key = str(view_config.get("basemap_choice", "")).replace(" ", "_")
            apply_key = "scale_on" if view_config.get("apply_scale_to_zoom") else "scale_off"

            sync_key = str(sync_config.get("mode", "off")).replace(" ", "_")
            render_map(
                panel_map,
                height=height,
                key_suffix=f"view_{idx}_{layer_key}_{basemap_key}_{scale_key}_{apply_key}_{sync_key}",
                view_idx=idx,
                sync_config=sync_config,
            )

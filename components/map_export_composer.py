from __future__ import annotations

import io
import json
import re
import tempfile
import zipfile
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any

import streamlit as st
import streamlit.components.v1 as components


WGS84_PRJ = """GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]]"""


def _safe_filename(value: str, default: str = "urban_os_export") -> str:
    value = str(value or default).strip()
    value = re.sub(r"[^0-9A-Za-zก-๙_\-]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or default


def _sanitize_field_name(name: str, existing: set[str]) -> str:
    """
    Shapefile DBF field names should be <= 10 chars.
    """

    base = re.sub(r"[^0-9A-Za-z_]+", "_", str(name or "field")).strip("_")
    if not base:
        base = "field"
    base = base[:10]

    candidate = base
    i = 1
    while candidate.lower() in existing:
        suffix = str(i)
        candidate = f"{base[:10-len(suffix)]}{suffix}"
        i += 1

    existing.add(candidate.lower())
    return candidate


def _infer_dbf_type(values: list[Any]) -> tuple[str, int, int]:
    """
    Returns pyshp field type, size, decimal.
    """

    clean = [v for v in values if v is not None]
    if not clean:
        return "C", 254, 0

    if all(isinstance(v, bool) for v in clean):
        return "L", 1, 0

    if all(isinstance(v, int) and not isinstance(v, bool) for v in clean):
        return "N", 18, 0

    if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in clean):
        return "F", 18, 6

    return "C", 254, 0


def _flatten_props(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return json.dumps(value, ensure_ascii=False)


def _iter_polygon_parts(geometry: dict) -> list[list[list[float]]]:
    """
    Convert GeoJSON Polygon / MultiPolygon into pyshp parts.
    pyshp expects parts as rings.
    """

    if not geometry:
        return []

    geom_type = geometry.get("type")
    coords = geometry.get("coordinates") or []

    parts: list[list[list[float]]] = []

    if geom_type == "Polygon":
        for ring in coords:
            if ring:
                parts.append(ring)

    elif geom_type == "MultiPolygon":
        for polygon in coords:
            for ring in polygon:
                if ring:
                    parts.append(ring)

    return parts


def _geojson_feature_collection_from_roi(roi) -> dict:
    """
    Convert current ROI to a GeoJSON FeatureCollection.
    """

    if roi is None:
        return {"type": "FeatureCollection", "features": []}

    try:
        geom = roi.geometry().getInfo() if hasattr(roi, "geometry") else roi.getInfo()
    except Exception:
        geom = None

    if not geom:
        return {"type": "FeatureCollection", "features": []}

    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": geom,
                "properties": {
                    "source": "roi_boundary",
                    "created_by": "Urban OS",
                },
            }
        ],
    }


def _load_candidate_geojson_from_session() -> dict | None:
    data = st.session_state.get("candidate_export_geojson_bytes")
    if not data:
        return None
    try:
        if isinstance(data, bytes):
            return json.loads(data.decode("utf-8"))
        if isinstance(data, str):
            return json.loads(data)
    except Exception:
        return None
    return None


def _geojson_to_bytes(geojson: dict) -> bytes:
    return json.dumps(geojson or {"type": "FeatureCollection", "features": []}, ensure_ascii=False, indent=2).encode("utf-8")


def _geojson_to_shapefile_zip_bytes(
    geojson: dict,
    *,
    layer_name: str = "urban_os_layer",
) -> tuple[bytes | None, str | None]:
    """
    Convert Polygon/MultiPolygon GeoJSON FeatureCollection to zipped Shapefile.

    Requires pyshp (`pip install pyshp`).
    """

    try:
        import shapefile  # pyshp
    except Exception as exc:
        return None, f"ไม่พบ library pyshp/shapefile: {exc}"

    features = (geojson or {}).get("features", []) or []
    polygon_features = []
    for feat in features:
        geom = feat.get("geometry") or {}
        if geom.get("type") in {"Polygon", "MultiPolygon"}:
            polygon_features.append(feat)

    if not polygon_features:
        return None, "ไม่มี Polygon/MultiPolygon สำหรับสร้าง Shapefile"

    # Collect fields
    prop_keys = []
    for feat in polygon_features:
        for key in (feat.get("properties") or {}).keys():
            if key not in prop_keys:
                prop_keys.append(key)

    if not prop_keys:
        prop_keys = ["name"]

    field_name_map = {}
    used_names: set[str] = set()
    for key in prop_keys:
        field_name_map[key] = _sanitize_field_name(key, used_names)

    safe_layer = _safe_filename(layer_name)

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        shp_base = tmp / safe_layer

        writer = shapefile.Writer(str(shp_base), shapeType=shapefile.POLYGON)
        writer.autoBalance = 1

        for key in prop_keys:
            values = [_flatten_props((feat.get("properties") or {}).get(key)) for feat in polygon_features]
            f_type, size, decimal = _infer_dbf_type(values)
            writer.field(field_name_map[key], f_type, size=size, decimal=decimal)

        for feat in polygon_features:
            geom = feat.get("geometry") or {}
            parts = _iter_polygon_parts(geom)
            if not parts:
                continue

            writer.poly(parts)

            props = feat.get("properties") or {}
            row = []
            for key in prop_keys:
                value = _flatten_props(props.get(key))
                if value is None:
                    value = ""
                row.append(value)
            writer.record(*row)

        writer.close()

        (tmp / f"{safe_layer}.prj").write_text(WGS84_PRJ, encoding="utf-8")
        (tmp / f"{safe_layer}.cpg").write_text("UTF-8", encoding="utf-8")
        (tmp / f"{safe_layer}_field_mapping.json").write_text(
            json.dumps(field_name_map, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as z:
            for file in tmp.iterdir():
                z.write(file, file.name)

        return zip_buf.getvalue(), None


def _render_html_export(Map, base_name: str) -> None:
    try:
        html = Map.get_root().render()
        st.download_button(
            "⬇️ Export Current Interactive Map HTML",
            data=html.encode("utf-8"),
            file_name=f"{base_name}_interactive_map.html",
            mime="text/html",
            use_container_width=True,
        )
    except Exception as exc:
        st.warning(f"ไม่สามารถสร้าง HTML map ได้: {exc}")


def _workspace_summary_markdown(
    *,
    selected_province: str,
    selected_district: str,
    is_whole_country: bool,
) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pane_label = st.session_state.get("map_pane_count_label", "1 หน้าจอ")
    height = st.session_state.get("map_panel_height", "")

    lines = [
        "# Urban OS Map Workspace Export Summary",
        "",
        f"Generated: {now}",
        "",
        "## Area",
        f"- Province: `{selected_province}`",
        f"- District: `{selected_district}`",
        f"- Whole country: `{is_whole_country}`",
        "",
        "## Layout",
        f"- Map Views: `{pane_label}`",
        f"- Map height: `{height}`",
        f"- Sync mode: `{st.session_state.get('map_sync_mode_label', 'ไม่ซิงก์')}`",
        f"- Sync lock zoom: `{st.session_state.get('map_sync_lock_zoom', True)}`",
        f"- Sync source view: `{st.session_state.get('map_sync_source_view', '')}`",
        "",
        "## Map View Settings",
    ]

    for idx in [1, 2, 3]:
        lines.extend(
            [
                f"### Map View {idx}",
                f"- Layer / analysis: `{st.session_state.get(f'map_view_{idx}_layer_choice', '')}`",
                f"- Basemap: `{st.session_state.get(f'map_view_{idx}_basemap', '')}`",
                f"- Target export scale: `{st.session_state.get(f'map_view_{idx}_scale_label', '')}`",
                f"- Current actual scale: `{st.session_state.get(f'map_view_{idx}_actual_scale_label', '')}`",
                f"- Current zoom: `{st.session_state.get(f'map_view_{idx}_zoom', '')}`",
                f"- Apply target scale to zoom: `{st.session_state.get(f'map_view_{idx}_apply_scale', '')}`",
                "",
            ]
        )

    lines.extend(
        [
            "## Notes",
            "- Web-map scale is approximate and depends on browser, DPI and export size.",
            "- For official cartographic production, verify scale again in QGIS/ArcGIS layout.",
        ]
    )

    return "\n".join(lines)




# ---------------------------------------------------------
# Print Layout Composer helpers
# ---------------------------------------------------------
PRINT_LAYOUT_PRESETS = {
    "Dashboard 16:9": {"png_size": (1920, 1080), "pdf": "A4"},
    "A4 Landscape": {"png_size": (1754, 1240), "pdf": "A4"},
    "A3 Landscape": {"png_size": (2480, 1754), "pdf": "A3"},
    "A1 Landscape": {"png_size": (3508, 2480), "pdf": "A1"},
}


def _get_visible_pane_count() -> int:
    pane_label = st.session_state.get("map_pane_count_label", "1 หน้าจอ")
    return {"1 หน้าจอ": 1, "2 หน้าจอ": 2, "3 หน้าจอ": 3}.get(pane_label, 1)


def _get_print_view_settings(max_views: int | None = None) -> list[dict]:
    max_views = max_views or _get_visible_pane_count()
    rows = []
    for idx in range(1, max_views + 1):
        rows.append(
            {
                "idx": idx,
                "layer": st.session_state.get(f"map_view_{idx}_layer_choice", "Current Mode Layers"),
                "basemap": st.session_state.get(f"map_view_{idx}_basemap", ""),
                "target_scale": st.session_state.get(f"map_view_{idx}_scale_label", ""),
                "actual_scale": st.session_state.get(f"map_view_{idx}_actual_scale_label", ""),
                "zoom": st.session_state.get(f"map_view_{idx}_zoom", ""),
                "apply_scale": st.session_state.get(f"map_view_{idx}_apply_scale", ""),
            }
        )
    return rows


def _build_print_layout_html(
    *,
    title: str,
    subtitle: str,
    selected_province: str,
    selected_district: str,
    is_whole_country: bool,
    preset: str,
    notes: str,
    include_north_arrow: bool = True,
    include_scale_note: bool = True,
    include_legend: bool = True,
) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    views = _get_print_view_settings()

    view_cards = ""
    for view in views:
        view_cards += f"""
        <section class="map-card">
            <div class="map-title">Map View {view['idx']}</div>
            <div class="map-placeholder">
                <div class="placeholder-title">Map View {view['idx']}</div>
                <div class="placeholder-sub">Use the interactive map / exported HTML for live tiles</div>
            </div>
            <table class="meta">
                <tr><th>Analysis Layer</th><td>{view['layer']}</td></tr>
                <tr><th>Basemap</th><td>{view['basemap']}</td></tr>
                <tr><th>Target scale</th><td>{view['target_scale']}</td></tr>
                <tr><th>Current actual</th><td>{view['actual_scale'] or '-'}</td></tr>
                <tr><th>Zoom</th><td>{view['zoom'] or '-'}</td></tr>
            </table>
        </section>
        """

    north = '<div class="north">▲<br>N</div>' if include_north_arrow else ""
    scale_note = '<div class="scale-note">Scale values are approximate web-map scales. Verify in GIS layout for official use.</div>' if include_scale_note else ""
    legend = """
    <div class="legend">
        <b>Suitability / Score Legend</b>
        <div><span style="background:#d7191c"></span> 1 Very Low / Restricted</div>
        <div><span style="background:#fdae61"></span> 2 Low</div>
        <div><span style="background:#ffffbf"></span> 3 Moderate</div>
        <div><span style="background:#a6d96a"></span> 4 High</div>
        <div><span style="background:#1a9641"></span> 5 Very High</div>
    </div>
    """ if include_legend else ""

    return f"""<!doctype html>
<html lang="th">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
@page {{
  size: landscape;
  margin: 12mm;
}}
* {{
  box-sizing: border-box;
}}
body {{
  margin: 0;
  font-family: Arial, "Noto Sans Thai", sans-serif;
  color: #172033;
  background: #eef3f7;
}}
.sheet {{
  width: 100%;
  min-height: 100vh;
  background: white;
  padding: 22px;
  position: relative;
}}
.header {{
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 16px;
  border-bottom: 3px solid #00bcd4;
  padding-bottom: 12px;
  margin-bottom: 14px;
}}
h1 {{
  margin: 0;
  font-size: 28px;
  color: #0b3040;
}}
.subtitle {{
  margin-top: 5px;
  color: #4d5b68;
  font-size: 14px;
}}
.badge {{
  border: 1px solid #b9d8e2;
  border-radius: 8px;
  padding: 8px 12px;
  background: #f6fbfd;
  font-size: 12px;
  min-width: 230px;
}}
.grid {{
  display: grid;
  grid-template-columns: repeat({max(1, len(views))}, 1fr);
  gap: 12px;
}}
.map-card {{
  border: 1px solid #d9e2ec;
  border-radius: 10px;
  overflow: hidden;
  background: #ffffff;
}}
.map-title {{
  font-weight: 700;
  padding: 8px 10px;
  background: #0b3040;
  color: #ffffff;
}}
.map-placeholder {{
  height: 360px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  color: #31515e;
  background:
    linear-gradient(90deg, rgba(20,140,160,.11) 1px, transparent 1px),
    linear-gradient(rgba(20,140,160,.11) 1px, transparent 1px),
    linear-gradient(135deg, #e5f3f7, #f6fafc);
  background-size: 80px 80px, 80px 80px, auto;
}}
.placeholder-title {{
  font-size: 22px;
  font-weight: 700;
}}
.placeholder-sub {{
  font-size: 12px;
  margin-top: 6px;
}}
.meta {{
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}}
.meta th {{
  width: 36%;
  text-align: left;
  background: #f4f7fa;
  border-top: 1px solid #e5edf2;
  padding: 6px 8px;
}}
.meta td {{
  border-top: 1px solid #e5edf2;
  padding: 6px 8px;
}}
.footer {{
  margin-top: 14px;
  display: grid;
  grid-template-columns: 1fr 280px;
  gap: 16px;
  font-size: 12px;
  color: #4d5b68;
}}
.legend {{
  border: 1px solid #d9e2ec;
  border-radius: 8px;
  padding: 8px;
  background: #f8fbfc;
}}
.legend span {{
  display: inline-block;
  width: 18px;
  height: 10px;
  border: 1px solid #888;
  margin-right: 6px;
}}
.north {{
  position: absolute;
  top: 105px;
  right: 28px;
  text-align: center;
  font-size: 22px;
  font-weight: 800;
  color: #0b3040;
}}
.scale-note {{
  margin-top: 8px;
  font-style: italic;
}}
.notes {{
  white-space: pre-wrap;
}}
@media print {{
  body {{ background: white; }}
  .sheet {{ box-shadow: none; }}
}}
</style>
</head>
<body>
<div class="sheet">
  {north}
  <div class="header">
    <div>
      <h1>{title}</h1>
      <div class="subtitle">{subtitle}</div>
    </div>
    <div class="badge">
      <b>Urban OS Print Layout</b><br>
      Preset: {preset}<br>
      Province: {selected_province or '-'}<br>
      District: {selected_district or '-'}<br>
      Whole country: {is_whole_country}<br>
      Generated: {now}
    </div>
  </div>

  <div class="grid">
    {view_cards}
  </div>

  <div class="footer">
    <div>
      <b>Notes</b>
      <div class="notes">{notes or 'Generated from Urban OS Map Workspace.'}</div>
      {scale_note}
    </div>
    {legend}
  </div>
</div>
</body>
</html>"""


def _build_print_layout_png_bytes(
    *,
    title: str,
    subtitle: str,
    selected_province: str,
    selected_district: str,
    preset: str,
    notes: str,
) -> tuple[bytes | None, str | None]:
    """
    Create a static PNG print-layout summary.

    This is a server-side layout export and intentionally avoids browser screenshot
    dependencies. Use HTML export if you need live map tiles.
    """

    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception as exc:
        return None, f"ไม่พบ Pillow สำหรับสร้าง PNG: {exc}"

    size = PRINT_LAYOUT_PRESETS.get(preset, PRINT_LAYOUT_PRESETS["A4 Landscape"])["png_size"]
    width, height = size

    img = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(img)

    try:
        font_title = ImageFont.truetype("DejaVuSans-Bold.ttf", max(28, width // 55))
        font_h = ImageFont.truetype("DejaVuSans-Bold.ttf", max(18, width // 85))
        font = ImageFont.truetype("DejaVuSans.ttf", max(14, width // 110))
        font_small = ImageFont.truetype("DejaVuSans.ttf", max(11, width // 145))
    except Exception:
        font_title = font_h = font = font_small = ImageFont.load_default()

    margin = int(width * 0.035)
    y = margin

    draw.text((margin, y), title or "Urban OS Print Layout", fill="#0b3040", font=font_title)
    y += int(width * 0.035)
    draw.text((margin, y), subtitle or "Map Workspace Export", fill="#4d5b68", font=font)
    y += int(width * 0.035)

    # Header line
    draw.line((margin, y, width - margin, y), fill="#00bcd4", width=max(3, width // 500))
    y += int(width * 0.02)

    pane_count = _get_visible_pane_count()
    views = _get_print_view_settings(pane_count)

    gap = int(width * 0.015)
    card_w = int((width - margin * 2 - gap * (pane_count - 1)) / pane_count)
    card_h = int(height * 0.54)
    card_y = y

    for view in views:
        idx = view["idx"]
        x = margin + (idx - 1) * (card_w + gap)

        draw.rounded_rectangle(
            (x, card_y, x + card_w, card_y + card_h),
            radius=18,
            outline="#d9e2ec",
            width=2,
            fill="#ffffff",
        )
        draw.rectangle((x, card_y, x + card_w, card_y + int(card_h * 0.095)), fill="#0b3040")
        draw.text((x + 14, card_y + 12), f"Map View {idx}", fill="white", font=font_h)

        ph_y = card_y + int(card_h * 0.095)
        ph_h = int(card_h * 0.57)
        draw.rectangle((x + 1, ph_y, x + card_w - 1, ph_y + ph_h), fill="#e5f3f7")

        # grid imitation
        grid_step = max(45, card_w // 5)
        for gx in range(x + grid_step, x + card_w, grid_step):
            draw.line((gx, ph_y, gx, ph_y + ph_h), fill="#c9e2e8", width=1)
        for gy in range(ph_y + grid_step, ph_y + ph_h, grid_step):
            draw.line((x, gy, x + card_w, gy), fill="#c9e2e8", width=1)

        draw.text(
            (x + 18, ph_y + ph_h // 2 - 12),
            "Map placeholder / use HTML for live tiles",
            fill="#31515e",
            font=font,
        )

        meta_y = ph_y + ph_h + 18
        meta_lines = [
            f"Layer: {view['layer']}",
            f"Basemap: {view['basemap']}",
            f"Target: {view['target_scale']}",
            f"Current: {view['actual_scale'] or '-'}",
            f"Zoom: {view['zoom'] or '-'}",
        ]
        for line in meta_lines:
            draw.text((x + 14, meta_y), line[:90], fill="#172033", font=font_small)
            meta_y += int(width * 0.014)

    y = card_y + card_h + int(width * 0.025)
    info_lines = [
        f"Area: {selected_province or '-'} / {selected_district or '-'}",
        f"Preset: {preset}",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "Scale values are approximate web-map scales. Verify in GIS layout for official use.",
    ]
    if notes:
        info_lines.append(f"Notes: {notes[:180]}")

    for line in info_lines:
        draw.text((margin, y), line, fill="#4d5b68", font=font_small)
        y += int(width * 0.014)

    # north arrow
    draw.text((width - margin - 55, margin + 8), "▲\nN", fill="#0b3040", font=font_h)

    out = io.BytesIO()
    img.save(out, format="PNG", optimize=True)
    return out.getvalue(), None


def _build_print_layout_pdf_bytes(
    *,
    title: str,
    subtitle: str,
    selected_province: str,
    selected_district: str,
    preset: str,
    notes: str,
) -> tuple[bytes | None, str | None]:
    """
    Create a static PDF print-layout summary.

    Use HTML export when users need live web-map tiles.
    """

    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A1, A3, A4, landscape
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas
    except Exception as exc:
        return None, f"ไม่พบ ReportLab สำหรับสร้าง PDF: {exc}"

    page_size_map = {
        "Dashboard 16:9": landscape(A4),
        "A4 Landscape": landscape(A4),
        "A3 Landscape": landscape(A3),
        "A1 Landscape": landscape(A1),
    }
    page_size = page_size_map.get(preset, landscape(A4))
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=page_size)

    width, height = page_size
    margin = 14 * mm
    y = height - margin

    c.setFillColor(colors.HexColor("#0b3040"))
    c.setFont("Helvetica-Bold", 18)
    c.drawString(margin, y, (title or "Urban OS Print Layout")[:90])
    y -= 8 * mm

    c.setFillColor(colors.HexColor("#4d5b68"))
    c.setFont("Helvetica", 9)
    c.drawString(margin, y, (subtitle or "Map Workspace Export")[:120])

    c.setStrokeColor(colors.HexColor("#00bcd4"))
    c.setLineWidth(2)
    c.line(margin, y - 5 * mm, width - margin, y - 5 * mm)
    y -= 14 * mm

    views = _get_print_view_settings()
    pane_count = max(1, len(views))
    gap = 5 * mm
    card_w = (width - margin * 2 - gap * (pane_count - 1)) / pane_count
    card_h = height * 0.48
    card_y = y - card_h

    for view in views:
        idx = view["idx"]
        x = margin + (idx - 1) * (card_w + gap)

        c.setStrokeColor(colors.HexColor("#d9e2ec"))
        c.setFillColor(colors.white)
        c.roundRect(x, card_y, card_w, card_h, 5, stroke=1, fill=1)

        c.setFillColor(colors.HexColor("#0b3040"))
        c.rect(x, card_y + card_h - 12 * mm, card_w, 12 * mm, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(x + 4 * mm, card_y + card_h - 8 * mm, f"Map View {idx}")

        ph_y = card_y + card_h * 0.38
        ph_h = card_h * 0.47
        c.setFillColor(colors.HexColor("#e5f3f7"))
        c.rect(x + 1, ph_y, card_w - 2, ph_h, stroke=0, fill=1)
        c.setFillColor(colors.HexColor("#31515e"))
        c.setFont("Helvetica", 8)
        c.drawCentredString(x + card_w / 2, ph_y + ph_h / 2, "Map placeholder / use HTML for live tiles")

        c.setFillColor(colors.HexColor("#172033"))
        c.setFont("Helvetica", 7)
        meta_y = card_y + card_h * 0.31
        lines = [
            f"Layer: {view['layer']}",
            f"Basemap: {view['basemap']}",
            f"Target: {view['target_scale']}",
            f"Current: {view['actual_scale'] or '-'}",
            f"Zoom: {view['zoom'] or '-'}",
        ]
        for line in lines:
            c.drawString(x + 4 * mm, meta_y, line[:82])
            meta_y -= 4 * mm

    y = card_y - 10 * mm
    c.setFillColor(colors.HexColor("#4d5b68"))
    c.setFont("Helvetica", 8)
    footer_lines = [
        f"Area: {selected_province or '-'} / {selected_district or '-'}",
        f"Preset: {preset}",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "Scale values are approximate web-map scales. Verify in GIS layout for official use.",
    ]
    if notes:
        footer_lines.append(f"Notes: {notes[:160]}")
    for line in footer_lines:
        c.drawString(margin, y, line[:150])
        y -= 4 * mm

    c.setFillColor(colors.HexColor("#0b3040"))
    c.setFont("Helvetica-Bold", 14)
    c.drawString(width - margin - 15 * mm, height - margin - 4 * mm, "▲")
    c.setFont("Helvetica-Bold", 9)
    c.drawString(width - margin - 13 * mm, height - margin - 10 * mm, "N")

    c.showPage()
    c.save()
    return buffer.getvalue(), None


def render_print_layout_composer(
    *,
    base_name: str,
    selected_province: str,
    selected_district: str,
    is_whole_country: bool,
) -> None:
    """
    Step 8.7.8: Print Layout PNG / PDF Export.
    """

    st.markdown("#### Print Layout PNG / PDF Export")
    st.caption(
        "สร้างไฟล์จัดหน้าแผนที่สำหรับนำเสนอ/รายงาน โดยแยก Target scale และ Current actual scale ในแต่ละ Map View"
    )

    col1, col2 = st.columns([1.35, 1.0])
    with col1:
        title = st.text_input(
            "ชื่อแผนที่ / ชื่อ Layout",
            value="Urban OS Map Workspace",
            key="print_layout_title",
        )
        subtitle = st.text_input(
            "คำอธิบายรอง",
            value=f"{selected_province or 'Thailand'} / {selected_district or 'Selected area'}",
            key="print_layout_subtitle",
        )
        notes = st.text_area(
            "หมายเหตุ",
            value="Generated from Urban OS Spatial AI Dashboard.",
            key="print_layout_notes",
            height=90,
        )

    with col2:
        preset = st.selectbox(
            "ขนาด Layout",
            list(PRINT_LAYOUT_PRESETS.keys()),
            index=1,
            key="print_layout_preset",
        )
        include_north_arrow = st.checkbox("North Arrow", value=True, key="print_include_north")
        include_scale_note = st.checkbox("Scale note", value=True, key="print_include_scale_note")
        include_legend = st.checkbox("Legend", value=True, key="print_include_legend")

    st.info(
        "HTML Layout เหมาะสำหรับเปิดแล้วสั่ง Print / Save as PDF จาก browser. "
        "PNG/PDF ในขั้นนี้เป็น static layout summary; หากต้องการภาพ tile แบบตรงหน้าจอจะทำต่อในขั้น Screenshot Engine"
    )

    html = _build_print_layout_html(
        title=title,
        subtitle=subtitle,
        selected_province=selected_province,
        selected_district=selected_district,
        is_whole_country=is_whole_country,
        preset=preset,
        notes=notes,
        include_north_arrow=include_north_arrow,
        include_scale_note=include_scale_note,
        include_legend=include_legend,
    )

    png_bytes, png_error = _build_print_layout_png_bytes(
        title=title,
        subtitle=subtitle,
        selected_province=selected_province,
        selected_district=selected_district,
        preset=preset,
        notes=notes,
    )

    pdf_bytes, pdf_error = _build_print_layout_pdf_bytes(
        title=title,
        subtitle=subtitle,
        selected_province=selected_province,
        selected_district=selected_district,
        preset=preset,
        notes=notes,
    )

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.download_button(
            "⬇️ Download Print Layout HTML",
            data=html.encode("utf-8"),
            file_name=f"{base_name}_print_layout.html",
            mime="text/html",
            use_container_width=True,
        )

    with col_b:
        if png_bytes:
            st.download_button(
                "⬇️ Download Print Layout PNG",
                data=png_bytes,
                file_name=f"{base_name}_print_layout.png",
                mime="image/png",
                use_container_width=True,
            )
        else:
            st.warning(png_error or "ไม่สามารถสร้าง PNG ได้")

    with col_c:
        if pdf_bytes:
            st.download_button(
                "⬇️ Download Print Layout PDF",
                data=pdf_bytes,
                file_name=f"{base_name}_print_layout.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        else:
            st.warning(pdf_error or "ไม่สามารถสร้าง PDF ได้")

    show_html_preview = st.checkbox(
        "แสดง Preview HTML source / Method note",
        value=False,
        key="print_layout_show_html_preview",
        help="ใช้ดู HTML ที่ระบบสร้างสำหรับตรวจสอบ layout โดยไม่ใช้ expander เพื่อเลี่ยง nested expander error",
    )
    if show_html_preview:
        st.code(html[:5000], language="html")
        if len(html) > 5000:
            st.caption("แสดงเฉพาะ HTML 5,000 ตัวอักษรแรก")




# ---------------------------------------------------------
# Pixel-Perfect Map Capture helpers
# ---------------------------------------------------------
PIXEL_CAPTURE_PRESETS = {
    "Dashboard 16:9 / 1920x1080": (1920, 1080),
    "A4 Landscape @150dpi / 1754x1240": (1754, 1240),
    "A3 Landscape @150dpi / 2480x1754": (2480, 1754),
    "A1 Landscape preview / 3508x2480": (3508, 2480),
    "Square 1600x1600": (1600, 1600),
}


def _get_current_map_html(Map) -> str:
    try:
        return Map.get_root().render()
    except Exception as exc:
        return f"<html><body><h3>Map render failed</h3><pre>{escape(str(exc))}</pre></body></html>"


def _build_capture_instruction_markdown(
    *,
    title: str,
    preset: str,
    width: int,
    height: int,
) -> str:
    lines = [
        "# Pixel-Perfect Map Capture Instructions",
        "",
        f"Title: `{title}`",
        f"Capture preset: `{preset}`",
        f"Canvas size: `{width} x {height}` px",
        "",
        "## วิธีใช้งาน",
        "",
        "1. Download `Pixel Capture HTML`",
        "2. เปิดไฟล์ HTML ใน Chrome / Edge",
        "3. รอให้ basemap และ layer โหลดครบ",
        "4. กดปุ่ม `Print / Save as PDF` ในหน้า HTML หรือใช้ `Ctrl+P`",
        "5. ถ้าต้องการ PNG ให้ใช้ปุ่ม `Export PNG (experimental)` หรือใช้เครื่องมือ screenshot ของ browser/OS",
        "",
        "## หมายเหตุ",
        "",
        "- HTML นี้เก็บแผนที่ interactive map ไว้ใน capture sheet เพื่อให้ส่งต่อหรือเปิดบันทึกภาพได้ง่าย",
        "- การ export PNG ด้วย browser อาจติดข้อจำกัด CORS ของ tile บางแหล่ง เช่น Esri/OSM/GEE",
        "- ถ้า PNG จากปุ่มทดลองไม่สำเร็จ ให้ใช้ Print/Save as PDF หรือ screenshot จาก browser แทน",
        "- Scale ที่แสดงมี 2 ค่า: Target export scale และ Current actual scale จาก zoom ปัจจุบัน",
        "- สำหรับแผนที่ราชการควรตรวจ scale ซ้ำใน QGIS/ArcGIS layout",
    ]
    return "\n".join(lines)


def _build_pixel_capture_html(
    *,
    Map,
    title: str,
    subtitle: str,
    selected_province: str,
    selected_district: str,
    preset: str,
    notes: str,
    include_toolbar: bool = True,
) -> str:
    """
    Build a browser-side capture HTML file.

    This avoids heavy Streamlit Cloud dependencies like Playwright/Chromium.
    Users open the HTML in a browser and print/save/capture it there.
    """

    width, height = PIXEL_CAPTURE_PRESETS.get(
        preset,
        PIXEL_CAPTURE_PRESETS["Dashboard 16:9 / 1920x1080"],
    )
    map_html = _get_current_map_html(Map)
    map_srcdoc = escape(map_html, quote=True)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    view_rows = ""
    for view in _get_print_view_settings():
        view_rows += f"""
        <tr>
          <td>Map View {view['idx']}</td>
          <td>{escape(str(view['layer']))}</td>
          <td>{escape(str(view['basemap']))}</td>
          <td>{escape(str(view['target_scale']))}</td>
          <td>{escape(str(view['actual_scale'] or '-'))}</td>
          <td>{escape(str(view['zoom'] or '-'))}</td>
        </tr>
        """

    toolbar = """
    <div class="toolbar">
      <button onclick="window.print()">Print / Save as PDF</button>
      <button onclick="downloadPng()">Export PNG (experimental)</button>
      <span id="status">รอให้แผนที่โหลดครบก่อน capture</span>
    </div>
    """ if include_toolbar else ""

    return f"""<!doctype html>
<html lang="th">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
<style>
* {{
  box-sizing: border-box;
}}
body {{
  margin: 0;
  background: #0b1320;
  font-family: Arial, "Noto Sans Thai", sans-serif;
  color: #172033;
}}
.toolbar {{
  position: sticky;
  top: 0;
  z-index: 99999;
  display: flex;
  gap: 8px;
  align-items: center;
  padding: 10px 14px;
  background: #07111f;
  color: white;
  border-bottom: 1px solid #26384d;
}}
.toolbar button {{
  border: 0;
  border-radius: 8px;
  padding: 9px 12px;
  background: #00bcd4;
  color: #001018;
  font-weight: 700;
  cursor: pointer;
}}
.toolbar #status {{
  font-size: 12px;
  color: #a9bacb;
}}
#capture-sheet {{
  width: {width}px;
  height: {height}px;
  margin: 18px auto;
  background: white;
  position: relative;
  overflow: hidden;
  box-shadow: 0 10px 35px rgba(0,0,0,0.45);
}}
.header {{
  height: 92px;
  padding: 18px 24px 12px 24px;
  border-bottom: 4px solid #00bcd4;
  display: grid;
  grid-template-columns: 1fr 300px;
  gap: 20px;
}}
h1 {{
  margin: 0;
  font-size: 28px;
  color: #0b3040;
}}
.subtitle {{
  margin-top: 6px;
  color: #4d5b68;
  font-size: 13px;
}}
.badge {{
  font-size: 11px;
  line-height: 1.4;
  background: #f4fbfd;
  border: 1px solid #cce9ef;
  border-radius: 8px;
  padding: 8px 10px;
}}
.map-frame {{
  width: 100%;
  height: calc(100% - 232px);
  border: 0;
  display: block;
}}
.footer {{
  height: 140px;
  border-top: 1px solid #d9e2ec;
  display: grid;
  grid-template-columns: 1fr 430px;
  gap: 14px;
  padding: 10px 18px;
  font-size: 11px;
  color: #273746;
}}
.view-table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 10px;
}}
.view-table th,
.view-table td {{
  border: 1px solid #d9e2ec;
  padding: 4px 5px;
  text-align: left;
}}
.view-table th {{
  background: #f4f7fa;
}}
.notes {{
  white-space: pre-wrap;
  color: #4d5b68;
  margin-top: 5px;
}}
.north {{
  position: absolute;
  right: 28px;
  top: 112px;
  text-align: center;
  font-weight: 800;
  font-size: 24px;
  color: #0b3040;
  background: rgba(255,255,255,.85);
  padding: 6px 10px;
  border-radius: 8px;
}}
.scale-note {{
  position: absolute;
  left: 24px;
  bottom: 152px;
  background: rgba(255,255,255,.92);
  border: 1px solid rgba(0,0,0,.2);
  border-radius: 8px;
  padding: 6px 9px;
  font-size: 11px;
  color: #111;
}}
@media print {{
  body {{
    background: white;
  }}
  .toolbar {{
    display: none;
  }}
  #capture-sheet {{
    margin: 0;
    box-shadow: none;
    width: 100vw;
    height: 100vh;
  }}
}}
</style>
</head>
<body>
{toolbar}
<div id="capture-sheet">
  <div class="header">
    <div>
      <h1>{escape(title)}</h1>
      <div class="subtitle">{escape(subtitle)}</div>
    </div>
    <div class="badge">
      <b>Urban OS Pixel Capture</b><br>
      Preset: {escape(preset)}<br>
      Size: {width:,} × {height:,} px<br>
      Area: {escape(selected_province or "-")} / {escape(selected_district or "-")}<br>
      Generated: {now}
    </div>
  </div>

  <div class="north">▲<br>N</div>
  <div class="scale-note">Scale shown in each map overlay: Target vs Current actual</div>
  <iframe class="map-frame" srcdoc="{map_srcdoc}"></iframe>

  <div class="footer">
    <div>
      <b>Capture Notes</b>
      <div class="notes">{escape(notes or "Generated from Urban OS Spatial AI Dashboard.")}</div>
      <div class="notes">Pixel-perfect capture depends on browser rendering, loaded tiles, DPI and CORS policy.</div>
    </div>
    <div>
      <b>Map View Metadata</b>
      <table class="view-table">
        <thead>
          <tr>
            <th>View</th><th>Layer</th><th>Basemap</th><th>Target</th><th>Current</th><th>Zoom</th>
          </tr>
        </thead>
        <tbody>{view_rows}</tbody>
      </table>
    </div>
  </div>
</div>

<script>
async function downloadPng() {{
  const status = document.getElementById('status');
  status.textContent = 'กำลังโหลด html2canvas...';
  try {{
    if (!window.html2canvas) {{
      await new Promise((resolve, reject) => {{
        const s = document.createElement('script');
        s.src = 'https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js';
        s.onload = resolve;
        s.onerror = reject;
        document.head.appendChild(s);
      }});
    }}
    status.textContent = 'กำลัง capture PNG...';
    const node = document.getElementById('capture-sheet');
    const canvas = await html2canvas(node, {{
      useCORS: true,
      allowTaint: false,
      backgroundColor: '#ffffff',
      scale: 1
    }});
    const a = document.createElement('a');
    a.download = 'urban_os_pixel_capture.png';
    a.href = canvas.toDataURL('image/png');
    a.click();
    status.textContent = 'สร้าง PNG แล้ว หากไม่สำเร็จให้ใช้ Print/Save PDF หรือ screenshot';
  }} catch (err) {{
    console.error(err);
    status.textContent = 'PNG capture ไม่สำเร็จ อาจเกิดจาก CORS ของ map tiles ให้ใช้ Print/Save PDF หรือ screenshot แทน';
    alert('PNG capture ไม่สำเร็จ อาจเกิดจาก CORS ของ map tiles ให้ใช้ Print/Save PDF หรือ screenshot แทน');
  }}
}}
</script>
</body>
</html>"""




def _view_config_from_session(view_idx: int) -> dict:
    """
    Build a Map View config from current session_state.
    """

    return {
        "layer_choice": st.session_state.get(f"map_view_{view_idx}_layer_choice", "Current Mode Layers"),
        "basemap_choice": st.session_state.get(f"map_view_{view_idx}_basemap", "OpenStreetMap"),
        "scale_label": st.session_state.get(f"map_view_{view_idx}_scale_label", "1 : 2,000"),
        "apply_scale_to_zoom": bool(st.session_state.get(f"map_view_{view_idx}_apply_scale", True)),
        "paper_preset": st.session_state.get("map_export_paper_preset", "Screen / Dashboard"),
    }


def _build_map_for_selected_view(
    *,
    original_map,
    view_idx: int,
    roi=None,
    is_whole_country: bool = False,
    selected_province: str = "",
    selected_district: str = "",
):
    """
    Rebuild the selected Map View for pixel capture.
    """

    try:
        from components.map_renderer import _create_independent_view_map

        return _create_independent_view_map(
            original_map=original_map,
            view_config=_view_config_from_session(view_idx),
            view_idx=view_idx,
            roi=roi,
            is_whole_country=is_whole_country,
            selected_province=selected_province,
            selected_district=selected_district,
        )
    except Exception as exc:
        st.warning(
            "ไม่สามารถ rebuild Map View สำหรับ capture แยกได้ "
            f"จึงใช้ current map layer stack แทน: {exc}"
        )
        return original_map


def render_one_click_png_capture(
    *,
    Map,
    base_name: str,
    roi=None,
    selected_province: str = "",
    selected_district: str = "",
    is_whole_country: bool = False,
) -> None:
    """
    Step 8.7.10: One-click browser-side PNG export from selected Map View.
    """

    st.markdown("#### One-Click True PNG Export จาก Map View")
    st.caption(
        "เลือก Map View ที่ต้องการ แล้วกด Export PNG ในกรอบ preview เพื่อดาวน์โหลดภาพจาก browser"
    )

    pane_count = _get_visible_pane_count()
    view_options = [f"Map View {idx}" for idx in range(1, pane_count + 1)]

    c1, c2 = st.columns([1.1, 1.2])
    with c1:
        selected_view_label = st.selectbox(
            "เลือก Map View ที่จะ export",
            view_options,
            index=0,
            key="one_click_png_view_label",
        )
        view_idx = int(selected_view_label.replace("Map View ", ""))

        preset = st.selectbox(
            "PNG canvas size",
            list(PIXEL_CAPTURE_PRESETS.keys()),
            index=0,
            key="one_click_png_preset",
        )

    with c2:
        title = st.text_input(
            "ชื่อภาพ PNG",
            value=st.session_state.get("pixel_capture_title", "Urban OS Map PNG Export"),
            key="one_click_png_title",
        )
        subtitle = st.text_input(
            "คำอธิบายภาพ",
            value=f"{selected_province or 'Thailand'} / {selected_district or 'Selected area'}",
            key="one_click_png_subtitle",
        )

    notes = st.text_area(
        "หมายเหตุในภาพ",
        value="One-click browser-side PNG capture from Urban OS Map Workspace.",
        key="one_click_png_notes",
        height=70,
    )

    capture_map = _build_map_for_selected_view(
        original_map=Map,
        view_idx=view_idx,
        roi=roi,
        is_whole_country=is_whole_country,
        selected_province=selected_province,
        selected_district=selected_district,
    )

    html = _build_pixel_capture_html(
        Map=capture_map,
        title=title,
        subtitle=subtitle,
        selected_province=selected_province,
        selected_district=selected_district,
        preset=preset,
        notes=notes,
        include_toolbar=True,
    )

    width, height = PIXEL_CAPTURE_PRESETS.get(preset, PIXEL_CAPTURE_PRESETS["Dashboard 16:9 / 1920x1080"])

    st.success(
        "กด `Export PNG (experimental)` ในกรอบ preview ด้านล่างเพื่อดาวน์โหลด PNG "
        "ถ้า tile บางแหล่งติด CORS ให้ใช้ Print / Save as PDF หรือดาวน์โหลด HTML ไปเปิดใน Chrome/Edge"
    )

    preview_height = min(900, max(620, int(height * 0.55)))
    components.html(html, height=preview_height, scrolling=True)

    st.download_button(
        "⬇️ Download Same Capture HTML",
        data=html.encode("utf-8"),
        file_name=f"{base_name}_map_view_{view_idx}_one_click_png_capture.html",
        mime="text/html",
        use_container_width=True,
    )


def render_pixel_perfect_capture(
    *,
    Map,
    base_name: str,
    roi=None,
    selected_province: str,
    selected_district: str,
    is_whole_country: bool = False,
) -> None:
    """
    Step 8.7.9: Pixel-Perfect Map Capture.

    Safe implementation: generate a standalone browser capture HTML with current
    interactive map embedded. Users can open it and use Print / Save as PDF or
    the experimental client-side PNG button.
    """

    st.markdown("#### Pixel-Perfect Map Capture")
    st.caption(
        "สร้าง HTML สำหรับ capture ภาพแผนที่จริงจาก browser ตาม tile/layer ที่โหลดในแผนที่ "
        "โดยไม่เพิ่ม dependency หนักบน Streamlit Cloud"
    )

    render_one_click_png_capture(
        Map=Map,
        base_name=base_name,
        roi=roi,
        selected_province=selected_province,
        selected_district=selected_district,
        is_whole_country=is_whole_country,
    )

    st.markdown("---")
    st.markdown("#### Advanced / Standalone Pixel Capture HTML")

    c1, c2 = st.columns([1.35, 1.0])
    with c1:
        title = st.text_input(
            "ชื่อ Capture",
            value=st.session_state.get("print_layout_title", "Urban OS Pixel Map Capture"),
            key="pixel_capture_title",
        )
        subtitle = st.text_input(
            "คำอธิบาย Capture",
            value=f"{selected_province or 'Thailand'} / {selected_district or 'Selected area'}",
            key="pixel_capture_subtitle",
        )
        notes = st.text_area(
            "Capture notes",
            value="Open this HTML in Chrome/Edge, wait for map tiles to load, then Print/Save PDF or Export PNG.",
            key="pixel_capture_notes",
            height=85,
        )

    with c2:
        preset = st.selectbox(
            "Capture canvas size",
            list(PIXEL_CAPTURE_PRESETS.keys()),
            index=0,
            key="pixel_capture_preset",
        )
        include_toolbar = st.checkbox(
            "แสดง toolbar ในไฟล์ HTML",
            value=True,
            key="pixel_capture_include_toolbar",
        )

    width, height = PIXEL_CAPTURE_PRESETS.get(preset, PIXEL_CAPTURE_PRESETS["Dashboard 16:9 / 1920x1080"])
    html = _build_pixel_capture_html(
        Map=Map,
        title=title,
        subtitle=subtitle,
        selected_province=selected_province,
        selected_district=selected_district,
        preset=preset,
        notes=notes,
        include_toolbar=include_toolbar,
    )
    instruction_md = _build_capture_instruction_markdown(
        title=title,
        preset=preset,
        width=width,
        height=height,
    )

    st.info(
        "วิธีใช้งาน: ดาวน์โหลด HTML → เปิดใน Chrome/Edge → รอแผนที่โหลดครบ → กด Print/Save PDF "
        "หรือ Export PNG (experimental). ถ้า PNG ติด CORS ให้ใช้ Print/Save PDF หรือ screenshot ของ browser"
    )

    col_a, col_b = st.columns(2)
    with col_a:
        st.download_button(
            "⬇️ Download Pixel Capture HTML",
            data=html.encode("utf-8"),
            file_name=f"{base_name}_pixel_capture.html",
            mime="text/html",
            use_container_width=True,
        )

    with col_b:
        st.download_button(
            "⬇️ Download Capture Instructions",
            data=instruction_md.encode("utf-8"),
            file_name=f"{base_name}_pixel_capture_instructions.md",
            mime="text/markdown",
            use_container_width=True,
        )

    show_preview = st.checkbox(
        "แสดง HTML preview source",
        value=False,
        key="pixel_capture_show_html_preview",
    )
    if show_preview:
        st.code(html[:5000], language="html")
        if len(html) > 5000:
            st.caption("แสดงเฉพาะ HTML 5,000 ตัวอักษรแรก")


def render_map_export_composer(
    *,
    Map,
    roi=None,
    selected_province: str = "",
    selected_district: str = "",
    is_whole_country: bool = False,
) -> None:
    """
    Step 8.7.6: Map Export Composer + GIS Export
    """

    st.markdown("### 🖨️ Map Export Composer / GIS Export")
    st.caption(
        "ส่งออกแผนที่และข้อมูล GIS สำหรับนำไปใช้ต่อใน QGIS, ArcGIS, GeoLibre, GeoServer หรือรายงาน"
    )

    with st.container():

        base_name = _safe_filename(
            f"urban_os_{selected_province or 'thailand'}_{selected_district or 'area'}"
        )

        tab_map, tab_capture, tab_print, tab_gis, tab_report = st.tabs(
            ["🗺️ Map Export", "📸 Pixel Capture", "🖨️ Print Layout", "🧩 GIS Export", "📝 Layout Summary"]
        )

        with tab_map:
            st.markdown("#### Interactive HTML Map")
            st.caption("ส่งออกแผนที่แบบ interactive HTML จาก current map layer stack")
            _render_html_export(Map, base_name)

        with tab_capture:
            render_pixel_perfect_capture(
                Map=Map,
                base_name=base_name,
                roi=roi,
                selected_province=selected_province,
                selected_district=selected_district,
                is_whole_country=is_whole_country,
            )

        with tab_print:
            render_print_layout_composer(
                base_name=base_name,
                selected_province=selected_province,
                selected_district=selected_district,
                is_whole_country=is_whole_country,
            )

        with tab_gis:
            st.markdown("#### Shapefile / GeoJSON Export")

            source = st.selectbox(
                "เลือกชุดข้อมูล GIS ที่ต้องการ export",
                [
                    "ROI Boundary",
                    "Candidate Areas จาก Candidate Export",
                ],
                key="gis_export_source",
            )

            if source == "ROI Boundary":
                geojson = _geojson_feature_collection_from_roi(roi)
                export_name = f"{base_name}_roi_boundary"
            else:
                geojson = _load_candidate_geojson_from_session()
                export_name = f"{base_name}_candidate_areas"

            if not geojson:
                st.warning(
                    "ยังไม่มี Candidate Areas GeoJSON ใน session ให้ไปที่ Candidate Area Export แล้วกด Generate Candidate GeoJSON ก่อน"
                )
            else:
                feature_count = len((geojson or {}).get("features", []) or [])
                st.metric("Feature count", feature_count)

                col1, col2 = st.columns(2)
                with col1:
                    st.download_button(
                        "⬇️ Download GeoJSON",
                        data=_geojson_to_bytes(geojson),
                        file_name=f"{export_name}.geojson",
                        mime="application/geo+json",
                        use_container_width=True,
                    )

                with col2:
                    shp_zip, error = _geojson_to_shapefile_zip_bytes(
                        geojson,
                        layer_name=export_name,
                    )
                    if shp_zip:
                        st.download_button(
                            "⬇️ Download Shapefile ZIP",
                            data=shp_zip,
                            file_name=f"{export_name}_shapefile.zip",
                            mime="application/zip",
                            use_container_width=True,
                        )
                    else:
                        st.warning(error or "ไม่สามารถสร้าง Shapefile ได้")

                st.info(
                    "หมายเหตุ: Shapefile รองรับ field name ไม่เกิน 10 ตัวอักษร จึงมีไฟล์ field_mapping.json แนบใน zip"
                )

        with tab_report:
            st.markdown("#### Map Workspace Summary")
            md = _workspace_summary_markdown(
                selected_province=selected_province,
                selected_district=selected_district,
                is_whole_country=is_whole_country,
            )
            st.download_button(
                "⬇️ Download Map Layout Summary Markdown",
                data=md.encode("utf-8"),
                file_name=f"{base_name}_map_workspace_summary.md",
                mime="text/markdown",
                use_container_width=True,
            )
            st.code(md, language="markdown")

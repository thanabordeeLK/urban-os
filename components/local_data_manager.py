from __future__ import annotations

from datetime import datetime
import json
import re
from typing import Any

import pandas as pd
import streamlit as st


REGISTRY_KEY = "local_data_registry"

CATEGORY_OPTIONS = {
    "roads": {
        "label": "🛣️ Roads / Transport Network",
        "target_key": "suit_road_asset_ids",
        "enabled_key": "suit_use_road_accessibility",
        "description": "ถนน ทางหลวง ทางท้องถิ่น โครงข่ายคมนาคม",
    },
    "public_facilities": {
        "label": "🏥 Public Facilities / POI",
        "target_key": "suit_facility_asset_ids",
        "enabled_key": "suit_use_public_facilities",
        "description": "โรงพยาบาล โรงเรียน ตลาด ศูนย์ราชการ สถานีขนส่ง ฯลฯ",
    },
    "protected_forest": {
        "label": "🌲 Protected / Forest Constraint",
        "target_key": "suit_forest_asset_ids",
        "enabled_key": None,
        "description": "ป่าสงวน อุทยาน เขตห้ามล่า พื้นที่อนุรักษ์ พื้นที่ห้ามพัฒนา",
    },
    "water": {
        "label": "💧 Water / Waterways",
        "target_key": None,
        "enabled_key": None,
        "description": "ลำน้ำ อ่างเก็บน้ำ คลอง แหล่งน้ำ พื้นที่ชุ่มน้ำ",
    },
    "zoning": {
        "label": "🧩 Zoning / Land Use Plan",
        "target_key": None,
        "enabled_key": None,
        "description": "ผังเมืองรวม ผังสี เขตการใช้ประโยชน์ที่ดิน",
    },
    "parcels": {
        "label": "📐 Parcels / Land Plots",
        "target_key": None,
        "enabled_key": None,
        "description": "แปลงที่ดิน กรรมสิทธิ์ ขอบเขตโครงการ",
    },
    "buildings": {
        "label": "🏢 Buildings / Built-up",
        "target_key": None,
        "enabled_key": None,
        "description": "อาคาร footprint ชุมชนเดิม สิ่งปลูกสร้าง",
    },
    "custom": {
        "label": "🧪 Custom / Other",
        "target_key": None,
        "enabled_key": None,
        "description": "ชั้นข้อมูลอื่น ๆ",
    },
}


def _now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _validate_asset_id(asset_id: str) -> tuple[bool, str]:
    asset_id = _normalize_text(asset_id)
    if not asset_id:
        return False, "Asset ID ว่าง"

    valid_prefix = asset_id.startswith("projects/") or asset_id.startswith("users/")
    if not valid_prefix:
        return False, "Asset ID ควรขึ้นต้นด้วย projects/... หรือ users/..."

    if " " in asset_id:
        return False, "Asset ID ไม่ควรมีช่องว่าง"

    return True, "รูปแบบดูถูกต้อง"


def _split_asset_ids(text: str) -> list[str]:
    result = []
    for line in str(text or "").splitlines():
        for item in line.split(","):
            item = item.strip()
            if item:
                result.append(item)
    return list(dict.fromkeys(result))


def get_local_data_registry() -> list[dict]:
    if REGISTRY_KEY not in st.session_state:
        st.session_state[REGISTRY_KEY] = []
    return st.session_state[REGISTRY_KEY]


def set_local_data_registry(items: list[dict]) -> None:
    cleaned = []
    for idx, item in enumerate(items or [], start=1):
        if not isinstance(item, dict):
            continue

        category = item.get("category", "custom")
        if category not in CATEGORY_OPTIONS:
            category = "custom"

        asset_id = _normalize_text(item.get("asset_id"))
        if not asset_id:
            continue

        valid, message = _validate_asset_id(asset_id)

        cleaned.append(
            {
                "id": item.get("id") or f"layer_{idx}_{int(datetime.now().timestamp())}",
                "layer_name": _normalize_text(item.get("layer_name")) or f"Layer {idx}",
                "category": category,
                "asset_id": asset_id,
                "layer_type": _normalize_text(item.get("layer_type")) or "FeatureCollection",
                "source": _normalize_text(item.get("source")) or "GEE Asset",
                "use_in_suitability": bool(item.get("use_in_suitability", True)),
                "notes": _normalize_text(item.get("notes")),
                "created_at": item.get("created_at") or _now_text(),
                "updated_at": item.get("updated_at") or _now_text(),
                "is_valid_format": valid,
                "validation_message": message,
            }
        )

    st.session_state[REGISTRY_KEY] = cleaned


def get_registry_asset_ids_by_category(category: str, only_enabled: bool = True) -> list[str]:
    registry = get_local_data_registry()
    asset_ids = []
    for item in registry:
        if item.get("category") != category:
            continue
        if only_enabled and not item.get("use_in_suitability", True):
            continue
        asset_id = _normalize_text(item.get("asset_id"))
        if asset_id:
            asset_ids.append(asset_id)
    return list(dict.fromkeys(asset_ids))


def apply_registry_to_suitability_widgets() -> dict:
    """
    นำข้อมูลจาก Local Data Registry ไปใส่ widget state ของ Suitability Analysis
    ใช้ได้เมื่ออยู่หน้า Local Data Manager ก่อนสลับไป Suitability Analysis
    """

    applied = {}

    for category, meta in CATEGORY_OPTIONS.items():
        target_key = meta.get("target_key")
        enabled_key = meta.get("enabled_key")

        if not target_key:
            continue

        asset_ids = get_registry_asset_ids_by_category(category, only_enabled=True)
        st.session_state[target_key] = "\n".join(asset_ids)

        if enabled_key:
            st.session_state[enabled_key] = bool(asset_ids)

        applied[category] = len(asset_ids)

    return applied


def registry_to_dataframe() -> pd.DataFrame:
    registry = get_local_data_registry()
    rows = []
    for idx, item in enumerate(registry, start=1):
        category = item.get("category", "custom")
        rows.append(
            {
                "ลำดับ": idx,
                "ชื่อชั้นข้อมูล": item.get("layer_name", ""),
                "ประเภท": CATEGORY_OPTIONS.get(category, CATEGORY_OPTIONS["custom"])["label"],
                "Asset ID": item.get("asset_id", ""),
                "ใช้ใน Suitability": item.get("use_in_suitability", False),
                "สถานะรูปแบบ": "OK" if item.get("is_valid_format") else "Check",
                "หมายเหตุ": item.get("notes", ""),
                "แก้ไขล่าสุด": item.get("updated_at", ""),
            }
        )
    return pd.DataFrame(rows)


def _registry_json_bytes() -> bytes:
    payload = {
        "exported_from": "Urban OS Local Data Manager",
        "exported_at": _now_text(),
        "version": "0.1",
        "layers": get_local_data_registry(),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def _registry_csv_bytes() -> bytes:
    df = registry_to_dataframe()
    if df.empty:
        return "".encode("utf-8-sig")
    return df.to_csv(index=False).encode("utf-8-sig")


def _template_csv_bytes() -> bytes:
    template = pd.DataFrame(
        [
            {
                "layer_name": "roads_uttaradit_osm",
                "category": "roads",
                "asset_id": "projects/your-project/assets/roads_uttaradit_osm",
                "layer_type": "FeatureCollection",
                "source": "OpenStreetMap / QGIS Clip",
                "use_in_suitability": True,
                "notes": "Road Accessibility",
            },
            {
                "layer_name": "public_facilities_uttaradit",
                "category": "public_facilities",
                "asset_id": "projects/your-project/assets/public_facilities_uttaradit",
                "layer_type": "FeatureCollection",
                "source": "OSM POI / Local agency",
                "use_in_suitability": True,
                "notes": "โรงพยาบาล โรงเรียน ตลาด ศูนย์ราชการ",
            },
            {
                "layer_name": "forest_reserve_uttaradit",
                "category": "protected_forest",
                "asset_id": "projects/your-project/assets/forest_reserve_uttaradit",
                "layer_type": "FeatureCollection",
                "source": "Local agency",
                "use_in_suitability": True,
                "notes": "Hard Constraint",
            },
        ]
    )
    return template.to_csv(index=False).encode("utf-8-sig")


def _import_registry_from_json(uploaded_file) -> tuple[bool, str]:
    try:
        raw = uploaded_file.read().decode("utf-8")
        payload = json.loads(raw)

        if isinstance(payload, dict):
            items = payload.get("layers", [])
        elif isinstance(payload, list):
            items = payload
        else:
            return False, "JSON ต้องเป็น list หรือ object ที่มี key 'layers'"

        set_local_data_registry(items)
        return True, f"นำเข้า registry สำเร็จ {len(get_local_data_registry())} ชั้นข้อมูล"
    except Exception as exc:
        return False, f"นำเข้าไม่สำเร็จ: {exc}"


def _add_registry_item(
    *,
    layer_name: str,
    category: str,
    asset_ids_text: str,
    layer_type: str,
    source: str,
    use_in_suitability: bool,
    notes: str,
) -> tuple[int, list[str]]:
    registry = get_local_data_registry()
    asset_ids = _split_asset_ids(asset_ids_text)
    messages = []

    for asset_id in asset_ids:
        valid, message = _validate_asset_id(asset_id)
        registry.append(
            {
                "id": f"layer_{len(registry)+1}_{int(datetime.now().timestamp())}",
                "layer_name": layer_name.strip() or asset_id.split("/")[-1],
                "category": category,
                "asset_id": asset_id,
                "layer_type": layer_type,
                "source": source,
                "use_in_suitability": use_in_suitability,
                "notes": notes,
                "created_at": _now_text(),
                "updated_at": _now_text(),
                "is_valid_format": valid,
                "validation_message": message,
            }
        )
        messages.append(f"{asset_id}: {message}")

    # remove exact duplicate asset ids while keeping latest order
    seen = set()
    deduped = []
    for item in registry:
        key = item.get("asset_id")
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    st.session_state[REGISTRY_KEY] = deduped
    return len(asset_ids), messages


def render_registry_overview() -> None:
    registry = get_local_data_registry()

    counts = {key: 0 for key in CATEGORY_OPTIONS}
    for item in registry:
        category = item.get("category", "custom")
        counts[category] = counts.get(category, 0) + 1

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("ชั้นข้อมูลทั้งหมด", len(registry))
    col2.metric("ถนน", counts.get("roads", 0))
    col3.metric("บริการสาธารณะ", counts.get("public_facilities", 0))
    col4.metric("ป่า/พื้นที่กันออก", counts.get("protected_forest", 0))

    missing = []
    if counts.get("roads", 0) == 0:
        missing.append("ยังไม่มี Road Asset")
    if counts.get("public_facilities", 0) == 0:
        missing.append("ยังไม่มี Public Facility Asset")
    if counts.get("protected_forest", 0) == 0:
        missing.append("ยังไม่มี Forest/Protected Constraint Asset")

    if missing:
        st.warning("ข้อมูลที่ยังควรเติม: " + " | ".join(missing))
    else:
        st.success("มีข้อมูลหลักสำหรับ Suitability Model ครบ 3 กลุ่ม: ถนน / บริการสาธารณะ / พื้นที่กันออก")

    df = registry_to_dataframe()
    if df.empty:
        st.info("ยังไม่มีรายการใน Local Data Registry")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)


def render_add_layer_form() -> None:
    st.markdown("#### ➕ Add GEE Asset to Registry")

    with st.form("add_local_data_asset_form", clear_on_submit=False):
        col1, col2 = st.columns(2)

        with col1:
            layer_name = st.text_input(
                "ชื่อชั้นข้อมูล",
                placeholder="เช่น roads_uttaradit_osm",
                key="ldm_layer_name",
            )

            category_labels = {v["label"]: k for k, v in CATEGORY_OPTIONS.items()}
            selected_label = st.selectbox(
                "ประเภทข้อมูล",
                options=list(category_labels.keys()),
                index=0,
                key="ldm_category_label",
            )
            category = category_labels[selected_label]

            layer_type = st.selectbox(
                "ชนิดข้อมูล",
                options=["FeatureCollection", "Image", "ImageCollection", "Table / CSV", "Other"],
                index=0,
                key="ldm_layer_type",
            )

        with col2:
            source = st.text_input(
                "แหล่งที่มา",
                value="GEE Asset",
                key="ldm_source",
            )

            use_in_suitability = st.checkbox(
                "ใช้ใน Suitability Analysis",
                value=True,
                key="ldm_use_in_suitability",
            )

            notes = st.text_area(
                "หมายเหตุ",
                height=80,
                key="ldm_notes",
                placeholder="เช่น Road Accessibility / Hard Constraint / POI",
            )

        asset_ids_text = st.text_area(
            "GEE Asset ID / ใส่ได้หลายบรรทัด",
            height=110,
            key="ldm_asset_ids_text",
            placeholder=(
                "projects/your-project/assets/roads_uttaradit_osm\n"
                "users/yourname/local_roads"
            ),
        )

        submitted = st.form_submit_button("➕ Add to Local Data Registry", use_container_width=True)

    if submitted:
        count, messages = _add_registry_item(
            layer_name=layer_name,
            category=category,
            asset_ids_text=asset_ids_text,
            layer_type=layer_type,
            source=source,
            use_in_suitability=use_in_suitability,
            notes=notes,
        )
        if count > 0:
            st.success(f"เพิ่มข้อมูล {count} รายการแล้ว")
            for msg in messages:
                st.caption(msg)
        else:
            st.error("ยังไม่ได้ใส่ Asset ID")


def render_registry_actions() -> None:
    st.markdown("#### 🛠️ Registry Actions")

    registry = get_local_data_registry()

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🔁 Apply to Suitability Widgets", use_container_width=True):
            applied = apply_registry_to_suitability_widgets()
            st.success(
                "ส่ง Asset ID ไปที่ Suitability Analysis แล้ว: "
                + ", ".join([f"{k}={v}" for k, v in applied.items()])
            )
            st.caption("ให้สลับไปหน้า Suitability Analysis แล้วกด Run อีกครั้ง")

    with col2:
        if st.button("🧹 Clear Registry", use_container_width=True):
            st.session_state[REGISTRY_KEY] = []
            st.success("ล้าง Local Data Registry แล้ว")
            st.rerun()

    with col3:
        st.download_button(
            "⬇️ Download CSV Template",
            data=_template_csv_bytes(),
            file_name="urban_os_local_data_template.csv",
            mime="text/csv",
            use_container_width=True,
        )

    if registry:
        options = [
            f"{idx+1}. {item.get('layer_name')} | {item.get('asset_id')}"
            for idx, item in enumerate(registry)
        ]
        selected = st.selectbox(
            "เลือกรายการที่ต้องการลบ",
            options=["-- ไม่ลบ --"] + options,
            key="ldm_delete_select",
        )

        if selected != "-- ไม่ลบ --":
            selected_index = int(selected.split(".", 1)[0]) - 1
            if st.button("🗑️ Delete Selected Layer", type="secondary"):
                deleted = registry.pop(selected_index)
                st.session_state[REGISTRY_KEY] = registry
                st.success(f"ลบ {deleted.get('layer_name')} แล้ว")
                st.rerun()


def render_import_export_panel() -> None:
    st.markdown("#### 📦 Import / Export Registry")

    col1, col2 = st.columns(2)

    with col1:
        st.download_button(
            "⬇️ Download Registry JSON",
            data=_registry_json_bytes(),
            file_name="urban_os_local_data_registry.json",
            mime="application/json",
            use_container_width=True,
        )

    with col2:
        st.download_button(
            "⬇️ Download Registry CSV",
            data=_registry_csv_bytes(),
            file_name="urban_os_local_data_registry.csv",
            mime="text/csv",
            use_container_width=True,
        )

    uploaded_json = st.file_uploader(
        "Import Registry JSON",
        type=["json"],
        key="ldm_import_json",
        help="นำเข้าไฟล์ urban_os_local_data_registry.json ที่เคย export ไว้",
    )

    if uploaded_json is not None:
        if st.button("📥 Import JSON Registry", use_container_width=True):
            ok, message = _import_registry_from_json(uploaded_json)
            if ok:
                st.success(message)
                st.rerun()
            else:
                st.error(message)


def render_local_data_manager(
    selected_province: str = "",
    selected_district: str = "",
    is_whole_country: bool = False,
) -> None:
    st.markdown("### 🗂️ Local Data Manager")
    st.caption(
        "ศูนย์จัดการ GEE Asset ID และข้อมูลเฉพาะพื้นที่ เพื่อใช้กับ Suitability Analysis และโมดูลต่อไป"
    )

    area_name = "ทั้งประเทศไทย" if is_whole_country else f"{selected_district}, {selected_province}"
    st.info(f"พื้นที่ทำงานปัจจุบัน: {area_name}")

    tab1, tab2, tab3 = st.tabs(
        [
            "📋 Registry Overview",
            "➕ Add / Manage Assets",
            "📦 Import / Export",
        ]
    )

    with tab1:
        render_registry_overview()

        with st.expander("ℹ️ วิธีใช้ Local Data Manager", expanded=False):
            st.markdown(
                """
                1. อัปโหลด Shapefile/GeoJSON เข้า Google Earth Engine Assets ก่อน  
                2. คัดลอก Asset ID เช่น `projects/.../assets/roads_uttaradit_osm`  
                3. เพิ่มรายการในแท็บ Add / Manage Assets  
                4. กด **Apply to Suitability Widgets**  
                5. สลับไปหน้า Suitability Analysis แล้วกด Run ใหม่  

                หมายเหตุ: Registry นี้เก็บใน session ของ Streamlit เป็นหลัก  
                หากต้องการเก็บถาวร ให้กด Download Registry JSON ไว้ แล้ว import กลับมาได้
                """
            )

    with tab2:
        render_add_layer_form()
        st.divider()
        render_registry_actions()

    with tab3:
        render_import_export_panel()

"""Streamlit integration for Urban OS Multi-Agent mode."""
from __future__ import annotations

import json

import streamlit as st

from agents.coordinator_agent import CoordinatorAgent
from core_engine.general_plan import add_general_plan_layers


DEFAULT_AGENT_LAYER_SETTINGS = {
    "show_cop_dem": True,
    "op_cop_dem": 0.55,
    "show_dswx_s1": False,
    "op_dswx_s1": 0.60,
    "show_gfd": True,
    "op_gfd": 0.55,
    "show_landcover": True,
    "op_landcover": 0.55,
    "show_dw": False,
    "op_dw": 0.55,
    "show_chirts": False,
    "op_chirts": 0.55,
    "show_urban": True,
    "op_urban": 0.55,
    "show_pop": False,
    "op_pop": 0.55,
}


def add_multi_agent_evidence_layers(Map, roi, is_whole_country: bool, settings: dict):
    """เพิ่มชั้นข้อมูลหลักสำหรับให้ผู้ใช้เห็น evidence เดียวกับที่ Agent ใช้."""
    layer_settings = DEFAULT_AGENT_LAYER_SETTINGS.copy()
    layer_settings.update(settings.get("evidence_layers", {}))
    add_general_plan_layers(
        Map=Map,
        roi=roi,
        is_whole_country=is_whole_country,
        layer_settings=layer_settings,
    )


def run_multi_agent_if_requested(
    roi,
    is_whole_country: bool,
    selected_province: str,
    selected_district: str,
    multi_agent_settings: dict | None,
):
    if not multi_agent_settings:
        return None

    if not multi_agent_settings.get("run_multi_agent", False):
        st.info("ตั้งค่า Multi-Agent ใน Sidebar แล้วกด ▶️ Run Multi-Agent เพื่อเริ่มวิเคราะห์")
        return None

    task = multi_agent_settings.get("task", "").strip()
    if not task:
        st.warning("กรุณาใส่คำถามหรือเป้าหมายการวิเคราะห์ก่อน")
        return None

    selected_agents = multi_agent_settings.get("selected_agents", [])
    context = {
        "roi": roi,
        "is_whole_country": is_whole_country,
        "selected_province": selected_province,
        "selected_district": selected_district,
        "analysis_scale_m": 30,
        "local_data_note": multi_agent_settings.get("local_data_note", ""),
    }

    with st.spinner("Smart City CEO กำลังเรียก Agent แต่ละตัว..."):
        coordinator = CoordinatorAgent()
        outputs = coordinator.run(
            task=task,
            context=context,
            selected_agents=selected_agents,
        )

    st.session_state["multi_agent_outputs"] = outputs
    return outputs


def render_multi_agent_outputs(outputs: dict | None = None):
    if outputs is None:
        outputs = st.session_state.get("multi_agent_outputs")

    if not outputs:
        return

    st.markdown("### 🤖 Multi-Agent Results")

    report = outputs.get("Report Agent")
    if report:
        st.markdown("#### 📄 Executive Report")
        st.markdown(report.get("summary", ""))

    with st.expander("🔎 ดูผลลัพธ์แยกตาม Agent", expanded=False):
        for agent_name, result in outputs.items():
            st.markdown(f"#### {agent_name}")
            st.markdown(result.get("summary", ""))
            evidence = result.get("evidence")
            if evidence:
                st.json(evidence)

    st.download_button(
        "⬇️ Download Multi-Agent JSON",
        data=json.dumps(outputs, ensure_ascii=False, indent=2, default=str),
        file_name="urban_os_multi_agent_result.json",
        mime="application/json",
    )

# Suitability Persistence Patch

แก้ปัญหา Suitability Analysis วิเคราะห์แล้วผลหายหลัง Streamlit rerun

## สาเหตุ
`st.button()` คืนค่า `True` แค่รอบเดียว เมื่อแผนที่ Folium/Streamlit rerun จากการซูม แพน หรือ widget เปลี่ยน ค่า `run_suitability` กลับเป็น `False` ทำให้ layer และ summary ไม่ถูก render ซ้ำ

## วิธีแก้
- เพิ่ม `st.session_state["suitability_run_active"]`
- เพิ่มปุ่ม Clear สำหรับล้างผลลัพธ์
- ให้ผลวิเคราะห์คงอยู่จนกว่าจะกด Clear
- เก็บ summary/dataframe ไว้ใน `st.session_state`
- ลดการคำนวณ area statistics ซ้ำด้วย `suitability_config_signature`

ไฟล์ที่แก้:
- `components/sidebar.py`
- `core_engine/suitability.py`
- `app.py`

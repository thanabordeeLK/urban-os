# Patch: Fix nested Map Export expander

แก้ error:

`StreamlitAPIException` ที่เกิดจากการใช้ `st.expander()` ซ้อนอยู่ภายใน `st.expander()` อีกชั้น

## สาเหตุ
ในบาง mode เช่น Local Data Manager / Spatial Database / System Diagnostics
แผนที่ถูก render อยู่ภายใน expander:

`🗺️ แสดง/ซ่อนแผนที่พื้นที่อ้างอิง`

แต่ `Map Export Composer / GIS Export` ก็ใช้ `st.expander()` อีกชั้น
ทำให้ Streamlit แจ้ง error เพราะไม่รองรับ nested expander

## สิ่งที่แก้
เปลี่ยน `Map Export Composer / GIS Export` จาก `st.expander()` เป็น:
- `st.markdown("### 🖨️ Map Export Composer / GIS Export")`
- `st.container()`

จึงยังแสดง panel export เหมือนเดิม แต่ไม่ซ้อน expander แล้ว

## ไฟล์ที่แก้
- `components/map_export_composer.py`

## Commit message แนะนำ
`Fix nested map export expander`
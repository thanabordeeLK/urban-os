# Patch: Fix map not refreshing after analysis

แก้ปัญหา:
คำนวณ Suitability / UHI เสร็จแล้ว แต่แผนที่ยังไม่แสดง layer วิเคราะห์ หรือยังค้างแผนที่เดิม

สาเหตุ:
`streamlit-folium` อาจ reuse map component เดิมถ้า `key` ไม่เปลี่ยน
แม้จะมีการ add GEE layer ใหม่เข้าไปใน Folium map แล้วก็ตาม

สิ่งที่แก้:
- เพิ่ม `urban_os_map_refresh_token` ใน `st.session_state`
- เมื่อกด Run Suitability หรือ config วิเคราะห์เปลี่ยน จะเพิ่ม token
- `render_map()` ใช้ token นี้ใน `st_folium(key=...)`
- ทำให้ map component โหลด GEE tile layer ใหม่
- ยังรักษา center/zoom จาก session_state เท่าที่ทำได้
- เพิ่มข้อความยืนยันว่า Urban Suitability Class ถูกสร้างแล้ว

ไฟล์ที่แก้:
- `app.py`
- `components/map_renderer.py`
- `core_engine/suitability.py`

Commit message แนะนำ:
`Fix map refresh after suitability analysis`
# Patch: Fix uhi_settings UnboundLocalError

แก้ปัญหา:
`UnboundLocalError: local variable 'uhi_settings' referenced before assignment`

สาเหตุ:
`render_sidebar()` ส่งคืนค่า `"uhi_settings": uhi_settings` ทุกโหมด
แต่ตัวแปร `uhi_settings` ถูกสร้างเฉพาะเมื่อเลือกโหมด Urban Heat Island
เมื่ออยู่ General Plan / Suitability / Local Data Manager จึง error

สิ่งที่แก้:
เพิ่มค่าเริ่มต้นที่ต้นฟังก์ชัน `render_sidebar()`:
- suitability_config = {}
- multi_agent_settings = {}
- uhi_settings = {}

ไฟล์ที่แก้:
- components/sidebar.py

Commit message แนะนำ:
`Fix uhi settings default state`
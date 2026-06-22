# Patch: Local Data Manager Output Fix

แก้ปัญหา:
- เลือกเมนู Local Data Manager แล้วเห็นเฉพาะแผนที่ แต่ไม่เห็นแท็บ Registry / Add / Import Export

สาเหตุ:
- app.py มี mode สำหรับ Local Data Manager ในส่วน map-layer แล้ว
- แต่ยังไม่มี output branch ที่เรียก `render_local_data_manager(...)` หลัง `render_map(Map)`

สิ่งที่แก้:
- เพิ่ม branch:
  `elif selected_mode == "Local Data Manager": render_local_data_manager(...)`

ไฟล์ที่แก้:
- app.py

Commit message แนะนำ:
`Fix local data manager output panel`
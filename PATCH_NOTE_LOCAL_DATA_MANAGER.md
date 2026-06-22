# Patch: Local Data Manager

เพิ่ม Step 5: Local Data Manager

## สิ่งที่เพิ่ม
- เพิ่มเมนูใหม่ `Local Data Manager`
- จัดเก็บ GEE Asset ID เป็น registry ใน session state
- แบ่งประเภทข้อมูล:
  - Roads / Transport Network
  - Public Facilities / POI
  - Protected / Forest Constraint
  - Water / Waterways
  - Zoning / Land Use Plan
  - Parcels / Land Plots
  - Buildings / Built-up
  - Custom / Other
- เพิ่ม/ลบ asset ได้จากหน้า UI
- Download / Import registry เป็น JSON
- Download registry เป็น CSV
- Download CSV template
- ปุ่ม `Apply to Suitability Widgets`
  - ส่ง roads ไปยัง Road Accessibility
  - ส่ง public facilities ไปยัง Public Facility Proximity
  - ส่ง protected forest ไปยัง Forest Constraint
- Suitability Analysis จะ prefill asset จาก registry เมื่อ widget ยังไม่เคยถูกสร้าง

## ไฟล์ที่เพิ่ม/แก้
- app.py
- components/sidebar.py
- components/local_data_manager.py
- core_engine/report_export.py

## Commit message แนะนำ
`Add local data manager for GEE assets`
# Patch: Candidate Area Export

เพิ่ม Step 4: Candidate Area Export ใน Suitability Analysis

## สิ่งที่เพิ่ม
- เก็บ `suitability_final_class` ไว้ใน `st.session_state`
- เพิ่ม Candidate Area Export Panel ใต้ผล Suitability
- แปลงพื้นที่ Class 4–5 หรือ Class 5 เป็น polygon ด้วย `reduceToVectors`
- ดาวน์โหลดได้เป็น:
  - GeoJSON สำหรับเปิดใน QGIS / GIS software
  - CSV สำหรับดู centroid และพื้นที่แต่ละ polygon
- ตั้งค่าได้:
  - class ขั้นต่ำที่จะ export
  - vectorization scale
  - minimum polygon area
  - simplify tolerance
  - max features
- ล้าง cache candidate export อัตโนมัติเมื่อพื้นที่/น้ำหนัก/constraint เปลี่ยน

## ไฟล์ที่เพิ่ม/แก้
- app.py
- components/sidebar.py
- core_engine/suitability.py
- core_engine/report_export.py
- core_engine/candidate_export.py

## Commit message แนะนำ
`Add candidate area GeoJSON export`
# Patch: Public Facility Proximity Factor

เพิ่ม Step 3: Public Facility Proximity ใน Suitability Analysis

## สิ่งที่เพิ่ม
- เพิ่มน้ำหนัก Public Facility Proximity ใน Sidebar
- เพิ่มช่องใส่ GEE Asset ID ของสถานบริการสาธารณะ
- รองรับโรงพยาบาล โรงเรียน ศูนย์ราชการ ตลาด สถานีขนส่ง หรือ POI อื่น ๆ
- คำนวณระยะจากพื้นที่ถึงจุดบริการสาธารณะ
- ให้คะแนน:
  - ≤ 1,000m = 5
  - ≤ 3,000m = 4
  - ≤ 5,000m = 3
  - ≤ 10,000m = 2
  - > 10,000m = 1
- ถ้าไม่มี Facility Asset ระบบจะตัดน้ำหนัก facility ออกจากสมการอัตโนมัติ
- เพิ่ม Factor Layer: Public Facility Proximity
- เพิ่มข้อมูล facility ใน Export Report และ Validation Panel

## ไฟล์ที่แก้
- app.py
- components/sidebar.py
- core_engine/suitability.py
- core_engine/report_export.py

## Commit message แนะนำ
`Add public facility proximity factor`
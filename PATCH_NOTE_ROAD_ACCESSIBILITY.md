# Patch: Road Accessibility Factor

เพิ่ม Road Accessibility เป็นปัจจัยใน Suitability Analysis

## สิ่งที่เพิ่ม
- Slider น้ำหนัก `Road Accessibility`
- Sidebar สำหรับใส่ GEE Asset ID ของถนน/โครงข่ายคมนาคม
- Road distance score:
  - <= 500m = 5
  - <= 1,500m = 4
  - <= 3,000m = 3
  - <= 5,000m = 2
  - > 5,000m = 1
- ถ้ายังไม่มี Road Asset ระบบจะตัดน้ำหนักถนนออกจากสมการอัตโนมัติ
- Factor Layer: `Factor: Road Accessibility Suitability` ถูกซ่อนไว้ก่อนใน Layer Control

## ไฟล์ที่แก้
- app.py
- components/sidebar.py
- core_engine/suitability.py

## วิธีใช้
1. อัปโหลด shapefile/GeoJSON ถนนเข้า Google Earth Engine Assets
2. เอา Asset ID มาใส่ใน Sidebar > Road Accessibility
3. เปิด `ใช้ชั้นข้อมูลถนนเป็นปัจจัยวิเคราะห์`
4. กด Run Suitability Analysis

Commit message แนะนำ:
`Add road accessibility factor to suitability analysis`
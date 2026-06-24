# Patch: Step 8.5 Spatial Database Bridge

เพิ่มระบบเชื่อม Urban OS กับฐานข้อมูลพื้นที่ของหน่วยงาน โดยเน้น PostGIS / Supabase PostGIS

## สิ่งที่เพิ่ม
- เพิ่มเมนูใหม่ `Spatial Database`
- เพิ่ม `services/spatial_db_service.py`
- เพิ่ม `components/spatial_database_connector.py`
- รองรับการอ่าน Streamlit Secrets:
  - `[postgis] host / port / database / user / password`
  - หรือ `[postgis] url`
- ทดสอบการเชื่อมต่อ PostGIS
- แสดงรายชื่อ spatial tables จาก `geometry_columns`
- Preview table ตาม ROI ปัจจุบัน
- Register PostGIS layer เป็น Spatial DB Registry
- เพิ่มตัวเลือกใน Suitability Analysis:
  - Road Accessibility: GEE Asset ID หรือ PostGIS table
  - Public Facility Proximity: GEE Asset ID หรือ PostGIS table
  - Protected / Forest Constraints: GEE Asset ID หรือ PostGIS table
- แปลง PostGIS GeoJSON เป็น `ee.FeatureCollection` เพื่อส่งเข้า GEE calculation
- เพิ่ม dependencies:
  - SQLAlchemy
  - psycopg2-binary

## ข้อจำกัด v1
- เหมาะกับข้อมูลที่ถูก clip ตาม ROI หรือมี feature ไม่ใหญ่มาก
- ข้อมูลขนาดใหญ่มากควรสร้าง materialized view รายจังหวัด/อำเภอ หรือ sync ไป GEE Asset
- Optional SQL filter มีระบบกันคำสั่งอันตรายเบื้องต้น แต่ควรให้สิทธิฐานข้อมูลเป็น read-only

## ไฟล์ที่เพิ่ม/แก้
- `services/spatial_db_service.py`
- `components/spatial_database_connector.py`
- `components/sidebar.py`
- `core_engine/suitability.py`
- `app.py`
- `requirements.txt`
- `core_engine/report_export.py`

## Commit message แนะนำ
`Add spatial database bridge for PostGIS layers`
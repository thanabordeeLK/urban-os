# Patch: Step 8.8.1 Import to PostGIS / Supabase PostGIS

เพิ่มระบบนำเข้า Last Imported Layer จาก Import Wizard เข้าฐานข้อมูล PostGIS โดยตรง

## สิ่งที่เพิ่ม
ในหน้า `📥 Import Wizard` > tab `🐘 PostGIS Import Guide` เพิ่มส่วน:

`Direct Import to PostGIS / Supabase PostGIS`

## ความสามารถ
- Test PostGIS Connection
- เลือก schema
- เลือก target table
- เลือก geometry column
- เลือก import mode:
  - append
  - overwrite
- เลือกสร้าง attribute columns
- เลือกสร้าง spatial index
- จำกัดจำนวน features ที่ import
- Import Last Layer to PostGIS
- แสดงผลลัพธ์การ import

## ตารางที่สร้าง
ระบบสร้างตาราง PostGIS ที่มี column หลัก:
- `id`
- `geom`
- `properties` JSONB
- `layer_name`
- `category`
- `source_file`
- `imported_at`

ถ้าเปิด `Create attribute columns` ระบบจะแปลง properties เป็น columns เพิ่มให้ด้วย

## Spatial Index
ถ้าเปิด `Create spatial index` ระบบจะสร้าง GIST index ให้กับ geometry column

## ความปลอดภัย
- ชื่อ schema/table/column ถูก sanitize ก่อนใช้
- mode overwrite ต้องติ๊ก confirm ก่อน
- ใช้ Streamlit secrets `[postgis]` เดิมของระบบ

## ไฟล์ที่แก้
- `services/spatial_db_service.py`
- `components/import_wizard.py`

## Commit message แนะนำ
`Add import wizard direct PostGIS import`
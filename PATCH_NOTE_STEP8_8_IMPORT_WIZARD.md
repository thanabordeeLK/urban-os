# Patch: Step 8.8 Import Wizard

เพิ่มระบบนำเข้าข้อมูล GIS จากไฟล์ผู้ใช้

## Menu ใหม่
เพิ่มเมนูใน sidebar:

`📥 Import Wizard`

## รองรับไฟล์
- Shapefile ZIP (`.zip` ที่มี `.shp/.shx/.dbf/.prj`)
- GeoJSON (`.geojson`, `.json`)
- KML / KMZ (`.kml`, `.kmz`)
- CSV พิกัด X,Y (`.csv`)

## ความสามารถ
- Upload file
- ตรวจชนิดไฟล์
- อ่าน geometry / attribute
- Preview attribute table
- Preview geometry บนแผนที่
- เลือก category ของข้อมูล
- Export เป็น GeoJSON
- Export เป็น Shapefile ZIP
- Add to Imported Registry
- Download metadata JSON
- Generate ogr2ogr command สำหรับนำเข้า PostGIS

## ข้อจำกัด
- Import Wizard เวอร์ชันนี้ยังเก็บข้อมูลใน session เป็นหลัก
- ยังไม่เขียนเข้า PostGIS โดยตรง เพื่อป้องกันปัญหา credential/permission
- CSV ต้องเลือก column Longitude/X และ Latitude/Y
- KML/KMZ รองรับ Point, LineString และ Polygon แบบพื้นฐาน

## ไฟล์ที่เพิ่ม/แก้
- `components/import_wizard.py`
- `app.py`
- `components/sidebar.py`
- `requirements.txt`

## Commit message แนะนำ
`Add GIS import wizard`
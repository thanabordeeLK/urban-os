# Patch: Step 8.7.6 Map Export Composer + GIS Export

เพิ่มระบบส่งออกแผนที่และข้อมูล GIS รวมถึง Shapefile

## สิ่งที่เพิ่ม
- เพิ่ม `components/map_export_composer.py`
- เพิ่ม panel ใต้ Map Workspace:
  - `🖨️ Map Export Composer / GIS Export`
- เพิ่ม dependency:
  - `pyshp>=2.3.1`

## Map Export
รองรับ:
- Export Current Interactive Map HTML
- Download Map Layout Summary Markdown

## GIS Export
รองรับ:
- ROI Boundary GeoJSON
- ROI Boundary Shapefile ZIP
- Candidate Areas GeoJSON
- Candidate Areas Shapefile ZIP

## Shapefile ZIP
ไฟล์ zip จะประกอบด้วย:
- `.shp`
- `.shx`
- `.dbf`
- `.prj`
- `.cpg`
- `field_mapping.json`

## ข้อจำกัด
- Shapefile รองรับเฉพาะ vector geometry
- Raster เช่น Suitability / Heat Risk ต้องแปลงเป็น polygon ก่อน เช่น Candidate Area Export
- DBF field name จำกัด 10 ตัวอักษร ระบบจึงแนบ `field_mapping.json`

## Commit message แนะนำ
`Add map export composer and shapefile export`
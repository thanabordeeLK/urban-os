# Patch: Step 8.7 Spatial Database Template / PostGIS Schema Generator

เพิ่ม PostGIS Schema Generator ในเมนู Spatial Database

## สิ่งที่เพิ่ม
- เพิ่ม `services/postgis_schema_generator.py`
- เพิ่ม `components/postgis_schema_generator.py`
- เพิ่ม tab ใหม่ใน Spatial Database: `Schema Generator`
- สร้าง SQL schema สำหรับ Urban OS:
  - urban_layers
  - roads
  - public_facilities
  - protected_areas
  - zoning
  - parcels
  - buildings
  - waterways
  - candidate_areas
  - uhi_hotspots
  - planning_projects
- สร้าง GIST index สำหรับ geometry
- สร้าง attribute index ที่ใช้บ่อย
- สร้าง table/column comments
- สร้าง views:
  - v_enabled_layers
  - v_development_candidates_high
  - v_heat_hotspots_high
- Download ได้:
  - PostGIS Schema SQL
  - CSV Templates ZIP
  - Data Dictionary CSV
- เพิ่ม template files ใน `templates/postgis/`

## Commit message แนะนำ
`Add PostGIS schema generator`
# Patch: Step 8.7.4 Auto Criteria Score from PostGIS Geometry

เพิ่มการสร้างคะแนน Advanced Criteria จาก PostGIS geometry โดยตรง

## สิ่งที่เพิ่ม
- เพิ่ม `core_engine/postgis_geometry_scoring.py`
- เพิ่ม UI `🗺️ Auto Criteria Score from PostGIS Geometry`
- ทุก factor มี checkbox แยกสำหรับเปิด geometry scoring:
  - Population Capacity
  - Infrastructure Capacity
  - Service Coverage
  - Multi-Hazard Risk
  - Socioeconomic / Equity
  - Zoning / Legal Compliance

## หลักการ
ระบบดึง geometry จาก PostGIS ตาม ROI แล้วแปลงเป็น `ee.FeatureCollection`
จากนั้น rasterize `score_field` เป็น score image 1-5 และใช้แทนคะแนน manual/auto-fill ใน Suitability Engine

## Field ที่แนะนำ
- `population_registry.population_capacity_score`
- `infrastructure_capacity.capacity_score`
- `service_areas.coverage_score`
- `hazard_zones.risk_level`
- `socioeconomic.equity_score`
- `planning_controls.zoning_score`

## Hazard
ถ้าใช้ `risk_level` ให้เปิด invert score/risk:
- risk 1 → suitability 5
- risk 5 → suitability 1

## Fallback
ถ้าไม่พบ geometry ใน ROI หรือเกิด error ระบบ fallback เป็น default score 3 เพื่อไม่ให้แอปล่ม

## Commit message แนะนำ
`Add PostGIS geometry scoring for advanced criteria`
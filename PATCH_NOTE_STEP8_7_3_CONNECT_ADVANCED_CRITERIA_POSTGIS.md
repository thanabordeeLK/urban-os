# Patch: Step 8.7.3 Connect Advanced Criteria to PostGIS

เชื่อม Advanced Planning Criteria กับ PostGIS แบบ auto-fill และเพิ่มการตรวจ Zoning / Legal Compliance รายข้อ

## สิ่งที่เพิ่ม
- เพิ่ม `components/advanced_criteria_postgis.py`
- เพิ่ม helper ใน `services/spatial_db_service.py`
  - `summarize_postgis_numeric_by_roi`
  - `fetch_postgis_records_by_roi`
- ปรับ `core_engine/advanced_planning_criteria.py`
  - Zoning score รองรับ criteria รายข้อ
  - criteria ที่ไม่ติ๊กจะไม่มีผลต่อ zoning score
- ปรับ `components/sidebar.py`
  - เพิ่ม `Advanced Criteria Data Source: Manual / PostGIS`
  - เพิ่ม auto-fill จาก PostGIS สำหรับ:
    - Population Capacity
    - Infrastructure Capacity
    - Service Coverage
    - Hazard Risk
    - Socioeconomic / Equity
  - ปรับ Zoning / Legal Compliance ให้มี checkbox รายปัจจัย

## Zoning / Legal Compliance รายข้อ
แต่ละข้อมี checkbox แยก:
- permitted_use
- prohibited_use
- far
- bcr
- osr
- height_limit_m
- buffer_rule

หลักการ:
- ไม่ติ๊ก = ไม่มีผล
- ติ๊ก = ถูกนำไปเฉลี่ยเป็น zoning score
- master checkbox `ใช้ผังสี / ข้อกำหนดกฎหมาย เป็นปัจจัยคะแนน` ยังเป็นตัวเปิด/ปิดใหญ่
- Zoning / Legal Compliance ยังอยู่ท้ายสุดของสมการ

## ตาราง PostGIS ที่รองรับ
- `urban_os.population_registry`
- `urban_os.household_statistics`
- `urban_os.infrastructure_capacity`
- `urban_os.service_areas`
- `urban_os.hazard_zones`
- `urban_os.socioeconomic`
- `urban_os.planning_controls`

## Commit message แนะนำ
`Connect advanced criteria to PostGIS`
# Patch: Step 7 UHI Heat Penalty in Suitability

เพิ่ม Step 7: เชื่อม Urban Heat Island / LST เข้ากับ Suitability Analysis

## สิ่งที่เพิ่ม
- เพิ่มน้ำหนัก `Urban Heat Risk / UHI Penalty`
- เพิ่ม checkbox ใน Suitability Analysis:
  `ใช้ UHI / Heat Risk เป็นปัจจัยหักคะแนนความเหมาะสม`
- ใช้ Landsat 8/9 Collection 2 Level 2:
  - `ST_B10` → LST Celsius
  - `QA_PIXEL` → mask เมฆ/เงาเมฆ
- Heat Risk แบ่งได้ 2 แบบ:
  - relative: percentile ภายใน ROI
  - absolute: threshold °C
- แปลง Heat Risk เป็น Suitability Score:
  - Heat Risk 1 → Suitability 5
  - Heat Risk 2 → Suitability 4
  - Heat Risk 3 → Suitability 3
  - Heat Risk 4 → Suitability 2
  - Heat Risk 5 → Suitability 1
- เพิ่ม Factor Layers:
  - Urban Heat Risk Suitability
  - Heat Risk Class
- ปรับ DPT Planning Standards Preset weights:
  - Slope 0.10
  - Flood 0.18
  - Land Cover 0.14
  - Urbanization 0.08
  - Road 0.18
  - Public Facility 0.18
  - Water 0.04
  - Heat 0.10
- เพิ่ม Heat Penalty ใน Export Report / Validation Notes

## ไฟล์ที่แก้
- config/planning_standards.py
- components/sidebar.py
- core_engine/suitability.py
- core_engine/report_export.py
- app.py

## Commit message แนะนำ
`Add UHI heat penalty to suitability analysis`
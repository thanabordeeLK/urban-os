# Patch: Planning Standards Preset

เพิ่มการนำเกณฑ์/มาตรฐานด้านผังเมืองมาใช้เป็น preset ใน Urban OS

## สิ่งที่เพิ่ม
- เพิ่ม `config/planning_standards.py`
- เพิ่ม DPT Standards Profile:
  - PSA Suitability
  - Restrictive Area / Veto
  - Accessibility
  - Community Utilities and Facilities
  - Density Reference
- ปรับค่า default weights ของ Suitability:
  - Slope = 0.10
  - Flood = 0.20
  - Land Cover = 0.15
  - Urbanization = 0.10
  - Road Accessibility = 0.20
  - Public Facility Proximity = 0.20
  - Water Proximity = 0.05
- เพิ่มปุ่ม `Apply DPT Standards Preset` ใน Suitability Analysis
- ตั้งค่าเริ่มต้น:
  - Road max distance = 5,000m
  - Facility max distance = 10,000m
  - Forest/Protected buffer = 100m
  - WDPA เปิดเป็น hard constraint
- เพิ่มปุ่ม `Apply DPT UHI Preset` ใน Urban Heat Island
- เพิ่ม standard profile ใน export report

## เหตุผล
เอกสารมาตรฐานใช้แนวคิด Potential Surface Analysis (PSA), Restrictive Area/Veto,
Accessibility, Community Utilities and Facilities และ Density Reference
จึงนำมาปรับเป็น preset สำหรับ scoring model โดยไม่ล็อกเป็นข้อกำหนดตายตัว

## Commit message แนะนำ
`Add planning standards preset for suitability and UHI`
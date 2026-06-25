# Patch: Step 8.7.5 Advanced Criteria Score Audit & Validation

เพิ่มระบบตรวจสอบที่มาของคะแนน Advanced Criteria หลังจากเปิดใช้ Manual / PostGIS Auto-fill / PostGIS Geometry Score

## สิ่งที่เพิ่ม
- เพิ่ม `components/advanced_criteria_audit.py`
- เพิ่ม panel ในหน้า Suitability Analysis:
  - `🧪 Advanced Criteria Score Audit & Validation`
- เพิ่ม audit rows เข้า `st.session_state`
  - `advanced_criteria_audit_rows`
  - `advanced_criteria_audit_json`

## ตรวจสอบสถานะของแต่ละปัจจัย
ระบบจะแสดง 6 ปัจจัย:
- Population Capacity
- Infrastructure Capacity
- Service Coverage
- Multi-Hazard Safety
- Socioeconomic / Equity
- Zoning / Legal Compliance

สถานะที่ตรวจได้:
- OK - PostGIS Geometry Score
- OK - PostGIS Geometry Score (Inverted)
- Manual / Auto-fill
- Fallback Score 3
- Error / Fallback
- No effect

## ตาราง Audit
แสดง:
- factor
- source
- status
- score
- normalized_weight
- table_name
- score_field
- feature_count
- note

## Export
เพิ่มปุ่มดาวน์โหลด:
- Download Score Audit JSON
- Download Score Audit CSV
- Download Methodology Markdown

## Zoning Audit
Zoning / Legal Compliance ยังอยู่ท้ายสุด และ audit จะแสดง:
- เปิดใช้หรือไม่
- source
- status
- checked rules
- score
- normalized weight

## Commit message แนะนำ
`Add advanced criteria score audit`
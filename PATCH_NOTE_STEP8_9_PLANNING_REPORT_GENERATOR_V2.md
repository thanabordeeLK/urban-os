# Patch: Step 8.9 Planning Report Generator V2

เพิ่มระบบสร้างรายงานผังเมืองอัตโนมัติจากผลวิเคราะห์ล่าสุดใน Urban OS

## Menu ใหม่
เพิ่มเมนูใน Sidebar:

`📄 Planning Report`

## ไฟล์ใหม่
- `components/planning_report_generator.py`

## ไฟล์ที่แก้
- `app.py`
- `components/sidebar.py`

## Output ที่รองรับ
- Markdown Report
- HTML Report
- Evidence JSON
- Summary CSV

## ข้อมูลที่ดึงเข้า Report
- ข้อมูลพื้นที่ศึกษา จังหวัด/อำเภอ
- Suitability Summary
- Suitability area table
- Normalized weights
- Urban Heat Island / LST summary
- Heat Risk area table
- Candidate Area table
- Imported Layer / PostGIS metadata
- Imported Layer Overlay metadata
- Advanced Criteria Score Audit
- Map Workspace metadata เช่น Map View, Basemap, Target scale, Current actual scale

## Report sections
- ข้อมูลพื้นที่ศึกษา
- วัตถุประสงค์
- Suitability Analysis
- Urban Heat Island / LST
- Candidate Areas
- Imported Layers / PostGIS
- Advanced Criteria / Score Audit
- Map Workspace / Export Metadata
- ข้อเสนอเชิงผังเมืองเบื้องต้น
- ข้อจำกัดและ Data Gaps
- หมายเหตุการใช้งาน

## วิธีใช้งาน
1. Run Suitability Analysis
2. Generate Candidate Area ถ้าต้องการ
3. Run UHI ถ้าต้องการ
4. Import GIS / PostGIS / Overlay ถ้าต้องการ
5. ไปที่ `Planning Report`
6. ตั้งค่า sections
7. Download Markdown / HTML / JSON / CSV

## หมายเหตุ
- HTML Report สามารถเปิดใน browser แล้ว Print / Save as PDF ได้
- Evidence JSON เก็บข้อมูลสนับสนุนรายงานเพื่อ audit / traceability
- Summary CSV ใช้สรุป metric สำคัญต่อใน Excel ได้

## Commit message แนะนำ
`Add planning report generator v2`
# Patch: Step 9 Candidate Area Ranking & Recommendation

เพิ่มระบบจัดอันดับพื้นที่ Candidate และสร้างข้อเสนอแนะเชิงผังเมือง

## Menu ใหม่
เพิ่มเมนูใน Sidebar:

`🏆 Candidate Ranking`

## ไฟล์ใหม่
- `components/candidate_ranking.py`

## ไฟล์ที่แก้
- `app.py`
- `components/sidebar.py`
- `components/planning_report_generator.py`

## ความสามารถ
- อ่าน `candidate_export_df` จาก Candidate Area Export
- จัดอันดับพื้นที่ candidate ตามคะแนนรวม
- สร้าง Priority Class:
  - A: พื้นที่พร้อมพัฒนาระยะสั้น
  - B: พื้นที่เหมาะสม / ระยะกลาง
  - C: พื้นที่มีศักยภาพแบบมีเงื่อนไข
  - D: ไม่ใช่ candidate หลัก
- สร้าง recommendation รายพื้นที่
- ระบุ constraint/risk notes
- Export CSV / Markdown / HTML / JSON
- ส่งผล ranking เข้า Planning Report V2

## Scoring structure
- Suitability score: 45 คะแนน
- Area suitability score: 20 คะแนน
- Data readiness score: 15 คะแนน
- Risk adjustment จาก UHI และสัดส่วนพื้นที่เหมาะสมสูง

## Workflow
1. Run Suitability Analysis
2. Generate Candidate Area Export
3. ไปที่ Candidate Ranking
4. ตั้งค่า ideal area range
5. Download Ranking CSV / Markdown / HTML / JSON
6. ไปที่ Planning Report เพื่อรวมผล ranking ในรายงานหลัก

## หมายเหตุ
คะแนนนี้เป็น heuristic เพื่อคัดกรองเบื้องต้น
ยังไม่แทนการตรวจภาคสนาม กฎหมายผังเมือง กรรมสิทธิ์ ราคาที่ดิน และข้อจำกัดหน่วยงาน

## Commit message แนะนำ
`Add candidate area ranking and recommendations`
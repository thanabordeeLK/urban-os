# Patch: Step 8 Standards-Based Feasibility Bridge

เพิ่ม Step 8: เชื่อม Suitability + Candidate Area + UHI + Planning Standards Preset
เพื่อสร้างรายงานความเป็นไปได้เบื้องต้นตามมาตรฐานผังเมือง

## สิ่งที่เพิ่ม
- เพิ่ม `core_engine/feasibility_bridge.py`
- เพิ่ม panel ใต้ Candidate Area Export:
  `Standards-Based Feasibility Bridge`
- ใช้ข้อมูลจาก session:
  - Suitability summary
  - Suitability class area table
  - Candidate Area Export DataFrame
  - Planning Standards Preset
  - Suitability config / weights / heat penalty status
- จัดลำดับ Candidate Area เป็น A/B/C/D
- สร้าง Feasibility Report แบบ deterministic โดยไม่ต้องใช้ API
- ตัวเลือกให้ GPT Planning Agent ช่วยเขียนรายงานเพิ่มเติม หากมี `OPENAI_API_KEY`
- Export:
  - Feasibility Report Markdown
  - Evidence JSON
  - Candidate Priority CSV
- ล้าง feasibility cache อัตโนมัติเมื่อ candidate export ถูกสร้างใหม่/ล้าง

## Workflow
1. Run Suitability Analysis
2. Generate Candidate GeoJSON
3. Generate Standards-Based Feasibility Report
4. Download report/evidence/candidate priority

## ไฟล์ที่เพิ่ม/แก้
- app.py
- core_engine/feasibility_bridge.py
- core_engine/candidate_export.py
- core_engine/report_export.py

## Commit message แนะนำ
`Add standards-based feasibility bridge`

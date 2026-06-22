# Patch: Suitability Export Report

เพิ่ม Step 2 ระหว่างรอ Road Asset:
- Export ตารางสรุปพื้นที่เป็น CSV
- Export รายงานผลวิเคราะห์เป็น Markdown
- เพิ่ม Model Validation / Data Completeness checklist
- รายงานแยกพื้นที่ศึกษา, summary, suitability class area, weights, road/forest inputs และข้อควรตรวจสอบเพิ่ม

ไฟล์ที่เพิ่ม/แก้:
- app.py
- core_engine/report_export.py

Commit message แนะนำ:
`Add suitability export report and validation panel`
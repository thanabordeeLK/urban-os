# Patch: Step 8.7.8 Print Layout PNG / PDF Export

เพิ่มระบบจัดหน้าแผนที่เพื่อส่งออกเป็น HTML / PNG / PDF

## สิ่งที่เพิ่ม
ใน `🖨️ Map Export Composer / GIS Export` เพิ่ม tab ใหม่:

`🖨️ Print Layout`

## Export ที่รองรับ
- Print Layout HTML
- Print Layout PNG
- Print Layout PDF

## Preset Layout
- Dashboard 16:9
- A4 Landscape
- A3 Landscape
- A1 Landscape

## ข้อมูลที่อยู่ใน Layout
- ชื่อแผนที่
- คำอธิบายพื้นที่
- จังหวัด / อำเภอ
- Map View 1 / 2 / 3
- Analysis Layer ของแต่ละ View
- Basemap ของแต่ละ View
- Target export scale
- Current actual scale
- Zoom
- North Arrow
- Legend
- Scale note
- วันที่จัดทำ
- หมายเหตุ

## Dependency ที่เพิ่ม
- `pillow>=10.0.0,<11`
- `reportlab>=4.0.0,<5`

## หมายเหตุสำคัญ
PNG/PDF ในขั้นนี้เป็น static print layout summary ที่สร้างฝั่ง server
ยังไม่ใช่ screenshot ของ web map tiles แบบ pixel-perfect

หากต้องการ capture ภาพแผนที่จริงจาก browser พร้อม tile/layer ตามที่เห็นบนจอ
ให้ทำต่อในขั้นถัดไปเป็น Screenshot Engine / Browser Capture

## ไฟล์ที่แก้
- `components/map_export_composer.py`
- `requirements.txt`

## Commit message แนะนำ
`Add print layout PNG and PDF export`
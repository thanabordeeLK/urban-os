# Patch: Clarify Static Print Layout vs Pixel Capture

แก้ความสับสนจาก PNG export ที่ออกมาเป็นช่อง placeholder

## สาเหตุ
ปุ่ม `Download Print Layout PNG` ใน Step 8.7.8 เป็น static layout summary ที่สร้างฝั่ง server
จึงไม่สามารถ capture web map tiles จริงได้ และจะแสดงเป็น placeholder

ภาพแผนที่จริงต้องใช้ workflow ของ Step 8.7.9:
`📸 Pixel Capture`

## สิ่งที่แก้
- เปลี่ยนหัวข้อ `Print Layout PNG / PDF Export` เป็น `Static Print Layout Summary PNG / PDF`
- เปลี่ยนปุ่ม:
  - `Download Print Layout PNG` → `Download Static Summary PNG`
  - `Download Print Layout PDF` → `Download Static Summary PDF`
  - `Download Print Layout HTML` → `Download Static Layout HTML`
- เพิ่ม warning ชัดเจนว่า PNG/PDF ใน tab นี้เป็น static summary
- ชี้ให้ใช้ tab `📸 Pixel Capture` เมื่อต้องการภาพแผนที่จริง
- ปรับข้อความ placeholder ให้บอกว่าเป็น static summary

## ไฟล์ที่แก้
- `components/map_export_composer.py`

## Commit message แนะนำ
`Clarify static print layout and pixel capture workflow`
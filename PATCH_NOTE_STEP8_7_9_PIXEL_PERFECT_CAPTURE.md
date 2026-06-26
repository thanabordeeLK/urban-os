# Patch: Step 8.7.9 Pixel-Perfect Map Capture

เพิ่มระบบสร้างไฟล์ HTML สำหรับ capture ภาพแผนที่จริงจาก browser

## สิ่งที่เพิ่ม
ใน `🖨️ Map Export Composer / GIS Export` เพิ่ม tab ใหม่:

`📸 Pixel Capture`

## Export ที่รองรับ
- Download Pixel Capture HTML
- Download Capture Instructions Markdown

## หลักการ
ไฟล์ Pixel Capture HTML จะ embed current interactive map ไว้ใน capture sheet
ผู้ใช้เปิดไฟล์ HTML ใน Chrome/Edge แล้ว:
- รอให้ basemap/layer โหลดครบ
- กด `Print / Save as PDF`
- หรือกด `Export PNG (experimental)`

## เหตุผลที่ใช้แนวทางนี้
ไม่เพิ่ม dependency หนัก เช่น Playwright / Chromium บน Streamlit Cloud
จึงลดความเสี่ยงติดตั้งล้มเหลว และเหมาะกับ deployment ปัจจุบัน

## ข้อจำกัด
- PNG capture แบบ browser-side อาจติด CORS ของ tile บางแหล่ง
- ถ้า PNG ไม่สำเร็จ ให้ใช้ Print/Save as PDF หรือ screenshot ของ browser
- HTML/PDF จะเก็บ map tile/layer ตามที่ browser โหลดได้
- Scale ยังเป็นค่า approximate ของ web map ต้องตรวจซ้ำใน GIS layout ถ้าใช้ทางราชการ

## Preset
- Dashboard 16:9 / 1920x1080
- A4 Landscape @150dpi / 1754x1240
- A3 Landscape @150dpi / 2480x1754
- A1 Landscape preview / 3508x2480
- Square 1600x1600

## ไฟล์ที่แก้
- `components/map_export_composer.py`

## Commit message แนะนำ
`Add pixel perfect map capture HTML export`
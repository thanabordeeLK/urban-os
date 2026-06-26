# Patch: Step 8.7.10 One-Click True PNG Export from Current Map View

เพิ่มระบบ One-Click PNG Export จาก Map View ที่เลือกใน browser โดยตรง

## สิ่งที่เพิ่ม
ใน tab `📸 Pixel Capture` เพิ่มส่วนใหม่:

`One-Click True PNG Export จาก Map View`

## ความสามารถ
- เลือก Map View ที่จะ export:
  - Map View 1
  - Map View 2
  - Map View 3
- เลือกขนาด PNG canvas:
  - Dashboard 16:9 / 1920x1080
  - A4 Landscape @150dpi / 1754x1240
  - A3 Landscape @150dpi / 2480x1754
  - A1 Landscape preview / 3508x2480
  - Square 1600x1600
- แสดง browser capture preview ใน Streamlit โดยตรง
- กด `Export PNG (experimental)` ใน preview เพื่อดาวน์โหลด PNG
- Download Same Capture HTML เพื่อเปิดใน Chrome/Edge ได้เหมือนเดิม

## หลักการทำงาน
- สร้าง map สำหรับ Map View ที่เลือกใหม่จาก session state
- ใช้ layer/basemap/scale ของ View นั้น
- สร้าง HTML capture sheet
- embed HTML ใน Streamlit ผ่าน `streamlit.components.v1.html`
- PNG export ทำงานฝั่ง browser เพื่อลด dependency หนักบน Streamlit Cloud

## ข้อจำกัด
- Tile บางแหล่ง เช่น Esri / OSM / GEE อาจติด CORS ทำให้ PNG capture จากปุ่มทดลองไม่สำเร็จ
- ถ้าเกิด CORS ให้ใช้ Print / Save as PDF หรือ Download Same Capture HTML แล้วเปิดใน Chrome/Edge เพื่อ screenshot
- ระบบนี้ไม่ติดตั้ง Playwright/Chromium เพื่อหลีกเลี่ยงปัญหา deployment บน Streamlit Cloud

## ไฟล์ที่แก้
- `components/map_export_composer.py`

## Commit message แนะนำ
`Add one click browser PNG export for map views`
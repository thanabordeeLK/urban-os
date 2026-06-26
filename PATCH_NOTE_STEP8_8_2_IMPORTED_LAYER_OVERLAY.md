# Patch: Step 8.8.2 Imported Layer Overlay on Map Workspace

เพิ่มระบบแสดงชั้นข้อมูลที่นำเข้าแล้วเป็น overlay บน Map Workspace

## สิ่งที่เพิ่ม
เพิ่มไฟล์ใหม่:

- `components/imported_layer_overlay.py`

แก้ไฟล์:

- `components/import_wizard.py`
- `app.py`

## UI ใหม่
ในหน้า `📥 Import Wizard` เพิ่ม tab:

`🧩 Overlay`

## Overlay source
รองรับ 3 แหล่งข้อมูล:

1. `Session: Last Imported Layer`
   - ใช้ GeoJSON ล่าสุดจาก Upload & Preview

2. `PostGIS: Last Imported Table`
   - ใช้ตารางล่าสุดจาก Direct Import to PostGIS

3. `PostGIS: Custom Table`
   - ระบุ `schema.table` และ geometry column เอง

## Style controls
- เปิด/ปิด overlay
- ตั้งชื่อ layer บนแผนที่
- เลือก line color
- เลือก fill color
- line weight
- line opacity
- fill opacity
- tooltip fields

## PostGIS filter
เมื่อใช้ PostGIS source:
- Clip to current ROI bbox
- Fetch limit
- Optional safe WHERE filter

## การทำงาน
เมื่อเปิด overlay แล้ว ระบบจะ add layer นี้ทับบน `Map Workspace`
และสามารถดูร่วมกับ:
- Suitability Analysis
- Urban Heat Island
- General Plan
- Spatial Database reference map
- Export PNG / HTML / PDF workflow

## หมายเหตุ
- Session source จะอยู่ได้ตาม session ของ Streamlit
- ถ้าต้องการถาวรให้ Import to PostGIS ก่อน แล้วใช้ PostGIS overlay
- Overlay ถูกเพิ่มก่อน render map จึงส่งต่อไปยัง Map Export Composer / Pixel Capture ได้

## Commit message แนะนำ
`Add imported layer overlay on map workspace`
# Patch: Fix Map View Scale Controls

แก้ปัญหา:
- ปรับ scale ในแต่ละ Map View แล้วแผนที่ไม่เปลี่ยน zoom
- Export scale ด้านบนซ้ำซ้อนกับ scale ของแต่ละ Map View

## สิ่งที่แก้
1. ตัด `Export scale` และ `Export preset` ที่อยู่ด้านบนของ Map Workspace ออก
2. ให้ scale ควบคุมเฉพาะระดับ Map View 1 / 2 / 3
3. เพิ่ม scale เข้า map key เพื่อบังคับให้ `st_folium` render ใหม่เมื่อเปลี่ยน scale
4. แก้ `Current Mode Layers` ให้สามารถ apply scale กับ zoom ได้ด้วย ไม่ใช่เฉพาะ layer เฉพาะ
5. ยังคง Map height อยู่ด้านบน เพราะเป็นค่าร่วมของพื้นที่แสดงผล

## ผลลัพธ์
- Map View 1 เปลี่ยน scale แล้วมีผลเฉพาะ View 1
- Map View 2 เปลี่ยน scale แล้วมีผลเฉพาะ View 2
- Map View 3 เปลี่ยน scale แล้วมีผลเฉพาะ View 3
- ไม่มี Export scale ด้านบนที่ซ้ำซ้อนแล้ว

## ไฟล์ที่แก้
- `components/map_renderer.py`

## Commit message แนะนำ
`Fix per-view map scale controls`
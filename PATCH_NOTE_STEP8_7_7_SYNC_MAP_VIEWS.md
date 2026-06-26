# Patch: Step 8.7.7 Lock Pan-Zoom / Sync Map Views

เพิ่มระบบล็อกตำแหน่งแผนที่เพื่อเปรียบเทียบ Map View 1 / 2 / 3 ให้ตรงพื้นที่เดียวกัน

## สิ่งที่เพิ่ม
ใน `🖥️ Map Workspace` เพิ่ม control:

- `🔒 Sync Map Views`
  - ไม่ซิงก์
  - ซิงก์ตาม Map View 1
  - ซิงก์ตาม Map View 2
  - ซิงก์ตาม Map View 3
  - ซิงก์ทุก View (ล่าสุด)
- `ล็อก zoom ด้วย`
- `Reset Sync Viewport`

## หลักการทำงาน
- หากเลือก `ซิงก์ตาม Map View 1`
  - Pan/Zoom ใน Map View 1 จะกลายเป็น viewport ต้นแบบ
  - Map View 2 และ 3 จะตาม center/zoom ของ View 1 หลัง rerun
- หากเลือก `ซิงก์ทุก View (ล่าสุด)`
  - View ล่าสุดที่มีการเปลี่ยน pan/zoom จะเป็นแหล่ง sync
- หากไม่เปิด `ล็อก zoom ด้วย`
  - ระบบจะ sync เฉพาะ center โดยยังให้แต่ละ view ใช้ zoom/scale ของตัวเอง

## ข้อมูลที่บันทึกใน session_state
- `map_sync_center`
- `map_sync_zoom`
- `map_sync_source_view`
- `map_sync_token`
- `map_view_1_center`, `map_view_1_zoom`
- `map_view_2_center`, `map_view_2_zoom`
- `map_view_3_center`, `map_view_3_zoom`

## ไฟล์ที่แก้
- `components/map_renderer.py`
- `components/map_export_composer.py`

## Commit message แนะนำ
`Add map view pan zoom synchronization`
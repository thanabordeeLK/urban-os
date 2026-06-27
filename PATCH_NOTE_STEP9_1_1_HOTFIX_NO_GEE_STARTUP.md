# Hotfix: Step 9.1.1 Non-GEE Safe Startup

แก้ปัญหาหลังทำ GEE Auth + User Roles แล้วหน้า Planning Report ยังมี error จาก Area Selector:

- `Earth Engine client library not initialized. Run ee.Initialize()`
- `สร้างพื้นที่วิเคราะห์ไม่สำเร็จ`

## สาเหตุ
แม้ระบบจะไม่ `st.stop()` แล้ว แต่ Sidebar ยังเรียก:

- `get_provinces()`
- `get_districts()`
- `get_roi()`

ซึ่งต้องใช้ Earth Engine จึงเกิด error ซ้ำในหน้าเมนูที่จริง ๆ ไม่ต้องใช้ GEE เช่น Planning Report

## สิ่งที่แก้

### `components/sidebar.py`
เพิ่ม fallback ใน `render_area_selector()`:

ถ้า `st.session_state["gee_ready"] == False`

- ไม่เรียก `get_provinces()`
- ไม่เรียก `get_districts()`
- ไม่เรียก `get_roi()`
- ตั้งพื้นที่อ้างอิงเป็นระดับประเทศ
- return `roi=None`
- แสดงข้อความอธิบายว่า GEE ยังไม่พร้อม

### `components/map_renderer.py`
ปรับ `add_boundary()`:

ถ้า `roi=None` และ GEE ยังไม่พร้อม จะไม่แสดง warning ซ้ำ

### `app.py`
เพิ่มคำอธิบายว่า:

- หน้า public/report ยังเปิดได้
- หน้า analysis จะถูกซ่อนจนกว่าจะตั้งค่า GEE Service Account

## ผลลัพธ์หลัง patch
เมื่อ GEE token หมดอายุหรือ Service Account ยังไม่ตั้งค่า:

- Dashboard ไม่ล้ม
- Sidebar ไม่ error ซ้ำ
- Planning Report ยังเปิดได้
- เมนูที่ต้องใช้ GEE จะยังถูกซ่อนตามสิทธิ์/สถานะระบบ
- เมื่อใส่ Service Account ถูกต้องแล้ว General Plan / Suitability / UHI จะกลับมาใช้งานได้

## Commit message แนะนำ

`Fix non-GEE startup area selector`
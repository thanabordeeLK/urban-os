# Patch: Map Layout Comparison + Export Scale Controls

เพิ่มการเลือกแสดงแผนที่แบบ 1 / 2 / 3 หน้าจอ และตั้งค่ามาตราส่วนเป้าหมายสำหรับ export

## สิ่งที่เพิ่ม
- Sidebar panel ใหม่: `🖥️ Map Layout / Export Scale`
- เลือกจำนวนหน้าจอแผนที่: 1 / 2 / 3 หน้าจอ
- เลือกมาตราส่วนเป้าหมาย:
  - Auto / ตาม zoom
  - 1 : 500
  - 1 : 1,000
  - 1 : 2,000
  - 1 : 5,000
  - 1 : 10,000
  - 1 : 25,000
  - 1 : 50,000
  - 1 : 100,000
  - 1 : 250,000
- ตัวเลือก `ปรับ zoom ให้ใกล้มาตราส่วนนี้`
- ตัวเลือกขนาดงานส่งออก: Screen, A4, A3, A1, Custom
- ป้าย overlay บนแผนที่เพื่อแสดง Export scale target

## การเปรียบเทียบ
ในโหมด 2/3 หน้าจอ ระบบแสดง layer stack เดียวกันทุก pane
ผู้ใช้สามารถใช้ Layer Control ของแต่ละ pane เพื่อเปิด/ปิดชั้นข้อมูลแยกกันและเปรียบเทียบข้อมูลได้

## หมายเหตุเรื่องมาตราส่วน
การปรับ zoom ใช้สูตรประมาณการ Web Mercator:
`resolution(m/px) ≈ scale denominator × 0.00028`

เหมาะสำหรับเตรียมงาน export/screenshot แต่ถ้าต้องใช้เป็นแผนที่ทางกฎหมายหรือรายงานราชการควรตรวจสอบซ้ำใน GIS layout

## ไฟล์ที่แก้
- `components/map_renderer.py`
- `components/sidebar.py`
- `app.py`
- `core_engine/report_export.py`

## Commit message แนะนำ
`Add map comparison layout and export scale controls`
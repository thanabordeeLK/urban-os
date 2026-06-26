# Patch: Show actual map scale from current zoom

แก้ปัญหา:
- `Scale ของ View นี้` เป็นค่า target export scale
- เมื่อผู้ใช้ zoom เข้า/ออก scale จริงของแผนที่เปลี่ยน แต่ป้าย `Export scale` ยังแสดงค่า target ทำให้เข้าใจผิด

## สิ่งที่แก้
- เปลี่ยน label จาก `Scale ของ View นี้` เป็น `Target export scale`
- เพิ่มค่า `Current actual ≈ 1 : x` แยกจาก target scale
- คำนวณ actual scale จาก Leaflet zoom และ latitude ปัจจุบัน
- แสดงทั้งบน caption ของแต่ละ Map View และ overlay บนแผนที่:
  - Target 1 : x
  - Current ≈ 1 : y
  - zoom z
- บันทึกค่า actual scale ต่อ view:
  - `map_view_1_actual_scale_label`
  - `map_view_2_actual_scale_label`
  - `map_view_3_actual_scale_label`

## หมายเหตุ
ค่า Current actual เป็นค่าประมาณตาม Web Mercator:
`resolution = 156543.03392 × cos(latitude) / 2^zoom`
`scale denominator = resolution / 0.00028`

จึงเหมาะสำหรับช่วยจัด export แต่ถ้าต้องใช้เป็นแผนที่ทางราชการควรตรวจสอบซ้ำใน GIS layout

## ไฟล์ที่แก้
- `components/map_renderer.py`
- `components/map_export_composer.py`

## Commit message แนะนำ
`Show actual map scale from current zoom`
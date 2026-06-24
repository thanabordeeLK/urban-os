# Patch: Fix Spatial Database panel visibility

แก้ปัญหา:
เข้าเมนู `Spatial Database` แล้วเห็นเฉพาะแผนที่ แต่ไม่เห็น tabs เช่น `Schema Generator`

สาเหตุ:
หน้า Spatial Database เดิมถูก render หลังแผนที่ขนาดใหญ่ ทำให้ tabs อยู่ด้านล่าง map และดูเหมือนว่าไม่มี panel

สิ่งที่แก้:
- ให้โหมด data-management แสดง panel ก่อนแผนที่:
  - Local Data Manager
  - Spatial Database
  - System Diagnostics
- ย้ายแผนที่ไปอยู่ใน expander `แสดง/ซ่อนแผนที่พื้นที่อ้างอิง`
- ป้องกันการ render panel ซ้ำหลังแผนที่
- ทำให้ tab `Schema Generator` มองเห็นทันทีเมื่อเข้า Spatial Database

ไฟล์ที่แก้:
- `app.py`

Commit message แนะนำ:
`Show spatial database panel above map`
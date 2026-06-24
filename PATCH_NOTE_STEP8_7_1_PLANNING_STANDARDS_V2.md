# Patch: Step 8.7.1 Planning Standards Preset V2

เพิ่ม Planning Standards Preset V2 ตามขนาดเมืองและเป้าหมายการวิเคราะห์

## สิ่งที่เพิ่ม
- เพิ่ม `config/planning_standards_v2.py`
- เพิ่ม `components/planning_standards_v2.py`
- เพิ่ม panel ใน Suitability Analysis:
  - `Planning Standards Preset V2`
- ประเมินขนาดเมืองจาก:
  - จำนวนอาคารในขอบเขตพื้นที่
  - อัตราครัวเรือนต่ออาคาร
  - คนต่อครัวเรือน
  - ประชากรทะเบียนราษฎร ถ้ามี
- แหล่งข้อมูลจำนวนอาคาร:
  - Manual
  - GEE FeatureCollection
  - PostGIS table
- แยกขนาดเมือง:
  - เมืองขนาดเล็ก
  - เมืองขนาดกลาง
  - เมืองขนาดใหญ่
  - เมืองขนาดใหญ่มาก
- แยกเป้าหมายวิเคราะห์:
  - พื้นที่ขยายเมือง
  - ที่อยู่อาศัย
  - พาณิชยกรรม
  - อุตสาหกรรม/โลจิสติกส์
  - โครงสร้างพื้นฐานสีเขียว/ภูมิคุ้มกันภูมิอากาศ
- เมื่อกด Apply V2 ระบบจะตั้งค่า weight slider และระยะ road/facility ให้โดยอัตโนมัติ

## เพิ่มฐานข้อมูลรองรับขั้นถัดไป
เพิ่มตารางใน PostGIS Schema Generator:
- population_registry
- household_statistics
- infrastructure_capacity
- hazard_zones
- planning_controls
- service_areas
- socioeconomic

## ข้อจำกัด
Preset V2 เป็นค่าเริ่มต้นสำหรับช่วยวิเคราะห์ ไม่ใช่ข้อกำหนดทางกฎหมายตายตัว
ต้องตรวจสอบกับผังเมืองรวม ข้อกำหนดพื้นที่ และข้อมูลราชการจริงเสมอ

## Commit message แนะนำ
`Add planning standards preset v2 by city size`
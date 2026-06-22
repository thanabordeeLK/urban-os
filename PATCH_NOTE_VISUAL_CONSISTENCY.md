# Patch: Suitability Visual Consistency

แก้ปัญหาผล Suitability Analysis ดูเหมือนเปลี่ยนเมื่อซูมเข้า/ออก

## สิ่งที่แก้
1. ล็อก projection ของ final class ตาม ESA WorldCover projection ในระดับจังหวัด/อำเภอ/ROI
2. ปรับ final result opacity เป็น 0.92 เพื่ออ่านผลหลักชัดขึ้น
3. Factor Layers ยังเพิ่มได้ แต่ซ่อนไว้ก่อน (`shown=False`) และลด opacity
4. เพิ่มข้อความเตือนว่า Factor Layers เป็นชั้นข้อมูลประกอบ ไม่ใช่ final result
5. กรอง noise ของ ESA water pixel ก่อนคำนวณ Water Proximity เพื่อลดวงกลมหลอกจาก pixel น้ำเล็ก ๆ

## ไฟล์หลัก
- core_engine/suitability.py

## วิธีใช้
อัปโหลดทับ repo เดิม แล้ว commit:
`Fix suitability visual consistency across zoom levels`
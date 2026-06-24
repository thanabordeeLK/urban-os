# Patch: Step 8.7.2 Phase B - Advanced Planning Criteria

ต่อยอด Phase A โดยเพิ่มปัจจัยขั้นสูงอีก 3 กลุ่มเข้า Suitability Engine จริง:

1. Service Coverage by Type
2. Multi-Hazard Safety
3. Socioeconomic / Equity

## จุดสำคัญ
ยังคงให้ `Zoning / Legal Compliance` อยู่ท้ายสุดของ Advanced Planning Criteria
เพื่อเปรียบเทียบผลก่อน/หลังติ๊กเลือกได้ชัดเจน

## ปัจจัยใหม่
### Service Coverage by Type
ประเมินบริการสาธารณะแยกประเภท:
- สาธารณสุข
- การศึกษา
- สวนสาธารณะ/นันทนาการ
- ตลาด/พาณิชยกรรมชุมชน
- ตำรวจ/ความปลอดภัย
- ดับเพลิง/ฉุกเฉิน
- ขนส่งสาธารณะ/สถานี

### Multi-Hazard Safety
ผู้ใช้กรอกระดับความเสี่ยง 1-5 แล้วระบบกลับด้านเป็น suitability:
- ความเสี่ยงต่ำ = คะแนนเหมาะสมสูง
- ความเสี่ยงสูง = คะแนนเหมาะสมต่ำ

ครอบคลุม:
- น้ำท่วม
- ดินถล่ม
- กัดเซาะ/พังทลาย
- ไฟป่า/หมอกควัน
- แผ่นดินไหว/รอยเลื่อน
- น้ำหลาก/ระบายน้ำไม่ทัน

### Socioeconomic / Equity
ประเมินมิติชุมชนและความเป็นธรรม:
- แก้ปัญหาการเข้าถึงบริการ
- ประโยชน์ต่อชุมชน
- ช่วยกลุ่มเปราะบาง/รายได้น้อย
- ความพร้อมกรรมสิทธิ์/ที่ดิน
- ลดความเสี่ยงย้ายถิ่น/ผลกระทบชุมชน

## ไฟล์ที่แก้
- `core_engine/advanced_planning_criteria.py`
- `core_engine/suitability.py`
- `components/sidebar.py`

## Commit message แนะนำ
`Add advanced planning criteria phase B`
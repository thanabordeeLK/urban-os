# Patch: Step 8.7.2 Phase A - Advanced Planning Criteria Scoring Engine

เพิ่มปัจจัยขั้นสูงเข้า Suitability Engine จริง 3 กลุ่มแรก:

1. Population Capacity Score
2. Infrastructure Capacity Score
3. Zoning / Legal Compliance Score

## จุดสำคัญตามคำขอ
ปัจจัย `Zoning / Legal Compliance` ถูกวางเป็นปัจจัยท้ายสุดใน UI และในสมการ
เพื่อให้เปรียบเทียบได้ว่า:
- ถ้ายังไม่ติ๊กเลือก: weight = 0 และไม่มีผลต่อ final suitability
- ถ้าติ๊กเลือก: คะแนนจะถูก normalize รวมและอาจเปลี่ยน final class

## UI ใหม่
อยู่ใน `Suitability Analysis`:
- `🏗️ Advanced Planning Criteria Phase A`

## Scoring
### Population Capacity
ใช้ current population / planned population capacity:
- <=60% = 5
- <=80% = 4
- <=100% = 3
- <=120% = 2
- >120% = 1

### Infrastructure Capacity
เฉลี่ยคะแนน 1-5 ของ:
- ประปา
- น้ำเสีย
- ไฟฟ้า
- ขยะ
- ระบายน้ำ

### Zoning / Legal Compliance
- สอดคล้อง/อนุญาต = 5
- มีเงื่อนไข/ต้องทบทวน = 3
- จำกัดมาก = 2
- ห้าม/ไม่สอดคล้อง = 1
- ไม่เปิดใช้ = ไม่มีผล

## ไฟล์ที่เพิ่ม/แก้
- `core_engine/advanced_planning_criteria.py`
- `core_engine/suitability.py`
- `components/sidebar.py`
- `app.py`
- `components/system_diagnostics.py`

## Commit message แนะนำ
`Add advanced planning criteria scoring phase A`
# Patch: Map Workspace Independent View Controls

ปรับ Map Workspace ให้ควบคุมจากหน้าจอหลักโดยตรง และให้แต่ละ Map View เลือกงาน/ผลวิเคราะห์แยกกันได้

## สิ่งที่เพิ่ม
- ย้ายการควบคุมจำนวน Map View และ export scale มาไว้เหนือแผนที่
- Map View 1 / 2 / 3 มี controls ของตัวเอง
- แต่ละ View เลือกได้อิสระ:
  - Basemap
  - Scale ของ view นั้น
  - ใช้ scale กับ zoom หรือไม่
  - การทำงาน/ผลวิเคราะห์ของ view นั้น

## ตัวเลือกผลวิเคราะห์ราย View
- Current Mode Layers
- Boundary Only
- Suitability: Final Class
- Suitability: Raw Score
- Advanced: Population Capacity
- Advanced: Infrastructure Capacity
- Advanced: Service Coverage
- Advanced: Multi-Hazard Safety
- Advanced: Socioeconomic / Equity
- Advanced: Zoning / Legal Compliance
- UHI: Heat Risk
- UHI: Land Surface Temperature

## หลักการ
- ถ้าเลือก `Current Mode Layers` จะใช้แผนที่/ชั้นข้อมูลของโหมดปัจจุบัน
- ถ้าเลือก layer เฉพาะ ระบบจะสร้าง base map ใหม่สำหรับ pane นั้น และใส่เฉพาะ layer ที่เลือก
- การเลือกของ Map View 1 ไม่กระทบ Map View 2 และ 3

## ไฟล์ที่แก้
- `components/map_renderer.py`
- `components/sidebar.py`
- `core_engine/suitability.py`
- `app.py`

## Commit message แนะนำ
`Add independent map workspace view controls`
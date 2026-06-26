# Patch: Step 8.8.3 Use Imported Layers in Suitability Criteria

ทำให้ชั้นข้อมูลที่ upload/import ผ่าน Import Wizard ถูกนำไปใช้เป็นปัจจัยคำนวณ Suitability ได้จริง

## สิ่งที่เพิ่มใน Suitability Analysis

เพิ่ม source ใหม่:

`Imported session layer`

ให้กับ 3 กลุ่มปัจจัย:

1. `Road Accessibility`
   - ใช้ชั้นข้อมูลล่าสุดจาก Import Wizard เป็นถนน/โครงข่ายคมนาคม
   - นำไป rasterize และคำนวณ distance to road

2. `Public Facility Proximity`
   - ใช้ชั้นข้อมูลล่าสุดจาก Import Wizard เป็นจุด/พื้นที่บริการสาธารณะ
   - นำไป rasterize และคำนวณ distance to facility

3. `Protected / Forest Constraints`
   - ใช้ชั้นข้อมูลล่าสุดจาก Import Wizard เป็น hard constraint
   - กันพื้นที่ออกจากผล suitability

## Workflow ใหม่

```text
Import Wizard
→ Upload & Preview
→ Suitability Analysis
→ เลือก Imported session layer
→ Run Suitability Analysis
```

## รองรับแหล่งข้อมูล

ตอนนี้แต่ละ factor ใช้ source ได้ 3 แบบ:

- `GEE Asset ID`
- `PostGIS table`
- `Imported session layer`

## สิ่งที่แก้ใน engine

`core_engine/suitability.py`

- เพิ่ม helper สำหรับอ่าน `import_wizard_last_geojson`
- แปลง GeoJSON จาก session เป็น `ee.FeatureCollection`
- เพิ่ม source_type ใหม่: `imported_session`
- ปรับ logic road/facility enabled ให้รองรับ imported session
- ปรับ protected constraint ให้รองรับ imported session

## สิ่งที่แก้ใน UI

`components/sidebar.py`

- เพิ่มตัวเลือก source ของ Road Accessibility
- เพิ่มตัวเลือก source ของ Public Facility Proximity
- เพิ่มตัวเลือก source ของ Protected / Forest Constraints
- แสดงชื่อ layer / category / จำนวน feature ล่าสุดจาก Import Wizard
- ตั้ง max features สำหรับส่งเข้า Earth Engine

## ข้อจำกัด

- Imported session layer อยู่ได้เท่าที่ session ของ Streamlit ยังอยู่
- ถ้าต้องการใช้งานถาวร ควร Import to PostGIS ก่อน แล้วเลือก `PostGIS table`
- การส่ง GeoJSON จำนวนมากเข้า Earth Engine โดยตรงอาจช้า จึงมีค่า max features
- เหมาะกับข้อมูลระดับพื้นที่/อำเภอ/โครงการ ไม่เหมาะกับชั้นข้อมูลขนาดประเทศที่มีหลายแสน feature

## ไฟล์ที่แก้

- `core_engine/suitability.py`
- `components/sidebar.py`

## Commit message แนะนำ

`Use imported layers in suitability criteria`
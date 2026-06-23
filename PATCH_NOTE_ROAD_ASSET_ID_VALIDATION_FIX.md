# Patch: Road Asset ID Validation Fix

แก้ปัญหาเมื่อผู้ใช้ใส่ URL จากปุ่ม Get Link ของ Google Earth Engine Code Editor ในช่อง Road Asset ID

## สาเหตุ
URL แบบ `https://code.earthengine.google.com/...` เป็นลิงก์แชร์สคริปต์ ไม่ใช่ GEE Asset ID
เมื่อระบบส่ง URL นี้ไปยัง `ee.FeatureCollection(...)` จะทำให้ Earth Engine error ตอน render map tile

## สิ่งที่แก้
- เพิ่ม helper ตรวจ Asset ID ใน `core_engine/suitability.py`
- รับเฉพาะ Asset ID ที่ขึ้นต้นด้วย:
  - `projects/...`
  - `users/...`
- ข้ามค่าที่เป็น URL หรือมีรูปแบบผิด
- เพิ่ม warning ใน Sidebar ถ้าผู้ใช้ใส่ URL หรือค่าไม่ถูกต้อง
- ใช้รายการ Asset ID ที่ valid เท่านั้นในการคำนวณ Road / Facility / Forest

## Asset ID ที่ควรใช้จากภาพตัวอย่าง
`projects/project-25609b11-1067-4ef1-a1d/assets/gis_osm_roads_free_1`

## ไฟล์ที่แก้
- components/sidebar.py
- core_engine/suitability.py

## Commit message แนะนำ
`Fix road asset id validation`
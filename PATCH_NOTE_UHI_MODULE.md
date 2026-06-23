# Patch: Urban Heat Island / LST Module

เพิ่ม Step 6: Urban Heat Island / Land Surface Temperature

## สิ่งที่เพิ่ม
- เพิ่มเมนูใหม่ `Urban Heat Island`
- ดึง Landsat 8/9 Collection 2 Level 2 จาก Google Earth Engine
- ใช้ band `ST_B10` แปลงเป็น Land Surface Temperature หน่วย Celsius
- กรองเมฆ/เงาเมฆด้วย `QA_PIXEL`
- ทำ composite ได้ 3 แบบ:
  - median
  - mean
  - max
- แสดงแผนที่:
  - Landsat LST Celsius
  - Urban Heat Risk Class 1–5
  - Heat Hotspot Class 5
- คำนวณสถิติ:
  - Mean / Min / Max / Median LST
  - พื้นที่ Heat Risk แต่ละระดับเป็นไร่
  - พื้นที่ Hotspot Class 5
- Export:
  - Heat Area CSV
  - UHI Report Markdown
  - UHI Summary JSON

## ไฟล์ที่เพิ่ม/แก้
- app.py
- components/sidebar.py
- core_engine/uhi.py
- core_engine/report_export.py

## Commit message แนะนำ
`Add urban heat island LST module`

## หมายเหตุ
LST คืออุณหภูมิผิวดิน ไม่ใช่อุณหภูมิอากาศโดยตรง ควรใช้ประกอบกับ Land Cover / Built-up / Tree cover / Field survey
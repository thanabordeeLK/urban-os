# Patch: Fix constraint_source_type_label NameError

แก้ error:
`NameError: constraint_source_type_label is not defined`

สาเหตุ:
ใน Step 8.5 มีการเพิ่ม Spatial Database Bridge และ return config ของ
`Protected / Forest Constraints` อ้างอิงตัวแปร `constraint_source_type_label`
แต่บางกรณี UI selector ของ Protected source ไม่ถูก render/ไม่ถูกสร้างก่อนถึง return

สิ่งที่แก้:
- เพิ่ม default values ให้ optional Spatial DB variables ก่อน return config
- เพิ่ม Protected / Forest source selector สำหรับเลือก:
  - GEE Asset ID
  - PostGIS table
- ทำให้ Road / Facility / Protected DB config มี fallback เสมอ

ไฟล์ที่แก้:
- `components/sidebar.py`

Commit message แนะนำ:
`Fix protected constraint source defaults`
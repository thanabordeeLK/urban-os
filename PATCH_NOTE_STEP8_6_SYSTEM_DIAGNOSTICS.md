# Patch: Step 8.6 System Stability & Diagnostic Center

เพิ่มหน้า `System Diagnostics` สำหรับตรวจสุขภาพ Urban OS

## สิ่งที่เพิ่ม
- เพิ่มเมนูใหม่ `System Diagnostics`
- เพิ่มไฟล์ `components/system_diagnostics.py`
- แสดงสถานะ:
  - ROI
  - Map refresh token
  - Suitability result
  - UHI result
  - Candidate Export
  - Spatial Database Registry
  - OpenAI/Agent secret readiness
- Runtime checks:
  - Python version
  - session_state count
  - Earth Engine quick test
  - PostGIS quick test
- Data Source status:
  - normalized weights
  - Spatial DB registry
  - Local/GEE registry
- Cache / Reset actions:
  - Reset Map Cache
  - Clear Suitability Cache
  - Clear UHI Cache
  - Clear Candidate Export
  - Clear Feasibility Bridge
  - Clear Multi-Agent Cache
  - Clear All Analysis Runtime Cache
- Export sanitized diagnostics JSON

## ความปลอดภัย
Diagnostics JSON จะ sanitize ค่า sensitive เช่น password, token, api_key, secret

## ไฟล์ที่เพิ่ม/แก้
- `components/system_diagnostics.py`
- `components/sidebar.py`
- `app.py`

## Commit message แนะนำ
`Add system diagnostics center`
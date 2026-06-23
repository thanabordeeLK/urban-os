# Patch: Collapsible Suitability Controls

ปรับหน้า Suitability Analysis ให้เป็นกลุ่มพับ/กางได้ด้วย `st.expander`
เพื่อให้ sidebar สั้นลงและใช้งานเหมือนส่วน Heat Penalty

## สิ่งที่เปลี่ยน
- รวม slider น้ำหนักปัจจัยทั้งหมดไว้ใน:
  - `⚖️ ตั้งค่าน้ำหนักปัจจัย Suitability`
- แยก Factor Layers ไว้ใน:
  - `🧩 การแสดงผล Factor Layers`
- พับ/กางกลุ่มข้อมูลย่อย:
  - `🛣️ Road Accessibility`
  - `🏥 Public Facility Proximity`
  - `🌡️ Urban Heat Risk / UHI Penalty`
  - `🌲 Protected / Forest Constraints`

## ไฟล์ที่แก้
- `components/sidebar.py`

## Commit message แนะนำ
`Make suitability controls collapsible`
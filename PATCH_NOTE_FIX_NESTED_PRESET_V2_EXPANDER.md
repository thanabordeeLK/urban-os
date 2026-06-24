# Patch: Fix nested expander in Planning Standards Preset V2

แก้ error:
`StreamlitAPIException` ที่เกิดจาก `st.expander()` ซ้อนอยู่ใน `st.expander()` ภายใน `Planning Standards Preset V2`

## สาเหตุ
`components/planning_standards_v2.py` มี panel หลักเป็น `st.expander("Planning Standards Preset V2")`
แต่ภายในมี `st.expander("ปัจจัยที่ควรเพิ่มในขั้นถัดไป")` อีกชั้น ทำให้ Streamlit error

## สิ่งที่แก้
เปลี่ยน inner expander เป็นข้อความธรรมดา:
- `st.markdown("#### ปัจจัยที่ควรเพิ่มในขั้นถัดไป")`
- `st.caption(...)`
- รายการ future factors แสดงตามปกติ

## ไฟล์ที่แก้
- `components/planning_standards_v2.py`

## Commit message แนะนำ
`Fix nested expander in preset v2`
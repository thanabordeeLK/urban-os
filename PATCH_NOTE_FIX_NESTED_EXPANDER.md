# Patch: Fix nested Streamlit expander error

แก้ error:
`StreamlitAPIException` ที่เกิดจากการใช้ `st.expander()` ซ้อนอยู่ภายใน `st.expander()`

สาเหตุ:
ใน patch ก่อนหน้า มีการพับกลุ่ม `🌡️ Urban Heat Risk / UHI Penalty`
แล้วภายในยังมี `with st.expander("ตั้งค่า Heat Penalty")`
ซึ่ง Streamlit ไม่อนุญาตให้ซ้อน expander ภายใน expander

สิ่งที่แก้:
- คงกลุ่มหลัก `🌡️ Urban Heat Risk / UHI Penalty` ไว้
- เปลี่ยน expander ชั้นใน `ตั้งค่า Heat Penalty` เป็นหัวข้อธรรมดา
- ปรับ indentation เฉพาะ body ของ Heat Penalty settings ให้ถูกต้อง

ไฟล์ที่แก้:
- `components/sidebar.py`

Commit message แนะนำ:
`Fix nested heat penalty expander`
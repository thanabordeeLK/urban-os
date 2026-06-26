# Patch: Fix nested Print Layout expander

แก้ error ในหน้า Spatial Database Bridge / data-management modes:

`StreamlitAPIException` จากการใช้ `st.expander()` ซ้อนกัน

## สาเหตุ
`Map Export Composer / GIS Export` ถูก render อยู่ใน expander ของแผนที่อ้างอิงบาง mode
และภายใน `Print Layout` มี:

`with st.expander("Preview HTML source / Method note", expanded=False):`

จึงกลายเป็น nested expander ซึ่ง Streamlit ไม่รองรับ

## สิ่งที่แก้
เปลี่ยน preview HTML source จาก `st.expander()` เป็น `st.checkbox()` + `st.code()`

## ไฟล์ที่แก้
- `components/map_export_composer.py`

## Commit message แนะนำ
`Fix nested print layout expander`
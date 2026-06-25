# Patch: Fix requirements pyshp install error

แก้ error บน Streamlit Cloud:

`ERROR: Invalid requirement: '\\npyshp>=2.3.1\\n'`

## สาเหตุ
ไฟล์ `requirements.txt` มีอักขระ `\n` แบบ literal ติดอยู่ในบรรทัด dependency ทำให้ pip อ่านเป็น requirement ที่ไม่ถูกต้อง

## สิ่งที่แก้
- แปลง literal `\n` ให้เป็น newline จริง
- ใส่ dependency เป็นบรรทัดปกติ:
  - `pyshp>=2.3.1`
- pin `rich` ให้เข้ากับ Streamlit 1.32.2:
  - `rich>=10.14.0,<14`

## ไฟล์ที่แก้
- `requirements.txt`

## Commit message แนะนำ
`Fix pyshp requirement for Streamlit Cloud`

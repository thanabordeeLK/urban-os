# Patch: Fix Export Report ImportError

แก้ error:
`ImportError: Missing optional dependency 'tabulate'`

สาเหตุ:
`pandas.DataFrame.to_markdown()` ต้องใช้ package `tabulate` แต่ Streamlit Cloud ยังไม่ได้ติดตั้ง

สิ่งที่แก้:
1. เปลี่ยน report_export.py ให้สร้าง Markdown table เอง ไม่พึ่ง `df.to_markdown()`
2. เพิ่ม `tabulate>=0.9.0` ใน requirements.txt เป็น fallback

ไฟล์ที่แก้:
- core_engine/report_export.py
- requirements.txt

Commit message แนะนำ:
`Fix export report markdown dependency`
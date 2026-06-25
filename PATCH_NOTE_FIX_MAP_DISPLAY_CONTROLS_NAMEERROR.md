# Patch: Fix render_map_display_controls NameError

แก้ error:
`NameError: name 'render_map_display_controls' is not defined`

## สาเหตุ
ใน patch Map Layout / Export Scale มีการเรียก `render_map_display_controls()` ใน `render_sidebar()`
แต่ function ไม่ได้ถูกเพิ่มเข้า `components/sidebar.py` ใน zip ที่ deploy

## สิ่งที่แก้
เพิ่ม function `render_map_display_controls()` ไว้ก่อน `render_sidebar()` โดยตรง เพื่อให้เรียกใช้ได้เสมอ

## ไฟล์ที่แก้
- `components/sidebar.py`

## Commit message แนะนำ
`Fix map display controls name error`
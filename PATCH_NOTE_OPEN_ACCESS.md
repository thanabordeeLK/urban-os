# Patch: Open Access Mode for Land Use Checker

ปรับ `usdc-landuse-checker` ให้ไม่ล็อกสมาชิกภายในแอปแล้ว

## แนวคิดใหม่

- แอปนี้เปิด workspace ให้ใช้ได้ปกติ
- การล็อกสมาชิก/ผู้ใช้ทั่วไปให้ไปทำที่หน้า `usdc-city-portal`
- URL `?role=member` หรือ `?role=admin` เป็นแค่ role hint ไม่ใช่ตัวล็อกสิทธิ์

## ไฟล์ที่แก้

- `app.py`
- `components/access_control.py`

## Commit message

`Use open access mode for landuse checker`
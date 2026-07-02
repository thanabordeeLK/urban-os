# Patch: Open Access Mode for Planning Law Chat

ปรับ `usdc-planning-law-chat` ให้ไม่ล็อกสมาชิกภายในแอปแล้ว

## แนวคิดใหม่

- แอปนี้เปิด workspace ให้ใช้ได้ปกติ
- การล็อกสมาชิก/ผู้ใช้ทั่วไปให้ไปทำที่หน้า `usdc-city-portal`
- URL `?role=member` หรือ `?role=admin` เป็นแค่ role hint ไม่ใช่ตัวล็อกสิทธิ์
- Legal Chat, Document Upload และ Memo Generator ใช้ได้ใน workspace เดียว

## ไฟล์ที่แก้

- `app.py`
- `components/access_control.py`

## Commit message

`Use open access mode for planning law chat`
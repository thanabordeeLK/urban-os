# Hotfix: Remove Member / Access Code Panel from Urban OS

ปรับ Urban OS ให้ไม่แสดงส่วนสมาชิกใน sidebar แล้ว

## แนวคิดใหม่

- ไม่แสดง `User role`
- ไม่แสดง `Access code`
- ไม่แสดง `Role` / `Available menus`
- ไม่ล็อกเมนูด้วย member/admin ภายใน Urban OS แล้ว
- สิทธิ์สมาชิก/ผู้ใช้ทั่วไปให้จัดการที่หน้า `usdc-city-portal` กลางก่อน redirect เข้าแอป
- Urban OS ใช้ `role` ใน URL เป็นเพียง role hint สำหรับเชื่อมต่อระบบเท่านั้น
- เมนูยังคงถูกซ่อนเฉพาะกรณีที่ต้องใช้ Google Earth Engine แต่ GEE ยังไม่พร้อม

## ตัวอย่าง URL จาก Portal

```text
?role=public&portal=executive
?role=member&portal=research
?role=member&portal=landuse
?role=public&portal=legal
```

## ไฟล์ที่แก้

- `components/access_control.py`

## Commit message

`Remove member access panel from Urban OS`
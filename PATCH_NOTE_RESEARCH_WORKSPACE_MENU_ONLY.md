# Patch: Research Workspace Menu Only

ปรับ Urban OS ให้เป็นพื้นที่ทำงานของหัวข้อ `นักวิเคราะห์ วิจัย` โดยตรง

## สิ่งที่เอาออกจาก Sidebar

- ผู้บริหารเมือง
- นักวิเคราะห์ วิจัย
- ตรวจสอบการใช้ประโยชน์ที่ดิน
- พูดคุยข้อกฎหมายผังเมือง
- ส่วน User role / Access code / Available menus

## สิ่งที่เพิ่ม

- ปุ่ม `🏠 กลับหน้าเพจกลาง`
- อ่าน URL จาก `PORTAL_HOME_URL`
- เหลือเฉพาะเมนูงานวิเคราะห์/วิจัย

## เมนูที่เหลือใน Urban OS

- General Plan
- Suitability Analysis
- Urban Heat Island
- AI Simulation
- Import Wizard
- Candidate Ranking
- AI Recommendation
- Planning Report

## แนวคิดระบบ

- `usdc-city-portal` เป็นหน้ากลางหลัก
- ปุ่มในหน้ากลางส่งผู้ใช้มายัง app ปลายทาง
- `urban-os` คือ workspace สำหรับงานนักวิเคราะห์/วิจัย
- `usdc-landuse-checker` และ `usdc-planning-law-chat` เป็น app แยกของหัวข้อเฉพาะ

## Secrets ที่ควรตั้งใน Urban OS

```toml
PORTAL_HOME_URL = "https://your-usdc-city-portal.app"
```

## Commit message

`Show research workspace menu only`
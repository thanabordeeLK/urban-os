# Patch: Step 9.1.3 External App Launcher / Portal App Links

ปรับ Urban OS Core ให้แยกงานเฉพาะเรื่องออกไปเป็นแอปภายนอกตามหน้า Portal หลัก

## แนวคิดใหม่

`urban-os` จะเป็น Core Spatial AI Dashboard:

- ผู้บริหารเมือง
- นักวิเคราะห์ วิจัย
- Suitability Analysis
- UHI
- Candidate Ranking
- AI Recommendation
- Planning Report
- Map Export
- Admin tools

ส่วนงานเฉพาะเรื่องจะแยกเป็น app/repo ใหม่:

- `usdc-landuse-checker`
- `usdc-planning-law-chat`

## สิ่งที่เพิ่ม

เพิ่มไฟล์:

- `config/external_apps.py`

สำหรับอ่าน URL ของแอปภายนอกจาก Streamlit Secrets / environment

## สิ่งที่แก้

แก้ `components/portal_pages.py`

- หน้า `ตรวจสอบการใช้ประโยชน์ที่ดิน` เปลี่ยนเป็น launcher ไปยัง Land Use Checker
- หน้า `พูดคุยข้อกฎหมายผังเมือง` เปลี่ยนเป็น launcher ไปยัง Planning Law Chat
- หน้า `นักวิเคราะห์ วิจัย` มีปุ่มลิงก์ไปยังแอปเฉพาะเรื่อง
- เอา logic legal chat ภายใน Urban OS ออก เพื่อไม่ให้ซ้ำกับแอปใหม่

แก้ `app.py`

- หน้า Land Use ไม่แสดง map workspace ภายใน Urban OS แล้ว เพราะจะส่งต่อไป external app

แก้ `components/system_diagnostics.py`

- เพิ่มสถานะ External Apps ว่าตั้งค่า LANDUSE_APP_URL / LEGAL_CHAT_APP_URL แล้วหรือยัง

## Secrets ใหม่

ตั้งค่าใน Streamlit Cloud Secrets:

```toml
PORTAL_HOME_URL = "https://your-usdc-city-portal.app"
URBAN_OS_APP_URL = "https://your-urban-os.streamlit.app"
LANDUSE_APP_URL = "https://your-landuse-checker.streamlit.app"
LEGAL_CHAT_APP_URL = "https://your-planning-law-chat.streamlit.app"
ADMIN_CONSOLE_URL = "https://your-admin-console.app"
```

## Deep links

Urban OS จะสร้างลิงก์ไปยังแอปภายนอกพร้อม role/portal:

```text
LANDUSE_APP_URL?role=member&portal=landuse
LEGAL_CHAT_APP_URL?role=public&portal=legal
LEGAL_CHAT_APP_URL?role=member&portal=legal
```

## Repo ที่แนะนำ

```text
thanabordeeLK/usdc-city-portal
thanabordeeLK/urban-os
thanabordeeLK/usdc-landuse-checker
thanabordeeLK/usdc-planning-law-chat
thanabordeeLK/usdc-admin-console
```

## Commit message แนะนำ

`Add external app launcher links`
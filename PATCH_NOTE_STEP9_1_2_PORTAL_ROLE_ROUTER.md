# Patch: Step 9.1.2 Portal Role Router

ปรับระบบให้รองรับ workflow ตามหน้า Portal:

- ไม่ล็อกอิน = ผู้ใช้ทั่วไป
- ล็อกอินสมาชิก = เข้าได้ทุกหน้าหลัก
- ผู้ดูแลระบบ = หลังบ้านเพิ่มเติม

## แนวคิดสิทธิ์ใหม่

### ผู้ใช้ทั่วไป / ไม่ล็อกอิน
เข้าได้:
- ผู้บริหารเมือง
- พูดคุยข้อกฎหมายผังเมือง แบบทั่วไป
- Planning Report
- General Plan เฉพาะเมื่อ GEE พร้อม

### สมาชิก / วิเคราะห์ได้
เข้าได้ทุกหน้าหลัก:
- ผู้บริหารเมือง
- นักวิเคราะห์ วิจัย
- ตรวจสอบการใช้ประโยชน์ที่ดิน
- พูดคุยข้อกฎหมายผังเมือง
- General Plan
- Suitability Analysis
- Urban Heat Island
- Import Wizard
- Candidate Ranking
- AI Recommendation
- Planning Report
- AI Simulation

### ผู้ดูแลระบบ
เข้าได้ทุกอย่างของสมาชิก และหลังบ้าน:
- Local Data Manager
- Spatial Database
- System Diagnostics
- Multi-Agent

## หน้า Portal ใหม่ใน Urban OS

เพิ่มไฟล์:
- `components/portal_pages.py`

เพิ่มหน้า:
- `ผู้บริหารเมือง`
- `นักวิเคราะห์ วิจัย`
- `ตรวจสอบการใช้ประโยชน์ที่ดิน`
- `พูดคุยข้อกฎหมายผังเมือง`

## Deep Link จากหน้า Portal HTML

หน้า HTML / React Portal สามารถลิงก์เข้า Urban OS ได้ เช่น:

```text
?role=public&portal=executive
?role=public&portal=legal
?role=member&portal=research
?role=member&portal=landuse
?role=admin&portal=admin
```

ตัวอย่าง:
```text
https://your-urban-os.streamlit.app/?role=public&portal=executive
https://your-urban-os.streamlit.app/?role=member&portal=research
```

หมายเหตุ:
- URL role เป็นเพียง landing hint
- ถ้าเป็น member/admin ต้องใส่ Access code ตามระบบ
- ผู้ใช้แก้ URL เองไม่ได้สิทธิ์เพิ่ม ถ้าไม่มี code

## Secrets สำหรับล็อกสมาชิก

```toml
URBAN_OS_AUTH_MODE = "passcode"
URBAN_OS_MEMBER_CODE = "member-code"
URBAN_OS_ADMIN_CODE = "admin-code"
```

สำหรับพัฒนา local แบบไม่ล็อก:
```toml
URBAN_OS_AUTH_MODE = "open"
```

## ไฟล์ที่แก้/เพิ่ม

- `components/access_control.py`
- `components/portal_pages.py`
- `components/sidebar.py`
- `app.py`
- `PATCH_NOTE_STEP9_1_2_PORTAL_ROLE_ROUTER.md`

## Commit message แนะนำ

`Add portal role router and landing pages`
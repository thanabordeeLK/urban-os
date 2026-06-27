# Patch: Step 9.1.1 GEE Service Account Auth + User Roles

แก้ปัญหา Google Earth Engine token หมดอายุ/ถูก revoke และเริ่มวางระบบกลุ่มผู้ใช้สำหรับ Public Deployment

## ปัญหาที่แก้

Error เดิม:

`invalid_grant: Token has been expired or revoked`

ระบบเดิมใช้ OAuth token / local credential แล้ว `st.stop()` ทำให้ dashboard เปิดไม่ได้ทั้งระบบ

## สิ่งที่แก้ใน GEE Auth

แก้ `config/auth.py`

- รองรับ Service Account แบบ Streamlit Secrets:
  - `GEE_PROJECT_ID`
  - `GEE_SERVICE_ACCOUNT`
  - `GEE_PRIVATE_KEY`
- รองรับ full JSON:
  - `GOOGLE_APPLICATION_CREDENTIALS_JSON`
- รองรับ local development:
  - `earthengine authenticate`
- ถ้า auth fail:
  - ไม่ `st.stop()`
  - set `st.session_state["gee_ready"] = False`
  - แสดง Recovery Panel
  - เมนูที่ไม่ใช้ GEE ยังเปิดได้

## Streamlit Secrets ที่แนะนำสำหรับ Public App

```toml
GEE_PROJECT_ID = "your-google-cloud-project-id"
GEE_SERVICE_ACCOUNT = "your-service-account@your-project.iam.gserviceaccount.com"
GEE_PRIVATE_KEY = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
```

ห้ามอัปโหลด private key หรือ service account JSON เข้า GitHub

## User Roles ที่เพิ่ม

เพิ่มไฟล์:

`components/access_control.py`

แบ่งผู้ใช้เป็น 3 กลุ่ม:

1. `ผู้ใช้ทั่วไป`
   - General Plan เมื่อ GEE พร้อม
   - Planning Report
   - เหมาะสำหรับประชาชนทั่วไป / public viewer

2. `สมาชิก / วิเคราะห์ได้`
   - วิเคราะห์ Suitability
   - UHI
   - Import Wizard
   - Candidate Ranking
   - AI Recommendation
   - Planning Report
   - เหมาะสำหรับนักผังเมือง/เจ้าหน้าที่/สมาชิก

3. `ผู้ดูแลระบบ`
   - Local Data Manager
   - Spatial Database
   - System Diagnostics
   - Multi-Agent
   - รวมสิทธิ์ของสมาชิกทั้งหมด
   - เหมาะสำหรับผู้ทำระบบ/ผู้ดูแลหลังบ้าน

## Access code optional

ถ้าต้องการใช้ passcode ใน Streamlit Secrets:

```toml
URBAN_OS_AUTH_MODE = "passcode"
URBAN_OS_MEMBER_CODE = "member-code"
URBAN_OS_ADMIN_CODE = "admin-code"
```

ถ้าไม่ตั้งค่า จะเป็น open/prototype mode เพื่อทดสอบง่าย

## ไฟล์ที่แก้/เพิ่ม

- `config/auth.py`
- `components/access_control.py`
- `components/sidebar.py`
- `components/system_diagnostics.py`
- `app.py`

## Commit message แนะนำ

`Harden GEE auth and add user role gating`
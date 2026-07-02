# Hotfix: Restore Urban OS after wrong app.py upload

สาเหตุ error:
`/mount/src/urban-os/app.py` import `config.app_config`
แปลว่า `app.py` ของแอปแยก เช่น Land Use Checker หรือ Planning Law Chat ถูกอัปโหลดทับใน repo `urban-os`

Patch นี้ restore ไฟล์หลักของ Urban OS จาก Step 9.1.3 External App Launcher

## ไฟล์ที่ restore

- app.py
- components/access_control.py
- components/portal_pages.py
- config/external_apps.py
- PATCH_NOTE_STEP9_1_3_EXTERNAL_APP_LAUNCHER.md

## Commit message

Restore Urban OS app after wrong upload

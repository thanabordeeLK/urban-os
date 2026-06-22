import json
import os
import tempfile

import ee
import streamlit as st

from config.settings import PROJECT_ID


def _secret(name: str, default=None):
    try:
        value = st.secrets.get(name, None)
        if value:
            return value
    except Exception:
        pass
    return os.getenv(name, default)


def initialize_earth_engine(project_id: str | None = None) -> None:
    """
    เชื่อมต่อ Google Earth Engine

    รองรับ:
    1) Local development: เคยรัน `earthengine authenticate` แล้ว
    2) Streamlit secrets: EARTHENGINE_TOKEN แบบเดิม
    3) Streamlit secrets: service account JSON
       - GEE_PROJECT_ID
       - GEE_SERVICE_ACCOUNT
       - GOOGLE_APPLICATION_CREDENTIALS_JSON
    """
    resolved_project_id = project_id or _secret("GEE_PROJECT_ID", PROJECT_ID)

    try:
        service_account = _secret("GEE_SERVICE_ACCOUNT")
        credentials_json = _secret("GOOGLE_APPLICATION_CREDENTIALS_JSON")

        if service_account and credentials_json:
            key_data = json.loads(credentials_json)
            with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
                json.dump(key_data, f)
                key_path = f.name

            credentials = ee.ServiceAccountCredentials(service_account, key_path)
            ee.Initialize(credentials, project=resolved_project_id)
            return

        if "EARTHENGINE_TOKEN" in st.secrets:
            secret_token = st.secrets["EARTHENGINE_TOKEN"]

            dot_ee_dir = os.path.expanduser("~/.config/earthengine")
            os.makedirs(dot_ee_dir, exist_ok=True)

            credentials_path = os.path.join(dot_ee_dir, "credentials")
            with open(credentials_path, "w", encoding="utf-8") as f:
                f.write(secret_token)

            ee.Initialize(project=resolved_project_id)
            return

        # สำหรับเครื่อง local ที่เคยรัน earthengine authenticate แล้ว
        ee.Initialize(project=resolved_project_id)

    except Exception as exc:
        st.error(f"การเชื่อมต่อ Google Earth Engine ล้มเหลว: {exc}")
        st.info(
            "ถ้ารันในเครื่อง ให้ลองใช้คำสั่ง `earthengine authenticate` ก่อน "
            "หรือถ้ารันบน Streamlit Cloud ให้ตั้งค่า GEE_PROJECT_ID และ service account ใน Secrets"
        )
        st.stop()

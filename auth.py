import os
import streamlit as st
import ee

from config.settings import PROJECT_ID


def initialize_earth_engine(project_id: str = PROJECT_ID) -> None:
    """
    เชื่อมต่อ Google Earth Engine

    รองรับ 2 รูปแบบ:
    1. Streamlit Cloud / Production: ใช้ st.secrets["EARTHENGINE_TOKEN"]
    2. Local development: ใช้ credential ที่เคย authenticate ผ่าน earthengine authenticate

    หมายเหตุ:
    - ไม่ควร hardcode credential ลงไฟล์
    - PROJECT_ID แยกไว้ใน config/settings.py
    """
    try:
        if "EARTHENGINE_TOKEN" in st.secrets:
            secret_token = st.secrets["EARTHENGINE_TOKEN"]

            dot_ee_dir = os.path.expanduser("~/.config/earthengine")
            os.makedirs(dot_ee_dir, exist_ok=True)

            credentials_path = os.path.join(dot_ee_dir, "credentials")
            with open(credentials_path, "w", encoding="utf-8") as f:
                f.write(secret_token)

            ee.Initialize(project=project_id)
        else:
            # สำหรับเครื่อง local ที่เคยรัน earthengine authenticate แล้ว
            ee.Initialize(project=project_id)

    except Exception as exc:
        st.error(f"การเชื่อมต่อ Google Earth Engine ล้มเหลว: {exc}")
        st.info(
            "ถ้ารันในเครื่อง ให้ลองใช้คำสั่ง `earthengine authenticate` ก่อน "
            "หรือถ้ารันบน Streamlit Cloud ให้ตั้งค่า EARTHENGINE_TOKEN ใน Secrets"
        )
        st.stop()

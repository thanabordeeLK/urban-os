from __future__ import annotations

import json
import os
import tempfile
from typing import Any

import ee
import streamlit as st

from config.settings import PROJECT_ID


GEE_STATUS_KEY = "gee_auth_status"
GEE_READY_KEY = "gee_ready"
GEE_MODE_KEY = "gee_auth_mode"
GEE_ERROR_KEY = "gee_error"


def _secret(name: str, default=None):
    try:
        value = st.secrets.get(name, None)
        if value:
            return value
    except Exception:
        pass
    return os.getenv(name, default)


def _normalize_private_key(private_key: str) -> str:
    """
    Streamlit Secrets often stores private keys with escaped newlines.
    Convert \\n to real newlines before building the service account key file.
    """

    private_key = str(private_key or "").strip()
    if "\\n" in private_key:
        private_key = private_key.replace("\\n", "\n")
    return private_key


def _write_temp_service_account_key(key_data: dict[str, Any]) -> str:
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(key_data, f)
        return f.name


def _build_key_from_private_key(
    *,
    service_account: str,
    project_id: str,
    private_key: str,
) -> dict[str, Any]:
    return {
        "type": "service_account",
        "project_id": project_id,
        "private_key_id": _secret("GEE_PRIVATE_KEY_ID", ""),
        "private_key": _normalize_private_key(private_key),
        "client_email": service_account,
        "client_id": _secret("GEE_CLIENT_ID", ""),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": _secret("GEE_CLIENT_X509_CERT_URL", ""),
        "universe_domain": "googleapis.com",
    }


def _set_gee_status(
    *,
    ready: bool,
    mode: str,
    project_id: str | None = None,
    error: str = "",
) -> dict:
    status = {
        "ready": bool(ready),
        "mode": mode,
        "project_id": project_id or "",
        "error": str(error or ""),
    }
    st.session_state[GEE_STATUS_KEY] = status
    st.session_state[GEE_READY_KEY] = bool(ready)
    st.session_state[GEE_MODE_KEY] = mode
    st.session_state[GEE_ERROR_KEY] = str(error or "")
    return status


def initialize_earth_engine(project_id: str | None = None) -> dict:
    """
    Hardened Google Earth Engine initialization.

    This function does not call st.stop() when auth fails.
    It records status in session_state so non-GEE pages can still open.
    """

    resolved_project_id = str(project_id or _secret("GEE_PROJECT_ID", PROJECT_ID) or "").strip()

    existing = st.session_state.get(GEE_STATUS_KEY)
    if isinstance(existing, dict) and existing.get("ready"):
        return existing

    try:
        service_account = _secret("GEE_SERVICE_ACCOUNT")
        private_key = _secret("GEE_PRIVATE_KEY")
        credentials_json = _secret("GOOGLE_APPLICATION_CREDENTIALS_JSON")

        if service_account and private_key:
            key_data = _build_key_from_private_key(
                service_account=service_account,
                project_id=resolved_project_id,
                private_key=private_key,
            )
            key_path = _write_temp_service_account_key(key_data)
            credentials = ee.ServiceAccountCredentials(service_account, key_path)
            ee.Initialize(credentials, project=resolved_project_id)
            return _set_gee_status(
                ready=True,
                mode="service_account_private_key",
                project_id=resolved_project_id,
            )

        if credentials_json:
            key_data = json.loads(str(credentials_json))
            service_account_from_json = service_account or key_data.get("client_email")
            if not service_account_from_json:
                raise RuntimeError("GOOGLE_APPLICATION_CREDENTIALS_JSON ไม่มี client_email")
            key_path = _write_temp_service_account_key(key_data)
            credentials = ee.ServiceAccountCredentials(service_account_from_json, key_path)
            ee.Initialize(credentials, project=resolved_project_id)
            return _set_gee_status(
                ready=True,
                mode="service_account_json",
                project_id=resolved_project_id,
            )

        if "EARTHENGINE_TOKEN" in st.secrets:
            secret_token = st.secrets["EARTHENGINE_TOKEN"]

            dot_ee_dir = os.path.expanduser("~/.config/earthengine")
            os.makedirs(dot_ee_dir, exist_ok=True)

            credentials_path = os.path.join(dot_ee_dir, "credentials")
            with open(credentials_path, "w", encoding="utf-8") as f:
                f.write(secret_token)

            ee.Initialize(project=resolved_project_id)
            return _set_gee_status(
                ready=True,
                mode="legacy_earthengine_token",
                project_id=resolved_project_id,
            )

        ee.Initialize(project=resolved_project_id)
        return _set_gee_status(
            ready=True,
            mode="local_user_credentials",
            project_id=resolved_project_id,
        )

    except Exception as exc:
        return _set_gee_status(
            ready=False,
            mode="not_connected",
            project_id=resolved_project_id,
            error=str(exc),
        )


def gee_is_ready() -> bool:
    return bool(st.session_state.get(GEE_READY_KEY, False))


def gee_status() -> dict:
    status = st.session_state.get(GEE_STATUS_KEY)
    if isinstance(status, dict):
        return status
    return {
        "ready": False,
        "mode": "not_initialized",
        "project_id": "",
        "error": "",
    }


def render_gee_auth_recovery_panel(compact: bool = False) -> None:
    status = gee_status()
    error = status.get("error", "")

    if status.get("ready"):
        st.success(f"Google Earth Engine พร้อมใช้งาน: {status.get('mode')} / project={status.get('project_id')}")
        return

    st.error(f"Google Earth Engine ยังไม่พร้อมใช้งาน: {error or 'not initialized'}")

    if compact:
        st.info("เมนูที่ไม่ต้องใช้ GEE ยังเปิดได้ เช่น Planning Report, Candidate Ranking, AI Recommendation, Import Wizard, Spatial Database")
        return

    st.markdown("### 🔐 GEE Authentication Recovery")

    st.warning(
        "สำหรับระบบที่ให้บุคคลทั่วไปใช้งาน ไม่ควรใช้ OAuth token จากเครื่องส่วนตัว "
        "ควรใช้ Service Account กลางของระบบและเก็บไว้ใน Streamlit Secrets"
    )

    st.markdown("#### Streamlit Cloud Secrets ที่แนะนำ")
    st.code(
        "GEE_PROJECT_ID = \"your-google-cloud-project-id\"\\n"
        "GEE_SERVICE_ACCOUNT = \"your-service-account@your-project.iam.gserviceaccount.com\"\\n"
        "GEE_PRIVATE_KEY = \"-----BEGIN PRIVATE KEY-----\\\\n...\\\\n-----END PRIVATE KEY-----\\\\n\"",
        language="toml",
    )

    st.markdown("#### ถ้ารันบนเครื่องตัวเอง")
    st.code(
        "earthengine authenticate\\nstreamlit run app.py",
        language="bash",
    )

    st.caption(
        "ห้ามอัปโหลด private key หรือ service account JSON เข้า GitHub ให้ใส่ใน Streamlit Secrets เท่านั้น"
    )

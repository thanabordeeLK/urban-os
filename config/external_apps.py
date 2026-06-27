from __future__ import annotations

import os

import streamlit as st


def _secret(name: str, default: str = "") -> str:
    try:
        value = st.secrets.get(name, None)
        if value:
            return str(value)
    except Exception:
        pass
    return os.getenv(name, default)


def get_external_app_url(app_key: str) -> str:
    """
    External app URL resolver.

    Supported keys:
    - portal_home
    - urban_os
    - landuse_checker
    - planning_law_chat
    - admin_console
    """

    app_key = str(app_key or "").strip().lower()

    mapping = {
        "portal_home": "PORTAL_HOME_URL",
        "urban_os": "URBAN_OS_APP_URL",
        "landuse_checker": "LANDUSE_APP_URL",
        "planning_law_chat": "LEGAL_CHAT_APP_URL",
        "admin_console": "ADMIN_CONSOLE_URL",
    }

    env_key = mapping.get(app_key, app_key.upper())
    return _secret(env_key, "")


def build_external_url(app_key: str, *, role: str = "public", portal: str = "", mode: str = "") -> str:
    """
    Build URL with simple query params for cross-app navigation.
    """

    base = get_external_app_url(app_key)
    if not base:
        return ""

    params = []
    if role:
        params.append(f"role={role}")
    if portal:
        params.append(f"portal={portal}")
    if mode:
        from urllib.parse import quote

        params.append(f"mode={quote(mode)}")

    if not params:
        return base

    separator = "&" if "?" in base else "?"
    return base + separator + "&".join(params)


def external_apps_status() -> dict:
    return {
        "PORTAL_HOME_URL": get_external_app_url("portal_home"),
        "URBAN_OS_APP_URL": get_external_app_url("urban_os"),
        "LANDUSE_APP_URL": get_external_app_url("landuse_checker"),
        "LEGAL_CHAT_APP_URL": get_external_app_url("planning_law_chat"),
        "ADMIN_CONSOLE_URL": get_external_app_url("admin_console"),
    }

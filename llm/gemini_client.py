"""Gemini client wrapper for Urban OS agents.

เก็บ API key ใน Streamlit secrets หรือ environment variable:
GEMINI_API_KEY, GEMINI_MODEL
"""
from __future__ import annotations

import os
import streamlit as st


def _get_secret(name: str, default: str | None = None) -> str | None:
    try:
        value = st.secrets.get(name, None)
        if value:
            return value
    except Exception:
        pass
    return os.getenv(name, default)


def ask_gemini(
    prompt: str,
    model: str | None = None,
    temperature: float = 0.2,
) -> str:
    """Call Gemini. Return Thai error text instead of crashing UI."""
    api_key = _get_secret("GEMINI_API_KEY")
    if not api_key:
        return "ยังไม่ได้ตั้งค่า GEMINI_API_KEY ใน Streamlit secrets หรือ environment variable"

    selected_model = model or _get_secret("GEMINI_MODEL", "gemini-2.5-flash")

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=selected_model,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=temperature),
        )
        return getattr(response, "text", str(response))

    except Exception as exc:
        return f"Gemini error: {exc}"

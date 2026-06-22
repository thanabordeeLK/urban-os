"""OpenAI client wrapper for Urban OS agents.

เก็บ API key ใน Streamlit secrets หรือ environment variable:
OPENAI_API_KEY, OPENAI_MODEL
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


def ask_openai(
    prompt: str,
    system_prompt: str | None = None,
    model: str | None = None,
    temperature: float = 0.2,
) -> str:
    """Call OpenAI Responses API. Return Thai error text instead of crashing UI."""
    api_key = _get_secret("OPENAI_API_KEY")
    if not api_key:
        return "ยังไม่ได้ตั้งค่า OPENAI_API_KEY ใน Streamlit secrets หรือ environment variable"

    selected_model = model or _get_secret("OPENAI_MODEL", "gpt-4.1-mini")

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)

        content = []
        if system_prompt:
            content.append({"role": "system", "content": system_prompt})
        content.append({"role": "user", "content": prompt})

        response = client.responses.create(
            model=selected_model,
            input=content,
            temperature=temperature,
        )

        return getattr(response, "output_text", str(response))

    except Exception as exc:
        return f"OpenAI error: {exc}"

"""Statistics and planning indicator utilities."""
from __future__ import annotations

import pandas as pd

from config.datasets import (
    ESA_CLASS_NAMES,
    ESA_GREEN_CODES,
    ESA_BUILTUP_CODES,
    ESA_WATER_CODES,
)
from services.gee_service import reduce_frequency_histogram


def histogram_to_area_dataframe(histogram: dict, scale: int) -> pd.DataFrame:
    """Convert Earth Engine frequency histogram to area table in rai."""
    rows = []
    pixel_area_sqm = scale**2

    for code, count in histogram.items():
        code_text = str(code)
        area_rai = float(count) * pixel_area_sqm / 1600.0
        rows.append(
            {
                "code": code_text,
                "ประเภทพื้นที่": ESA_CLASS_NAMES.get(code_text, f"ประเภท {code_text}"),
                "ขนาด (ไร่)": area_rai,
            }
        )

    if not rows:
        return pd.DataFrame(columns=["code", "ประเภทพื้นที่", "ขนาด (ไร่)"])

    return pd.DataFrame(rows).sort_values(by="ขนาด (ไร่)", ascending=False)


def build_planning_summary(df: pd.DataFrame) -> dict:
    """Summarize ESA land cover table into simple planning indicators."""
    if df.empty:
        return {
            "total_area_rai": 0,
            "green_area_rai": 0,
            "builtup_area_rai": 0,
            "water_area_rai": 0,
            "green_percent": 0,
            "builtup_percent": 0,
            "water_percent": 0,
            "planning_score": 0,
        }

    total_area = float(df["ขนาด (ไร่)"].sum())
    green_area = float(df[df["code"].isin(ESA_GREEN_CODES)]["ขนาด (ไร่)"].sum())
    builtup_area = float(df[df["code"].isin(ESA_BUILTUP_CODES)]["ขนาด (ไร่)"].sum())
    water_area = float(df[df["code"].isin(ESA_WATER_CODES)]["ขนาด (ไร่)"].sum())

    green_percent = (green_area / total_area * 100) if total_area else 0
    builtup_percent = (builtup_area / total_area * 100) if total_area else 0
    water_percent = (water_area / total_area * 100) if total_area else 0

    # Prototype score: เน้นพื้นที่สีเขียว + พื้นที่น้ำ + คุมความหนาแน่นสิ่งปลูกสร้าง
    # คะแนนนี้ยังไม่ใช่ suitability model เต็มรูปแบบ แต่ใช้เป็น quick planning indicator ได้
    planning_score = (green_percent * 0.55) + (water_percent * 0.15) + ((100 - builtup_percent) * 0.30)
    planning_score = max(0, min(100, planning_score))

    return {
        "total_area_rai": total_area,
        "green_area_rai": green_area,
        "builtup_area_rai": builtup_area,
        "water_area_rai": water_area,
        "green_percent": green_percent,
        "builtup_percent": builtup_percent,
        "water_percent": water_percent,
        "planning_score": planning_score,
    }


def calculate_esa_landcover_statistics(landcover, roi, scale: int) -> tuple[pd.DataFrame, dict]:
    """Calculate ESA area dataframe and summary indicators."""
    histogram = reduce_frequency_histogram(landcover, roi, scale)
    df = histogram_to_area_dataframe(histogram, scale)
    summary = build_planning_summary(df)
    return df, summary

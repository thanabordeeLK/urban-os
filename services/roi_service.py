"""ROI and administrative boundary helpers."""
import streamlit as st
import ee

from config.settings import (
    GAUL_LEVEL0,
    GAUL_LEVEL1,
    GAUL_LEVEL2,
    THAILAND_ALL_LABEL,
    PROVINCE_ALL_LABEL,
)


@st.cache_data(show_spinner=False)
def get_provinces() -> list[str]:
    """ดึงรายชื่อจังหวัดของประเทศไทยจาก GAUL level1"""
    fc = ee.FeatureCollection(GAUL_LEVEL1).filter(ee.Filter.eq("ADM0_NAME", "Thailand"))
    return sorted(fc.aggregate_array("ADM1_NAME").getInfo())


@st.cache_data(show_spinner=False)
def get_districts(province_name: str) -> list[str]:
    """ดึงรายชื่ออำเภอจาก GAUL level2 ตามจังหวัดที่เลือก"""
    fc = ee.FeatureCollection(GAUL_LEVEL2).filter(ee.Filter.eq("ADM1_NAME", province_name))
    return sorted(fc.aggregate_array("ADM2_NAME").getInfo())


def get_roi(selected_province: str, selected_district: str):
    """
    สร้าง ROI ตามตัวเลือกจังหวัด/อำเภอ

    Returns:
        roi: ee.FeatureCollection
        is_whole_country: bool
    """
    is_whole_country = selected_province == THAILAND_ALL_LABEL

    if is_whole_country:
        roi = ee.FeatureCollection(GAUL_LEVEL0).filter(ee.Filter.eq("ADM0_NAME", "Thailand"))
        return roi, True

    if selected_district != PROVINCE_ALL_LABEL:
        roi = ee.FeatureCollection(GAUL_LEVEL2).filter(
            ee.Filter.And(
                ee.Filter.eq("ADM1_NAME", selected_province),
                ee.Filter.eq("ADM2_NAME", selected_district),
            )
        )
    else:
        roi = ee.FeatureCollection(GAUL_LEVEL1).filter(ee.Filter.eq("ADM1_NAME", selected_province))

    return roi, False

import streamlit as st

APP_TITLE = "Urban OS"
APP_ICON = "🌐"
PROJECT_ID = "project-25609b11-1067-4ef1-a1d"

DEFAULT_CENTER = [15.87, 100.99]
DEFAULT_ZOOM = 6

THAILAND_ALL_LABEL = "-- ประเทศไทย (รวมทุกจังหวัด) --"
THAILAND_DISTRICT_ALL_LABEL = "-- วิเคราะห์ทั่วประเทศ --"
PROVINCE_ALL_LABEL = "-- วิเคราะห์ทั้งจังหวัด --"

DEFAULT_PROVINCE = "Uttaradit"
DEFAULT_DISTRICT = "Tha Pla"

GAUL_LEVEL0 = "FAO/GAUL/2015/level0"
GAUL_LEVEL1 = "FAO/GAUL/2015/level1"
GAUL_LEVEL2 = "FAO/GAUL/2015/level2"

CUSTOM_CSS = """
<style>
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 0rem !important;
        max-width: 98% !important;
    }

    .stApp {
        background-color: #060B14;
    }

    [data-testid="stSidebar"] {
        background-color: #0B132B !important;
        border-right: 1px solid #1E293B;
    }

    p, span, label {
        color: #E2E8F0 !important;
    }

    h1, h2, h3 {
        color: #00F2FE !important;
        text-shadow: 0px 0px 8px rgba(0, 242, 254, 0.4);
    }

    [data-baseweb="popover"] > div {
        background-color: #0B132B !important;
    }

    ul[data-baseweb="menu"] {
        background-color: #0B132B !important;
    }

    li[role="option"]:hover {
        background-color: rgba(0, 242, 254, 0.2) !important;
        color: #00F2FE !important;
    }

    [data-testid="stFileUploadDropzone"] {
        background-color: #0B132B !important;
        border: 2px dashed #00F2FE !important;
        border-radius: 10px;
    }

    [data-testid="stFileUploadDropzone"] * {
        color: #E2E8F0 !important;
    }

    .stButton>button {
        background-color: #09203F !important;
        border: 1px solid #00F2FE !important;
        color: #00F2FE !important;
        font-weight: bold;
        border-radius: 6px;
        width: 100%;
        transition: all 0.3s ease;
    }

    .stButton>button:hover {
        background-color: #00F2FE !important;
        color: #060B14 !important;
        box-shadow: 0px 0px 15px rgba(0, 242, 254, 0.6);
    }
</style>
"""


def configure_page() -> None:
    """ตั้งค่าหน้า Streamlit หลัก"""
    st.set_page_config(
        layout="wide",
        page_title=APP_TITLE,
        page_icon=APP_ICON,
    )


def inject_css() -> None:
    """ฝัง CSS ตกแต่ง UI"""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

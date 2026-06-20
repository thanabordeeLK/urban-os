import streamlit as st
import geemap.foliumap as geemap
import ee
import os
from streamlit_option_menu import option_menu # ไลบรารีใหม่สำหรับเมนู

# 1. ตั้งค่าหน้าเว็บให้แสดงผลแบบเต็มจอ
st.set_page_config(layout="wide", page_title="Urban OS", page_icon="🌐")

# ==========================================
# 🎨 2. ฝัง CSS ตกแต่ง UI สไตล์ AI & Dark Neon
# ==========================================
st.markdown("""
<style>
    /* ปรับแต่งสีพื้นหลังหลักและตัวหนังสือ */
    .stApp {
        background-color: #0A0E17;
        color: #E2E8F0;
    }
    /* ปรับแต่ง Sidebar */
    [data-testid="stSidebar"] {
        background-color: #0B132B !important;
        border-right: 1px solid #1E293B;
    }
    /* เอฟเฟกต์ตัวหนังสือเรืองแสงสำหรับหัวข้อ */
    h1, h2, h3 {
        color: #00F2FE !important;
        text-shadow: 0px 0px 10px rgba(0, 242, 254, 0.4);
    }
    /* ตกแต่งกรอบคำเตือน/ข้อมูล */
    div.stAlert {
        background-color: rgba(11, 19, 43, 0.8) !important;
        border: 1px solid #00F2FE !important;
        color: #E2E8F0 !important;
    }
    /* ตกแต่งปุ่มกดให้ดูล้ำสมัย */
    .stButton>button {
        background: linear-gradient(90deg, #09203F 0%, #537895 100%);
        border: 1px solid #00F2FE;
        color: white;
        border-radius: 8px;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background: linear-gradient(90deg, #537895 0%, #09203F 100%);
        box-shadow: 0px 0px 15px rgba(0, 242, 254, 0.6);
        border: 1px solid #FFFFFF;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================

st.title("🌐 Urban OS : Spatial AI Dashboard")
st.markdown("*ระบบปฏิบัติการผังเมืองอัจฉริยะ และการจำลองสถานการณ์เชิงพื้นที่*")

# 3. การเชื่อมต่อ Google Earth Engine (โค้ดเดิมที่ทำงานสมบูรณ์)
PROJECT_ID = 'project-25609b11-1067-4ef1-a1d'
try:
    if "EARTHENGINE_TOKEN" in st.secrets:
        secret_token = st.secrets["EARTHENGINE_TOKEN"]
        dot_ee_dir = os.path.expanduser('~/.config/earthengine')
        os.makedirs(dot_ee_dir, exist_ok=True)
        credentials_path = os.path.join(dot_ee_dir, 'credentials')
        with open(credentials_path, 'w') as f:
            f.write(secret_token)
        ee.Initialize(project=PROJECT_ID)
    else:
        st.error("ไม่พบกุญแจ EARTHENGINE_TOKEN")
        st.stop()
except Exception as e:
    st.error(f"การเชื่อมต่อระบบล้มเหลว: {e}")
    st.stop()

# สร้างแผนที่หลัก
Map = geemap.Map(center=[17.62, 100.09], zoom=10, ee_initialize=False)

# 4. จัดการแถบเมนูด้านข้าง (Sidebar) แบบล้ำสมัย
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>⚙️ CONTROL PANEL</h2>", unsafe_allow_html=True)
    
    # สร้างเมนูที่มีไอคอนสวยงาม
    selected_mode = option_menu(
        menu_title=None, 
        options=["General Plan", "AI Simulation"],
        icons=["map", "cpu"], # ใช้ไอคอนจาก Bootstrap
        menu_icon="cast",
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"color": "#00F2FE", "font-size": "20px"}, 
            "nav-link": {"font-size": "16px", "text-align": "left", "margin":"0px", "--hover-color": "#1E293B"},
            "nav-link-selected": {"background-color": "rgba(0, 242, 254, 0.2)", "border-left": "4px solid #00F2FE"},
        }
    )
    st.divider()

    # ==========================================
    # โหมดที่ 1: งานแผนทั่วไป
    # ==========================================
    if selected_mode == "General Plan":
        st.markdown("### 🥞 Data Layers")
        basemap_choice = st.selectbox("🗺️ Basemap", ["HYBRID", "SATELLITE", "ROADMAP", "TERRAIN"])
        Map.add_basemap(basemap_choice)
        
        show_dem = st.checkbox("⛰️ Terrain Model (DEM)", value=True)
        show_landcover = st.checkbox("🟢 ESA Land Cover", value=False)
        opacity = st.slider("Opacity (ความโปร่งแสง)", 0.0, 1.0, 0.7)
        
        if show_dem:
            dem = ee.Image('USGS/SRTMGL1_003')
            dem_vis = {'min': 0, 'max': 1000, 'palette': ['006633', 'E5FFCC', '662A00', 'D8D8D8', 'F5F5F5']}
            Map.addLayer(dem, dem_vis, 'Elevation (DEM)', opacity=opacity)
            
        if show_landcover:
            landcover = ee.ImageCollection("ESA/WorldCover/v200").first()
            Map.addLayer(landcover, {}, 'Land Use', opacity=opacity)
            
        st.divider()
        st.markdown("### 📊 Area Statistics")
        st.info("ระบบจะดึงข้อมูลสถิติพื้นที่เมื่อเลือก Polygon (รออัปเดตฟีเจอร์)")

    # ==========================================
    # โหมดที่ 2: วิเคราะห์ขั้นสูง (AI Simulation)
    # ==========================================
    elif selected_mode == "AI Simulation":
        Map.add_basemap("SATELLITE") 
        
        st.markdown("### 🏢 1. Import Data")
        uploaded_file = st.file_uploader("Upload Shapefile / KML", type=['zip', 'kml'])
        
        st.markdown("### 🔍 2. Spatial Analysis")
        analysis_type = st.selectbox("Model Type", ["-- เลือกโมเดล --", "Flood Risk Simulation", "Land Suitability", "Urban Growth Tracking"])
        
        st.markdown("### 📈 3. Predictive Modeling")
        predict_years = st.slider("Forecast Timeline (Years)", 1, 30, 5)
        
        st.markdown("### 🛡️ 4. Engineering Mitigation")
        sim_tool = st.radio("Simulation Tools", ["กั้นแนวคันดิน (ท่าเสา)", "จำลองฝายชะลอน้ำ (ท่าปลา)", "ปรับแก้ระดับตลิ่ง"])
        
        st.divider()
        if st.button("▶️ RUN AI ENGINE"):
            st.success("Compute Engine Active: กำลังเตรียมทรัพยากรประมวลผล...")

# 5. แสดงผลแผนที่หลัก
Map.to_streamlit(height=700)

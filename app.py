import streamlit as st
import geemap.foliumap as geemap
import ee
import os
from streamlit_option_menu import option_menu

# 1. ตั้งค่าหน้าเว็บให้แสดงผลแบบเต็มจอ
st.set_page_config(layout="wide", page_title="Urban OS", page_icon="🌐")

# ==========================================
# 🎨 2. ฝัง CSS ตกแต่ง UI ใหม่ (แก้ปัญหา Dropdown มองไม่เห็น)
# ==========================================
st.markdown("""
<style>
    /* ปรับสีพื้นหลังหลัก */
    .stApp {
        background-color: #060B14;
    }
    /* ปรับสีพื้นหลัง Sidebar */
    [data-testid="stSidebar"] {
        background-color: #0B132B !important;
        border-right: 1px solid #1E293B;
    }
    /* บังคับให้ข้อความทั่วไปเป็นสีขาว/เทาสว่าง (เอา div ออกเพื่อไม่ให้กระทบระบบอื่น) */
    p, span, label {
        color: #E2E8F0 !important;
    }
    /* หัวข้อเรืองแสงสี Cyan */
    h1, h2, h3 {
        color: #00F2FE !important;
        text-shadow: 0px 0px 8px rgba(0, 242, 254, 0.4);
    }
    
    /* -------------------------------------- */
    /* แก้ไขสีพื้นหลัง Dropdown ให้เป็นโหมดมืด */
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
    /* -------------------------------------- */

    /* ตกแต่งกรอบอัปโหลดไฟล์ให้เป็นสไตล์ AI */
    [data-testid="stFileUploadDropzone"] {
        background-color: #111A30 !important;
        border: 2px dashed #00F2FE !important;
        border-radius: 10px;
    }
    /* ตกแต่งปุ่มกด */
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
""", unsafe_allow_html=True)

# ==========================================

st.title("🌐 Urban OS : Spatial AI Dashboard")
st.markdown("*ระบบปฏิบัติการผังเมืองอัจฉริยะ และการจำลองสถานการณ์เชิงพื้นที่*")

# 3. การเชื่อมต่อ Google Earth Engine
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

# สร้างแผนที่หลัก (ปรับพิกัดศูนย์กลางมาที่ประเทศไทย และ Zoom out ออกมา)
Map = geemap.Map(center=[15.87, 100.99], zoom=6, ee_initialize=False)

# 4. จัดการแถบเมนูด้านข้าง (Sidebar) แบบล้ำสมัย (แก้สีเมนูแล้ว)
with st.sidebar:
    st.markdown("<h3 style='text-align: center; margin-bottom: 20px;'>⚙️ CONTROL PANEL</h3>", unsafe_allow_html=True)
    
    # สร้างเมนูที่มีไอคอน (แก้สีไม่ให้กลืนกับพื้นหลัง)
    selected_mode = option_menu(
        menu_title=None, 
        options=["General Plan", "AI Simulation"],
        icons=["map", "cpu"],
        menu_icon="cast",
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "#0B132B"},
            "icon": {"color": "#00F2FE", "font-size": "18px"}, 
            "nav-link": {"color": "#E2E8F0", "font-size": "16px", "text-align": "left", "margin":"0px"},
            "nav-link-selected": {"background-color": "rgba(0, 242, 254, 0.2)", "color": "#00F2FE", "border-left": "4px solid #00F2FE", "font-weight": "bold"},
        }
    )
    st.markdown("<hr style='border-color: #1E293B;'>", unsafe_allow_html=True)

    # ==========================================
    # โหมดที่ 1: งานแผนทั่วไป
    # ==========================================
    if selected_mode == "General Plan":
        st.markdown("### 🥞 Data Layers")
        basemap_choice = st.selectbox("🗺️ Basemap", ["HYBRID", "SATELLITE", "ROADMAP", "TERRAIN", "OSM"])
        Map.add_basemap(basemap_choice)
        
        # จัดกลุ่มเมนูให้ดูเป็นระเบียบ
        st.markdown("**🌍 ข้อมูลกายภาพ (Physical)**")
        show_dem = st.checkbox("⛰️ Terrain Model (ความสูงภูมิประเทศ)", value=True)
        show_water = st.checkbox("💧 Surface Water (แหล่งน้ำผิวดิน)", value=False)
        show_landcover = st.checkbox("🟢 ESA Land Cover (การใช้ที่ดิน)", value=False)
        
        st.markdown("**🏙️ ข้อมูลเศรษฐกิจและสังคม (Socio-Economic)**")
        show_nightlight = st.checkbox("💡 Nighttime Lights (แสงไฟกลางคืน)", value=False)
        show_pop = st.checkbox("👥 Population Density (ความหนาแน่นประชากร)", value=False)
        
        opacity = st.slider("Opacity (ความโปร่งแสง)", 0.0, 1.0, 0.7)
        
        # ---------------------------------------------------------
        # ส่วนดึงข้อมูลจาก Google Earth Engine มาแสดงบนแผนที่
        # ---------------------------------------------------------
        if show_dem:
            dem = ee.Image('USGS/SRTMGL1_003')
            dem_vis = {'min': 0, 'max': 1000, 'palette': ['006633', 'E5FFCC', '662A00', 'D8D8D8', 'F5F5F5']}
            Map.addLayer(dem, dem_vis, 'Elevation (DEM)', opacity=opacity)
            
        if show_water:
            # ดึงข้อมูลแหล่งน้ำผิวดินย้อนหลัง
            water = ee.Image("JRC/GSW1_4/GlobalSurfaceWater").select('occurrence')
            water_vis = {'min': 0, 'max': 100, 'palette': ['lightblue', 'blue', 'darkblue']}
            # updateMask เพื่อให้แสดงเฉพาะจุดที่มีน้ำ (ทะลุเห็นพื้นหลัง)
            Map.addLayer(water.updateMask(water.gt(0)), water_vis, 'Surface Water', opacity=opacity)
            
        if show_landcover:
            landcover = ee.ImageCollection("ESA/WorldCover/v200").first()
            Map.addLayer(landcover, {}, 'Land Use', opacity=opacity)
            
        if show_nightlight:
            # ดึงข้อมูลแสงไฟกลางคืน
            dataset = ee.ImageCollection('NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG').filterDate('2022-01-01', '2022-12-31').median()
            night_lights = dataset.select('avg_rad')
            nl_vis = {'min': 0, 'max': 60, 'palette': ['black', 'blue', 'purple', 'cyan', 'green', 'yellow', 'red', 'white']}
            Map.addLayer(night_lights, nl_vis, 'Nighttime Lights', opacity=opacity)
            
        if show_pop:
            # ดึงข้อมูลประชากรโลก กรองเฉพาะประเทศไทย
            pop = ee.ImageCollection("WorldPop/GP/100m/pop").filter(ee.Filter.eq('country', 'THA')).median()
            pop_vis = {'min': 0, 'max': 50, 'palette': ['24126c', '1fff4f', 'd4ff50']}
            Map.addLayer(pop, pop_vis, 'Population Density', opacity=opacity)
            
        st.markdown("<hr style='border-color: #1E293B;'>", unsafe_allow_html=True)
        st.markdown("### 📊 Area Statistics")
        st.info("📌 ระบบจะดึงข้อมูลสถิติพื้นที่เมื่อเลือก Polygon")

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
        
        st.write("") # เว้นบรรทัด
        if st.button("▶️ RUN AI ENGINE"):
            st.success("Compute Engine Active: กำลังเตรียมทรัพยากรประมวลผล...")

# 5. แสดงผลแผนที่หลัก
Map.to_streamlit(height=700)

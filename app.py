import streamlit as st
import geemap.foliumap as geemap
import ee
import os
from streamlit_option_menu import option_menu
from streamlit_folium import st_folium
import pandas as pd   

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

   /* ตกแต่งกรอบอัปโหลดไฟล์ให้เป็นสไตล์ AI และแก้ตัวหนังสืออ่านไม่ออก */
    [data-testid="stFileUploadDropzone"] {
        background-color: #0B132B !important;
        border: 2px dashed #00F2FE !important;
        border-radius: 10px;
    }
    /* บังคับให้ข้อความและไอคอนข้างในกล่องอัปโหลดเป็นสีสว่าง */
    [data-testid="stFileUploadDropzone"] * {
        color: #E2E8F0 !important;

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
# ---------------------------------------------------------
# ระบบดึงพิกัดและความจำแผนที่ (Session State)
# ---------------------------------------------------------
map_center = [15.87, 100.99] # ค่าเริ่มต้น (ประเทศไทย)
map_zoom = 6

# ถ้าระบบเคยจำพิกัดไว้แล้ว ให้ดึงพิกัดล่าสุดมาใช้
if "urban_map" in st.session_state and st.session_state["urban_map"].get("center"):
    map_center = [st.session_state["urban_map"]["center"]["lat"], st.session_state["urban_map"]["center"]["lng"]]
    map_zoom = st.session_state["urban_map"]["zoom"]

# สร้างแผนที่หลักจากพิกัดล่าสุด
Map = geemap.Map(center=map_center, zoom=map_zoom, ee_initialize=False)

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
        basemap_choice = st.selectbox("🗺️ Basemap", ["HYBRID", "SATELLITE", "ROADMAP", "TERRAIN"])
        Map.add_basemap(basemap_choice)

        # ฟังก์ชันดึงข้อมูลจังหวัดและอำเภอจาก GEE (Cache ไว้เพื่อให้แอปโหลดเร็ว)
        @st.cache_data
        def get_provinces():
            fc = ee.FeatureCollection("FAO/GAUL/2015/level1").filter(ee.Filter.eq('ADM0_NAME', 'Thailand'))
            return sorted(fc.aggregate_array('ADM1_NAME').getInfo())

        @st.cache_data
        def get_districts(province_name):
            fc = ee.FeatureCollection("FAO/GAUL/2015/level2").filter(ee.Filter.eq('ADM1_NAME', province_name))
            return sorted(fc.aggregate_array('ADM2_NAME').getInfo())

        # ---------------------------------------------------------
        # 📍 ระบบค้นหาและโฟกัสพื้นที่ (Location Filter)
        # ---------------------------------------------------------
        st.markdown("<hr style='border-color: #1E293B;'>", unsafe_allow_html=True)
        st.markdown("**📍 กำหนดพื้นที่วิเคราะห์**")

        provinces = get_provinces()
        default_prov_idx = provinces.index("Uttaradit") if "Uttaradit" in provinces else 0
        selected_province = st.selectbox("เลือกจังหวัด (Province)", provinces, index=default_prov_idx)

        districts = get_districts(selected_province)
        default_dist_idx = districts.index("Tha Pla") if "Tha Pla" in districts else 0
        dist_options = ["-- วิเคราะห์ทั้งจังหวัด --"] + districts
        selected_district = st.selectbox("เลือกอำเภอ (District)", dist_options, index=default_dist_idx + 1 if "Tha Pla" in districts else 0)

       # สร้างขอบเขตพื้นที่ (ROI - Region of Interest)
        if selected_district != "-- วิเคราะห์ทั้งจังหวัด --":
            roi = ee.FeatureCollection("FAO/GAUL/2015/level2").filter(ee.Filter.And(
                ee.Filter.eq('ADM1_NAME', selected_province),
                ee.Filter.eq('ADM2_NAME', selected_district)
            ))
        else:
            roi = ee.FeatureCollection("FAO/GAUL/2015/level1").filter(ee.Filter.eq('ADM1_NAME', selected_province))

        # 1. Boundary Highlighting: วาดเส้นขอบเขตเรืองแสงสีฟ้านีออน
        Map.addLayer(ee.Image().paint(roi, 0, 3), {'palette': ['00F2FE']}, f'Boundary: {selected_district}')

        # 2. Auto-Pan/Zoom: ซูมไปที่พื้นที่เป้าหมาย (แก้ไขให้ซูมเฉพาะตอนเปลี่ยนพื้นที่เท่านั้น)
        # ตรวจสอบว่าระบบเคยจำค่าพื้นที่ไว้หรือยัง
        if "last_location" not in st.session_state:
            st.session_state["last_location"] = (selected_province, selected_district)
            Map.centerObject(roi) # ซูมครั้งแรกเมื่อเปิดแอป
        else:
            # ถ้าพื้นที่เป้าหมาย "เปลี่ยนไปจากเดิม" ค่อยสั่งซูมใหม่
            if st.session_state["last_location"] != (selected_province, selected_district):
                st.session_state["last_location"] = (selected_province, selected_district)
                Map.centerObject(roi)

        # ---------------------------------------------------------
        # 🌍 ชั้นข้อมูล และ Data Masking
        # ---------------------------------------------------------
        st.markdown("<hr style='border-color: #1E293B;'>", unsafe_allow_html=True)
        st.markdown("**🌍 ข้อมูลกายภาพ (Physical)**")
        show_landcover = st.checkbox("🟢 ESA Land Cover (การใช้ที่ดิน)", value=True)
        opacity = st.slider("Opacity (ความโปร่งแสง)", 0.0, 1.0, 0.7)

       if show_landcover:
            landcover = ee.ImageCollection("ESA/WorldCover/v200").first()
            # 3. Data Masking: ตัดขอบภาพให้แสดงเฉพาะในพื้นที่เป้าหมาย
            landcover_clipped = landcover.clip(roi) 
            Map.addLayer(landcover_clipped, {}, 'Land Use (Clipped)', opacity=opacity)

            # --- แก้ไขกล่องคำอธิบาย (Legend) ให้แสดงครบทุกสี ---
            esa_legend_dict = {
                'สิ่งปลูกสร้าง/เมือง (สีแดง)': 'fa0000',
                'พื้นที่เกษตรกรรม (สีชมพู)': 'f096ff',
                'ต้นไม้/ป่าไม้ (สีเขียวเข้ม)': '006400',
                'ทุ่งหญ้า (สีเหลือง)': 'ffff4c',
                'พุ่มไม้ (สีส้ม)': 'ffbb22',
                'แหล่งน้ำ (สีน้ำเงิน)': '0064c8',
                'พื้นที่ชุ่มน้ำ (สีฟ้าอมเขียว)': '0096a0',
                'ป่าชายเลน (สีเขียวสว่าง)': '00cf75',
                'พื้นที่ว่างเปล่า (สีเทา)': 'b4b4b4'
            }
            Map.add_legend(title="การใช้ที่ดิน", legend_dict=esa_legend_dict)

        # ---------------------------------------------------------
        # 📊 4. ดึงตัวเลขสถิติพื้นที่ (Area Statistics)
        # ---------------------------------------------------------
        st.markdown("<hr style='border-color: #1E293B;'>", unsafe_allow_html=True)
        st.markdown("### 📊 Area Statistics")

        if show_landcover and st.button("📈 เริ่มการคำนวณสถิติพื้นที่"):
            with st.spinner("AI กำลังสแกนพื้นที่และประมวลผลข้อมูล..."):
                # สั่งให้ AI คำนวณจำนวนพิกเซลในเขตที่เลือก
                stats = landcover_clipped.reduceRegion(
                    reducer=ee.Reducer.frequencyHistogram(),
                    geometry=roi.geometry(),
                    scale=100, # คำนวณที่ความละเอียด 100 เมตรเพื่อความรวดเร็ว
                    maxPixels=1e9
                ).getInfo()

                if 'Map' in stats:
                    raw_data = stats['Map']
                    esa_names = {
                        '10': 'ต้นไม้/ป่าไม้', '20': 'พุ่มไม้', '30': 'ทุ่งหญ้า',
                        '40': 'เกษตรกรรม', '50': 'สิ่งปลูกสร้าง/เมือง',
                        '60': 'พื้นที่ว่างเปล่า', '80': 'แหล่งน้ำ', '90': 'พื้นที่ชุ่มน้ำ', '95': 'ป่าชายเลน'
                    }

                    # แปลงข้อมูลเป็นตารางและกราฟ
                    df_data = []
                    for key, val in raw_data.items():
                        name = esa_names.get(key, f"ประเภท {key}")
                        # พิกเซล 100x100 ม. = 10,000 ตร.ม. (ประมาณ 6.25 ไร่)
                        area_rai = val * 6.25
                        df_data.append({"ประเภทพื้นที่": name, "ขนาด (ไร่)": area_rai})

                    df = pd.DataFrame(df_data).sort_values(by="ขนาด (ไร่)", ascending=False)
                    
                    st.success("ประมวลผลเสร็จสิ้น!")
                    st.dataframe(df.style.format({"ขนาด (ไร่)": "{:,.2f}"}), hide_index=True, use_container_width=True)
                    st.bar_chart(df.set_index("ประเภทพื้นที่"))

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
        # เอาชื่อพื้นที่เฉพาะออก เพื่อให้รองรับการวิเคราะห์ทุกพื้นที่
        sim_tool = st.radio("Simulation Tools", ["กั้นแนวคันดิน", "จำลองฝายชะลอน้ำ", "ปรับแก้ระดับตลิ่ง"])
        
        st.write("") # เว้นบรรทัด
        if st.button("▶️ RUN AI ENGINE"):
            st.success("Compute Engine Active: กำลังเตรียมทรัพยากรประมวลผล...")

# 5. แสดงผลแผนที่หลัก และเปิดระบบดักจับพิกัด
st_folium(
    Map, 
    key="urban_map", # ชื่อหน่วยความจำที่ตั้งไว้เชื่อมโยงกับโค้ดด้านบน
    height=700, 
    use_container_width=True,
    returned_objects=["center", "zoom"] # ให้ระบบส่งค่าแค่พิกัดและระยะซูมกลับมาเพื่อลดความหน่วง
)

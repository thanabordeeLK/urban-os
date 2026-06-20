import streamlit as st
import geemap.foliumap as geemap
import ee
import os
import pandas as pd
from streamlit_option_menu import option_menu

# 1. ตั้งค่าหน้าเว็บ
st.set_page_config(layout="wide", page_title="Urban OS", page_icon="🌐")

# ==========================================
# 🎨 2. ฝัง CSS ตกแต่ง UI
# ==========================================
st.markdown("""
<style>
    .stApp { background-color: #060B14; }
    [data-testid="stSidebar"] { background-color: #0B132B !important; border-right: 1px solid #1E293B; }
    p, span, label { color: #E2E8F0 !important; }
    h1, h2, h3 { color: #00F2FE !important; text-shadow: 0px 0px 8px rgba(0, 242, 254, 0.4); }
    [data-baseweb="popover"] > div { background-color: #0B132B !important; }
    ul[data-baseweb="menu"] { background-color: #0B132B !important; }
    li[role="option"]:hover { background-color: rgba(0, 242, 254, 0.2) !important; color: #00F2FE !important; }
    [data-testid="stFileUploadDropzone"] { background-color: #0B132B !important; border: 2px dashed #00F2FE !important; border-radius: 10px; }
    [data-testid="stFileUploadDropzone"] * { color: #E2E8F0 !important; }
    .stButton>button { background-color: #09203F !important; border: 1px solid #00F2FE !important; color: #00F2FE !important; font-weight: bold; border-radius: 6px; width: 100%; transition: all 0.3s ease; }
    .stButton>button:hover { background-color: #00F2FE !important; color: #060B14 !important; box-shadow: 0px 0px 15px rgba(0, 242, 254, 0.6); }
</style>
""", unsafe_allow_html=True)

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

# ---------------------------------------------------------
# ส่วนควบคุม Sidebar ด้านซ้าย
# ---------------------------------------------------------
with st.sidebar:
    st.markdown("<h3 style='text-align: center; margin-bottom: 20px;'>⚙️ CONTROL PANEL</h3>", unsafe_allow_html=True)
    
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

    # 📍 ระบบค้นหาและกำหนดพื้นที่
    st.markdown("**📍 กำหนดพื้นที่วิเคราะห์**")

    @st.cache_data
    def get_provinces():
        fc = ee.FeatureCollection("FAO/GAUL/2015/level1").filter(ee.Filter.eq('ADM0_NAME', 'Thailand'))
        return sorted(fc.aggregate_array('ADM1_NAME').getInfo())

    @st.cache_data
    def get_districts(province_name):
        fc = ee.FeatureCollection("FAO/GAUL/2015/level2").filter(ee.Filter.eq('ADM1_NAME', province_name))
        return sorted(fc.aggregate_array('ADM2_NAME').getInfo())

    provinces_list = ["-- ประเทศไทย (รวมทุกจังหวัด) --"] + get_provinces()
    default_prov_idx = provinces_list.index("Uttaradit") if "Uttaradit" in provinces_list else 0
    selected_province = st.selectbox("เลือกจังหวัด (Province)", provinces_list, index=default_prov_idx)

    # เช็คว่าผู้ใช้กำลังดูทั้งประเทศหรือไม่ เพื่อใช้ระบบ Smart Load
    is_whole_country = (selected_province == "-- ประเทศไทย (รวมทุกจังหวัด) --")

    if is_whole_country:
        selected_district = "-- วิเคราะห์ทั่วประเทศ --"
        st.selectbox("เลือกอำเภอ (District)", [selected_district], disabled=True)
        roi = ee.FeatureCollection("FAO/GAUL/2015/level0").filter(ee.Filter.eq('ADM0_NAME', 'Thailand'))
    else:
        districts = get_districts(selected_province)
        default_dist_idx = districts.index("Tha Pla") if "Tha Pla" in districts else 0
        dist_options = ["-- วิเคราะห์ทั้งจังหวัด --"] + districts
        selected_district = st.selectbox("เลือกอำเภอ (District)", dist_options, index=default_dist_idx + 1 if "Tha Pla" in districts else 0)

        if selected_district != "-- วิเคราะห์ทั้งจังหวัด --":
            roi = ee.FeatureCollection("FAO/GAUL/2015/level2").filter(ee.Filter.And(ee.Filter.eq('ADM1_NAME', selected_province), ee.Filter.eq('ADM2_NAME', selected_district)))
        else:
            roi = ee.FeatureCollection("FAO/GAUL/2015/level1").filter(ee.Filter.eq('ADM1_NAME', selected_province))

# ---------------------------------------------------------
# สร้างตัวแผนที่ (เปลี่ยนไปใช้ Native Render ป้องกันจอดำ)
# ---------------------------------------------------------
Map = geemap.Map(center=[15.87, 100.99], zoom=6, ee_initialize=False)

# ซูมและวาดขอบเขตเฉพาะเวลาเจาะจงจังหวัดเท่านั้น (ป้องกันแผนที่โหลดหนัก)
if not is_whole_country:
    Map.centerObject(roi)
    Map.addLayer(ee.Image().paint(roi, 0, 2), {'palette': ['00F2FE']}, f'Boundary')

# ---------------------------------------------------------
# จัดการชั้นข้อมูลตามโหมดการทำงาน
# ---------------------------------------------------------
with st.sidebar:
    st.markdown("<hr style='border-color: #1E293B;'>", unsafe_allow_html=True)

    if selected_mode == "General Plan":
        st.markdown("### 🥞 Data Layers (ชั้นข้อมูล)")
        basemap_choice = st.selectbox("🗺️ Basemap (แผนที่ฐาน)", ["HYBRID", "SATELLITE", "ROADMAP", "TERRAIN", "OSM"])
        Map.add_basemap(basemap_choice)

        st.markdown("**🌍 ข้อมูลภูมิประเทศ & แหล่งน้ำ**")
        show_cop_dem = st.checkbox("⛰️ Copernicus DEM", value=False)
        if show_cop_dem: op_cop_dem = st.slider("ความโปร่งแสง DEM", 0.0, 1.0, 0.7)

        show_dswx_s1 = st.checkbox("💧 DSWx-S1 (แหล่งน้ำ Radar)", value=False)
        if show_dswx_s1: op_dswx_s1 = st.slider("ความโปร่งแสง DSWx-S1", 0.0, 1.0, 0.7)

        show_gfd = st.checkbox("🌊 Global Flood Database", value=False)
        if show_gfd: op_gfd = st.slider("ความโปร่งแสง ประวัติน้ำท่วม", 0.0, 1.0, 0.7)

        st.markdown("**🌱 ข้อมูลการใช้ที่ดิน & อากาศ**")
        show_landcover = st.checkbox("🟢 ESA Land Cover", value=False)
        if show_landcover: op_landcover = st.slider("ความโปร่งแสง ESA", 0.0, 1.0, 0.7)

        show_dw = st.checkbox("🌿 Dynamic World V1", value=False)
        if show_dw: op_dw = st.slider("ความโปร่งแสง Dynamic World", 0.0, 1.0, 0.7)

        show_chirts = st.checkbox("🌡️ CHIRTS Max Temp", value=False)
        if show_chirts: op_chirts = st.slider("ความโปร่งแสง อุณหภูมิ", 0.0, 1.0, 0.7)

        st.markdown("**🏙️ ข้อมูลความเป็นเมือง & ประชากร**")
        show_urban = st.checkbox("🏢 GHSL: Degree of Urbanization", value=False)
        if show_urban: op_urban = st.slider("ความโปร่งแสง ความเป็นเมือง", 0.0, 1.0, 0.7)

        show_pop = st.checkbox("👥 GHSL: Global Population", value=False)
        if show_pop: op_pop = st.slider("ความโปร่งแสง ประชากร", 0.0, 1.0, 0.7)

        # ---------------------------------------------------------
        # ระบบโหลดข้อมูลพร้อม Smart Clip (ตัดขอบเฉพาะเมื่อจำเป็น)
        # ---------------------------------------------------------

        if show_cop_dem:
            dem = ee.ImageCollection("COPERNICUS/DEM/GLO30").select('DEM').mosaic()
            if not is_whole_country: dem = dem.clip(roi)
            dem_vis = {'min': 0, 'max': 1000, 'palette': ['006633', 'E5FFCC', '662A00', 'D8D8D8', 'F5F5F5']}
            Map.addLayer(dem, dem_vis, 'Copernicus DEM 30m', opacity=op_cop_dem)
            try: Map.add_colorbar(dem_vis, label="ความสูง (เมตร)", layer_name="Copernicus DEM")
            except: pass

        if show_dswx_s1:
            try:
                img = ee.ImageCollection('OPERA/DSWX/L3_V1/S1').filterBounds(roi).filterDate('2022-01-01', '2024-12-31').mosaic().select('WTR_Water_classification')
                if not is_whole_country: img = img.clip(roi)
                wtr_remapped = img.remap([0, 1, 2, 252, 253, 254], [0, 1, 2, 3, 4, 5])
                Map.addLayer(wtr_remapped, {'min': 0, 'max': 5, 'palette': ['ffffff', '0000ff', '0088ff', 'f2f2f2', 'dfdfdf', 'da00ff']}, 'DSWx-S1', opacity=op_dswx_s1)
                try: Map.add_legend(title="DSWx-S1 สถานะน้ำ", legend_dict={'แหล่งน้ำผิวดิน (Open Water)': '0000ff', 'น้ำท่วมขังบางส่วน (Partial)': '0088ff'})
                except: pass
            except: st.warning("⚠️ ไม่พบข้อมูล DSWx-S1 ในบริเวณนี้")

        if show_gfd:
            try:
                gfdFloodedSum = ee.ImageCollection('GLOBAL_FLOOD_DB/MODIS_EVENTS/V1').filterBounds(roi).select('flooded').sum()
                if not is_whole_country: gfdFloodedSum = gfdFloodedSum.clip(roi)
                durationPalette = ['c3effe', '1341e8', '051cb0', '001133']
                Map.addLayer(gfdFloodedSum.selfMask(), {'min': 0, 'max': 10, 'palette': durationPalette}, 'GFD Flood History', opacity=op_gfd)
                try: Map.add_colorbar({'min': 0, 'max': 10, 'palette': durationPalette}, label="ความถี่น้ำท่วมสะสม", layer_name="Flood DB")
                except: pass
            except: st.warning("⚠️ ไม่พบประวัติน้ำท่วมในบริเวณนี้")

        if show_landcover:
            landcover = ee.ImageCollection("ESA/WorldCover/v200").first()
            if not is_whole_country: landcover = landcover.clip(roi)
            Map.addLayer(landcover, {}, 'ESA Land Use', opacity=op_landcover)
            try: Map.add_legend(title="การใช้ที่ดิน (ESA)", legend_dict={'สิ่งปลูกสร้าง/เมือง': 'fa0000', 'พื้นที่เกษตรกรรม': 'f096ff', 'ต้นไม้/ป่าไม้': '006400', 'ทุ่งหญ้า': 'ffff4c', 'พุ่มไม้': 'ffbb22', 'แหล่งน้ำ': '0064c8', 'พื้นที่ชุ่มน้ำ': '0096a0'})
            except: pass

        if show_dw:
            dw_image = ee.ImageCollection('GOOGLE/DYNAMICWORLD/V1').filterBounds(roi).filterDate('2023-01-01', '2024-01-01').select('label').mode()
            if not is_whole_country: dw_image = dw_image.clip(roi)
            Map.addLayer(dw_image, {'min': 0, 'max': 8, 'palette': ['419bdf', '397d49', '88b053', '7a87c6', 'e49635', 'dfc35a', 'c4281b', 'a59b8f', 'b39fe1']}, 'Dynamic World', opacity=op_dw)
            try: Map.add_legend(title="Dynamic World", legend_dict={'แหล่งน้ำ': '419bdf', 'ต้นไม้': '397d49', 'หญ้า': '88b053', 'เกษตรกรรม': 'e49635', 'สิ่งปลูกสร้าง': 'c4281b'})
            except: pass

        if show_chirts:
            max_temp = ee.ImageCollection('UCSB-CHG/CHIRTS/DAILY').filter(ee.Filter.date('2016-05-01', '2016-05-31')).select('maximum_temperature').mean()
            if not is_whole_country: max_temp = max_temp.clip(roi)
            temp_vis = {'min': 20, 'max': 40, 'palette': ['darkblue', 'blue', 'cyan', 'green', 'yellow', 'orange', 'red', 'darkred']}
            Map.addLayer(max_temp, temp_vis, 'CHIRTS Max Temp', opacity=op_chirts)
            try: Map.add_colorbar(temp_vis, label="อุณหภูมิสูงสุด (°C)", layer_name="CHIRTS")
            except: pass

        if show_urban:
            urban_image = ee.Image("JRC/GHSL/P2023A/GHS_SMOD_V2-0/2030").select('smod_code')
            if not is_whole_country: urban_image = urban_image.clip(roi)
            Map.addLayer(urban_image, {}, 'Degree of Urbanization', opacity=op_urban)
            try: Map.add_legend(title="ระดับความเป็นเมือง", legend_dict={'ศูนย์กลางเมือง (หนาแน่น)': 'ff0000', 'ชุมชนชานเมือง (ปานกลาง)': 'ffa500', 'ชนบท (เบาบาง)': '00ff00'})
            except: pass

        if show_pop:
            pop_image = ee.Image('JRC/GHSL/P2023A/GHS_POP/2020')
            if not is_whole_country: pop_image = pop_image.clip(roi)
            pop_image = pop_image.updateMask(pop_image.gt(0))
            pop_vis = {'min': 0.0, 'max': 100.0, 'palette': ['000004', '320A5A', '781B6C', 'BB3654', 'EC6824', 'FBB41A', 'FCFFA4']}
            Map.addLayer(pop_image, pop_vis, 'Population Density', opacity=op_pop)
            try: Map.add_colorbar(pop_vis, label="ความหนาแน่นประชากร (คน)", layer_name="Population")
            except: pass

        # 📊 สถิติ (เพิ่มระบบ Auto-Scale ป้องกันแอปค้างเมื่อคำนวณทั้งประเทศ)
        st.markdown("<hr style='border-color: #1E293B;'>", unsafe_allow_html=True)
        st.markdown("### 📊 Area Statistics")
        if show_landcover and st.button("📈 คำนวณสถิติพื้นที่ (ESA)"):
            with st.spinner("AI กำลังสแกนพื้นที่..."):
                calc_scale = 1000 if is_whole_country else 100
                stats = landcover.reduceRegion(reducer=ee.Reducer.frequencyHistogram(), geometry=roi.geometry(), scale=calc_scale, maxPixels=1e13).getInfo()
                if 'Map' in stats:
                    df = pd.DataFrame([{"ประเภทพื้นที่": {'10': 'ต้นไม้', '40': 'เกษตรกรรม', '50': 'เมือง', '80': 'แหล่งน้ำ'}.get(k, f"ประเภท {k}"), "ขนาด (ไร่)": v * (calc_scale**2) / 1600} for k, v in stats['Map'].items()])
                    st.success("สำเร็จ!")
                    st.bar_chart(df.sort_values(by="ขนาด (ไร่)", ascending=False).set_index("ประเภทพื้นที่"))

    elif selected_mode == "AI Simulation":
        Map.add_basemap("SATELLITE") 
        st.markdown("### 🏢 1. Import Data")
        uploaded_file = st.file_uploader("Upload Shapefile / KML", type=['zip', 'kml'])
        
        st.markdown("### 🔍 2. Spatial Analysis")
        analysis_type = st.selectbox("Model Type", ["Urban Growth Tracking", "Flood Risk Simulation"])
        if analysis_type == "Urban Growth Tracking":
            start_year = st.slider("เลือกปีเริ่มต้น (อดีต)", min_value=2014, max_value=2022, value=2015)
        
        st.markdown("### 🛡️ 4. Engineering Mitigation")
        sim_tool = st.radio("Simulation Tools", ["กั้นแนวคันดิน", "จำลองฝายชะลอน้ำ", "ปรับแก้ระดับตลิ่ง"])
        run_ai = st.button("▶️ RUN AI ENGINE")

        if analysis_type == "Urban Growth Tracking" and run_ai:
            with st.spinner(f"🧠 ประมวลผลระหว่างปี {start_year} กับ 2023..."):
                viirs_past = ee.ImageCollection('NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG').filterDate(f'{start_year}-01-01', f'{start_year}-12-31').median().select('avg_rad')
                viirs_present = ee.ImageCollection('NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG').filterDate('2023-01-01', '2023-12-31').median().select('avg_rad')
                
                if not is_whole_country:
                    viirs_past = viirs_past.clip(roi)
                    viirs_present = viirs_present.clip(roi)
                    
                urban_growth = viirs_present.gt(3).And(viirs_past.gt(3).Not())
                Map.addLayer(viirs_present, {'min': 0, 'max': 20, 'palette': ['black', 'purple', 'blue']}, 'Nighttime Lights 2023', False)
                Map.addLayer(urban_growth.updateMask(urban_growth), {'palette': ['#FF007F']}, f'New Growth ({start_year}-2023)')
                try: Map.add_legend(title="ผลลัพธ์ GEO AI", legend_dict={f'พื้นที่ขยายตัวใหม่ ({start_year}-2023)': 'FF007F'})
                except: pass
                st.toast("จำลองโมเดลเสร็จสิ้น!", icon="✨")

# 5. แสดงผลแผนที่หลักแบบ Native (เสถียรที่สุด ไม่ดับกลางอากาศ)
Map.to_streamlit(height=700)

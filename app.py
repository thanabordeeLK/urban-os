import streamlit as st
import geemap.foliumap as geemap
import ee
import os
import pandas as pd
from streamlit_option_menu import option_menu
from streamlit_folium import st_folium

# 1. ตั้งค่าหน้าเว็บให้แสดงผลแบบเต็มจอ
st.set_page_config(layout="wide", page_title="Urban OS", page_icon="🌐")

# ==========================================
# 🎨 2. ฝัง CSS ตกแต่ง UI สไตล์ AI Cyberpunk
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
# ระบบดึงพิกัดและความจำแผนที่ (Session State) แบบปลอดภัย 100%
# ---------------------------------------------------------
map_center = [15.87, 100.99]
map_zoom = 6

# แก้ไขบั๊กหน้าจอดำ: ดักจับกรณีที่หน่วยความจำ (Session) ยังว่างเปล่า
if "urban_map" in st.session_state and st.session_state["urban_map"] is not None:
    state = st.session_state["urban_map"]
    if "center" in state and state["center"] is not None:
        map_center = [state["center"]["lat"], state["center"]["lng"]]
    if "zoom" in state and state["zoom"] is not None:
        map_zoom = state["zoom"]

Map = geemap.Map(center=map_center, zoom=map_zoom, ee_initialize=False)

# 4. จัดการแถบเมนูด้านข้าง (Sidebar)
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

    # 📍 ระบบค้นหาและกำหนดพื้นที่ระดับสากล
    st.markdown("**📍 กำหนดพื้นที่วิเคราะห์**")

    @st.cache_data
    def get_provinces():
        fc = ee.FeatureCollection("FAO/GAUL/2015/level1").filter(ee.Filter.eq('ADM0_NAME', 'Thailand'))
        return sorted(fc.aggregate_array('ADM1_NAME').getInfo())

    @st.cache_data
    def get_districts(province_name):
        fc = ee.FeatureCollection("FAO/GAUL/2015/level2").filter(ee.Filter.eq('ADM1_NAME', province_name))
        return sorted(fc.aggregate_array('ADM2_NAME').getInfo())

    provinces = get_provinces()
    default_prov_idx = provinces.index("Uttaradit") if "Uttaradit" in provinces else 0
    selected_province = st.selectbox("เลือกจังหวัด (Province)", provinces, index=default_prov_idx)

    districts = get_districts(selected_province)
    default_dist_idx = districts.index("Tha Pla") if "Tha Pla" in districts else 0
    dist_options = ["-- วิเคราะห์ทั้งจังหวัด --"] + districts
    selected_district = st.selectbox("เลือกอำเภอ (District)", dist_options, index=default_dist_idx + 1 if "Tha Pla" in districts else 0)

    # สร้างขอบเขตพื้นที่ (ROI)
    if selected_district != "-- วิเคราะห์ทั้งจังหวัด --":
        roi = ee.FeatureCollection("FAO/GAUL/2015/level2").filter(ee.Filter.And(
            ee.Filter.eq('ADM1_NAME', selected_province),
            ee.Filter.eq('ADM2_NAME', selected_district)
        ))
    else:
        roi = ee.FeatureCollection("FAO/GAUL/2015/level1").filter(ee.Filter.eq('ADM1_NAME', selected_province))

    Map.addLayer(ee.Image().paint(roi, 0, 3), {'palette': ['00F2FE']}, f'Boundary')

    if "last_location" not in st.session_state:
        st.session_state["last_location"] = (selected_province, selected_district)
        Map.centerObject(roi)
    else:
        if st.session_state["last_location"] != (selected_province, selected_district):
            st.session_state["last_location"] = (selected_province, selected_district)
            Map.centerObject(roi)

    st.markdown("<hr style='border-color: #1E293B;'>", unsafe_allow_html=True)

# ==========================================
    # โหมดที่ 1: งานแผนทั่วไป
    # ==========================================
    if selected_mode == "General Plan":
        st.markdown("### 🥞 Data Layers (ชั้นข้อมูล)")
        basemap_choice = st.selectbox("🗺️ Basemap (มีข้อมูลถนนและซอยใน OSM)", ["HYBRID", "SATELLITE", "ROADMAP", "TERRAIN", "OSM"])
        Map.add_basemap(basemap_choice)

        st.markdown("**🌍 ข้อมูลภูมิประเทศ & แหล่งน้ำ (Physical & Water)**")
        
        show_cop_dem = st.checkbox("⛰️ Copernicus DEM (ความสูง 30m)", value=False)
        if show_cop_dem: op_cop_dem = st.slider("ความโปร่งแสง DEM", 0.0, 1.0, 0.7, key="op1")

        show_eng_dem = st.checkbox("⛰️ England 1m DTM (เฉพาะ UK)", value=False)
        if show_eng_dem: op_eng_dem = st.slider("ความโปร่งแสง England DTM", 0.0, 1.0, 0.7, key="op2")

        show_dswx_s1 = st.checkbox("💧 DSWx-S1 (แหล่งน้ำ Radar)", value=False)
        if show_dswx_s1: op_dswx_s1 = st.slider("ความโปร่งแสง DSWx-S1", 0.0, 1.0, 0.7, key="op3")

        show_dswx_hls = st.checkbox("💧 DSWx-HLS (แหล่งน้ำ Optical)", value=False)
        if show_dswx_hls: op_dswx_hls = st.slider("ความโปร่งแสง DSWx-HLS", 0.0, 1.0, 0.7, key="op4")

        show_gfd = st.checkbox("🌊 Global Flood Database (ประวัติน้ำท่วมขัง)", value=False)
        if show_gfd: op_gfd = st.slider("ความโปร่งแสง Flood Database", 0.0, 1.0, 0.7, key="op5")

        st.markdown("**🌱 ข้อมูลการใช้ที่ดิน & อากาศ (Land Cover & Climate)**")
        
        show_landcover = st.checkbox("🟢 ESA Land Cover (การใช้ที่ดิน)", value=False)
        if show_landcover: op_landcover = st.slider("ความโปร่งแสง ESA", 0.0, 1.0, 0.7, key="op6")

        show_dw = st.checkbox("🌿 Dynamic World V1 (การใช้ที่ดิน Real-time)", value=False)
        if show_dw: op_dw = st.slider("ความโปร่งแสง Dynamic World", 0.0, 1.0, 0.7, key="op7")

        show_chirts = st.checkbox("🌡️ CHIRTS Max Temperature (อุณหภูมิ 2016)", value=False)
        if show_chirts: op_chirts = st.slider("ความโปร่งแสง อุณหภูมิ", 0.0, 1.0, 0.7, key="op8")

        st.markdown("**🏙️ ข้อมูลการขยายตัวเมือง & ประชากร (Urbanization)**")
        
        show_urban = st.checkbox("🏢 GHSL: Degree of Urbanization (ระดับความเป็นเมือง)", value=False)
        if show_urban: op_urban = st.slider("ความโปร่งแสง ความเป็นเมือง", 0.0, 1.0, 0.7, key="op9")

        show_pop = st.checkbox("👥 GHSL: Global Population (ความหนาแน่นประชากร)", value=False)
        if show_pop: op_pop = st.slider("ความโปร่งแสง ประชากร", 0.0, 1.0, 0.7, key="op10")

        # ---------------------------------------------------------
        # ส่วนเรียกใช้ข้อมูลและดึงค่าความโปร่งแสงแบบแยกอิสระ
        # ---------------------------------------------------------

        if show_cop_dem:
            dem = ee.ImageCollection("COPERNICUS/DEM/GLO30").select('DEM').mosaic().clip(roi)
            dem_vis = {'min': 0, 'max': 1000, 'palette': ['006633', 'E5FFCC', '662A00', 'D8D8D8', 'F5F5F5']}
            Map.addLayer(dem, dem_vis, 'Copernicus DEM 30m', opacity=op_cop_dem)

        if show_eng_dem:
            eng_img = ee.Image('UK/EA/ENGLAND_1M_TERRAIN/2022').select('dtm')
            eng_vis = {'palette': ['0000ff', '00ffff', 'ffff00', 'ff0000', 'ffffff'], 'max': 630, 'min': -5}
            Map.addLayer(eng_img, eng_vis, 'England 1m DTM', opacity=op_eng_dem)

        if show_dswx_s1:
            dswx_s1_col = ee.ImageCollection('OPERA/DSWX/L3_V1/S1').filterBounds(roi).filterDate('2023-01-01', '2024-01-01')
            def mask_s1(image):
                wtr = image.select('WTR_Water_classification')
                return wtr.updateMask(wtr.lt(252))
            dswx_s1 = dswx_s1_col.map(mask_s1).reduce(ee.Reducer.max()).rename('WTR_Water_classification').clip(roi)
            wtr_palette = ['ffffff', '0000ff', '0088ff', 'f2f2f2', 'dfdfdf', 'da00ff']
            wtr_remapped = dswx_s1.remap([0, 1, 2, 252, 253, 254], [0, 1, 2, 3, 4, 5])
            Map.addLayer(wtr_remapped, {'min': 0, 'max': 5, 'palette': wtr_palette}, 'DSWx-S1 Water Extent', opacity=op_dswx_s1)

        if show_dswx_hls:
            dswx_hls_col = ee.ImageCollection('OPERA/DSWX/L3_V1/HLS').filterBounds(roi).filterDate('2023-01-01', '2024-01-01')
            def mask_hls(image):
                wtr = image.select('WTR_Water_classification')
                return wtr.updateMask(wtr.lt(252))
            dswx_hls = dswx_hls_col.map(mask_hls).reduce(ee.Reducer.mode()).rename('WTR_Water_classification').clip(roi)
            wtr_remapped_hls = dswx_hls.remap([0, 1, 2, 252, 253, 254], [0, 1, 2, 3, 4, 5])
            wtr_palette_hls = ['ffffff', '0000ff', '0088ff', 'f2f2f2', 'dfdfdf', 'da00ff']
            Map.addLayer(wtr_remapped_hls, {'min': 0, 'max': 5, 'palette': wtr_palette_hls}, 'DSWx-HLS Water Extent', opacity=op_dswx_hls)

        if show_gfd:
            gfd = ee.ImageCollection('GLOBAL_FLOOD_DB/MODIS_EVENTS/V1').filterBounds(roi)
            gfdFloodedSum = gfd.select('flooded').sum().clip(roi)
            durationPalette = ['c3effe', '1341e8', '051cb0', '001133']
            Map.addLayer(gfdFloodedSum.selfMask(), {'min': 0, 'max': 10, 'palette': durationPalette}, 'GFD Flood History', opacity=op_gfd)

        if show_landcover:
            landcover = ee.ImageCollection("ESA/WorldCover/v200").first().clip(roi)
            Map.addLayer(landcover, {}, 'ESA Land Use', opacity=op_landcover)
            esa_legend_dict = {
                'สิ่งปลูกสร้าง/เมือง (สีแดง)': 'fa0000', 'พื้นที่เกษตรกรรม (สีชมพู)': 'f096ff',
                'ต้นไม้/ป่าไม้ (สีเขียวเข้ม)': '006400', 'ทุ่งหญ้า (สีเหลือง)': 'ffff4c',
                'พุ่มไม้ (สีส้ม)': 'ffbb22', 'แหล่งน้ำ (สีน้ำเงิน)': '0064c8',
                'พื้นที่ชุ่มน้ำ (สีฟ้าอมเขียว)': '0096a0', 'ป่าชายเลน (สีเขียวสว่าง)': '00cf75',
                'พื้นที่ว่างเปล่า (สีเทา)': 'b4b4b4'
            }
            Map.add_legend(title="การใช้ที่ดิน", legend_dict=esa_legend_dict)

        if show_dw:
            dw_col = ee.ImageCollection('GOOGLE/DYNAMICWORLD/V1').filterBounds(roi).filterDate('2023-01-01', '2024-01-01')
            dw_image = dw_col.select('label').mode().clip(roi)
            dw_vis = {'min': 0, 'max': 8, 'palette': ['419bdf', '397d49', '88b053', '7a87c6', 'e49635', 'dfc35a', 'c4281b', 'a59b8f', 'b39fe1']}
            Map.addLayer(dw_image, dw_vis, 'Dynamic World LULC', opacity=op_dw)

        if show_chirts:
            chirts_dataset = ee.ImageCollection('UCSB-CHG/CHIRTS/DAILY').filter(ee.Filter.date('2016-05-01', '2016-05-31'))
            max_temp = chirts_dataset.select('maximum_temperature').mean().clip(roi)
            temp_vis = {'min': 10, 'max': 40, 'palette': ['darkblue', 'blue', 'cyan', 'green', 'yellow', 'orange', 'red', 'darkred']}
            Map.addLayer(max_temp, temp_vis, 'CHIRTS Max Temp', opacity=op_chirts)

        if show_urban:
            urban_image = ee.Image("JRC/GHSL/P2023A/GHS_SMOD_V2-0/2030").select('smod_code').clip(roi)
            Map.addLayer(urban_image, {}, 'Degree of Urbanization', opacity=op_urban)

        if show_pop:
            pop_image = ee.Image('JRC/GHSL/P2023A/GHS_POP/2020').clip(roi)
            pop_image = pop_image.updateMask(pop_image.gt(0))
            pop_vis = {'min': 0.0, 'max': 100.0, 'palette': ['000004', '320A5A', '781B6C', 'BB3654', 'EC6824', 'FBB41A', 'FCFFA4']}
            Map.addLayer(pop_image, pop_vis, 'Population Density 2020', opacity=op_pop)

        # 📊 คำนวณสถิติพื้นที่
        st.markdown("<hr style='border-color: #1E293B;'>", unsafe_allow_html=True)
        st.markdown("### 📊 Area Statistics")
        if show_landcover and st.button("📈 เริ่มการคำนวณสถิติพื้นที่ (จาก ESA Land Cover)"):
            with st.spinner("AI กำลังสแกนพื้นที่และประมวลผลข้อมูล..."):
                stats = landcover.reduceRegion(
                    reducer=ee.Reducer.frequencyHistogram(), geometry=roi.geometry(), scale=100, maxPixels=1e9
                ).getInfo()

                if 'Map' in stats:
                    raw_data = stats['Map']
                    esa_names = {
                        '10': 'ต้นไม้/ป่าไม้', '20': 'พุ่มไม้', '30': 'ทุ่งหญ้า',
                        '40': 'เกษตรกรรม', '50': 'สิ่งปลูกสร้าง/เมือง',
                        '60': 'พื้นที่ว่างเปล่า', '80': 'แหล่งน้ำ', '90': 'พื้นที่ชุ่มน้ำ', '95': 'ป่าชายเลน'
                    }
                    df_data = []
                    for key, val in raw_data.items():
                        name = esa_names.get(key, f"ประเภท {key}")
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
        analysis_type = st.selectbox("Model Type", ["Urban Growth Tracking", "Flood Risk Simulation", "Land Suitability"])
        
        if analysis_type == "Urban Growth Tracking":
            st.info("💡 โมเดล AI จะวิเคราะห์การขยายตัวของเมืองจากความเข้มของแสงไฟและกิจกรรมทางเศรษฐกิจในอดีตเทียบกับปัจจุบัน (ปี 2023)")
            start_year = st.slider("เลือกปีเริ่มต้น (อดีต) เพื่อเปรียบเทียบ", min_value=2014, max_value=2022, value=2015)
        
        st.markdown("### 📈 3. Predictive Modeling")
        predict_years = st.slider("Forecast Timeline (Years)", 1, 30, 5)
        
        st.markdown("### 🛡️ 4. Engineering Mitigation")
        sim_tool = st.radio("Simulation Tools", ["กั้นแนวคันดิน", "จำลองฝายชะลอน้ำ", "ปรับแก้ระดับตลิ่ง"])
        
        st.write("") 
        run_ai = st.button("▶️ RUN AI ENGINE")

        # นำบล็อกการประมวลผล AI เข้ามาไว้ในโหมดที่ 2 โดยตรงเพื่อไม่ให้ตีกับโหมด General Plan
        if analysis_type == "Urban Growth Tracking" and run_ai:
            with st.spinner(f"🧠 GEO AI Engine กำลังประมวลผลการคำนวณความแตกต่างเชิงพื้นที่ระหว่างปี {start_year} กับ 2023..."):
                viirs_past = ee.ImageCollection('NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG')\
                    .filterDate(f'{start_year}-01-01', f'{start_year}-12-31').median().select('avg_rad').clip(roi)
                    
                viirs_present = ee.ImageCollection('NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG')\
                    .filterDate('2023-01-01', '2023-12-31').median().select('avg_rad').clip(roi)
                
                urban_past = viirs_past.gt(3)
                urban_present = viirs_present.gt(3)
                
                urban_growth = urban_present.And(urban_past.Not())
                
                Map.addLayer(viirs_present, {'min': 0, 'max': 20, 'palette': ['black', 'purple', 'blue']}, 'Base: Nighttime Lights 2023', False)
                Map.addLayer(urban_growth.updateMask(urban_growth), {'palette': ['#FF007F']}, f'📈 New Urban Growth ({start_year}-2023)')
                
                growth_legend = {f'พื้นที่ขยายตัวใหม่ ({start_year}-2023)': 'FF007F'}
                Map.add_legend(title="ผลลัพธ์ GEO AI", legend_dict=growth_legend)
                
                st.toast("🧠 AI จำลองโมเดลเสร็จสิ้น! แสดงแถบสีชมพูในจุดที่เมืองขยายตัว", icon="✨")

# 5. ประมวลผลแผนที่หลัก
# ใช้ Map.to_streamlit แทน st_folium(Map) เพื่อความเสถียรของไลบรารี
Map.to_streamlit(height=700, key="urban_map", returned_objects=["center", "zoom"])

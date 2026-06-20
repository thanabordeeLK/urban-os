import streamlit as st
import geemap.foliumap as geemap
import ee
import os
import pandas as pd

# 1. ตั้งค่าหน้าเว็บ
st.set_page_config(layout="wide", page_title="Urban OS", page_icon="🌐")

# ==========================================
# 🎨 2. ฝัง CSS ตกแต่ง UI สไตล์ AI Cyberpunk
# ==========================================
st.markdown("""
<style>
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 0rem !important;
        max-width: 98% !important;
    }
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
# ส่วนควบคุม Sidebar ด้านซ้าย (เมนูและพื้นที่)
# ---------------------------------------------------------
with st.sidebar:
    st.markdown("<h3 style='text-align: center; margin-bottom: 20px;'>⚙️ CONTROL PANEL</h3>", unsafe_allow_html=True)
    from streamlit_option_menu import option_menu
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

    st.markdown("<hr style='border-color: #1E293B;'>", unsafe_allow_html=True)
    if selected_mode == "General Plan":
        st.markdown("### 🥞 Data Layers (ชั้นข้อมูล)")
        basemap_choice = st.selectbox("🗺️ Basemap (แผนที่ฐาน)", ["HYBRID", "SATELLITE", "ROADMAP", "TERRAIN", "OSM"])
    else:
        basemap_choice = "SATELLITE"

# ---------------------------------------------------------
# สร้างตัวแผนที่หลัก
# ---------------------------------------------------------
Map = geemap.Map(center=[15.87, 100.99], zoom=6, basemap=basemap_choice, ee_initialize=False)

if not is_whole_country:
    Map.centerObject(roi)
    Map.addLayer(ee.Image().paint(roi, 0, 2), {'palette': ['00F2FE']}, f'Boundary')

master_legend = {}

# ---------------------------------------------------------
# บล็อกควบคุมตามโหมดการทำงาน
# ---------------------------------------------------------
with st.sidebar:
    if selected_mode == "General Plan":
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

        # เรนเดอร์ชั้นข้อมูลฝั่ง แพลนทั่วไป
        if show_cop_dem:
            dem = ee.ImageCollection("COPERNICUS/DEM/GLO30").select('DEM').mosaic()
            if not is_whole_country: dem = dem.clip(roi)
            Map.addLayer(dem, {'min': 0, 'max': 1000, 'palette': ['006633', 'E5FFCC', '662A00', 'D8D8D8', 'F5F5F5']}, 'Copernicus DEM 30m', opacity=op_cop_dem)

        if show_dswx_s1:
            try:
                img = ee.ImageCollection('OPERA/DSWX/L3_V1/S1').filterBounds(roi).filterDate('2022-01-01', '2024-12-31').mosaic().select('WTR_Water_classification')
                if not is_whole_country: img = img.clip(roi)
                wtr_remapped = img.remap([0, 1, 2, 252, 253, 254], [0, 1, 2, 3, 4, 5])
                Map.addLayer(wtr_remapped, {'min': 0, 'max': 5, 'palette': ['ffffff', '0000ff', '0088ff', 'f2f2f2', 'dfdfdf', 'da00ff']}, 'DSWx-S1', opacity=op_dswx_s1)
                master_legend.update({'[น้ำ] ผิวดิน (Radar)': '0000ff', '[น้ำ] ท่วมขัง (Radar)': '0088ff'})
            except: pass

        if show_gfd:
            try:
                gfdFloodedSum = ee.ImageCollection('GLOBAL_FLOOD_DB/MODIS_EVENTS/V1').filterBounds(roi).select('flooded').sum()
                if not is_whole_country: gfdFloodedSum = gfdFloodedSum.clip(roi)
                Map.addLayer(gfdFloodedSum.selfMask(), {'min': 0, 'max': 10, 'palette': ['c3effe', '1341e8', '051cb0', '001133']}, 'GFD Flood History', opacity=op_gfd)
            except: pass

        if show_landcover:
            landcover = ee.ImageCollection("ESA/WorldCover/v200").first()
            if not is_whole_country: landcover = landcover.clip(roi)
            Map.addLayer(landcover, {}, 'ESA Land Use', opacity=op_landcover)
            master_legend.update({'[ESA] เมือง/สร้าง': 'fa0000', '[ESA] เกษตร': 'f096ff', '[ESA] ป่าไม้': '006400', '[ESA] แหล่งน้ำ': '0064c8'})

        if show_dw:
            dw_image = ee.ImageCollection('GOOGLE/DYNAMICWORLD/V1').filterBounds(roi).filterDate('2023-01-01', '2024-01-01').select('label').mode()
            if not is_whole_country: dw_image = dw_image.clip(roi)
            Map.addLayer(dw_image, {'min': 0, 'max': 8, 'palette': ['419bdf', '397d49', '88b053', '7a87c6', 'e49635', 'dfc35a', 'c4281b', 'a59b8f', 'b39fe1']}, 'Dynamic World', opacity=op_dw)
            master_legend.update({'[DW] แหล่งน้ำ': '419bdf', '[DW] ต้นไม้': '397d49', '[DW] สิ่งปลูกสร้าง': 'c4281b'})

        if show_chirts:
            max_temp = ee.ImageCollection('UCSB-CHG/CHIRTS/DAILY').filter(ee.Filter.date('2016-05-01', '2016-05-31')).select('maximum_temperature').mean()
            if not is_whole_country: max_temp = max_temp.clip(roi)
            Map.addLayer(max_temp, {'min': 20, 'max': 40, 'palette': ['darkblue', 'blue', 'cyan', 'green', 'yellow', 'orange', 'red', 'darkred']}, 'CHIRTS Max Temp', opacity=op_chirts)

        if show_urban:
            urban_image = ee.Image("JRC/GHSL/P2023A/GHS_SMOD_V2-0/2030").select('smod_code')
            if not is_whole_country: urban_image = urban_image.clip(roi)
            Map.addLayer(urban_image, {}, 'Degree of Urbanization', opacity=op_urban)
            master_legend.update({'[เมือง] หนาแน่น': 'ff0000', '[เมือง] ปานกลาง': 'ffa500', '[เมือง] ชนบท': '00ff00'})

        if show_pop:
            pop_image = ee.Image('JRC/GHSL/P2023A/GHS_POP/2020')
            if not is_whole_country: pop_image = pop_image.clip(roi)
            pop_image = pop_image.updateMask(pop_image.gt(0))
            Map.addLayer(pop_image, {'min': 0.0, 'max': 100.0, 'palette': ['000004', '320A5A', '781B6C', 'BB3654', 'EC6824', 'FBB41A', 'FCFFA4']}, 'Population Density', opacity=op_pop)

        if master_legend:
            try: Map.add_legend(title="สัญลักษณ์ชั้นข้อมูล", legend_dict=master_legend)
            except: pass

        st.markdown("<hr style='border-color: #1E293B;'>", unsafe_allow_html=True)
        st.markdown("### 📊 Area Statistics")
        if show_landcover and st.button("📈 คำนวณสถิติพื้นที่ (ESA)"):
            with st.spinner("AI กำลังสแกนพื้นที่..."):
                calc_scale = 1000 if is_whole_country else 100
                stats = landcover.reduceRegion(reducer=ee.Reducer.frequencyHistogram(), geometry=roi.geometry(), scale=calc_scale, maxPixels=1e13).getInfo()
                if 'Map' in stats:
                    df = pd.DataFrame([{"ประเภทพื้นที่": {'10': 'ต้นไม้', '40': 'เกษตรกรรม', '50': 'เมือง', '80': 'แหล่งน้ำ'}.get(k, f"ประเภท {k}"), "ขนาด (ไร่)": v * (calc_scale**2) / 1600} for k, v in stats['Map'].items()])
                    st.bar_chart(df.sort_values(by="ขนาด (ไร่)", ascending=False).set_index("ประเภทพื้นที่"))

    # ==========================================
    # 🧠 โหมดที่ 2: วิเคราะห์ขั้นสูง (AI Simulation) พร้อมระบบสกัดข้อมูล & พยากรณ์จริง
    # ==========================================
    elif selected_mode == "AI Simulation":
        st.markdown("### 🏢 1. Import Data")
        uploaded_file = st.file_uploader("Upload Shapefile / KML", type=['zip', 'kml'])
        
        st.markdown("### 🔍 2. Spatial Analysis")
        analysis_type = st.selectbox("Model Type", ["Urban Growth Tracking", "Flood Risk Simulation"])
        
        if analysis_type == "Urban Growth Tracking":
            st.info("🧠 ระบบจะใช้โมเดลดึงข้อมูลอนุกรมเวลาเพื่อสแกนอัตราการขยายตัวของเมืองในอดีต และทำนายแนวโน้มอนาคตเชิงพื้นที่")
            start_year = st.slider("เลือกปีเริ่มต้นในอดีต (เพื่อสร้างสมการ)", min_value=2014, max_value=2021, value=2015)
        
        st.markdown("### 📈 3. Predictive Modeling")
        predict_years = st.slider("Forecast Timeline (จำนวนปีที่ทำนายไปข้างหน้า)", 1, 30, 10)
        
        st.markdown("### 🛡️ 4. Engineering Mitigation")
        sim_tool = st.radio("Simulation Tools", ["กั้นแนวคันดิน", "จำลองฝายชะลอน้ำ", "ปรับแก้ระดับตลิ่ง"])
        
        run_ai = st.button("▶️ RUN AI ENGINE")

# ---------------------------------------------------------
# ส่วนสมองกลประมวลผลอนุกรมเวลา และวาดกราฟทำนาย (High-Resolution NDBI)
# ---------------------------------------------------------
df_trend = None 

if selected_mode == "AI Simulation" and analysis_type == "Urban Growth Tracking" and run_ai:
    st.toast("🚀 กำลังเชื่อมต่อดาวเทียม Landsat-8 (ความละเอียด 30m/พิกเซล)...", icon="🛰️")
    
    # สร้างหลอด Progress Bar เพื่อให้ผู้ใช้รู้สถานะการดึงข้อมูล 10 ปี
    progress_text = "กำลังสแกนพื้นที่ด้วย AI..."
    my_bar = st.progress(0, text=progress_text)
    
    with st.spinner("🧠 ขั้นตอนที่ 1/2: ดึงข้อมูลโครงสร้างพื้นฐานระดับ High-Res..."):
        try:
            current_max_year = 2023
            years = list(range(start_year, current_max_year + 1))
            time_series_data = []
            
            ndbi_past = None
            ndbi_present = None

            # วนลูปดึงภาพดาวเทียม Landsat-8 ทีละปี เพื่อความแม่นยำสูง
            for i, y in enumerate(years):
                my_bar.progress((i + 1) / len(years), text=f"กำลังสกัดข้อมูลตึกและสิ่งปลูกสร้าง ปี {y}...")
                
                # 1. ดึงข้อมูล Landsat 8 (คัดกรองเมฆน้อยกว่า 30%)
                l8 = ee.ImageCollection("LANDSAT/LC08/C02/T1_TOA") \
                    .filterBounds(roi) \
                    .filterDate(f'{y}-01-01', f'{y}-12-31') \
                    .filter(ee.Filter.lt('CLOUD_COVER', 30))
                
                # 2. คำนวณ NDBI (ดัชนีสิ่งปลูกสร้าง) สมการ: (SWIR1 - NIR) / (SWIR1 + NIR)
                def calc_ndbi(img):
                    return img.normalizedDifference(['B6', 'B5']).rename('NDBI')
                    
                ndbi_year = l8.map(calc_ndbi).median().clip(clip_roi)
                
                # 3. คัดแยกเฉพาะพิกเซลที่เป็นสิ่งปลูกสร้าง (ค่า NDBI > 0)
                built_up = ndbi_year.gt(0.0)
                
                # 4. แปลงจำนวนพิกเซลเป็นพื้นที่ตารางเมตร (sqm) และหารเป็น "ไร่"
                area_image = built_up.multiply(ee.Image.pixelArea())
                calc_scale = 30 # ความละเอียด 30 เมตร
                
                area_stats = area_image.reduceRegion(
                    reducer=ee.Reducer.sum(),
                    geometry=roi.geometry(),
                    scale=calc_scale,
                    maxPixels=1e13
                ).getInfo()
                
                area_sqm = area_stats.get('NDBI', 0)
                area_rai = area_sqm / 1600.0 if area_sqm else 0
                
                # บันทึกข้อมูลลงตาราง
                time_series_data.append({"Year": y, "Intensity": area_rai}) 
                
                # เก็บฐานข้อมูลปีอดีต และ ปัจจุบัน ไว้ทำแผนที่เปรียบเทียบ
                if y == start_year:
                    ndbi_past = built_up
                if y == current_max_year:
                    ndbi_present = built_up

            my_bar.empty() # ซ่อนหลอดโหลดเมื่อเสร็จ
            st.toast("⚡ สกัดข้อมูลตึกและคอนกรีตสำเร็จ! เตรียมพยากรณ์อนาคต...", icon="🤖")
            
            # --- 🤖 STEP 2: สมการคณิตศาสตร์ทำนายอนาคต (Linear Regression) ---
            df_history = pd.DataFrame(time_series_data)
            X = df_history['Year'].values
            Y = df_history['Intensity'].values
            n = len(X)
            
            m = (n * (X*Y).sum() - X.sum()*Y.sum()) / (n * (X**2).sum() - (X.sum())**2)
            c = (Y.sum() - m * X.sum()) / n
            
            future_years = list(range(current_max_year + 1, current_max_year + predict_years + 1))
            all_years = years + future_years
            
            final_chart_data = []
            for y in all_years:
                hist_val = float(df_history[df_history['Year'] == y]['Intensity'].values[0]) if y <= current_max_year else None
                pred_val = m * y + c
                
                final_chart_data.append({
                    "ปี พ.ศ./ค.ศ.": str(y),
                    "พื้นที่เมืองจริง (ไร่)": hist_val,
                    "เส้นพยากรณ์การขยายตัว (ไร่)": pred_val
                })
            
            df_trend = pd.DataFrame(final_chart_data)
            
            # --- STEP 3: วาดผลลัพธ์ระดับ High-Res ลงแผนที่ ---
            # หาพื้นที่งอกใหม่: ปัจจุบันเป็นตึก(1) และอดีตไม่ใช่ตึก(0)
            urban_growth = ndbi_present.eq(1).And(ndbi_past.eq(0))
            
            Map.addLayer(ndbi_present.selfMask(), {'palette': ['#00F2FE']}, 'เมืองและสิ่งปลูกสร้าง (ปัจจุบัน)')
            Map.addLayer(urban_growth.selfMask(), {'palette': ['#FF007F']}, f'พื้นที่ขยายตัวใหม่ ({start_year}-{current_max_year})')
            
            try: Map.add_legend(title="การวิเคราะห์เมือง (30m)", legend_dict={'เมืองและสิ่งปลูกสร้างเดิม': '00F2FE', 'พื้นที่ขยายตัวใหม่ (New Growth)': 'FF007F'})
            except: pass
            
        except Exception as e:
            st.error(f"❌ ระบบ AI ขัดข้องชั่วคราว: {e}")
            my_bar.empty()

# ---------------------------------------------------------
# 📊 ส่วนแสดงผลกราฟเส้นพยากรณ์อนาคต (แสดงใต้แผนที่อย่างเป็นระเบียบ)
# ---------------------------------------------------------
if df_trend is not None:
    st.markdown("### 📈 ผลลัพธ์การสกัดข้อมูลอนุกรมเวลา และเส้นทางทำนายอนาคต (Predictive Timeline)")
    st.markdown(f"วิเคราะห์ขอบเขตพื้นที่เป้าหมายแบบจำลองข้อมูลสะสมย้อนหลังตั้งแต่ปี {start_year} และลากเส้นพยากรณ์โครงสร้างเมืองล่วงหน้าไปอีก {predict_years} ปี")
    
    # พล็อตสองเส้นพร้อมกันอ้างอิงจากคอลัมน์ที่เราคำนวณไว้
    chart_df = df_trend.set_index("ปี พ.ศ./ค.ศ.")
    st.line_chart(chart_df)
    
    # แสดงคำอธิบายสถิติเชิงปริมาณเพิ่มความน่าเชื่อถือ
    with st.expander("🔍 ดูตารางตัวเลขผลลัพธ์เชิงลึก (Data Sheets)"):
        st.dataframe(df_trend, use_container_width=True, hide_index=True)

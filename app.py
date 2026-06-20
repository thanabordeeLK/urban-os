import streamlit as st
import geemap.foliumap as geemap
import ee
import os

# 1. ตั้งค่าหน้าเว็บให้แสดงผลแบบเต็มจอ
st.set_page_config(layout="wide", page_title="Uttaradit Urban OS", page_icon="🗺️")

st.title("🗺️ แพลตฟอร์มวิเคราะห์ข้อมูลผังเมือง (Urban OS Dashboard)")
st.markdown("**ระบบวิเคราะห์ข้อมูลเชิงพื้นที่และภูมิสารสนเทศเพื่อการพัฒนาเมือง จังหวัดอุตรดิตถ์**")

# 2. การเชื่อมต่อ Google Earth Engine (โค้ดชุดเดิมที่ทำงานสมบูรณ์แล้ว)
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
    st.error(f"การเชื่อมต่อระบบ Earth Engine ล้มเหลว: {e}")
    st.stop()

# สร้างแผนที่หลัก (กำหนดให้อยู่ตรงกลาง จ.อุตรดิตถ์)
Map = geemap.Map(center=[17.62, 100.09], zoom=10, ee_initialize=False)

# 3. จัดการแถบเมนูด้านข้าง (Sidebar) แบ่งเป็น 2 โหมดหลัก
with st.sidebar:
    st.header("⚙️ เมนูควบคุม Urban OS")
    
    # สวิตช์สลับโหมด
    mode = st.radio(
        "เลือกโหมดการทำงาน",
        ["🗺️ งานแผนทั่วไป (General Plan)", "🧠 วิเคราะห์ขั้นสูง (Advanced Analytics)"]
    )
    st.divider()

    # ==========================================
    # โหมดที่ 1: งานแผนทั่วไป
    # ==========================================
    if mode == "🗺️ งานแผนทั่วไป (General Plan)":
        st.subheader("🥞 การจัดการชั้นข้อมูล")
        basemap_choice = st.selectbox("เลือกแผนที่ฐาน (Basemap)", ["HYBRID", "SATELLITE", "ROADMAP", "TERRAIN"])
        Map.add_basemap(basemap_choice)
        
        show_dem = st.checkbox("✅ แบบจำลองความสูงภูมิประเทศ (DEM)", value=True)
        show_landcover = st.checkbox("✅ การใช้ประโยชน์ที่ดิน (ESA Land Cover)", value=False)
        opacity = st.slider("ความโปร่งแสงเลเยอร์", 0.0, 1.0, 0.7)
        
        # เพิ่มเลเยอร์ตามการเลือก
        if show_dem:
            dem = ee.Image('USGS/SRTMGL1_003')
            dem_vis = {'min': 0, 'max': 1000, 'palette': ['006633', 'E5FFCC', '662A00', 'D8D8D8', 'F5F5F5']}
            Map.addLayer(dem, dem_vis, 'Elevation (DEM)', opacity=opacity)
            
        if show_landcover:
            landcover = ee.ImageCollection("ESA/WorldCover/v200").first()
            Map.addLayer(landcover, {}, 'Land Use', opacity=opacity)
            
        st.divider()
        st.subheader("📊 รายงานสถิติพื้นที่ (Statistics)")
        st.info("คลิกเลือกพื้นที่บนแผนที่เพื่อดูสถิติ (ฟีเจอร์นี้จะพัฒนาในเฟสถัดไป)")
        # TODO: พื้นที่สำหรับใส่กราฟสถิติ เช่น พื้นที่สีเขียวกี่ %

    # ==========================================
    # โหมดที่ 2: วิเคราะห์ขั้นสูง
    # ==========================================
    elif mode == "🧠 วิเคราะห์ขั้นสูง (Advanced Analytics)":
        Map.add_basemap("SATELLITE") # โหมดนี้บังคับใช้ดาวเทียมเป็นค่าเริ่มต้น
        
        st.subheader("🏢 1. นำเข้าข้อมูลโมเดล/พื้นที่")
        uploaded_file = st.file_uploader("อัปโหลดไฟล์ (Zip Shapefile, GeoJSON, KML)", type=['zip', 'geojson', 'kml'])
        if uploaded_file is not None:
            st.success("อัปโหลดไฟล์สำเร็จ! (ระบบพร้อมประมวลผล)")
            
        st.subheader("🔍 2. ประมวลผลเชิงพื้นที่")
        analysis_type = st.selectbox("เลือกประเภทการวิเคราะห์", ["-- เลือก --", "วิเคราะห์พื้นที่เสี่ยงน้ำท่วม", "วิเคราะห์การขยายตัวของเมือง", "วิเคราะห์ความหนาแน่นป่าไม้"])
        
        st.subheader("📈 3. คาดการณ์อนาคต (Predictive)")
        predict_years = st.slider("จำลองภาพอนาคตล่วงหน้า (ปี)", 1, 50, 10)
        
        st.subheader("🌊 4. จำลองสิ่งก่อสร้าง & แก้ไขปัญหา")
        sim_tool = st.radio("เลือกโครงสร้างวิศวกรรม", ["วางแนวกั้นน้ำ / คันดิน", "สร้างฝายชะลอน้ำ", "ปรับระดับความสูงตลิ่ง"])
        if st.button("▶️ รันการจำลองสถานการณ์ (Run Simulation)"):
            st.warning("กำลังประมวลผลทางอุทกวิทยา... (ฟีเจอร์นี้จะพัฒนาในเฟสถัดไป)")

# 4. แสดงผลแผนที่หลัก
col1, col2 = st.columns([4, 1]) # แบ่ง Layout ถ้าเผื่ออนาคตจะเอากราฟมาไว้ข้างแผนที่

with col1:
    Map.to_streamlit(height=700)
    
with col2:
    if mode == "🗺️ งานแผนทั่วไป (General Plan)":
        st.markdown("### 📌 ข้อมูลสังเขป")
        st.write("เครื่องมือนี้ช่วยให้ผู้บริหารและประชาชนมองเห็นภาพรวมของเมืองได้อย่างรวดเร็ว")
    else:
        st.markdown("### 🧠 Console ประมวลผล")
        st.write("แสดงผลลัพธ์การคำนวณขั้นสูง และแจ้งเตือนผลกระทบจากการสร้างโครงสร้างพื้นฐาน")

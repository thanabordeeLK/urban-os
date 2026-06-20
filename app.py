import streamlit as st
import geemap.foliumap as geemap
import ee
import os

# 1. ตั้งค่าหน้าเว็บให้แสดงผลแบบเต็มจอ (ต้องเรียกใช้เป็นคำสั่งแรกสุดและครั้งเดียวเท่านั้น)
st.set_page_config(layout="wide", page_title="Uttaradit Urban OS")

st.title("🗺️ แพลตฟอร์มวิเคราะห์ข้อมูลผังเมือง (Urban OS Dashboard)")
st.write("ระบบวิเคราะห์ข้อมูลเชิงพื้นที่และภูมิสารสนเทศเพื่อการพัฒนาเมือง")

# 2. เชื่อมต่อระบบ Google Earth Engine ด้วย Token จาก Secrets
PROJECT_ID = 'project-25609b11-1067-4ef1-a1d'

try:
    if "EARTHENGINE_TOKEN" in st.secrets:
        secret_token = st.secrets["EARTHENGINE_TOKEN"]
        
        # สร้างโฟลเดอร์และไฟล์กุญแจไว้ในระบบคลาวด์เพื่อให้ Earth Engine เรียกใช้งานได้
        dot_ee_dir = os.path.expanduser('~/.config/earthengine')
        os.makedirs(dot_ee_dir, exist_ok=True)
        credentials_path = os.path.join(dot_ee_dir, 'credentials')
        
        with open(credentials_path, 'w') as f:
            f.write(secret_token)
            
        # เริ่มต้นระบบ Earth Engine ด้วย Project ID
        ee.Initialize(project=PROJECT_ID)
    else:
        st.error("ไม่พบกุญแจ EARTHENGINE_TOKEN ในระบบ Secrets ของ Streamlit")
        st.stop()
except Exception as e:
    st.error(f"การเชื่อมต่อระบบ Earth Engine ล้มเหลว: {e}")
    st.stop()

# 3. สร้างส่วนควบคุมด้านข้าง (Sidebar) สำหรับเลือกเลเยอร์ข้อมูล
with st.sidebar:
    st.header("⚙️ เมนูควบคุมชั้นข้อมูล")
    
    # ตัวเลือกแผนที่ฐาน
    basemap_choice = st.selectbox(
        "เลือกแผนที่ฐาน (Basemap)",
        ["HYBRID", "SATELLITE", "ROADMAP"]
    )
    
    # ตัวเลือกเลเยอร์ข้อมูลเชิงวิเคราะห์
    st.subheader("📊 ชั้นข้อมูลผังเมือง")
    show_dem = st.checkbox("แบบจำลองความสูงภูมิประเทศ (DEM)", value=True)
    show_landcover = st.checkbox("การใช้ประโยชน์ที่ดิน (ESA Land Cover)", value=False)
    
    # ตัวเลือกระดับความโปร่งแสง
    opacity = st.slider("ความโปร่งแสงของเลเยอร์ (Opacity)", 0.0, 1.0, 0.7)

# 4. ส่วนการแสดงผลแผนที่หลัก
# กำหนดจุดศูนย์กลางที่อุตรดิตถ์ [Lat, Lon]
Map = geemap.Map(center=[17.62, 100.09], zoom=10)
Map.add_basemap(basemap_choice)

# แสดงเลเยอร์ DEM หากติ๊กเลือก
if show_dem:
    dem = ee.Image('USGS/SRTMGL1_003')
    dem_vis = {
      'min': 0,
      'max': 1000,
      'palette': ['006633', 'E5FFCC', '662A00', 'D8D8D8', 'F5F5F5']
    }
    Map.addLayer(dem, dem_vis, 'Elevation (DEM)', opacity=opacity)

# แสดงเลเยอร์ Land Use หากติ๊กเลือก
if show_landcover:
    landcover = ee.ImageCollection("ESA/WorldCover/v200").first()
    Map.addLayer(landcover, {}, 'Land Use (การใช้ประโยชน์ที่ดิน)', opacity=opacity)

# เปิดเครื่องมือ Inspector ให้คลิกดูข้อมูลบนหน้าเว็บได้
Map.add_inspector()

# เรนเดอร์แผนที่ลงหน้าเว็บ Streamlit
Map.to_streamlit(height=650)

# Urban OS : Spatial AI Dashboard

Streamlit dashboard สำหรับงานผังเมืองที่เชื่อม Google Earth Engine และแยกโครงสร้างแบบ Modular แล้ว

## โครงสร้างโปรเจกต์

```text
Urban-OS-Project/
├── app.py
├── requirements.txt
├── README.md
├── legacy_app_original.py
│
├── config/
│   ├── __init__.py
│   ├── settings.py          # page config, CSS, project constants
│   ├── auth.py              # Earth Engine authentication
│   └── datasets.py          # dataset catalog, palettes, legends, class names
│
├── components/
│   ├── __init__.py
│   ├── sidebar.py           # sidebar UI and controls
│   ├── map_renderer.py      # map creation and Streamlit rendering
│   └── indicator_cards.py   # planning indicator cards
│
├── core_engine/
│   ├── __init__.py
│   ├── general_plan.py      # General Plan layer engine
│   └── ai_simulation.py     # NDBI urban growth simulation
│
└── services/
    ├── __init__.py
    ├── gee_service.py       # reusable Earth Engine helpers
    ├── roi_service.py       # province/district/ROI helpers
    └── statistics_service.py# ESA area statistics and planning score
```

## สิ่งที่แยกเพิ่มในรอบนี้

1. `config/datasets.py`  
   รวม Dataset ID, metadata, palette และ legend ไว้ที่เดียว ลดการ hardcode ใน engine

2. `services/roi_service.py`  
   ย้าย logic รายชื่อจังหวัด/อำเภอและ ROI ออกจาก sidebar

3. `services/gee_service.py`  
   รวม helper สำหรับ Earth Engine เช่น `safe_clip()` และ `reduce_frequency_histogram()`

4. `services/statistics_service.py`  
   คำนวณพื้นที่ ESA WorldCover เป็นไร่ และสร้าง quick planning indicators

5. `components/indicator_cards.py`  
   แสดง Green Area, Built-up Area, Water Area และ Planning Score จากผลคำนวณ

## วิธีรัน

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
earthengine authenticate
streamlit run app.py
```

ถ้าใช้ PowerShell แล้ว activate ไม่ได้:

```bash
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```

## วิธีใช้งาน Indicator Cards

1. เข้าโหมด `General Plan`
2. เปิดชั้นข้อมูล `ESA Land Cover`
3. กดปุ่ม `📈 คำนวณสถิติพื้นที่` ใน Sidebar
4. ค่า Green Area, Built-up Area, Water Area และ Planning Score จะแสดงใต้แผนที่

## หมายเหตุด้านวิชาการ

`Planning Score` ในเวอร์ชันนี้เป็น quick prototype จาก ESA WorldCover เท่านั้น ยังไม่ใช่ suitability model ฉบับสมบูรณ์ หากใช้ประกอบการตัดสินใจจริงควรเพิ่มชั้นข้อมูลอย่างน้อย:

- Flood risk
- Slope
- Road accessibility
- Public facilities
- Zoning constraints
- Parcel boundary
- Local field survey
- Infrastructure readiness

## Earth Engine Authentication

ในเครื่อง local ใช้:

```bash
earthengine authenticate
```

ถ้าขึ้น Streamlit Cloud สามารถใช้ `st.secrets["EARTHENGINE_TOKEN"]` ตาม logic ใน `config/auth.py`

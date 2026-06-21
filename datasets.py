"""Central dataset catalog and visualization settings for Urban OS.

เก็บ Dataset ID, palette, legend และ metadata ไว้ที่เดียว
เพื่อให้ core engine ไม่ต้อง hardcode ค่ากระจัดกระจาย
"""

DATASET_CATALOG = {
    "copernicus_dem": {
        "id": "COPERNICUS/DEM/GLO30",
        "name": "Copernicus DEM GLO-30",
        "resolution": "30 m",
        "temporal_coverage": "Global DEM",
        "planning_use": "วิเคราะห์ระดับความสูง ความลาดชัน และข้อจำกัดทางกายภาพ",
        "limitation": "ไม่ได้แทนข้อมูลสำรวจระดับวิศวกรรมภาคสนาม",
    },
    "dswx_s1": {
        "id": "OPERA/DSWX/L3_V1/S1",
        "name": "OPERA DSWx-S1",
        "resolution": "ประมาณ 30 m",
        "temporal_coverage": "ขึ้นกับรอบ Sentinel-1/OPERA",
        "planning_use": "ติดตามพื้นที่น้ำผิวดินและน้ำท่วมขังด้วย radar",
        "limitation": "ต้องตรวจสอบช่วงวันที่และความต่อเนื่องของข้อมูลในพื้นที่ศึกษา",
    },
    "global_flood_db": {
        "id": "GLOBAL_FLOOD_DB/MODIS_EVENTS/V1",
        "name": "Global Flood Database",
        "resolution": "MODIS scale",
        "temporal_coverage": "เหตุการณ์น้ำท่วมในอดีตจาก MODIS",
        "planning_use": "ดูประวัติพื้นที่เคยเกิดน้ำท่วม",
        "limitation": "ความละเอียดหยาบ ไม่เหมาะกับการตัดสินใจระดับแปลงที่ดิน",
    },
    "esa_worldcover": {
        "id": "ESA/WorldCover/v200",
        "name": "ESA WorldCover 2021 v200",
        "resolution": "10 m",
        "temporal_coverage": "2021",
        "planning_use": "จำแนกการใช้ที่ดิน/สิ่งปกคลุมดินเบื้องต้น",
        "limitation": "ต้อง cross-check กับข้อมูลท้องถิ่นและภาพถ่ายล่าสุด",
    },
    "dynamic_world": {
        "id": "GOOGLE/DYNAMICWORLD/V1",
        "name": "Google Dynamic World V1",
        "resolution": "10 m",
        "temporal_coverage": "Near real-time from Sentinel-2 era",
        "planning_use": "ติดตาม land cover แบบช่วงเวลาและดูแนวโน้มการเปลี่ยนแปลง",
        "limitation": "ผลจำแนกเป็น probability-based ต้องตรวจสอบพื้นที่จริง",
    },
    "chirts": {
        "id": "UCSB-CHG/CHIRTS/DAILY",
        "name": "CHIRTS Daily Temperature",
        "resolution": "ประมาณ 5 km",
        "temporal_coverage": "Daily temperature product",
        "planning_use": "ดูแนวโน้มอุณหภูมิสูงสุดและ heat stress ระดับภูมิภาค",
        "limitation": "ความละเอียดหยาบเกินไปสำหรับ microclimate รายชุมชน",
    },
    "ghsl_smod": {
        "id": "JRC/GHSL/P2023A/GHS_SMOD_V2-0/2030",
        "name": "GHSL Degree of Urbanization",
        "resolution": "GHSL grid",
        "temporal_coverage": "2030 scenario/product",
        "planning_use": "ดูระดับความเป็นเมืองและโครงสร้าง settlement",
        "limitation": "ควรใช้ประกอบข้อมูลผังเมืองและทะเบียนอาคารท้องถิ่น",
    },
    "ghsl_pop": {
        "id": "JRC/GHSL/P2023A/GHS_POP/2020",
        "name": "GHSL Population 2020",
        "resolution": "GHSL grid",
        "temporal_coverage": "2020",
        "planning_use": "ประมาณความหนาแน่นประชากรเชิงพื้นที่",
        "limitation": "เป็นค่าประมาณจากแบบจำลอง ไม่ใช่ทะเบียนราษฎร",
    },
    "landsat8_toa": {
        "id": "LANDSAT/LC08/C02/T1_TOA",
        "name": "Landsat 8 Collection 2 TOA",
        "resolution": "30 m",
        "temporal_coverage": "2013-present",
        "planning_use": "คำนวณ NDBI และติดตามการขยายตัวเมืองระยะยาว",
        "limitation": "NDBI อาจสับสนกับดินโล่ง/พื้นผิวสะท้อนสูง ต้อง cross-check",
    },
}

VIS_PARAMS = {
    "copernicus_dem": {
        "min": 0,
        "max": 1000,
        "palette": ["006633", "E5FFCC", "662A00", "D8D8D8", "F5F5F5"],
    },
    "dswx_s1": {
        "min": 0,
        "max": 5,
        "palette": ["ffffff", "0000ff", "0088ff", "f2f2f2", "dfdfdf", "da00ff"],
    },
    "global_flood_db": {
        "min": 0,
        "max": 10,
        "palette": ["c3effe", "1341e8", "051cb0", "001133"],
    },
    "dynamic_world": {
        "min": 0,
        "max": 8,
        "palette": [
            "419bdf", "397d49", "88b053", "7a87c6", "e49635",
            "dfc35a", "c4281b", "a59b8f", "b39fe1",
        ],
    },
    "chirts": {
        "min": 20,
        "max": 40,
        "palette": ["darkblue", "blue", "cyan", "green", "yellow", "orange", "red", "darkred"],
    },
    "ghsl_pop": {
        "min": 0.0,
        "max": 100.0,
        "palette": ["000004", "320A5A", "781B6C", "BB3654", "EC6824", "FBB41A", "FCFFA4"],
    },
}

LEGENDS = {
    "dswx_s1": {"[น้ำ] ผิวดิน": "0000ff", "[น้ำ] ท่วมขัง": "0088ff"},
    "esa_worldcover": {
        "[ESA] เมือง": "fa0000",
        "[ESA] เกษตร": "f096ff",
        "[ESA] ป่าไม้": "006400",
        "[ESA] แหล่งน้ำ": "0064c8",
    },
    "dynamic_world": {"[DW] น้ำ": "419bdf", "[DW] ต้นไม้": "397d49", "[DW] ตึก": "c4281b"},
    "ghsl_smod": {"[เมือง] แน่น": "ff0000", "[เมือง] กลาง": "ffa500"},
}

ESA_CLASS_NAMES = {
    "10": "ต้นไม้",
    "20": "ไม้พุ่ม",
    "30": "ทุ่งหญ้า",
    "40": "เกษตร",
    "50": "เมือง",
    "60": "พื้นที่โล่ง",
    "70": "หิมะ/น้ำแข็ง",
    "80": "แหล่งน้ำ",
    "90": "พื้นที่ชุ่มน้ำ",
    "95": "ป่าชายเลน",
    "100": "มอส/ไลเคน",
}

ESA_GREEN_CODES = {"10", "20", "30", "90", "95"}
ESA_BUILTUP_CODES = {"50"}
ESA_WATER_CODES = {"80"}

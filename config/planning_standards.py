"""
Planning Standards Presets for Urban OS

ฐานคิด:
- เกณฑ์และมาตรฐานผังเมืองรวมเมือง/ชุมชน
- มาตรฐานการวางและจัดทำผังเมืองรวม พ.ศ. 2566
- แนวคิด Potential Surface Analysis (PSA)
- Restrictive Area / Veto
- Density / Accessibility / Community Utilities and Facilities

หมายเหตุ:
ไฟล์นี้เป็น standard profile สำหรับช่วยตั้งค่าเริ่มต้นในระบบวิเคราะห์
ไม่ใช่ข้อกำหนดทางกฎหมายสำเร็จรูป ต้องใช้ร่วมกับข้อมูลพื้นที่และข้อกำหนดผังเมืองรวมจริง
"""

from __future__ import annotations


DPT_STANDARD_PROFILE_ID = "DPT_2566_PSA_SUITABILITY_V1"

DPT_STANDARD_PROFILE = {
    "profile_id": DPT_STANDARD_PROFILE_ID,
    "profile_name": "DPT Planning Standards 2566 / PSA Suitability",
    "profile_name_th": "มาตรฐานผังเมือง 2566 / วิเคราะห์ความเหมาะสมแบบ PSA",
    "description": (
        "ตั้งค่าเริ่มต้นสำหรับการวิเคราะห์ความเหมาะสมของพื้นที่ตามแนวคิด "
        "Potential Surface Analysis, Restrictive Area / Veto, Accessibility, "
        "Community Utilities and Facilities และ Density Reference"
    ),
    "source_documents": [
        "เกณฑ์และมาตรฐานผังเมืองรวมเมือง/ชุมชน",
        "มาตรฐานการวางและจัดทำผังเมืองรวม พ.ศ. 2566",
        "คู่มือเกณฑ์และมาตรฐานผังเมืองรวมเมือง/ชุมชน",
    ],
}


# ---------------------------------------------------------
# Suitability weights
# ---------------------------------------------------------
# แนวคิด:
# - Accessibility + Community Utilities and Facilities ให้ค่าน้ำหนักสูง
#   เพราะเอกสารมาตรฐานใช้เป็นปัจจัยสำคัญในการวิเคราะห์ศักยภาพที่อยู่อาศัย
# - Flood / Restrictive area เป็นความเสี่ยงหลัก
# - Land cover / slope / urban context เป็นปัจจัยรอง
# - Water proximity ใช้เป็นปัจจัยสนับสนุน แต่ต้องระวังพื้นที่ริมน้ำ/น้ำท่วม
DPT_SUITABILITY_WEIGHTS = {
    # Step 7: เพิ่ม Urban Heat Risk เป็น climate/livability penalty
    "slope": 0.10,
    "flood": 0.18,
    "landcover": 0.14,
    "urban": 0.08,
    "road": 0.18,
    "facility": 0.18,
    "water": 0.04,
    "heat": 0.10,
}


DPT_ROAD_ACCESSIBILITY_DEFAULTS = {
    # เส้นถนนจาก OSM/shapefile มักเป็น line จึง buffer เพื่อ rasterize ก่อนคำนวณระยะ
    "buffer_m": 20,
    # พื้นที่ไกลเกิน 5 กม. จากถนนถือว่าความเหมาะสมต่ำในระดับอำเภอ/ชุมชน
    "max_distance_m": 5000,
    "score_breaks_m": {
        5: 500,
        4: 1500,
        3: 3000,
        2: 5000,
        1: ">5000",
    },
}


DPT_PUBLIC_FACILITY_DEFAULTS = {
    # จุดบริการสาธารณะควร buffer เล็กน้อยเพื่อแปลงเป็น raster ได้เสถียร
    "buffer_m": 60,
    # ระยะวิเคราะห์ 10 กม. ใช้กับระดับอำเภอ/ชุมชน
    "max_distance_m": 10000,
    "score_breaks_m": {
        5: 1000,
        4: 3000,
        3: 5000,
        2: 10000,
        1: ">10000",
    },
    "recommended_facility_groups": [
        "บริการสาธารณสุข",
        "บริการการศึกษา",
        "ตลาด/ศูนย์พาณิชยกรรมชุมชน",
        "สถานีตำรวจ",
        "สถานีดับเพลิง",
        "สถานีขนส่ง/ระบบขนส่งสาธารณะ",
        "สาธารณูปโภคพื้นฐาน",
    ],
}


DPT_RESTRICTIVE_AREA_DEFAULTS = {
    "use_wdpa": True,
    # ค่ากลางสำหรับกันชนรอบพื้นที่อนุรักษ์ หากยังไม่มีข้อกำหนดเฉพาะพื้นที่
    "forest_buffer_m": 100,
    "restrictive_area_categories": [
        "พื้นที่อนุรักษ์ทรัพยากรป่าไม้และสิ่งแวดล้อม",
        "อุทยานแห่งชาติ",
        "เขตรักษาพันธุ์สัตว์ป่า / เขตห้ามล่า",
        "แหล่งน้ำธรรมชาติ / พื้นที่ชุ่มน้ำ",
        "พื้นที่เสี่ยงอุทกภัยรุนแรง",
        "พื้นที่ลาดชันสูง / ภูเขา",
        "พื้นที่ประวัติศาสตร์ ศิลปวัฒนธรรม",
        "เขตทหารหรือพื้นที่ความมั่นคง",
        "แนวกันชนแหล่งน้ำและพื้นที่อ่อนไหว",
    ],
}


DPT_UHI_DEFAULTS = {
    # หน้าแล้ง/ฤดูร้อนของไทย เหมาะสำหรับจับ thermal stress
    "start_month": 3,
    "start_day": 1,
    "end_month": 5,
    "end_day": 31,
    "composite_method": "median",
    "risk_mode": "relative",
    "cloud_cover_max": 60,
    "use_landsat8": True,
    "use_landsat9": True,
    "show_lst_layer": True,
    "show_heat_risk_layer": True,
    "show_hotspot_layer": True,
}

DPT_HEAT_PENALTY_DEFAULTS = {
    # ค่าเริ่มต้นสำหรับการนำ UHI เข้า Suitability เป็น Heat Penalty
    "enabled": False,
    "weight": 0.10,
    "start_month": 3,
    "start_day": 1,
    "end_month": 5,
    "end_day": 31,
    "composite_method": "median",
    "risk_mode": "relative",
    "cloud_cover_max": 60,
    "use_landsat8": True,
    "use_landsat9": True,
    "score_logic": {
        "Heat Risk Class 1": "Suitability Score 5",
        "Heat Risk Class 2": "Suitability Score 4",
        "Heat Risk Class 3": "Suitability Score 3",
        "Heat Risk Class 4": "Suitability Score 2",
        "Heat Risk Class 5": "Suitability Score 1",
    },
}


# ---------------------------------------------------------
# Density reference from DPT planning standards
# ---------------------------------------------------------
# ใช้เป็น reference สำหรับรายงาน/agent/การวิเคราะห์ zoning ในขั้นต่อไป
# หน่วย: คน/ไร่
DPT_COMMUNITY_DENSITY_REFERENCE = {
    "เมืองขนาดใหญ่มาก": {
        "ที่อยู่อาศัยหนาแน่นน้อย": "5 - 15",
        "ที่อยู่อาศัยหนาแน่นปานกลาง": "15 - 30",
        "ที่อยู่อาศัยหนาแน่นมาก": "30 - 40",
        "พาณิชยกรรมชุมชน": "24 - 40",
        "พาณิชยกรรมเมือง": "40 - 56",
        "พาณิชยกรรมภาค": "56 - 80",
        "อุตสาหกรรมเบา": "5 - 10",
        "อุตสาหกรรมหนัก": "3 - 5",
        "คลังสินค้า": "1.5 - 3",
        "เกษตรกรรม": "0 - 0.2",
    },
    "เมืองขนาดใหญ่": {
        "ที่อยู่อาศัยหนาแน่นน้อย": "5 - 10",
        "ที่อยู่อาศัยหนาแน่นปานกลาง": "10 - 20",
        "ที่อยู่อาศัยหนาแน่นมาก": "20 - 30",
        "พาณิชยกรรมชุมชน": "16 - 32",
        "พาณิชยกรรมเมือง": "32 - 48",
        "พาณิชยกรรมภาค": "48 - 56",
        "อุตสาหกรรมเบา": "5 - 10",
        "อุตสาหกรรมหนัก": "3 - 5",
        "คลังสินค้า": "1.5 - 3",
        "เกษตรกรรม": "0 - 0.2",
    },
    "เมืองขนาดกลาง": {
        "ที่อยู่อาศัยหนาแน่นน้อย": "5 - 10",
        "ที่อยู่อาศัยหนาแน่นปานกลาง": "10 - 20",
        "พาณิชยกรรมชุมชน": "16 - 32",
        "พาณิชยกรรมเมือง": "32 - 48",
        "อุตสาหกรรมเบา": "5 - 10",
        "คลังสินค้า": "1.5 - 3",
        "เกษตรกรรม": "0 - 0.2",
    },
    "เมืองขนาดเล็ก": {
        "ที่อยู่อาศัยหนาแน่นน้อย": "5 - 10",
        "ที่อยู่อาศัยหนาแน่นปานกลาง": "10 - 20",
        "พาณิชยกรรมชุมชน": "16 - 24",
        "พาณิชยกรรมเมือง": "24 - 40",
        "อุตสาหกรรมเบา": "5 - 10",
        "คลังสินค้า": "1.5 - 3",
        "เกษตรกรรม": "0 - 0.2",
    },
    "เมืองขนาดเล็กมาก": {
        "ที่อยู่อาศัยหนาแน่นน้อย": "5 - 10",
        "พาณิชยกรรมชุมชน": "16 - 24",
        "เกษตรกรรม": "0 - 0.2",
    },
}


PSA_RESIDENTIAL_POTENTIAL_FACTORS = [
    "ความลาดชันของพื้นที่",
    "ระยะห่างจากแหล่งน้ำผิวดินขนาดใหญ่",
    "พื้นที่เสี่ยงอุทกภัยซ้ำในรอบ 5-10 ปี",
    "ระยะห่างจากถนนหลัก",
    "การเข้าถึงถนนสายประธาน",
    "การเข้าถึงถนนสายหลัก",
    "การเข้าถึงถนนสายรองและสายท้องถิ่น",
    "การเข้าถึงบริการสาธารณสุข",
    "การเข้าถึงบริการการศึกษา",
    "การเข้าถึงสถานีดับเพลิง",
    "การเข้าถึงสถานีตำรวจ",
    "การเข้าถึงตลาด",
    "การเข้าถึงศาสนสถาน",
    "การเข้าถึงแหล่งนันทนาการ",
    "อยู่ในเขตให้บริการสาธารณูปโภค",
]


def get_standard_profile() -> dict:
    return DPT_STANDARD_PROFILE.copy()


def get_suitability_weight_preset() -> dict:
    return DPT_SUITABILITY_WEIGHTS.copy()


def get_road_defaults() -> dict:
    return DPT_ROAD_ACCESSIBILITY_DEFAULTS.copy()


def get_public_facility_defaults() -> dict:
    return DPT_PUBLIC_FACILITY_DEFAULTS.copy()


def get_restrictive_area_defaults() -> dict:
    return DPT_RESTRICTIVE_AREA_DEFAULTS.copy()


def get_uhi_defaults() -> dict:
    return DPT_UHI_DEFAULTS.copy()


def get_density_reference() -> dict:
    return DPT_COMMUNITY_DENSITY_REFERENCE.copy()


def get_psa_residential_factors() -> list[str]:
    return list(PSA_RESIDENTIAL_POTENTIAL_FACTORS)


def get_heat_penalty_defaults() -> dict:
    return DPT_HEAT_PENALTY_DEFAULTS.copy()



DPT_STANDARD_PROFILE_V2_NOTE = {
    "profile_id": "DPT_2566_PSA_SUITABILITY_V2_CITY_SIZE",
    "profile_name_th": "Planning Standards Preset V2 ตามขนาดเมือง",
    "description": (
        "ต่อยอดจาก V1 โดยแยกเกณฑ์ตามขนาดเมืองและเป้าหมายการวิเคราะห์ "
        "รวมถึงเตรียมรองรับอาคาร ครัวเรือน ประชากรทะเบียนราษฎร "
        "ความจุโครงสร้างพื้นฐาน และ zoning compliance"
    ),
}

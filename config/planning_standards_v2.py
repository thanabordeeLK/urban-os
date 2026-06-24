"""
Planning Standards Preset V2 for Urban OS

แนวคิด:
- แยกเกณฑ์ตามขนาดเมือง: เมืองขนาดเล็ก / กลาง / ใหญ่ / ใหญ่มาก
- แยกตามเป้าหมายวิเคราะห์: Urban Expansion, Residential, Commercial, Industrial, Green Infrastructure
- ใช้จำนวนอาคาร, จำนวนครัวเรือน และประชากร เพื่อประเมินระดับเมืองเบื้องต้น
- เป็นค่าเริ่มต้นเพื่อช่วยวิเคราะห์ ไม่ใช่ข้อกำหนดทางกฎหมายตายตัว
"""

from __future__ import annotations


CITY_SIZE_PROFILES = {
    "small": {
        "label_th": "เมืองขนาดเล็ก",
        "building_max": 10000,
        "population_max": 50000,
        "household_max": 20000,
        "road_max_distance_m": 5000,
        "facility_max_distance_m": 10000,
        "recommended_grid": "ศูนย์ชุมชนเดี่ยว/หลายหมู่บ้าน",
        "density_note": "เน้นความปลอดภัยจากภัยพิบัติ การเข้าถึงบริการพื้นฐาน และต้นทุนโครงสร้างพื้นฐานต่ำ",
    },
    "medium": {
        "label_th": "เมืองขนาดกลาง",
        "building_max": 50000,
        "population_max": 200000,
        "household_max": 80000,
        "road_max_distance_m": 4000,
        "facility_max_distance_m": 8000,
        "recommended_grid": "ศูนย์เมืองอำเภอ/เมืองรอง",
        "density_note": "เน้นการเข้าถึงบริการสาธารณะ คมนาคม และความพร้อมโครงสร้างพื้นฐาน",
    },
    "large": {
        "label_th": "เมืองขนาดใหญ่",
        "building_max": 150000,
        "population_max": 1000000,
        "household_max": 350000,
        "road_max_distance_m": 3000,
        "facility_max_distance_m": 5000,
        "recommended_grid": "เมืองศูนย์กลางจังหวัด/ภูมิภาค",
        "density_note": "เน้น capacity, service coverage, transit, zoning compliance และการลดผลกระทบสิ่งแวดล้อม",
    },
    "very_large": {
        "label_th": "เมืองขนาดใหญ่มาก",
        "building_max": None,
        "population_max": None,
        "household_max": None,
        "road_max_distance_m": 2000,
        "facility_max_distance_m": 3000,
        "recommended_grid": "มหานคร/เมืองศูนย์กลางขนาดใหญ่มาก",
        "density_note": "เน้น TOD, public transport, infrastructure capacity, climate resilience และ social equity",
    },
}


# weights ที่ใช้กับ Suitability engine ปัจจุบัน
# factor เพิ่มเติม เช่น infrastructure/legal/social จะถูกเก็บเป็น future_factors
# เพื่อใช้ต่อใน Step 8.7.2 / Step 9
PRESET_V2_WEIGHTS = {
    "urban_expansion": {
        "label_th": "พื้นที่ขยายเมือง",
        "small":      {"slope": 0.10, "flood": 0.20, "landcover": 0.15, "urban": 0.10, "road": 0.18, "facility": 0.15, "heat": 0.07, "water": 0.05},
        "medium":     {"slope": 0.09, "flood": 0.18, "landcover": 0.13, "urban": 0.10, "road": 0.18, "facility": 0.17, "heat": 0.10, "water": 0.05},
        "large":      {"slope": 0.07, "flood": 0.16, "landcover": 0.11, "urban": 0.09, "road": 0.17, "facility": 0.18, "heat": 0.14, "water": 0.08},
        "very_large": {"slope": 0.05, "flood": 0.15, "landcover": 0.10, "urban": 0.08, "road": 0.16, "facility": 0.18, "heat": 0.18, "water": 0.10},
    },
    "residential": {
        "label_th": "ที่อยู่อาศัย",
        "small":      {"slope": 0.10, "flood": 0.20, "landcover": 0.12, "urban": 0.08, "road": 0.15, "facility": 0.22, "heat": 0.08, "water": 0.05},
        "medium":     {"slope": 0.08, "flood": 0.18, "landcover": 0.10, "urban": 0.08, "road": 0.15, "facility": 0.23, "heat": 0.13, "water": 0.05},
        "large":      {"slope": 0.06, "flood": 0.16, "landcover": 0.09, "urban": 0.07, "road": 0.14, "facility": 0.24, "heat": 0.18, "water": 0.06},
        "very_large": {"slope": 0.04, "flood": 0.15, "landcover": 0.08, "urban": 0.06, "road": 0.14, "facility": 0.24, "heat": 0.22, "water": 0.07},
    },
    "commercial": {
        "label_th": "พาณิชยกรรม",
        "small":      {"slope": 0.06, "flood": 0.14, "landcover": 0.10, "urban": 0.16, "road": 0.25, "facility": 0.19, "heat": 0.05, "water": 0.05},
        "medium":     {"slope": 0.05, "flood": 0.12, "landcover": 0.08, "urban": 0.18, "road": 0.25, "facility": 0.20, "heat": 0.07, "water": 0.05},
        "large":      {"slope": 0.04, "flood": 0.11, "landcover": 0.07, "urban": 0.18, "road": 0.24, "facility": 0.20, "heat": 0.11, "water": 0.05},
        "very_large": {"slope": 0.03, "flood": 0.10, "landcover": 0.06, "urban": 0.18, "road": 0.24, "facility": 0.20, "heat": 0.14, "water": 0.05},
    },
    "industrial": {
        "label_th": "อุตสาหกรรม/โลจิสติกส์",
        "small":      {"slope": 0.12, "flood": 0.20, "landcover": 0.18, "urban": 0.05, "road": 0.25, "facility": 0.08, "heat": 0.05, "water": 0.07},
        "medium":     {"slope": 0.10, "flood": 0.18, "landcover": 0.17, "urban": 0.05, "road": 0.25, "facility": 0.08, "heat": 0.07, "water": 0.10},
        "large":      {"slope": 0.08, "flood": 0.17, "landcover": 0.16, "urban": 0.04, "road": 0.24, "facility": 0.08, "heat": 0.09, "water": 0.14},
        "very_large": {"slope": 0.07, "flood": 0.16, "landcover": 0.15, "urban": 0.04, "road": 0.23, "facility": 0.08, "heat": 0.12, "water": 0.15},
    },
    "green_infrastructure": {
        "label_th": "โครงสร้างพื้นฐานสีเขียว/ภูมิคุ้มกันภูมิอากาศ",
        "small":      {"slope": 0.08, "flood": 0.22, "landcover": 0.18, "urban": 0.06, "road": 0.08, "facility": 0.08, "heat": 0.20, "water": 0.10},
        "medium":     {"slope": 0.07, "flood": 0.22, "landcover": 0.17, "urban": 0.06, "road": 0.07, "facility": 0.08, "heat": 0.22, "water": 0.11},
        "large":      {"slope": 0.05, "flood": 0.21, "landcover": 0.16, "urban": 0.05, "road": 0.06, "facility": 0.07, "heat": 0.27, "water": 0.13},
        "very_large": {"slope": 0.04, "flood": 0.20, "landcover": 0.15, "urban": 0.05, "road": 0.05, "facility": 0.06, "heat": 0.32, "water": 0.13},
    },
}


FUTURE_FACTORS_V2 = {
    "infrastructure_capacity": "ขีดความสามารถประปา ไฟฟ้า น้ำเสีย ขยะ และระบายน้ำ",
    "legal_zoning_compliance": "การสอดคล้องกับผังสี FAR BCR OSR ความสูง และข้อห้าม",
    "service_coverage_by_type": "ระยะบริการแยกโรงพยาบาล โรงเรียน สวนสาธารณะ ตลาด ตำรวจ ดับเพลิง",
    "population_capacity": "ประชากรรองรับจาก density / household / dwelling unit",
    "socioeconomic_equity": "กลุ่มเปราะบาง รายได้ การเข้าถึงบริการ และผลกระทบชุมชน",
    "transport_capacity": "ความจุถนน ระบบขนส่งสาธารณะ และ TOD",
}


def estimate_population_from_buildings(building_count: int = 0, household_per_building: float = 1.15, persons_per_household: float = 2.7) -> int:
    building_count = max(int(building_count or 0), 0)
    household_per_building = max(float(household_per_building or 0), 0)
    persons_per_household = max(float(persons_per_household or 0), 0)
    return int(round(building_count * household_per_building * persons_per_household))


def estimate_households_from_buildings(building_count: int = 0, household_per_building: float = 1.15) -> int:
    return int(round(max(int(building_count or 0), 0) * max(float(household_per_building or 0), 0)))


def classify_city_size(building_count: int = 0, household_count: int = 0, population: int = 0) -> str:
    building_count = int(building_count or 0)
    household_count = int(household_count or 0)
    population = int(population or 0)

    # ใช้ค่าสูงสุดจาก 3 ตัวชี้วัดเพื่อกันการ underestimate
    if building_count > 150000 or household_count > 350000 or population > 1000000:
        return "very_large"
    if building_count > 50000 or household_count > 80000 or population > 200000:
        return "large"
    if building_count > 10000 or household_count > 20000 or population > 50000:
        return "medium"
    return "small"


def get_city_profile(city_size: str) -> dict:
    return CITY_SIZE_PROFILES.get(city_size, CITY_SIZE_PROFILES["small"])


def get_preset_v2_weights(objective: str, city_size: str) -> dict:
    obj = PRESET_V2_WEIGHTS.get(objective, PRESET_V2_WEIGHTS["urban_expansion"])
    return dict(obj.get(city_size, obj["small"]))


def get_objective_label(objective: str) -> str:
    return PRESET_V2_WEIGHTS.get(objective, {}).get("label_th", objective)


def get_city_size_label(city_size: str) -> str:
    return get_city_profile(city_size).get("label_th", city_size)


def normalize_weights(weights: dict) -> dict:
    total = sum(float(v or 0) for v in weights.values())
    if total <= 0:
        return dict(weights)
    return {k: round(float(v or 0) / total, 4) for k, v in weights.items()}

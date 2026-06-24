-- Urban OS PostGIS Schema Template
-- Generated at: 2026-06-24T14:09:38
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE SCHEMA IF NOT EXISTS "urban_os";

-- urban_layers: บัญชีรายการชั้นข้อมูลเมือง
CREATE TABLE IF NOT EXISTS "urban_os"."urban_layers" (
    "id" bigserial PRIMARY KEY,
    "layer_id" text,
    "layer_name" text,
    "category" text,
    "source_type" text,
    "table_name" text,
    "geom_col" text,
    "srid" integer,
    "enabled" boolean,
    "description" text,
    "created_at" timestamptz DEFAULT now(),
    "updated_at" timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS "urban_layers_layer_id_idx" ON "urban_os"."urban_layers" ("layer_id");
CREATE INDEX IF NOT EXISTS "urban_layers_category_idx" ON "urban_os"."urban_layers" ("category");
COMMENT ON TABLE "urban_os"."urban_layers" IS 'บัญชีรายการชั้นข้อมูลเมือง';
COMMENT ON COLUMN "urban_os"."urban_layers"."layer_id" IS 'รหัสชั้นข้อมูล';
COMMENT ON COLUMN "urban_os"."urban_layers"."layer_name" IS 'ชื่อชั้นข้อมูล';
COMMENT ON COLUMN "urban_os"."urban_layers"."category" IS 'หมวดข้อมูล';
COMMENT ON COLUMN "urban_os"."urban_layers"."source_type" IS 'ชนิดแหล่งข้อมูล';
COMMENT ON COLUMN "urban_os"."urban_layers"."table_name" IS 'ชื่อตาราง';
COMMENT ON COLUMN "urban_os"."urban_layers"."geom_col" IS 'ชื่อ geometry column';
COMMENT ON COLUMN "urban_os"."urban_layers"."srid" IS 'SRID';
COMMENT ON COLUMN "urban_os"."urban_layers"."enabled" IS 'เปิดใช้งาน';
COMMENT ON COLUMN "urban_os"."urban_layers"."description" IS 'คำอธิบาย';

-- roads: โครงข่ายถนนและคมนาคม
CREATE TABLE IF NOT EXISTS "urban_os"."roads" (
    "id" bigserial PRIMARY KEY,
    "road_id" text,
    "name" text,
    "road_class" text,
    "width_m" numeric,
    "surface" text,
    "lanes" integer,
    "source" text,
    "created_at" timestamptz DEFAULT now(),
    "updated_at" timestamptz DEFAULT now(),
    "geom" geometry(MULTILINESTRING, 4326)
);
CREATE INDEX IF NOT EXISTS "roads_geom_gix" ON "urban_os"."roads" USING GIST ("geom");
CREATE INDEX IF NOT EXISTS "roads_road_id_idx" ON "urban_os"."roads" ("road_id");
CREATE INDEX IF NOT EXISTS "roads_road_class_idx" ON "urban_os"."roads" ("road_class");
COMMENT ON TABLE "urban_os"."roads" IS 'โครงข่ายถนนและคมนาคม';
COMMENT ON COLUMN "urban_os"."roads"."road_id" IS 'รหัสถนน';
COMMENT ON COLUMN "urban_os"."roads"."name" IS 'ชื่อถนน';
COMMENT ON COLUMN "urban_os"."roads"."road_class" IS 'ระดับถนน';
COMMENT ON COLUMN "urban_os"."roads"."width_m" IS 'ความกว้างเมตร';
COMMENT ON COLUMN "urban_os"."roads"."surface" IS 'วัสดุผิวทาง';
COMMENT ON COLUMN "urban_os"."roads"."lanes" IS 'จำนวนช่องจราจร';
COMMENT ON COLUMN "urban_os"."roads"."source" IS 'แหล่งข้อมูล';

-- public_facilities: บริการสาธารณะและจุดบริการเมือง
CREATE TABLE IF NOT EXISTS "urban_os"."public_facilities" (
    "id" bigserial PRIMARY KEY,
    "facility_id" text,
    "name" text,
    "facility_type" text,
    "service_level" text,
    "owner_agency" text,
    "capacity" numeric,
    "source" text,
    "created_at" timestamptz DEFAULT now(),
    "updated_at" timestamptz DEFAULT now(),
    "geom" geometry(MULTIPOINT, 4326)
);
CREATE INDEX IF NOT EXISTS "public_facilities_geom_gix" ON "urban_os"."public_facilities" USING GIST ("geom");
CREATE INDEX IF NOT EXISTS "public_facilities_facility_id_idx" ON "urban_os"."public_facilities" ("facility_id");
CREATE INDEX IF NOT EXISTS "public_facilities_facility_type_idx" ON "urban_os"."public_facilities" ("facility_type");
COMMENT ON TABLE "urban_os"."public_facilities" IS 'บริการสาธารณะและจุดบริการเมือง';
COMMENT ON COLUMN "urban_os"."public_facilities"."facility_id" IS 'รหัสบริการ';
COMMENT ON COLUMN "urban_os"."public_facilities"."name" IS 'ชื่อสถานที่';
COMMENT ON COLUMN "urban_os"."public_facilities"."facility_type" IS 'ประเภทบริการ';
COMMENT ON COLUMN "urban_os"."public_facilities"."service_level" IS 'ระดับบริการ';
COMMENT ON COLUMN "urban_os"."public_facilities"."owner_agency" IS 'หน่วยงานเจ้าของ';
COMMENT ON COLUMN "urban_os"."public_facilities"."capacity" IS 'ศักยภาพบริการ';
COMMENT ON COLUMN "urban_os"."public_facilities"."source" IS 'แหล่งข้อมูล';

-- protected_areas: พื้นที่อนุรักษ์ พื้นที่กันออก และข้อจำกัดการพัฒนา
CREATE TABLE IF NOT EXISTS "urban_os"."protected_areas" (
    "id" bigserial PRIMARY KEY,
    "protected_id" text,
    "name" text,
    "category" text,
    "legal_status" text,
    "buffer_m" numeric,
    "restriction_level" text,
    "source" text,
    "created_at" timestamptz DEFAULT now(),
    "updated_at" timestamptz DEFAULT now(),
    "geom" geometry(MULTIPOLYGON, 4326)
);
CREATE INDEX IF NOT EXISTS "protected_areas_geom_gix" ON "urban_os"."protected_areas" USING GIST ("geom");
CREATE INDEX IF NOT EXISTS "protected_areas_protected_id_idx" ON "urban_os"."protected_areas" ("protected_id");
CREATE INDEX IF NOT EXISTS "protected_areas_category_idx" ON "urban_os"."protected_areas" ("category");
COMMENT ON TABLE "urban_os"."protected_areas" IS 'พื้นที่อนุรักษ์ พื้นที่กันออก และข้อจำกัดการพัฒนา';
COMMENT ON COLUMN "urban_os"."protected_areas"."protected_id" IS 'รหัสพื้นที่';
COMMENT ON COLUMN "urban_os"."protected_areas"."name" IS 'ชื่อพื้นที่';
COMMENT ON COLUMN "urban_os"."protected_areas"."category" IS 'ประเภทพื้นที่';
COMMENT ON COLUMN "urban_os"."protected_areas"."legal_status" IS 'สถานะกฎหมาย';
COMMENT ON COLUMN "urban_os"."protected_areas"."buffer_m" IS 'ระยะกันชนเมตร';
COMMENT ON COLUMN "urban_os"."protected_areas"."restriction_level" IS 'ระดับข้อจำกัด';
COMMENT ON COLUMN "urban_os"."protected_areas"."source" IS 'แหล่งข้อมูล';

-- zoning: ผังสีและการใช้ประโยชน์ที่ดิน
CREATE TABLE IF NOT EXISTS "urban_os"."zoning" (
    "id" bigserial PRIMARY KEY,
    "zone_id" text,
    "zone_code" text,
    "zone_name" text,
    "landuse_type" text,
    "far" numeric,
    "bcr" numeric,
    "osr" numeric,
    "note" text,
    "source" text,
    "created_at" timestamptz DEFAULT now(),
    "updated_at" timestamptz DEFAULT now(),
    "geom" geometry(MULTIPOLYGON, 4326)
);
CREATE INDEX IF NOT EXISTS "zoning_geom_gix" ON "urban_os"."zoning" USING GIST ("geom");
CREATE INDEX IF NOT EXISTS "zoning_zone_id_idx" ON "urban_os"."zoning" ("zone_id");
CREATE INDEX IF NOT EXISTS "zoning_zone_code_idx" ON "urban_os"."zoning" ("zone_code");
CREATE INDEX IF NOT EXISTS "zoning_landuse_type_idx" ON "urban_os"."zoning" ("landuse_type");
COMMENT ON TABLE "urban_os"."zoning" IS 'ผังสีและการใช้ประโยชน์ที่ดิน';
COMMENT ON COLUMN "urban_os"."zoning"."zone_id" IS 'รหัสพื้นที่ผัง';
COMMENT ON COLUMN "urban_os"."zoning"."zone_code" IS 'รหัสผังสี';
COMMENT ON COLUMN "urban_os"."zoning"."zone_name" IS 'ชื่อประเภทการใช้ประโยชน์ที่ดิน';
COMMENT ON COLUMN "urban_os"."zoning"."landuse_type" IS 'กลุ่มการใช้ประโยชน์';
COMMENT ON COLUMN "urban_os"."zoning"."far" IS 'FAR';
COMMENT ON COLUMN "urban_os"."zoning"."bcr" IS 'BCR';
COMMENT ON COLUMN "urban_os"."zoning"."osr" IS 'OSR';
COMMENT ON COLUMN "urban_os"."zoning"."note" IS 'หมายเหตุ';
COMMENT ON COLUMN "urban_os"."zoning"."source" IS 'แหล่งข้อมูล';

-- parcels: แปลงที่ดิน
CREATE TABLE IF NOT EXISTS "urban_os"."parcels" (
    "id" bigserial PRIMARY KEY,
    "parcel_id" text,
    "land_no" text,
    "parcel_no" text,
    "area_rai" numeric,
    "ownership_type" text,
    "source" text,
    "created_at" timestamptz DEFAULT now(),
    "updated_at" timestamptz DEFAULT now(),
    "geom" geometry(MULTIPOLYGON, 4326)
);
CREATE INDEX IF NOT EXISTS "parcels_geom_gix" ON "urban_os"."parcels" USING GIST ("geom");
CREATE INDEX IF NOT EXISTS "parcels_parcel_id_idx" ON "urban_os"."parcels" ("parcel_id");
COMMENT ON TABLE "urban_os"."parcels" IS 'แปลงที่ดิน';
COMMENT ON COLUMN "urban_os"."parcels"."parcel_id" IS 'รหัสแปลง';
COMMENT ON COLUMN "urban_os"."parcels"."land_no" IS 'เลขที่ดิน';
COMMENT ON COLUMN "urban_os"."parcels"."parcel_no" IS 'เลขแปลง';
COMMENT ON COLUMN "urban_os"."parcels"."area_rai" IS 'พื้นที่ไร่';
COMMENT ON COLUMN "urban_os"."parcels"."ownership_type" IS 'ประเภทกรรมสิทธิ์';
COMMENT ON COLUMN "urban_os"."parcels"."source" IS 'แหล่งข้อมูล';

-- buildings: อาคารและสิ่งปลูกสร้าง
CREATE TABLE IF NOT EXISTS "urban_os"."buildings" (
    "id" bigserial PRIMARY KEY,
    "building_id" text,
    "name" text,
    "use_type" text,
    "floors" integer,
    "height_m" numeric,
    "construction_year" integer,
    "source" text,
    "created_at" timestamptz DEFAULT now(),
    "updated_at" timestamptz DEFAULT now(),
    "geom" geometry(MULTIPOLYGON, 4326)
);
CREATE INDEX IF NOT EXISTS "buildings_geom_gix" ON "urban_os"."buildings" USING GIST ("geom");
CREATE INDEX IF NOT EXISTS "buildings_building_id_idx" ON "urban_os"."buildings" ("building_id");
COMMENT ON TABLE "urban_os"."buildings" IS 'อาคารและสิ่งปลูกสร้าง';
COMMENT ON COLUMN "urban_os"."buildings"."building_id" IS 'รหัสอาคาร';
COMMENT ON COLUMN "urban_os"."buildings"."name" IS 'ชื่ออาคาร';
COMMENT ON COLUMN "urban_os"."buildings"."use_type" IS 'ประเภทการใช้ประโยชน์';
COMMENT ON COLUMN "urban_os"."buildings"."floors" IS 'จำนวนชั้น';
COMMENT ON COLUMN "urban_os"."buildings"."height_m" IS 'ความสูงเมตร';
COMMENT ON COLUMN "urban_os"."buildings"."construction_year" IS 'ปีที่ก่อสร้าง';
COMMENT ON COLUMN "urban_os"."buildings"."source" IS 'แหล่งข้อมูล';

-- waterways: ลำน้ำ แหล่งน้ำ และโครงข่ายน้ำ
CREATE TABLE IF NOT EXISTS "urban_os"."waterways" (
    "id" bigserial PRIMARY KEY,
    "water_id" text,
    "name" text,
    "water_type" text,
    "seasonal" boolean,
    "buffer_m" numeric,
    "source" text,
    "created_at" timestamptz DEFAULT now(),
    "updated_at" timestamptz DEFAULT now(),
    "geom" geometry(MULTILINESTRING, 4326)
);
CREATE INDEX IF NOT EXISTS "waterways_geom_gix" ON "urban_os"."waterways" USING GIST ("geom");
CREATE INDEX IF NOT EXISTS "waterways_water_id_idx" ON "urban_os"."waterways" ("water_id");
COMMENT ON TABLE "urban_os"."waterways" IS 'ลำน้ำ แหล่งน้ำ และโครงข่ายน้ำ';
COMMENT ON COLUMN "urban_os"."waterways"."water_id" IS 'รหัสแหล่งน้ำ';
COMMENT ON COLUMN "urban_os"."waterways"."name" IS 'ชื่อแหล่งน้ำ';
COMMENT ON COLUMN "urban_os"."waterways"."water_type" IS 'ประเภทแหล่งน้ำ';
COMMENT ON COLUMN "urban_os"."waterways"."seasonal" IS 'ตามฤดูกาล';
COMMENT ON COLUMN "urban_os"."waterways"."buffer_m" IS 'ระยะกันชนเมตร';
COMMENT ON COLUMN "urban_os"."waterways"."source" IS 'แหล่งข้อมูล';

-- candidate_areas: พื้นที่ candidate จาก Urban OS
CREATE TABLE IF NOT EXISTS "urban_os"."candidate_areas" (
    "id" bigserial PRIMARY KEY,
    "candidate_id" text,
    "project_id" text,
    "suitability_class" integer,
    "area_rai" numeric,
    "heat_risk_class" integer,
    "feasibility_level" text,
    "priority_phase" text,
    "note" text,
    "created_at" timestamptz DEFAULT now(),
    "updated_at" timestamptz DEFAULT now(),
    "geom" geometry(MULTIPOLYGON, 4326)
);
CREATE INDEX IF NOT EXISTS "candidate_areas_geom_gix" ON "urban_os"."candidate_areas" USING GIST ("geom");
CREATE INDEX IF NOT EXISTS "candidate_areas_candidate_id_idx" ON "urban_os"."candidate_areas" ("candidate_id");
CREATE INDEX IF NOT EXISTS "candidate_areas_project_id_idx" ON "urban_os"."candidate_areas" ("project_id");
CREATE INDEX IF NOT EXISTS "candidate_areas_suitability_class_idx" ON "urban_os"."candidate_areas" ("suitability_class");
CREATE INDEX IF NOT EXISTS "candidate_areas_heat_risk_class_idx" ON "urban_os"."candidate_areas" ("heat_risk_class");
COMMENT ON TABLE "urban_os"."candidate_areas" IS 'พื้นที่ candidate จาก Urban OS';
COMMENT ON COLUMN "urban_os"."candidate_areas"."candidate_id" IS 'รหัส candidate';
COMMENT ON COLUMN "urban_os"."candidate_areas"."project_id" IS 'รหัสโครงการ';
COMMENT ON COLUMN "urban_os"."candidate_areas"."suitability_class" IS 'ระดับ suitability';
COMMENT ON COLUMN "urban_os"."candidate_areas"."area_rai" IS 'พื้นที่ไร่';
COMMENT ON COLUMN "urban_os"."candidate_areas"."heat_risk_class" IS 'ระดับ Heat Risk';
COMMENT ON COLUMN "urban_os"."candidate_areas"."feasibility_level" IS 'ระดับความเป็นไปได้';
COMMENT ON COLUMN "urban_os"."candidate_areas"."priority_phase" IS 'ระยะพัฒนา';
COMMENT ON COLUMN "urban_os"."candidate_areas"."note" IS 'หมายเหตุ';

-- uhi_hotspots: พื้นที่ Heat Hotspot / UHI
CREATE TABLE IF NOT EXISTS "urban_os"."uhi_hotspots" (
    "id" bigserial PRIMARY KEY,
    "hotspot_id" text,
    "analysis_date" date,
    "lst_mean_c" numeric,
    "lst_max_c" numeric,
    "heat_risk_class" integer,
    "area_rai" numeric,
    "recommendation" text,
    "created_at" timestamptz DEFAULT now(),
    "updated_at" timestamptz DEFAULT now(),
    "geom" geometry(MULTIPOLYGON, 4326)
);
CREATE INDEX IF NOT EXISTS "uhi_hotspots_geom_gix" ON "urban_os"."uhi_hotspots" USING GIST ("geom");
CREATE INDEX IF NOT EXISTS "uhi_hotspots_hotspot_id_idx" ON "urban_os"."uhi_hotspots" ("hotspot_id");
CREATE INDEX IF NOT EXISTS "uhi_hotspots_heat_risk_class_idx" ON "urban_os"."uhi_hotspots" ("heat_risk_class");
COMMENT ON TABLE "urban_os"."uhi_hotspots" IS 'พื้นที่ Heat Hotspot / UHI';
COMMENT ON COLUMN "urban_os"."uhi_hotspots"."hotspot_id" IS 'รหัส hotspot';
COMMENT ON COLUMN "urban_os"."uhi_hotspots"."analysis_date" IS 'วันที่วิเคราะห์';
COMMENT ON COLUMN "urban_os"."uhi_hotspots"."lst_mean_c" IS 'LST เฉลี่ย C';
COMMENT ON COLUMN "urban_os"."uhi_hotspots"."lst_max_c" IS 'LST สูงสุด C';
COMMENT ON COLUMN "urban_os"."uhi_hotspots"."heat_risk_class" IS 'ระดับความร้อน';
COMMENT ON COLUMN "urban_os"."uhi_hotspots"."area_rai" IS 'พื้นที่ไร่';
COMMENT ON COLUMN "urban_os"."uhi_hotspots"."recommendation" IS 'แนวทางลดความร้อน';

-- planning_projects: รายการโครงการวิเคราะห์หรือจัดทำผัง
CREATE TABLE IF NOT EXISTS "urban_os"."planning_projects" (
    "id" bigserial PRIMARY KEY,
    "project_id" text,
    "project_name" text,
    "province" text,
    "district" text,
    "planning_standard_profile" text,
    "created_by" text,
    "created_at_text" text,
    "description" text,
    "created_at" timestamptz DEFAULT now(),
    "updated_at" timestamptz DEFAULT now(),
    "geom" geometry(MULTIPOLYGON, 4326)
);
CREATE INDEX IF NOT EXISTS "planning_projects_geom_gix" ON "urban_os"."planning_projects" USING GIST ("geom");
CREATE INDEX IF NOT EXISTS "planning_projects_project_id_idx" ON "urban_os"."planning_projects" ("project_id");
COMMENT ON TABLE "urban_os"."planning_projects" IS 'รายการโครงการวิเคราะห์หรือจัดทำผัง';
COMMENT ON COLUMN "urban_os"."planning_projects"."project_id" IS 'รหัสโครงการ';
COMMENT ON COLUMN "urban_os"."planning_projects"."project_name" IS 'ชื่อโครงการ';
COMMENT ON COLUMN "urban_os"."planning_projects"."province" IS 'จังหวัด';
COMMENT ON COLUMN "urban_os"."planning_projects"."district" IS 'อำเภอ';
COMMENT ON COLUMN "urban_os"."planning_projects"."planning_standard_profile" IS 'profile มาตรฐาน';
COMMENT ON COLUMN "urban_os"."planning_projects"."created_by" IS 'ผู้สร้าง';
COMMENT ON COLUMN "urban_os"."planning_projects"."created_at_text" IS 'วันเวลาที่สร้าง';
COMMENT ON COLUMN "urban_os"."planning_projects"."description" IS 'คำอธิบาย';

-- Useful views for Urban OS
CREATE OR REPLACE VIEW "urban_os"."v_enabled_layers" AS SELECT layer_id, layer_name, category, source_type, table_name, geom_col, srid, enabled, description FROM "urban_os"."urban_layers" WHERE enabled IS TRUE;
CREATE OR REPLACE VIEW "urban_os"."v_development_candidates_high" AS SELECT * FROM "urban_os"."candidate_areas" WHERE suitability_class >= 4;
CREATE OR REPLACE VIEW "urban_os"."v_heat_hotspots_high" AS SELECT * FROM "urban_os"."uhi_hotspots" WHERE heat_risk_class >= 4;

-- Sample data for urban_layers registry
INSERT INTO "urban_os"."urban_layers" ("layer_id", "layer_name", "category", "source_type", "table_name", "geom_col", "srid", "enabled", "description") VALUES ('roads_default', 'roads', 'roads', 'postgis', 'urban_os.roads', 'geom', 4326, true, 'โครงข่ายถนนและคมนาคม') ON CONFLICT DO NOTHING;
INSERT INTO "urban_os"."urban_layers" ("layer_id", "layer_name", "category", "source_type", "table_name", "geom_col", "srid", "enabled", "description") VALUES ('public_facilities_default', 'public_facilities', 'public_facilities', 'postgis', 'urban_os.public_facilities', 'geom', 4326, true, 'บริการสาธารณะและจุดบริการเมือง') ON CONFLICT DO NOTHING;
INSERT INTO "urban_os"."urban_layers" ("layer_id", "layer_name", "category", "source_type", "table_name", "geom_col", "srid", "enabled", "description") VALUES ('protected_areas_default', 'protected_areas', 'protected_areas', 'postgis', 'urban_os.protected_areas', 'geom', 4326, true, 'พื้นที่อนุรักษ์ พื้นที่กันออก และข้อจำกัดการพัฒนา') ON CONFLICT DO NOTHING;
INSERT INTO "urban_os"."urban_layers" ("layer_id", "layer_name", "category", "source_type", "table_name", "geom_col", "srid", "enabled", "description") VALUES ('zoning_default', 'zoning', 'zoning', 'postgis', 'urban_os.zoning', 'geom', 4326, true, 'ผังสีและการใช้ประโยชน์ที่ดิน') ON CONFLICT DO NOTHING;
INSERT INTO "urban_os"."urban_layers" ("layer_id", "layer_name", "category", "source_type", "table_name", "geom_col", "srid", "enabled", "description") VALUES ('parcels_default', 'parcels', 'parcels', 'postgis', 'urban_os.parcels', 'geom', 4326, true, 'แปลงที่ดิน') ON CONFLICT DO NOTHING;
INSERT INTO "urban_os"."urban_layers" ("layer_id", "layer_name", "category", "source_type", "table_name", "geom_col", "srid", "enabled", "description") VALUES ('buildings_default', 'buildings', 'buildings', 'postgis', 'urban_os.buildings', 'geom', 4326, true, 'อาคารและสิ่งปลูกสร้าง') ON CONFLICT DO NOTHING;
INSERT INTO "urban_os"."urban_layers" ("layer_id", "layer_name", "category", "source_type", "table_name", "geom_col", "srid", "enabled", "description") VALUES ('waterways_default', 'waterways', 'waterways', 'postgis', 'urban_os.waterways', 'geom', 4326, true, 'ลำน้ำ แหล่งน้ำ และโครงข่ายน้ำ') ON CONFLICT DO NOTHING;
INSERT INTO "urban_os"."urban_layers" ("layer_id", "layer_name", "category", "source_type", "table_name", "geom_col", "srid", "enabled", "description") VALUES ('candidate_areas_default', 'candidate_areas', 'candidate_areas', 'postgis', 'urban_os.candidate_areas', 'geom', 4326, true, 'พื้นที่ candidate จาก Urban OS') ON CONFLICT DO NOTHING;
INSERT INTO "urban_os"."urban_layers" ("layer_id", "layer_name", "category", "source_type", "table_name", "geom_col", "srid", "enabled", "description") VALUES ('uhi_hotspots_default', 'uhi_hotspots', 'uhi_hotspots', 'postgis', 'urban_os.uhi_hotspots', 'geom', 4326, true, 'พื้นที่ Heat Hotspot / UHI') ON CONFLICT DO NOTHING;
INSERT INTO "urban_os"."urban_layers" ("layer_id", "layer_name", "category", "source_type", "table_name", "geom_col", "srid", "enabled", "description") VALUES ('planning_projects_default', 'planning_projects', 'planning_projects', 'postgis', 'urban_os.planning_projects', 'geom', 4326, true, 'รายการโครงการวิเคราะห์หรือจัดทำผัง') ON CONFLICT DO NOTHING;

-- Recommended read-only role
-- CREATE ROLE urban_reader LOGIN PASSWORD 'change-me';
-- GRANT USAGE ON SCHEMA "urban_os" TO urban_reader;
-- GRANT SELECT ON ALL TABLES IN SCHEMA "urban_os" TO urban_reader;
-- ALTER DEFAULT PRIVILEGES IN SCHEMA "urban_os" GRANT SELECT ON TABLES TO urban_reader;

"""GIS Agent: deterministic evidence from Google Earth Engine."""
from __future__ import annotations

import ee

from agents.base_agent import BaseAgent, AgentResult
from config.datasets import DATASET_CATALOG
from services.gee_service import safe_clip
from services.statistics_service import calculate_esa_landcover_statistics


def _dataset_id(key: str, fallback: str) -> str:
    return DATASET_CATALOG.get(key, {}).get("id", fallback)


def _geometry(roi):
    try:
        return roi.geometry()
    except Exception:
        return roi


def _safe_round(value, digits=2):
    try:
        if value is None:
            return None
        return round(float(value), digits)
    except Exception:
        return value


class GISAgent(BaseAgent):
    name = "GIS Agent"

    def run(self, task: str, context: dict) -> AgentResult:
        roi = context.get("roi")
        is_whole_country = bool(context.get("is_whole_country", False))

        if roi is None:
            return AgentResult(
                agent_name=self.name,
                summary="ไม่พบ ROI สำหรับวิเคราะห์",
                evidence={},
                confidence="low",
            )

        try:
            geom = _geometry(roi)
            scale = int(context.get("scale", 30))

            area_rai = ee.Number(geom.area(maxError=10)).divide(1600).getInfo()

            dem = (
                ee.ImageCollection(_dataset_id("copernicus_dem", "COPERNICUS/DEM/GLO30"))
                .select("DEM")
                .mosaic()
            )
            dem = safe_clip(dem, roi, is_whole_country)
            slope = ee.Terrain.slope(dem).rename("slope")

            dem_stats = dem.reduceRegion(
                reducer=ee.Reducer.mean().combine(ee.Reducer.minMax(), "", True),
                geometry=geom,
                scale=scale,
                maxPixels=1e13,
                bestEffort=True,
            ).getInfo()

            slope_stats = slope.reduceRegion(
                reducer=ee.Reducer.mean().combine(ee.Reducer.max(), "", True),
                geometry=geom,
                scale=scale,
                maxPixels=1e13,
                bestEffort=True,
            ).getInfo()

            landcover = (
                ee.ImageCollection(_dataset_id("esa_worldcover", "ESA/WorldCover/v200"))
                .first()
                .select("Map")
            )
            landcover = safe_clip(landcover, roi, is_whole_country)
            landcover_df, planning_summary = calculate_esa_landcover_statistics(
                landcover=landcover,
                roi=roi,
                scale=10,
            )

            top_landcover = landcover_df.head(8).to_dict(orient="records")

            evidence = {
                "พื้นที่ศึกษา": {
                    "จังหวัด": context.get("selected_province"),
                    "อำเภอ": context.get("selected_district"),
                    "ขนาดพื้นที่_ไร่": _safe_round(area_rai, 2),
                },
                "DEM": {
                    "mean_m": _safe_round(dem_stats.get("DEM_mean")),
                    "min_m": _safe_round(dem_stats.get("DEM_min")),
                    "max_m": _safe_round(dem_stats.get("DEM_max")),
                },
                "Slope": {
                    "mean_degree": _safe_round(slope_stats.get("slope_mean")),
                    "max_degree": _safe_round(slope_stats.get("slope_max")),
                },
                "ESA_WorldCover_summary": {
                    k: _safe_round(v, 2) for k, v in planning_summary.items()
                },
                "ESA_WorldCover_top_classes": top_landcover,
            }

            summary = (
                "GIS Agent ดึงหลักฐานจาก Google Earth Engine แล้ว: "
                "พื้นที่, DEM, slope และ ESA WorldCover พร้อมตัวชี้วัดพื้นที่สีเขียว/"
                "สิ่งปลูกสร้าง/แหล่งน้ำ เพื่อใช้เป็นฐานความจริงก่อนให้ LLM วิเคราะห์"
            )

            return AgentResult(
                agent_name=self.name,
                summary=summary,
                evidence=evidence,
                confidence="high",
            )

        except Exception as exc:
            return AgentResult(
                agent_name=self.name,
                summary=f"GIS Agent วิเคราะห์ไม่สำเร็จ: {exc}",
                evidence={},
                confidence="low",
            )

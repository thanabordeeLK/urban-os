"""Reusable Google Earth Engine helper functions."""
import ee


def safe_clip(image, roi, is_whole_country: bool):
    """Clip image เฉพาะกรณีไม่ใช่การวิเคราะห์ทั้งประเทศ"""
    return image if is_whole_country else image.clip(roi)


def reduce_frequency_histogram(image, roi, scale: int) -> dict:
    """Reduce raster class image to a frequency histogram inside ROI."""
    stats = (
        image.reduceRegion(
            reducer=ee.Reducer.frequencyHistogram(),
            geometry=roi.geometry(),
            scale=scale,
            maxPixels=1e13,
        )
        .getInfo()
    )
    return stats.get("Map", {})

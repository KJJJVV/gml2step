"""
CRS (Coordinate Reference System) detection from CityGML documents.

This module provides functions to automatically detect the source CRS from
CityGML srsName attributes and extract sample coordinates for CRS validation.
"""

from typing import Optional, Tuple
import xml.etree.ElementTree as ET

try:
    from ...coordinate_utils import detect_epsg_from_srs
except ImportError:

    def detect_epsg_from_srs(_: str):
        return None


def detect_source_crs(
    root: ET.Element,
) -> Tuple[Optional[str], Optional[float], Optional[float]]:
    """
    Scan XML for srsName attributes and detect EPSG code plus sample coordinates.

    This function searches the CityGML document for srsName attributes and
    extracts the first set of coordinates found for validation purposes.

    Args:
        root: Root element of parsed CityGML document

    Returns:
        Tuple of (epsg_code, sample_lat, sample_lon)
        - epsg_code: Detected EPSG code (e.g., "EPSG:6668") or None
        - sample_lat: First latitude/Y coordinate found or None
        - sample_lon: First longitude/X coordinate found or None

    Example:
        >>> tree = ET.parse("city.gml")
        >>> root = tree.getroot()
        >>> epsg_code, lat, lon = detect_source_crs(root)
        >>> epsg_code
        'EPSG:6668'
        >>> lat, lon
        (35.6811, 139.7670)

    Notes:
        - Scans up to 10,000 elements to find srsName
        - Automatically corrects lat/lon order if coordinates are outside Japan
        - Uses geospatial.jp coordinate_utils for EPSG detection
    """
    epsg_code = None
    sample_lat = None
    sample_lon = None

    # Breadth-first search for srsName and coordinates
    queue = [root]
    seen = 0
    while queue and seen < 10000:
        e = queue.pop(0)
        seen += 1

        # Check for srsName attribute
        srs = e.get("srsName")
        if srs and not epsg_code:
            epsg_code = detect_epsg_from_srs(srs)

        # Try to get sample coordinates from coordinate-bearing elements
        # Priority: posList > pos > lowerCorner > upperCorner
        if sample_lat is None:
            tag = e.tag
            is_coord_tag = (
                tag.endswith("posList")
                or tag.endswith("}pos")
                or tag == "pos"
                or tag.endswith("lowerCorner")
                or tag.endswith("upperCorner")
            )
            if is_coord_tag:
                txt = (e.text or "").strip()
                if txt:
                    parts = txt.split()
                    try:
                        if len(parts) >= 2:
                            lat_candidate = float(parts[0])
                            lon_candidate = float(parts[1])

                            # Sanity check for Japan area (lat: 20-50, lon: 120-155)
                            if (
                                20 <= lat_candidate <= 50
                                and 120 <= lon_candidate <= 155
                            ):
                                sample_lat = lat_candidate
                                sample_lon = lon_candidate
                            elif (
                                20 <= lon_candidate <= 50
                                and 120 <= lat_candidate <= 155
                            ):
                                # lon/lat order - swap
                                sample_lat = lon_candidate
                                sample_lon = lat_candidate
                            else:
                                # Not geographic coordinates (projected CRS) - still useful
                                sample_lat = lat_candidate
                                sample_lon = lon_candidate
                    except ValueError:
                        pass

        # Stop if both CRS and coordinates found
        if epsg_code and sample_lat is not None:
            break

        queue.extend(list(e))

    return epsg_code, sample_lat, sample_lon

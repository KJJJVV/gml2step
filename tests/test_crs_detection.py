"""Tests for citygml.transforms.crs_detection — CRS detection from CityGML."""

import xml.etree.ElementTree as ET

import pytest

from gml2step.citygml.transforms.crs_detection import detect_source_crs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _gml_with_srs(srs_name: str, poslist_text: str = "") -> ET.Element:
    """Create minimal GML root with srsName and optional posList."""
    poslist_part = ""
    if poslist_text:
        poslist_part = f'<gml:posList xmlns:gml="http://www.opengis.net/gml">{poslist_text}</gml:posList>'

    xml = f"""\
<CityModel xmlns="http://www.opengis.net/citygml/2.0"
           xmlns:gml="http://www.opengis.net/gml">
  <gml:boundedBy>
    <gml:Envelope srsName="{srs_name}">
      <gml:lowerCorner>35.0 139.0</gml:lowerCorner>
      <gml:upperCorner>36.0 140.0</gml:upperCorner>
    </gml:Envelope>
  </gml:boundedBy>
  <cityObjectMember>
    {poslist_part}
  </cityObjectMember>
</CityModel>"""
    return ET.fromstring(xml)


def _gml_without_srs(poslist_text: str = "") -> ET.Element:
    """Create minimal GML root without srsName."""
    poslist_part = ""
    if poslist_text:
        poslist_part = f'<gml:posList xmlns:gml="http://www.opengis.net/gml">{poslist_text}</gml:posList>'

    xml = f"""\
<CityModel xmlns="http://www.opengis.net/citygml/2.0"
           xmlns:gml="http://www.opengis.net/gml">
  <cityObjectMember>
    {poslist_part}
  </cityObjectMember>
</CityModel>"""
    return ET.fromstring(xml)


# ===================================================================
# detect_source_crs
# ===================================================================


class TestDetectSourceCrs:
    """Tests for detect_source_crs()."""

    def test_detects_epsg_from_srsname(self):
        """Detects EPSG code from srsName attribute."""
        root = _gml_with_srs(
            "http://www.opengis.net/def/crs/EPSG/0/6668", poslist_text="35.6 139.7 0.0"
        )
        epsg, lat, lon = detect_source_crs(root)
        assert epsg is not None
        assert "6668" in epsg

    def test_extracts_sample_coordinates(self):
        """Extracts lat/lon from first posList."""
        root = _gml_with_srs(
            "http://www.opengis.net/def/crs/EPSG/0/6668", poslist_text="35.6 139.7 0.0"
        )
        _, lat, lon = detect_source_crs(root)
        assert lat is not None
        assert lon is not None
        # Values should be in Japan area after sanity check
        assert 20 <= lat <= 50
        assert 120 <= lon <= 155

    def test_swaps_lon_lat_if_outside_japan(self):
        """If initial parse gives values outside Japan, swap lat/lon."""
        # 139.7 is longitude (outside lat range 20-50), so should swap
        root = _gml_with_srs(
            "http://www.opengis.net/def/crs/EPSG/0/6668", poslist_text="139.7 35.6 0.0"
        )
        _, lat, lon = detect_source_crs(root)
        assert lat is not None
        assert lon is not None
        # After swap: lat=35.6, lon=139.7 (valid Japan coordinates)
        assert 20 <= lat <= 50
        assert 120 <= lon <= 155

    def test_no_srsname_returns_none_epsg(self):
        """Returns None for EPSG when no srsName found."""
        root = _gml_without_srs(poslist_text="35.6 139.7 0.0")
        epsg, lat, lon = detect_source_crs(root)
        assert epsg is None
        # Coordinates should still be extracted
        assert lat is not None

    def test_empty_document(self):
        """Empty document returns all None."""
        root = ET.fromstring('<CityModel xmlns="http://www.opengis.net/citygml/2.0"/>')
        epsg, lat, lon = detect_source_crs(root)
        assert epsg is None
        assert lat is None
        assert lon is None

    def test_no_poslist_returns_none_coords(self):
        """Returns None coords when no posList elements."""
        root = _gml_with_srs("http://www.opengis.net/def/crs/EPSG/0/6668")
        epsg, lat, lon = detect_source_crs(root)
        # EPSG should still be detected from srsName
        assert epsg is not None
        assert lat is None
        assert lon is None

    def test_empty_poslist_ignored(self):
        """Empty posList text is ignored gracefully."""
        root = _gml_with_srs(
            "http://www.opengis.net/def/crs/EPSG/0/6668", poslist_text=""
        )
        _, lat, lon = detect_source_crs(root)
        assert lat is None

    def test_invalid_poslist_text_ignored(self):
        """Non-numeric posList text is ignored."""
        root = _gml_with_srs(
            "http://www.opengis.net/def/crs/EPSG/0/6668", poslist_text="invalid data"
        )
        _, lat, lon = detect_source_crs(root)
        assert lat is None

    def test_single_coordinate_ignored(self):
        """posList with only one number doesn't extract coords."""
        root = _gml_with_srs(
            "http://www.opengis.net/def/crs/EPSG/0/6668", poslist_text="35.6"
        )
        _, lat, lon = detect_source_crs(root)
        assert lat is None

    def test_stops_early_when_both_found(self):
        """BFS stops when both EPSG and coordinates are found (no crash)."""
        # Build a large-ish document
        poslist_items = "\n".join(
            f'<gml:posList xmlns:gml="http://www.opengis.net/gml">35.{i} 139.{i} 0.0</gml:posList>'
            for i in range(100)
        )
        xml = f"""\
<CityModel xmlns="http://www.opengis.net/citygml/2.0"
           xmlns:gml="http://www.opengis.net/gml">
  <gml:boundedBy>
    <gml:Envelope srsName="http://www.opengis.net/def/crs/EPSG/0/6668">
      <gml:lowerCorner>35.0 139.0</gml:lowerCorner>
      <gml:upperCorner>36.0 140.0</gml:upperCorner>
    </gml:Envelope>
  </gml:boundedBy>
  <cityObjectMember>
    {poslist_items}
  </cityObjectMember>
</CityModel>"""
        root = ET.fromstring(xml)
        epsg, lat, lon = detect_source_crs(root)
        assert epsg is not None
        assert lat is not None

    def test_with_sample_gml(self, sample_gml_root):
        """Uses shared fixture to detect CRS (no srsName in sample)."""
        epsg, lat, lon = detect_source_crs(sample_gml_root)
        # Sample GML has no srsName attribute
        assert epsg is None
        # But it does have posList coordinates
        assert lat is not None
        assert lon is not None

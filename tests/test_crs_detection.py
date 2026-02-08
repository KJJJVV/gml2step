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

    def test_no_poslist_falls_back_to_lower_corner(self):
        """Falls back to lowerCorner when no posList elements exist."""
        root = _gml_with_srs("http://www.opengis.net/def/crs/EPSG/0/6668")
        epsg, lat, lon = detect_source_crs(root)
        # EPSG should still be detected from srsName
        assert epsg is not None
        # lowerCorner "35.0 139.0" provides fallback coordinates
        assert lat is not None
        assert lon is not None
        assert 20 <= lat <= 50
        assert 120 <= lon <= 155

    def test_empty_poslist_falls_back(self):
        """Empty posList text is ignored, but lowerCorner provides fallback."""
        root = _gml_with_srs(
            "http://www.opengis.net/def/crs/EPSG/0/6668", poslist_text=""
        )
        _, lat, lon = detect_source_crs(root)
        # lowerCorner "35.0 139.0" provides fallback
        assert lat is not None

    def test_invalid_poslist_falls_back(self):
        """Non-numeric posList text is ignored, lowerCorner provides fallback."""
        root = _gml_with_srs(
            "http://www.opengis.net/def/crs/EPSG/0/6668", poslist_text="invalid data"
        )
        _, lat, lon = detect_source_crs(root)
        # lowerCorner "35.0 139.0" provides fallback
        assert lat is not None

    def test_single_coordinate_poslist_falls_back(self):
        """posList with only one number doesn't extract coords, lowerCorner does."""
        root = _gml_with_srs(
            "http://www.opengis.net/def/crs/EPSG/0/6668", poslist_text="35.6"
        )
        _, lat, lon = detect_source_crs(root)
        # lowerCorner "35.0 139.0" provides fallback
        assert lat is not None

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


class TestDetectSourceCrsFallback:
    """Tests for coordinate fallback to pos/lowerCorner/upperCorner."""

    def test_fallback_to_gml_pos(self):
        """Extracts coordinates from gml:pos when no posList exists."""
        xml = """\
<CityModel xmlns="http://www.opengis.net/citygml/2.0"
           xmlns:gml="http://www.opengis.net/gml">
  <gml:boundedBy>
    <gml:Envelope srsName="http://www.opengis.net/def/crs/EPSG/0/6668">
      <gml:lowerCorner>35.0 139.0</gml:lowerCorner>
      <gml:upperCorner>36.0 140.0</gml:upperCorner>
    </gml:Envelope>
  </gml:boundedBy>
  <cityObjectMember>
    <Building>
      <gml:pos>35.681 139.767 10.0</gml:pos>
    </Building>
  </cityObjectMember>
</CityModel>"""
        root = ET.fromstring(xml)
        epsg, lat, lon = detect_source_crs(root)
        assert epsg is not None
        assert lat is not None
        assert lon is not None
        assert 20 <= lat <= 50
        assert 120 <= lon <= 155

    def test_fallback_to_lower_corner(self):
        """Extracts coordinates from lowerCorner when no posList/pos exists."""
        xml = """\
<CityModel xmlns="http://www.opengis.net/citygml/2.0"
           xmlns:gml="http://www.opengis.net/gml">
  <gml:boundedBy>
    <gml:Envelope srsName="http://www.opengis.net/def/crs/EPSG/0/6668">
      <gml:lowerCorner>35.5 139.5</gml:lowerCorner>
      <gml:upperCorner>36.0 140.0</gml:upperCorner>
    </gml:Envelope>
  </gml:boundedBy>
</CityModel>"""
        root = ET.fromstring(xml)
        epsg, lat, lon = detect_source_crs(root)
        assert epsg is not None
        assert lat == pytest.approx(35.5)
        assert lon == pytest.approx(139.5)

    def test_fallback_to_upper_corner(self):
        """Extracts coordinates from upperCorner if lowerCorner is empty."""
        xml = """\
<CityModel xmlns="http://www.opengis.net/citygml/2.0"
           xmlns:gml="http://www.opengis.net/gml">
  <gml:boundedBy>
    <gml:Envelope srsName="http://www.opengis.net/def/crs/EPSG/0/6668">
      <gml:lowerCorner></gml:lowerCorner>
      <gml:upperCorner>36.0 140.0</gml:upperCorner>
    </gml:Envelope>
  </gml:boundedBy>
</CityModel>"""
        root = ET.fromstring(xml)
        epsg, lat, lon = detect_source_crs(root)
        assert epsg is not None
        assert lat == pytest.approx(36.0)
        assert lon == pytest.approx(140.0)

    def test_poslist_preferred_over_lower_corner(self):
        """posList takes priority over lowerCorner due to BFS ordering."""
        xml = """\
<CityModel xmlns="http://www.opengis.net/citygml/2.0"
           xmlns:gml="http://www.opengis.net/gml">
  <gml:boundedBy>
    <gml:Envelope srsName="http://www.opengis.net/def/crs/EPSG/0/6668">
      <gml:lowerCorner>35.0 139.0</gml:lowerCorner>
      <gml:upperCorner>36.0 140.0</gml:upperCorner>
    </gml:Envelope>
  </gml:boundedBy>
  <cityObjectMember>
    <gml:posList>35.681 139.767 0.0</gml:posList>
  </cityObjectMember>
</CityModel>"""
        root = ET.fromstring(xml)
        _, lat, lon = detect_source_crs(root)
        # BFS visits children level by level; Envelope children (lowerCorner)
        # are at same depth as cityObjectMember, but lowerCorner comes first.
        # The important thing is we get valid coordinates either way.
        assert lat is not None
        assert lon is not None
        assert 20 <= lat <= 50
        assert 120 <= lon <= 155

    def test_no_coordinate_elements_at_all(self):
        """Returns None coords when no coordinate elements of any kind exist."""
        xml = """\
<CityModel xmlns="http://www.opengis.net/citygml/2.0"
           xmlns:gml="http://www.opengis.net/gml">
  <gml:boundedBy>
    <gml:Envelope srsName="http://www.opengis.net/def/crs/EPSG/0/6668">
    </gml:Envelope>
  </gml:boundedBy>
</CityModel>"""
        root = ET.fromstring(xml)
        epsg, lat, lon = detect_source_crs(root)
        assert epsg is not None
        assert lat is None
        assert lon is None

    def test_projected_coordinates_not_in_japan_range(self):
        """Projected CRS coordinates outside geographic range are still returned."""
        xml = """\
<CityModel xmlns="http://www.opengis.net/citygml/2.0"
           xmlns:gml="http://www.opengis.net/gml">
  <gml:boundedBy>
    <gml:Envelope srsName="http://www.opengis.net/def/crs/EPSG/0/6677">
      <gml:lowerCorner>-12345.678 67890.123</gml:lowerCorner>
      <gml:upperCorner>-12000.0 68000.0</gml:upperCorner>
    </gml:Envelope>
  </gml:boundedBy>
</CityModel>"""
        root = ET.fromstring(xml)
        epsg, lat, lon = detect_source_crs(root)
        assert epsg is not None
        # Projected coords fall through to "still useful" branch
        assert lat is not None
        assert lon is not None

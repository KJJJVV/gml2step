"""Tests for citygml.parsers.polygons — polygon extraction utilities."""

import xml.etree.ElementTree as ET

import pytest

from gml2step.citygml.parsers.polygons import (
    count_polygons_in_element,
    estimate_building_height,
    find_building_parts,
    find_footprint_polygons,
)

from conftest import NS


# ---------------------------------------------------------------------------
# Helpers — build minimal CityGML building trees
# ---------------------------------------------------------------------------


def _building(gml_id: str = "B1", children_xml: str = "") -> ET.Element:
    """Create a bldg:Building element with optional inner XML."""
    xml = f"""\
<bldg:Building xmlns:bldg="http://www.opengis.net/citygml/building/2.0"
               xmlns:gml="http://www.opengis.net/gml"
               xmlns:uro="https://www.geospatial.jp/iur/uro/3.1"
               gml:id="{gml_id}">
  {children_xml}
</bldg:Building>"""
    return ET.fromstring(xml)


def _polygon(gml_id: str = "P1", coords: str = "0 0 0 1 0 0 1 1 0 0 1 0 0 0 0") -> str:
    """Return a gml:Polygon XML fragment."""
    return f"""\
<gml:Polygon xmlns:gml="http://www.opengis.net/gml" gml:id="{gml_id}">
  <gml:exterior>
    <gml:LinearRing>
      <gml:posList>{coords}</gml:posList>
    </gml:LinearRing>
  </gml:exterior>
</gml:Polygon>"""


def _footprint_xml(poly_xml: str) -> str:
    """Wrap polygon in lod0FootPrint > MultiSurface > surfaceMember."""
    return f"""\
<bldg:lod0FootPrint xmlns:bldg="http://www.opengis.net/citygml/building/2.0"
                    xmlns:gml="http://www.opengis.net/gml">
  <gml:MultiSurface>
    <gml:surfaceMember>
      {poly_xml}
    </gml:surfaceMember>
  </gml:MultiSurface>
</bldg:lod0FootPrint>"""


def _roofedge_xml(poly_xml: str) -> str:
    """Wrap polygon in lod0RoofEdge > MultiSurface > surfaceMember."""
    return f"""\
<bldg:lod0RoofEdge xmlns:bldg="http://www.opengis.net/citygml/building/2.0"
                   xmlns:gml="http://www.opengis.net/gml">
  <gml:MultiSurface>
    <gml:surfaceMember>
      {poly_xml}
    </gml:surfaceMember>
  </gml:MultiSurface>
</bldg:lod0RoofEdge>"""


def _groundsurface_xml(poly_xml: str) -> str:
    """Wrap polygon in boundedBy > GroundSurface."""
    return f"""\
<bldg:boundedBy xmlns:bldg="http://www.opengis.net/citygml/building/2.0"
                xmlns:gml="http://www.opengis.net/gml">
  <bldg:GroundSurface>
    <bldg:lod2MultiSurface>
      <gml:MultiSurface>
        <gml:surfaceMember>
          {poly_xml}
        </gml:surfaceMember>
      </gml:MultiSurface>
    </bldg:lod2MultiSurface>
  </bldg:GroundSurface>
</bldg:boundedBy>"""


# ===================================================================
# find_footprint_polygons
# ===================================================================


class TestFindFootprintPolygons:
    """Tests for find_footprint_polygons()."""

    def test_priority1_lod0footprint(self):
        """lod0FootPrint polygons are returned first."""
        bldg = _building(children_xml=_footprint_xml(_polygon("FP1")))
        polys = find_footprint_polygons(bldg)
        assert len(polys) == 1
        assert polys[0].get("{http://www.opengis.net/gml}id") == "FP1"

    def test_priority2_lod0roofedge(self):
        """lod0RoofEdge is used when no lod0FootPrint exists."""
        bldg = _building(children_xml=_roofedge_xml(_polygon("RE1")))
        polys = find_footprint_polygons(bldg)
        assert len(polys) == 1
        assert polys[0].get("{http://www.opengis.net/gml}id") == "RE1"

    def test_priority3_groundsurface(self):
        """GroundSurface fallback when neither footprint nor roofedge."""
        bldg = _building(children_xml=_groundsurface_xml(_polygon("GS1")))
        polys = find_footprint_polygons(bldg)
        assert len(polys) == 1
        assert polys[0].get("{http://www.opengis.net/gml}id") == "GS1"

    def test_footprint_takes_precedence_over_roofedge(self):
        """lod0FootPrint should win even if lod0RoofEdge is also present."""
        inner = _footprint_xml(_polygon("FP1")) + _roofedge_xml(_polygon("RE1"))
        bldg = _building(children_xml=inner)
        polys = find_footprint_polygons(bldg)
        assert len(polys) == 1
        assert polys[0].get("{http://www.opengis.net/gml}id") == "FP1"

    def test_no_polygons_returns_empty_list(self):
        """Building with no geometry returns empty list."""
        bldg = _building()
        assert find_footprint_polygons(bldg) == []

    def test_multiple_footprint_polygons(self):
        """Multiple polygons in lod0FootPrint are all returned."""
        two_polys = _polygon("P1") + _polygon("P2")
        # Wrap both in a single footprint
        inner = f"""\
<bldg:lod0FootPrint xmlns:bldg="http://www.opengis.net/citygml/building/2.0"
                    xmlns:gml="http://www.opengis.net/gml">
  <gml:MultiSurface>
    <gml:surfaceMember>{_polygon("P1")}</gml:surfaceMember>
    <gml:surfaceMember>{_polygon("P2")}</gml:surfaceMember>
  </gml:MultiSurface>
</bldg:lod0FootPrint>"""
        bldg = _building(children_xml=inner)
        polys = find_footprint_polygons(bldg)
        assert len(polys) == 2


# ===================================================================
# estimate_building_height
# ===================================================================


class TestEstimateBuildingHeight:
    """Tests for estimate_building_height()."""

    def test_measured_height_tag(self):
        """bldg:measuredHeight tag value is used."""
        inner = """\
<bldg:measuredHeight xmlns:bldg="http://www.opengis.net/citygml/building/2.0">25.5</bldg:measuredHeight>"""
        bldg = _building(children_xml=inner)
        assert estimate_building_height(bldg) == 25.5

    def test_uro_measured_height(self):
        """uro:measuredHeight is used."""
        inner = """\
<uro:measuredHeight xmlns:uro="https://www.geospatial.jp/iur/uro/3.1">15.0</uro:measuredHeight>"""
        bldg = _building(children_xml=inner)
        assert estimate_building_height(bldg) == 15.0

    def test_uro_building_height(self):
        """uro:buildingHeight is used."""
        inner = """\
<uro:buildingHeight xmlns:uro="https://www.geospatial.jp/iur/uro/3.1">30.0</uro:buildingHeight>"""
        bldg = _building(children_xml=inner)
        assert estimate_building_height(bldg) == 30.0

    def test_z_range_fallback(self):
        """Z range is used when no height tags exist."""
        # Z values: 0, 0, 10, 10, 0 → range = 10
        inner = _footprint_xml(_polygon(coords="0 0 0 1 0 0 1 1 10 0 1 10 0 0 0"))
        bldg = _building(children_xml=inner)
        assert estimate_building_height(bldg) == 10.0

    def test_default_height_fallback(self):
        """Default height is returned when no height info available."""
        bldg = _building()
        assert estimate_building_height(bldg) == 10.0  # DEFAULT_BUILDING_HEIGHT
        assert estimate_building_height(bldg, default_height=20.0) == 20.0

    def test_zero_height_tag_uses_z_range(self):
        """Zero in measuredHeight is ignored (falls through to Z range)."""
        inner = """\
<bldg:measuredHeight xmlns:bldg="http://www.opengis.net/citygml/building/2.0">0</bldg:measuredHeight>"""
        inner += _footprint_xml(_polygon(coords="0 0 5 1 0 5 1 1 15 0 1 15 0 0 5"))
        bldg = _building(children_xml=inner)
        assert estimate_building_height(bldg) == 10.0

    def test_negative_height_ignored(self):
        """Negative height in tag is ignored."""
        inner = """\
<bldg:measuredHeight xmlns:bldg="http://www.opengis.net/citygml/building/2.0">-5</bldg:measuredHeight>"""
        bldg = _building(children_xml=inner)
        assert estimate_building_height(bldg) == 10.0  # default

    def test_non_numeric_height_ignored(self):
        """Non-numeric measuredHeight is ignored gracefully."""
        inner = """\
<bldg:measuredHeight xmlns:bldg="http://www.opengis.net/citygml/building/2.0">N/A</bldg:measuredHeight>"""
        bldg = _building(children_xml=inner)
        assert estimate_building_height(bldg) == 10.0  # default

    def test_flat_z_uses_default(self):
        """If all Z values are the same, falls through to default."""
        inner = _footprint_xml(_polygon(coords="0 0 5 1 0 5 1 1 5 0 1 5 0 0 5"))
        bldg = _building(children_xml=inner)
        assert estimate_building_height(bldg) == 10.0  # default


# ===================================================================
# count_polygons_in_element
# ===================================================================


class TestCountPolygonsInElement:
    """Tests for count_polygons_in_element()."""

    def test_counts_polygons(self):
        """Counts gml:Polygon descendants."""
        inner = _footprint_xml(_polygon("P1"))
        bldg = _building(children_xml=inner)
        assert count_polygons_in_element(bldg) == 1

    def test_empty_element(self):
        """Empty element returns 0."""
        bldg = _building()
        assert count_polygons_in_element(bldg) == 0

    def test_multiple_polygons(self):
        """Counts all nested polygons."""
        inner = f"""\
<bldg:lod0FootPrint xmlns:bldg="http://www.opengis.net/citygml/building/2.0"
                    xmlns:gml="http://www.opengis.net/gml">
  <gml:MultiSurface>
    <gml:surfaceMember>{_polygon("P1")}</gml:surfaceMember>
    <gml:surfaceMember>{_polygon("P2")}</gml:surfaceMember>
    <gml:surfaceMember>{_polygon("P3")}</gml:surfaceMember>
  </gml:MultiSurface>
</bldg:lod0FootPrint>"""
        bldg = _building(children_xml=inner)
        assert count_polygons_in_element(bldg) == 3

    def test_with_sample_gml(self, sample_gml_root):
        """Uses shared fixture — counts polygons in first building."""
        buildings = sample_gml_root.findall(".//bldg:Building", NS)
        # BLD_001 has 1 polygon (with interior ring, but still 1 Polygon element)
        assert count_polygons_in_element(buildings[0]) == 1


# ===================================================================
# find_building_parts
# ===================================================================


class TestFindBuildingParts:
    """Tests for find_building_parts()."""

    def test_no_parts(self):
        """Building with no parts returns empty list."""
        bldg = _building()
        assert find_building_parts(bldg) == []

    def test_finds_parts(self):
        """Finds bldg:BuildingPart elements."""
        inner = """\
<bldg:consistsOfBuildingPart xmlns:bldg="http://www.opengis.net/citygml/building/2.0"
                             xmlns:gml="http://www.opengis.net/gml">
  <bldg:BuildingPart gml:id="BP1">
  </bldg:BuildingPart>
</bldg:consistsOfBuildingPart>
<bldg:consistsOfBuildingPart xmlns:bldg="http://www.opengis.net/citygml/building/2.0"
                             xmlns:gml="http://www.opengis.net/gml">
  <bldg:BuildingPart gml:id="BP2">
  </bldg:BuildingPart>
</bldg:consistsOfBuildingPart>"""
        bldg = _building(children_xml=inner)
        parts = find_building_parts(bldg)
        assert len(parts) == 2

import tempfile

from gml2step import extract_footprints, parse, stream_parse


SAMPLE_GML = """<?xml version="1.0" encoding="UTF-8"?>
<CityModel xmlns="http://www.opengis.net/citygml/2.0"
           xmlns:bldg="http://www.opengis.net/citygml/building/2.0"
           xmlns:gml="http://www.opengis.net/gml">
  <cityObjectMember>
    <bldg:Building gml:id="BLD_001">
      <bldg:lod0FootPrint>
        <gml:MultiSurface>
          <gml:surfaceMember>
            <gml:Polygon>
              <gml:exterior>
                <gml:LinearRing>
                  <gml:posList>139.0 35.0 0.0 139.1 35.0 0.0 139.1 35.1 0.0 139.0 35.1 0.0 139.0 35.0 0.0</gml:posList>
                </gml:LinearRing>
              </gml:exterior>
            </gml:Polygon>
          </gml:surfaceMember>
        </gml:MultiSurface>
      </bldg:lod0FootPrint>
    </bldg:Building>
  </cityObjectMember>
  <cityObjectMember>
    <bldg:Building gml:id="BLD_002"/>
  </cityObjectMember>
</CityModel>
"""


def write_sample_gml() -> str:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".gml", delete=False, encoding="utf-8") as f:
        f.write(SAMPLE_GML)
        return f.name


def test_parse_returns_summary() -> None:
    gml_path = write_sample_gml()
    result = parse(gml_path, limit=1)
    assert result["total_buildings"] == 2
    assert result["listed_building_ids"] == ["BLD_001"]


def test_stream_parse_reads_buildings() -> None:
    gml_path = write_sample_gml()
    ids = []
    for building, _ in stream_parse(gml_path, limit=2):
        ids.append(building.get("{http://www.opengis.net/gml}id"))
    assert ids == ["BLD_001", "BLD_002"]


def test_extract_footprints_returns_items() -> None:
    gml_path = write_sample_gml()
    fps = extract_footprints(gml_path, limit=5)
    assert len(fps) == 1
    assert fps[0].building_id == "BLD_001"
    assert len(fps[0].exterior) >= 4

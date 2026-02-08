import tempfile

from typer.testing import CliRunner

from gml2step.cli import app


runner = CliRunner()

SAMPLE_GML = """<?xml version="1.0" encoding="UTF-8"?>
<CityModel xmlns="http://www.opengis.net/citygml/2.0"
           xmlns:bldg="http://www.opengis.net/citygml/building/2.0"
           xmlns:gml="http://www.opengis.net/gml">
  <cityObjectMember>
    <bldg:Building gml:id="BLD_001"/>
  </cityObjectMember>
</CityModel>
"""


def write_sample_gml() -> str:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".gml", delete=False, encoding="utf-8") as f:
        f.write(SAMPLE_GML)
        return f.name


def test_cli_parse() -> None:
    gml_path = write_sample_gml()
    result = runner.invoke(app, ["parse", gml_path])
    assert result.exit_code == 0
    assert '"total_buildings": 1' in result.stdout


def test_cli_stream_parse() -> None:
    gml_path = write_sample_gml()
    result = runner.invoke(app, ["stream-parse", gml_path])
    assert result.exit_code == 0
    assert "BLD_001" in result.stdout
    assert "total=1" in result.stdout


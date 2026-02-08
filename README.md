# gml2step

`gml2step` is a standalone toolkit for CityGML parsing and STEP conversion, extracted from Paper-CAD.

## Features
- Library API: `convert`, `parse`, `stream_parse`, `extract_footprints`
- CLI: `gml2step convert|parse|stream-parse|extract-footprints`
- Optional PLATEAU integration via extras
- Docker workflow for OCCT-enabled conversion

## Documentation
- English: https://soynyuu.github.io/gml2step/
- 日本語 (Japanese): https://soynyuu.github.io/gml2step/ja/guides/plateau/

## Install
```bash
pip install gml2step
```

PLATEAU optional features:
```bash
pip install "gml2step[plateau]"
```

## OCCT note
STEP conversion requires OpenCASCADE (`pythonocc-core`), which is not reliably pip-installable on all platforms.
For full conversion features, use conda or Docker.

Conda example:
```bash
conda install -c conda-forge pythonocc-core
```

## CLI examples
```bash
gml2step parse ./input.gml
gml2step stream-parse ./input.gml --limit 100
gml2step extract-footprints ./input.gml --output-json ./footprints.json
gml2step convert ./input.gml ./output.step --method solid
```

## Library examples
```python
from gml2step import parse, stream_parse, extract_footprints, convert

summary = parse("input.gml")
for building, _ in stream_parse("input.gml", limit=10):
    print(building.get("{http://www.opengis.net/gml}id"))

footprints = extract_footprints("input.gml", limit=100)
ok, out = convert("input.gml", "output.step")
```

## Development
```bash
pip install -e ".[dev]"
pytest
```


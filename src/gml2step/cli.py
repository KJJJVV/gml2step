"""Typer-based CLI for gml2step."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import List, Optional

import typer

from .api import convert as convert_api
from .api import extract_footprints as extract_footprints_api
from .api import parse as parse_api
from .api import stream_parse as stream_parse_api

app = typer.Typer(add_completion=False, help="CityGML parsing and STEP conversion CLI.")


@app.command("convert")
def convert_cmd(
    input_gml: Path = typer.Argument(
        ..., exists=True, readable=True, help="Input CityGML file"
    ),
    output_step: Path = typer.Argument(..., help="Output STEP file"),
    limit: Optional[int] = typer.Option(None, help="Maximum number of buildings"),
    method: str = typer.Option(
        "solid", help="Conversion method: solid|auto|sew|extrude"
    ),
    debug: bool = typer.Option(False, help="Enable debug logging"),
    use_streaming: bool = typer.Option(True, help="Use streaming parser when possible"),
    building_id: Optional[List[str]] = typer.Option(
        None, "--building-id", help="Filter by building ID(s)"
    ),
    filter_attribute: str = typer.Option(
        "gml:id", help="Filter attribute for building ID matching"
    ),
) -> None:
    ok, result = convert_api(
        gml_path=str(input_gml),
        out_step=str(output_step),
        limit=limit,
        method=method,
        debug=debug,
        use_streaming=use_streaming,
        building_ids=building_id,
        filter_attribute=filter_attribute,
    )
    if not ok:
        typer.echo(f"Conversion failed: {result}", err=True)
        raise typer.Exit(1)
    typer.echo(result)


@app.command("parse")
def parse_cmd(
    input_gml: Path = typer.Argument(
        ..., exists=True, readable=True, help="Input CityGML file"
    ),
    limit: Optional[int] = typer.Option(None, help="Limit listed building IDs"),
) -> None:
    summary = parse_api(str(input_gml), limit=limit)
    typer.echo(json.dumps(summary, ensure_ascii=False, indent=2))


@app.command("stream-parse")
def stream_parse_cmd(
    input_gml: Path = typer.Argument(
        ..., exists=True, readable=True, help="Input CityGML file"
    ),
    limit: Optional[int] = typer.Option(None, help="Maximum number of buildings"),
    building_id: Optional[List[str]] = typer.Option(
        None, "--building-id", help="Filter building ID"
    ),
    filter_attribute: str = typer.Option("gml:id", help="Filter attribute"),
) -> None:
    count = 0
    for building, _ in stream_parse_api(
        gml_path=str(input_gml),
        limit=limit,
        building_ids=building_id,
        filter_attribute=filter_attribute,
    ):
        count += 1
        bid = (
            building.get("{http://www.opengis.net/gml}id")
            or building.get("id")
            or f"building_{count}"
        )
        typer.echo(bid)
    typer.echo(f"total={count}")


@app.command("extract-footprints")
def extract_footprints_cmd(
    input_gml: Path = typer.Argument(
        ..., exists=True, readable=True, help="Input CityGML file"
    ),
    output_json: Optional[Path] = typer.Option(None, help="Optional JSON output path"),
    limit: Optional[int] = typer.Option(None, help="Maximum number of buildings"),
    default_height: float = typer.Option(10.0, help="Default height in meters"),
) -> None:
    footprints = extract_footprints_api(
        gml_path=str(input_gml),
        default_height=default_height,
        limit=limit,
    )
    payload = [asdict(fp) for fp in footprints]

    if output_json is not None:
        output_json.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        typer.echo(str(output_json))
        return

    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    app()

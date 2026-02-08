#!/usr/bin/env python3
"""
End-to-end verification script for gml2step.

This script tests the entire pipeline:
1. Fetch CityGML data from PLATEAU API (Tokyo Station area)
2. Parse buildings from the fetched CityGML
3. Extract footprints from the saved GML file
4. Attempt STEP conversion (if pythonocc-core is available)
5. Use stream_parse on the saved GML file
"""

import json
import os
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path


# ============================================================================
# Step 1: Fetch CityGML from PLATEAU API
# ============================================================================
def test_fetch_citygml():
    """Fetch CityGML data from PLATEAU API for Tokyo Station area."""
    print("\n" + "=" * 70)
    print("STEP 1: Fetch CityGML from PLATEAU API")
    print("=" * 70)

    from gml2step.plateau.fetcher import fetch_citygml_from_plateau

    # Tokyo Station coordinates
    lat, lon = 35.681236, 139.767125
    print(f"Target: Tokyo Station ({lat}, {lon})")

    xml_content = fetch_citygml_from_plateau(lat, lon, timeout=60)

    if xml_content is None:
        print("FAILED: Could not fetch CityGML data from PLATEAU API")
        return None

    print(f"SUCCESS: Fetched {len(xml_content):,} bytes of CityGML XML")

    # Quick validation: parse as XML
    try:
        root = ET.fromstring(xml_content)
        print(f"XML root tag: {root.tag}")
    except ET.ParseError as e:
        print(f"WARNING: XML parse error: {e}")

    return xml_content


# ============================================================================
# Step 2: Parse buildings from CityGML
# ============================================================================
def test_parse_buildings(xml_content):
    """Parse building information from fetched CityGML."""
    print("\n" + "=" * 70)
    print("STEP 2: Parse Buildings from CityGML")
    print("=" * 70)

    from gml2step.plateau.fetcher import parse_buildings_from_citygml

    buildings = parse_buildings_from_citygml(xml_content)

    if not buildings:
        print("FAILED: No buildings parsed from CityGML")
        return []

    print(f"SUCCESS: Parsed {len(buildings)} buildings")
    print(f"\nTop 5 buildings:")
    for i, b in enumerate(buildings[:5], 1):
        name_str = f'"{b.name}"' if b.name else "unnamed"
        height_str = f"{b.measured_height or b.height or 'unknown'}m"
        lod_str = []
        if b.has_lod3:
            lod_str.append("LOD3")
        if b.has_lod2:
            lod_str.append("LOD2")
        if not lod_str:
            lod_str.append("LOD1")
        print(f"  {i}. {b.gml_id[:50]}")
        print(f"     Name: {name_str}, Height: {height_str}, LOD: {'/'.join(lod_str)}")
        print(f"     Coords: ({b.latitude:.6f}, {b.longitude:.6f})")

    return buildings


# ============================================================================
# Step 3: Save GML and test parse/stream_parse/extract_footprints APIs
# ============================================================================
def test_gml2step_apis(xml_content):
    """Test gml2step public APIs with the fetched CityGML data."""
    print("\n" + "=" * 70)
    print("STEP 3: Test gml2step Public APIs")
    print("=" * 70)

    # Save XML to temporary file
    tmpdir = tempfile.mkdtemp(prefix="gml2step_test_")
    gml_path = os.path.join(tmpdir, "tokyo_station.gml")

    with open(gml_path, "w", encoding="utf-8") as f:
        f.write(xml_content)
    print(f"Saved GML to: {gml_path}")
    print(f"File size: {os.path.getsize(gml_path):,} bytes")

    results = {}

    # Test 3a: parse API
    print("\n--- 3a: gml2step.parse() ---")
    try:
        from gml2step import parse

        summary = parse(gml_path, limit=10)
        print(f"  detected_source_crs: {summary['detected_source_crs']}")
        print(f"  total_buildings: {summary['total_buildings']}")
        print(f"  sample_lat: {summary['sample_latitude']}")
        print(f"  sample_lon: {summary['sample_longitude']}")
        print(
            f"  listed_building_ids ({len(summary['listed_building_ids'])}): {summary['listed_building_ids'][:3]}..."
        )
        results["parse"] = "PASS"
    except Exception as e:
        print(f"  FAILED: {type(e).__name__}: {e}")
        results["parse"] = f"FAIL: {e}"

    # Test 3b: stream_parse API
    print("\n--- 3b: gml2step.stream_parse() ---")
    try:
        from gml2step import stream_parse

        count = 0
        building_ids_found = []
        for building_elem, xlink_index in stream_parse(gml_path, limit=5):
            count += 1
            bid = building_elem.get("{http://www.opengis.net/gml}id") or "unknown"
            building_ids_found.append(bid)
        print(f"  Streamed {count} buildings")
        print(f"  IDs: {building_ids_found[:3]}...")
        results["stream_parse"] = "PASS"
    except Exception as e:
        print(f"  FAILED: {type(e).__name__}: {e}")
        results["stream_parse"] = f"FAIL: {e}"

    # Test 3c: extract_footprints API
    print("\n--- 3c: gml2step.extract_footprints() ---")
    try:
        from gml2step import extract_footprints

        footprints = extract_footprints(gml_path, limit=5)
        print(f"  Extracted {len(footprints)} footprints")
        for i, fp in enumerate(footprints[:3], 1):
            print(
                f"  {i}. {fp.building_id[:40]}: height={fp.height}m, vertices={len(fp.exterior)}"
            )
        results["extract_footprints"] = "PASS"
    except Exception as e:
        print(f"  FAILED: {type(e).__name__}: {e}")
        results["extract_footprints"] = f"FAIL: {e}"

    # Test 3d: convert API (requires pythonocc-core)
    print("\n--- 3d: gml2step.convert() (STEP conversion) ---")
    step_path = os.path.join(tmpdir, "tokyo_station.step")
    try:
        from gml2step import convert

        success, message = convert(
            gml_path=gml_path,
            out_step=step_path,
            limit=1,
            method="auto",
            debug=False,
        )
        if success:
            step_size = os.path.getsize(step_path)
            print(f"  SUCCESS: STEP file created at {step_path}")
            print(f"  File size: {step_size:,} bytes")
            results["convert"] = "PASS"
        else:
            print(f"  Conversion returned failure: {message}")
            results["convert"] = f"FAIL: {message}"
    except ImportError as e:
        print(f"  SKIPPED: pythonocc-core not available ({e})")
        results["convert"] = "SKIP (no pythonocc-core)"
    except Exception as e:
        print(f"  FAILED: {type(e).__name__}: {e}")
        results["convert"] = f"FAIL: {e}"

    # Test 3e: CLI parse command
    print("\n--- 3e: CLI 'parse' command ---")
    try:
        from typer.testing import CliRunner
        from gml2step.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["parse", gml_path, "--limit", "3"])
        if result.exit_code == 0:
            cli_output = json.loads(result.output)
            print(f"  CLI parse returned: {cli_output['total_buildings']} buildings")
            print(f"  CRS: {cli_output['detected_source_crs']}")
            results["cli_parse"] = "PASS"
        else:
            print(f"  CLI exit code: {result.exit_code}")
            print(f"  Output: {result.output[:200]}")
            results["cli_parse"] = f"FAIL: exit_code={result.exit_code}"
    except Exception as e:
        print(f"  FAILED: {type(e).__name__}: {e}")
        results["cli_parse"] = f"FAIL: {e}"

    return results, gml_path, tmpdir


# ============================================================================
# Step 4: Test search_buildings_by_address (high-level PLATEAU search)
# ============================================================================
def test_search_buildings():
    """Test the high-level building search function."""
    print("\n" + "=" * 70)
    print("STEP 4: Test search_buildings_by_address()")
    print("=" * 70)

    from gml2step.plateau.fetcher import search_buildings_by_address

    # Use a well-known location
    result = search_buildings_by_address(
        "東京駅",
        radius=0.001,
        limit=5,
        search_mode="distance",
    )

    if result["success"]:
        geo = result["geocoding"]
        print(f"Geocoding: {geo.display_name[:80]}")
        print(f"Coordinates: ({geo.latitude:.6f}, {geo.longitude:.6f})")
        print(f"Buildings found: {len(result['buildings'])}")
        print(f"CityGML XML size: {len(result['citygml_xml']):,} bytes")

        for i, b in enumerate(result["buildings"][:3], 1):
            print(f"  {i}. {b.gml_id[:40]} - {b.distance_meters:.1f}m away")
        return True
    else:
        print(f"FAILED: {result['error']}")
        return False


# ============================================================================
# Main
# ============================================================================
def main():
    print("=" * 70)
    print("gml2step End-to-End Verification")
    print("=" * 70)
    print(f"Python: {sys.version}")
    print(f"Working dir: {os.getcwd()}")

    all_results = {}

    # Step 1: Fetch CityGML
    xml_content = test_fetch_citygml()
    all_results["fetch_citygml"] = "PASS" if xml_content else "FAIL"

    if xml_content is None:
        print("\nCannot continue without CityGML data.")
        _print_summary(all_results)
        return 1

    # Step 2: Parse buildings
    buildings = test_parse_buildings(xml_content)
    all_results["parse_buildings"] = "PASS" if buildings else "FAIL"

    # Step 3: Test gml2step APIs
    api_results, gml_path, tmpdir = test_gml2step_apis(xml_content)
    all_results.update(api_results)

    # Step 4: Search buildings by address
    search_ok = test_search_buildings()
    all_results["search_buildings"] = "PASS" if search_ok else "FAIL"

    # Cleanup
    print(f"\nTemporary files in: {tmpdir}")
    print("(Not cleaning up so you can inspect them)")

    _print_summary(all_results)

    # Return 0 if all critical tests passed
    critical = [
        "fetch_citygml",
        "parse_buildings",
        "parse",
        "stream_parse",
        "extract_footprints",
    ]
    failed = [k for k in critical if all_results.get(k, "FAIL") != "PASS"]
    return 1 if failed else 0


def _print_summary(results):
    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    for name, status in results.items():
        icon = "✓" if status == "PASS" else ("⊘" if "SKIP" in str(status) else "✗")
        print(f"  {icon} {name}: {status}")

    passed = sum(1 for v in results.values() if v == "PASS")
    skipped = sum(1 for v in results.values() if "SKIP" in str(v))
    failed = len(results) - passed - skipped
    print(f"\n  Total: {passed} passed, {skipped} skipped, {failed} failed")


if __name__ == "__main__":
    sys.exit(main())

"""Optional PLATEAU integration."""

from .fetcher import (
    fetch_citygml_by_mesh_code,
    fetch_citygml_by_municipality,
    search_buildings_by_address,
    search_building_by_id,
    search_building_by_id_and_mesh,
)

__all__ = [
    "fetch_citygml_by_mesh_code",
    "fetch_citygml_by_municipality",
    "search_buildings_by_address",
    "search_building_by_id",
    "search_building_by_id_and_mesh",
]

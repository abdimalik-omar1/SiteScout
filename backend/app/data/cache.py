"""Load the cached one-time Cork pull written by app.data.fetch.

Real CSO + OSM data, pulled once and cached so /api/analyze runs offline
and deterministically. The engine reads this; it never hits the network.
Missing cache -> FileNotFoundError, and the engine falls back to sample.py.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

CACHE_DIR = Path(__file__).parent / "cache"
_ADULT_BANDS = ("18-24", "25-44", "45-64", "65+")


@dataclass
class SmallArea:
    id: str
    lon: float
    lat: float
    age_bands: dict[str, int]
    name: str | None = None

    def adults(self) -> int:
        return sum(self.age_bands.get(b, 0) for b in _ADULT_BANDS)

    def band(self, label: str) -> int:
        return self.age_bands.get(label, 0)


@dataclass
class Poi:
    id: str
    kind: str
    lon: float
    lat: float
    name: str | None = None


@dataclass
class Dataset:
    small_areas: list[SmallArea]
    pois: list[Poi]


def load() -> Dataset:
    sa_path = CACHE_DIR / "small_areas.json"
    poi_path = CACHE_DIR / "pois.json"
    if not sa_path.exists() or not poi_path.exists():
        raise FileNotFoundError(
            f"cache missing in {CACHE_DIR}; run: python -m app.data.fetch"
        )
    small_areas = [SmallArea(**d) for d in json.loads(sa_path.read_text())]
    pois = [Poi(**d) for d in json.loads(poi_path.read_text())]
    return Dataset(small_areas=small_areas, pois=pois)

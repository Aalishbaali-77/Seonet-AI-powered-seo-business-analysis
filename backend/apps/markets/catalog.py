from __future__ import annotations

from apps.markets.models import GeoPlace

PAKISTAN_PLACES: list[tuple[str, str, str, str | None]] = [
    ("PK", "Pakistan", GeoPlace.Kind.COUNTRY, None),
    ("PK-SD", "Sindh", GeoPlace.Kind.REGION, "PK"),
    ("PK-PB", "Punjab", GeoPlace.Kind.REGION, "PK"),
    ("PK-KP", "Khyber Pakhtunkhwa", GeoPlace.Kind.REGION, "PK"),
    ("PK-BA", "Balochistan", GeoPlace.Kind.REGION, "PK"),
    ("PK-IS", "Islamabad Capital Territory", GeoPlace.Kind.REGION, "PK"),
    ("PK-GB", "Gilgit-Baltistan", GeoPlace.Kind.REGION, "PK"),
    ("PK-JK", "Azad Jammu and Kashmir", GeoPlace.Kind.REGION, "PK"),
    ("PK-SD-KHI", "Karachi", GeoPlace.Kind.CITY, "PK-SD"),
    ("PK-SD-HYD", "Hyderabad", GeoPlace.Kind.CITY, "PK-SD"),
    ("PK-PB-LHE", "Lahore", GeoPlace.Kind.CITY, "PK-PB"),
    ("PK-PB-FSD", "Faisalabad", GeoPlace.Kind.CITY, "PK-PB"),
    ("PK-PB-RWP", "Rawalpindi", GeoPlace.Kind.CITY, "PK-PB"),
    ("PK-PB-MUX", "Multan", GeoPlace.Kind.CITY, "PK-PB"),
    ("PK-IS-ISB", "Islamabad", GeoPlace.Kind.CITY, "PK-IS"),
    ("PK-KP-PEW", "Peshawar", GeoPlace.Kind.CITY, "PK-KP"),
    ("PK-BA-UET", "Quetta", GeoPlace.Kind.CITY, "PK-BA"),
    ("PK-SD-KHI-DHA", "DHA", GeoPlace.Kind.AREA, "PK-SD-KHI"),
    ("PK-SD-KHI-CLT", "Clifton", GeoPlace.Kind.AREA, "PK-SD-KHI"),
    ("PK-SD-KHI-GSH", "Gulshan", GeoPlace.Kind.AREA, "PK-SD-KHI"),
    ("PK-PB-LHE-GLB", "Gulberg", GeoPlace.Kind.AREA, "PK-PB-LHE"),
    ("PK-PB-LHE-DHA", "DHA Lahore", GeoPlace.Kind.AREA, "PK-PB-LHE"),
    ("PK-PB-LHE-MTN", "Model Town", GeoPlace.Kind.AREA, "PK-PB-LHE"),
    ("PK-PB-LHE-JHT", "Johar Town", GeoPlace.Kind.AREA, "PK-PB-LHE"),
]


def ensure_geo_catalog() -> None:
    by_code: dict[str, GeoPlace] = {}
    for code, name, kind, parent_code in PAKISTAN_PLACES:
        parent = by_code.get(parent_code) if parent_code else None
        if parent is None and parent_code:
            parent = GeoPlace.objects.filter(code=parent_code).first()
        place, _ = GeoPlace.objects.get_or_create(
            code=code,
            defaults={"name": name, "kind": kind, "parent": parent, "country_code": "PK"},
        )
        if place.name != name or place.kind != kind or place.parent_id != (parent.id if parent else None):
            place.name = name
            place.kind = kind
            place.parent = parent
            place.save(update_fields=["name", "kind", "parent", "updated_at"])
        by_code[code] = place

"""Deterministic provider for tests and local development without a Mapbox token."""

from __future__ import annotations

from app.modules.maps.geo import duration_s_for, path_length_m
from app.modules.maps.ports import GeoPoint, RouteResult

MIN_QUERY_LEN = 2
MIN_ROUTE_STOPS = 2
LAT_MAX = 90
LNG_MAX = 180
REVERSE_MATCH_DEG = 0.15

# Well-known Greater Cairo / El Obour points (WGS84). Labels exist in ar and en.
_PLACES: tuple[tuple[str, str, float, float], ...] = (
    ("مدينة العبور", "El Obour City", 30.1935, 31.4694),
    ("المنطقة الصناعية بالعبور", "El Obour Industrial Zone", 30.2150, 31.4550),
    ("مدينة نصر", "Nasr City", 30.0561, 31.3300),
    ("مصر الجديدة", "Heliopolis", 30.0875, 31.3242),
    ("وسط البلد", "Downtown Cairo", 30.0444, 31.2357),
    ("محطة رمسيس", "Ramses Station", 30.0626, 31.2470),
    ("التجمع الخامس", "New Cairo", 30.0074, 31.4433),
    ("كايرو فستيفال سيتي", "Cairo Festival City", 30.0278, 31.4075),
    ("مدينة 6 أكتوبر", "6th of October City", 29.9285, 30.9188),
    ("مدينتي", "Madinaty", 30.0752, 31.6374),
    ("الشروق", "El Shorouk", 30.1186, 31.6050),
    ("بدر", "Badr City", 30.1360, 31.7150),
    ("القاهرة", "Cairo", 30.0444, 31.2357),
    ("الجيزة", "Giza", 30.0131, 31.2089),
    ("المعادي", "Maadi", 29.9600, 31.2500),
    ("حلوان", "Helwan", 29.8410, 31.3000),
    ("الزمالك", "Zamalek", 30.0609, 31.2196),
    ("المهندسين", "Mohandessin", 30.0530, 31.2000),
    ("الدقي", "Dokki", 30.0380, 31.2120),
    ("الهرم", "Haram", 29.9900, 31.1500),
    ("فيصل", "Faisal", 30.0170, 31.1750),
    ("الشيخ زايد", "Sheikh Zayed", 30.0200, 30.9800),
    ("حدائق الأهرام", "Hadayek Al Ahram", 29.9800, 31.1000),
    ("الرحاب", "Rehab", 30.0600, 31.4900),
    ("العاصمة الإدارية", "New Administrative Capital", 30.0200, 31.7500),
    ("شبرا الخيمة", "Shubra El Kheima", 30.1220, 31.2440),
    ("شبرا", "Shubra", 30.0765, 31.2440),
    ("عين شمس", "Ain Shams", 30.1280, 31.3300),
    ("المقطم", "Mokattam", 30.0100, 31.3000),
    ("إمبابة", "Imbaba", 30.0750, 31.2050),
    ("قليوب", "Qalyub", 30.1790, 31.2050),
    ("الخانكة", "El Khanka", 30.2100, 31.3680),
    ("بنها", "Banha", 30.4660, 31.1840),
)


def _label(arabic: str, english: str, locale: str) -> str:
    return arabic if locale.startswith("ar") else english


class FakeMapProvider:
    """Straight-line geodesic routes between known (or caller-supplied) points."""

    provider_name = "fake"

    async def autocomplete(self, query: str, *, locale: str) -> tuple[GeoPoint, ...]:
        needle = query.strip().casefold()
        if len(needle) < MIN_QUERY_LEN:
            return ()
        hits: list[GeoPoint] = []
        for arabic, english, lat, lng in _PLACES:
            haystack = f"{arabic} {english}".casefold()
            if needle in haystack:
                hits.append(GeoPoint(lat=lat, lng=lng, label=_label(arabic, english, locale)))
        return tuple(hits[:12])

    async def geocode(self, query: str, *, locale: str) -> GeoPoint | None:
        stripped = query.strip()
        if "," in stripped:
            left, _, right = stripped.partition(",")
            try:
                lat = float(left.strip())
                lng = float(right.strip())
            except ValueError:
                pass
            else:
                if -LAT_MAX <= lat <= LAT_MAX and -LNG_MAX <= lng <= LNG_MAX:
                    return GeoPoint(lat=lat, lng=lng, label=stripped)
        hits = await self.autocomplete(stripped, locale=locale)
        return hits[0] if hits else None

    async def reverse_geocode(self, lat: float, lng: float, *, locale: str) -> GeoPoint | None:
        best: tuple[GeoPoint, float] | None = None
        for arabic, english, plat, plng in _PLACES:
            delta = abs(plat - lat) + abs(plng - lng)
            point = GeoPoint(lat=plat, lng=plng, label=_label(arabic, english, locale))
            if best is None or delta < best[1]:
                best = (point, delta)
        return None if best is None or best[1] > REVERSE_MATCH_DEG else best[0]

    async def route(self, stops: tuple[GeoPoint, ...]) -> RouteResult:
        if len(stops) < MIN_ROUTE_STOPS:
            msg = "A route needs at least origin and destination"
            raise ValueError(msg)
        coordinates = tuple((stop.lng, stop.lat) for stop in stops)
        distance_m = path_length_m(coordinates)
        return RouteResult(
            coordinates=coordinates,
            distance_m=distance_m,
            duration_s=duration_s_for(distance_m),
            provider=self.provider_name,
            provider_ref="geodesic",
        )

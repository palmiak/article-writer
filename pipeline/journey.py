"""Process GPX tracks, geotagged photos, reflection text, and Telegram exports into a journey brief."""

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import gpxpy
import requests
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

_PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".heif"}
_geocode_cache: dict[tuple[float, float], str] = {}
_last_geocode_call = 0.0


@dataclass
class DaySummary:
    filename: str
    date: str
    start_place: str
    end_place: str
    start_coords: tuple[float, float]
    end_coords: tuple[float, float]
    distance_km: float
    elevation_gain_m: float
    elevation_loss_m: float
    moving_time_minutes: int
    max_elevation_m: float


@dataclass
class PhotoNote:
    filename: str
    date: str       # YYYY-MM-DD
    timestamp: str  # YYYY-MM-DD HH:MM
    lat: float
    lon: float
    place: str
    note: str


# ---------------------------------------------------------------------------
# Geocoding
# ---------------------------------------------------------------------------

def reverse_geocode(lat: float, lon: float) -> str:
    """Reverse geocode coordinates to a human-readable place name.
    Results are cached; Nominatim rate limit respected (1 req/sec)."""
    key = (round(lat, 3), round(lon, 3))
    if key in _geocode_cache:
        return _geocode_cache[key]

    global _last_geocode_call
    elapsed = time.time() - _last_geocode_call
    if elapsed < 1.1:
        time.sleep(1.1 - elapsed)

    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": lat, "lon": lon, "format": "json", "zoom": 14},
            headers={"User-Agent": "article-writer-pipeline/1.0"},
            timeout=10,
        )
        _last_geocode_call = time.time()
        addr = resp.json().get("address", {})
        parts = [
            addr.get("village") or addr.get("town") or addr.get("city") or addr.get("municipality"),
            addr.get("county") or addr.get("state"),
            addr.get("country"),
        ]
        result = ", ".join(p for p in parts if p) or f"{lat:.4f}°N {lon:.4f}°E"
    except Exception:
        _last_geocode_call = time.time()
        result = f"{lat:.4f}°N {lon:.4f}°E"

    _geocode_cache[key] = result
    return result


# ---------------------------------------------------------------------------
# GPX processing
# ---------------------------------------------------------------------------

def process_gpx(gpx_path: Path) -> DaySummary:
    with open(gpx_path) as f:
        gpx = gpxpy.parse(f)

    points = [p for track in gpx.tracks for seg in track.segments for p in seg.points]
    if not points:
        raise ValueError(f"No track points found in {gpx_path.name}")

    start_pt = points[0]
    end_pt = points[-1]

    distance_km = (gpx.length_2d() or 0) / 1000

    ud = gpx.get_uphill_downhill()
    elevation_gain = round(ud.uphill or 0) if ud else 0
    elevation_loss = round(ud.downhill or 0) if ud else 0

    md = gpx.get_moving_data()
    moving_minutes = int((md.moving_time or 0) / 60) if md else 0

    elevations = [p.elevation for p in points if p.elevation is not None]
    max_elevation = round(max(elevations)) if elevations else 0

    date_str = start_pt.time.strftime("%Y-%m-%d") if start_pt.time else "unknown"

    print(f"  Geocoding start point for {gpx_path.name}...")
    start_place = reverse_geocode(start_pt.latitude, start_pt.longitude)
    print(f"  Geocoding end point for {gpx_path.name}...")
    end_place = reverse_geocode(end_pt.latitude, end_pt.longitude)

    return DaySummary(
        filename=gpx_path.name,
        date=date_str,
        start_place=start_place,
        end_place=end_place,
        start_coords=(start_pt.latitude, start_pt.longitude),
        end_coords=(end_pt.latitude, end_pt.longitude),
        distance_km=round(distance_km, 1),
        elevation_gain_m=elevation_gain,
        elevation_loss_m=elevation_loss,
        moving_time_minutes=moving_minutes,
        max_elevation_m=max_elevation,
    )


# ---------------------------------------------------------------------------
# Photo processing
# ---------------------------------------------------------------------------

def _get_exif_gps(img: Image.Image) -> tuple[float, float] | None:
    try:
        raw_exif = img._getexif()
    except Exception:
        return None
    if not raw_exif:
        return None

    gps_raw = None
    for tag_id, value in raw_exif.items():
        if TAGS.get(tag_id) == "GPSInfo":
            gps_raw = value
            break
    if not gps_raw:
        return None

    gps = {GPSTAGS.get(k, k): v for k, v in gps_raw.items()}

    def to_degrees(vals) -> float | None:
        try:
            d, m, s = vals
            return float(d) + float(m) / 60 + float(s) / 3600
        except Exception:
            return None

    lat = to_degrees(gps.get("GPSLatitude"))
    lon = to_degrees(gps.get("GPSLongitude"))
    if lat is None or lon is None:
        return None
    if gps.get("GPSLatitudeRef") == "S":
        lat = -lat
    if gps.get("GPSLongitudeRef") == "W":
        lon = -lon
    return lat, lon


def _get_exif_datetime(img: Image.Image) -> str | None:
    try:
        raw_exif = img._getexif()
    except Exception:
        return None
    if not raw_exif:
        return None
    for tag_id, value in raw_exif.items():
        if TAGS.get(tag_id) == "DateTime":
            try:
                dt = datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
                return dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                return None
    return None


def _read_sidecar(photo_path: Path) -> str:
    """Look for a .txt or .md sidecar note next to the photo."""
    for ext in (".txt", ".md"):
        sidecar = photo_path.with_suffix(ext)
        if sidecar.exists():
            return sidecar.read_text().strip()
    return ""


def process_photos_dir(photos_dir: Path) -> list[PhotoNote]:
    notes: list[PhotoNote] = []
    photo_files = sorted(
        p for p in photos_dir.rglob("*")
        if p.suffix.lower() in _PHOTO_EXTENSIONS
    )

    if not photo_files:
        return notes

    print(f"  Processing {len(photo_files)} photos...")
    for photo_path in photo_files:
        try:
            img = Image.open(photo_path)
        except Exception:
            continue

        coords = _get_exif_gps(img)
        if coords is None:
            continue  # skip photos without GPS

        lat, lon = coords
        timestamp = _get_exif_datetime(img) or "unknown time"
        date_str = timestamp[:10] if len(timestamp) >= 10 else "unknown"
        note = _read_sidecar(photo_path)
        place = reverse_geocode(lat, lon)

        notes.append(PhotoNote(
            filename=photo_path.name,
            date=date_str,
            timestamp=timestamp,
            lat=lat,
            lon=lon,
            place=place,
            note=note,
        ))

    notes.sort(key=lambda p: p.timestamp)
    return notes


# ---------------------------------------------------------------------------
# Brief builder
# ---------------------------------------------------------------------------

def build_journey_brief(
    days: list[DaySummary],
    photo_notes: list[PhotoNote],
    reflection: str,
    topic: str,
) -> str:
    lines: list[str] = [f"# Journey Brief: {topic}\n"]

    if reflection:
        lines.append("## Motivation & Reflection\n")
        lines.append(reflection)
        lines.append("\n")

    total_distance = sum(d.distance_km for d in days)
    total_gain = sum(d.elevation_gain_m for d in days)
    total_days = len(days)
    lines.append("## Journey Overview\n")
    lines.append(
        f"**{total_days} days | {total_distance:.1f} km total | {total_gain:,}m elevation gain**\n"
    )

    lines.append("## Day-by-Day Summary\n")
    for day in days:
        h = day.moving_time_minutes // 60
        m = day.moving_time_minutes % 60
        lines.append(f"### {day.date} — {day.start_place} → {day.end_place}")
        lines.append(f"- Distance: {day.distance_km} km")
        lines.append(f"- Elevation: +{day.elevation_gain_m}m / -{day.elevation_loss_m}m")
        lines.append(f"- Moving time: {h}h {m}m")
        lines.append(f"- Highest point: {day.max_elevation_m}m")

        day_photos = [p for p in photo_notes if p.date == day.date]
        if day_photos:
            lines.append("\n**Points of interest:**")
            for photo in day_photos:
                note_text = f": {photo.note}" if photo.note else ""
                lines.append(f"- {photo.timestamp[11:16]} — {photo.place}{note_text}")

        lines.append("")

    # Photos not matched to any day
    day_dates = {d.date for d in days}
    unmatched = [p for p in photo_notes if p.date not in day_dates and p.note]
    if unmatched:
        lines.append("## Additional Notes (unmatched to a day)\n")
        for photo in unmatched:
            lines.append(f"- {photo.timestamp} at {photo.place}: {photo.note}")
        lines.append("")

    return "\n".join(lines)

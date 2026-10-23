"""Geographic helpers (distance, travel time)."""
import math

ROAD_FACTOR = 1.3      # roads are ~30% longer than straight-line distance
AVG_SPEED_KMPH = 50    # average speed on Karnataka highways + ghat roads


def haversine_km(lat1, lng1, lat2, lng2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def road_km(lat1, lng1, lat2, lng2):
    return haversine_km(lat1, lng1, lat2, lng2) * ROAD_FACTOR


def travel_hours(km):
    return km / AVG_SPEED_KMPH


def fmt_hours(hours):
    if hours < 1:
        return f"{max(10, int(round(hours * 60 / 5) * 5))} min"
    h = round(hours * 2) / 2
    return f"{h:g} hrs"

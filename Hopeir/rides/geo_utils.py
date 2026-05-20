import math


def haversine(lat1, lng1, lat2, lng2):
    """
    Returns distance in kilometers between two lat/lng points.
    """
    R = 6371.0
    lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def nearest_point_index_on_path(lat, lng, path):
    """
    Given a lat/lng and a list of {"lat": ..., "lng": ...} dicts,
    returns (min_distance_km, index_of_nearest_point).
    """
    min_dist = float("inf")
    nearest_idx = 0
    for i, point in enumerate(path):
        d = haversine(lat, lng, point["lat"], point["lng"])
        if d < min_dist:
            min_dist = d
            nearest_idx = i
    return min_dist, nearest_idx


def min_dist_to_path(lat, lng, path, sample_size=50):
    """
    Returns the minimum distance in km from a point to any point on the path.
    Samples the path if it has more than sample_size points to keep it fast.
    """
    if not path:
        return float("inf")

    if len(path) > sample_size:
        step = len(path) // sample_size
        path = path[::step]

    min_dist, _ = nearest_point_index_on_path(lat, lng, path)
    return min_dist
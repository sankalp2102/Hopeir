"""
Hopeir Backend — Full Test Script
===================================
No setup needed. Script creates its own test users via SuperTokens,
runs all tests, then cleans up.

Run with:
    pip install requests
    python test_hopeir.py

Make sure Django server is running:
    python manage.py runserver
"""

import requests
import json
import sys
import uuid

BASE = "https://hopeir.onrender.com"

# Test credentials — random suffix avoids conflicts on repeated runs
RUN_ID       = str(uuid.uuid4())[:8]
DRIVER_EMAIL = f"test.driver.{RUN_ID}@hopeir.test"
RIDER_EMAIL  = f"test.rider.{RUN_ID}@hopeir.test"
PASSWORD     = "TestPass123!"

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

passed = 0
failed = 0

# ── helpers ────────────────────────────────────────────────────────────────

def ok(label, data=None):
    global passed
    passed += 1
    print(f"  {GREEN}✓ PASS{RESET}  {label}")
    if data:
        print(f"          {YELLOW}{json.dumps(data, default=str)[:300]}{RESET}")

def fail(label, reason="", data=None):
    global failed
    failed += 1
    print(f"  {RED}✗ FAIL{RESET}  {label}")
    if reason:
        print(f"          {RED}{reason}{RESET}")
    if data:
        print(f"          {YELLOW}{json.dumps(data, default=str)[:400]}{RESET}")

def section(title):
    print(f"\n{BOLD}{CYAN}{'─'*60}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'─'*60}{RESET}")

def _parse(r, label):
    try:
        return r.json()
    except Exception:
        fail(label, f"Non-JSON response ({r.status_code}): {r.text[:200]}")
        return None

def post(path, payload, label, expect=None):
    try:
        r = requests.post(f"{BASE}{path}", json=payload, timeout=10)
        data = _parse(r, label)
        if data is None:
            return None
        if expect and r.status_code != expect:
            fail(label, f"Expected {expect}, got {r.status_code}", data)
            return None
        ok(label, data)
        return data
    except Exception as e:
        fail(label, str(e))
        return None

def get(path, label, expect=200, params=None):
    try:
        r = requests.get(f"{BASE}{path}", params=params, timeout=10)
        data = _parse(r, label)
        if data is None:
            return None
        if r.status_code != expect:
            fail(label, f"Expected {expect}, got {r.status_code}", data)
            return None
        ok(label, data)
        return data
    except Exception as e:
        fail(label, str(e))
        return None

def delete(path, label, expect=200, body=None):
    try:
        r = requests.delete(f"{BASE}{path}", json=body, timeout=10)
        data = _parse(r, label) or {}
        if r.status_code != expect:
            fail(label, f"Expected {expect}, got {r.status_code}", data)
            return None
        ok(label, data)
        return data
    except Exception as e:
        fail(label, str(e))
        return None


# ══════════════════════════════════════════════════════════════════════════
# 0. Health check
# ══════════════════════════════════════════════════════════════════════════
section("0. Server health check")
try:
    r = requests.get(f"{BASE}/Test/", timeout=5)
    if r.status_code < 500:
        ok("Server is reachable")
    else:
        fail("Server returned 5xx", f"status {r.status_code}")
        sys.exit(1)
except Exception as e:
    fail("Cannot reach server", str(e))
    print(f"\n  {RED}Start the server:  python manage.py runserver{RESET}\n")
    sys.exit(1)


# ══════════════════════════════════════════════════════════════════════════
# 1. Create users via SuperTokens  →  Django user auto-created by hook
# ══════════════════════════════════════════════════════════════════════════
section("1. User creation via SuperTokens")

DRIVER_ID = None
RIDER_ID  = None

def signup(email, password, label):
    """
    Calls the SuperTokens email-password signup endpoint.
    On success Django auto-creates the CustomUser via the override hook.
    Returns the SuperTokens user_id (UUID) or None.
    """
    try:
        r = requests.post(
            f"{BASE}/auth/signup",
            json={
                "formFields": [
                    {"id": "email",    "value": email},
                    {"id": "password", "value": password}
                ]
            },
            timeout=10
        )
        data = _parse(r, label)
        if data is None:
            return None

        if r.status_code == 200 and data.get("status") == "OK":
            user_id = data["user"]["id"]
            ok(label, {"user_id": user_id, "email": email})
            return user_id
        else:
            fail(label, f"SuperTokens status: {data.get('status', r.status_code)}", data)
            return None
    except Exception as e:
        fail(label, str(e))
        return None

DRIVER_ID = signup(DRIVER_EMAIL, PASSWORD, "Sign up driver via SuperTokens")
RIDER_ID  = signup(RIDER_EMAIL,  PASSWORD, "Sign up rider  via SuperTokens")

if not DRIVER_ID or not RIDER_ID:
    print(f"\n  {RED}Cannot continue without both users. "
          f"Check that SuperTokens core is reachable from your server.{RESET}\n")
    sys.exit(1)

# Verify Django user was auto-created by the hook
get(f"/profiles/{DRIVER_ID}/", "Fetch driver profile from Django DB")
get(f"/profiles/{RIDER_ID}/",  "Fetch rider  profile from Django DB")


# ══════════════════════════════════════════════════════════════════════════
# 2. Vehicle
# ══════════════════════════════════════════════════════════════════════════
section("2. Vehicle")

vehicle_data = post("/vehicles/", {
    "user": DRIVER_ID,
    "vehicle_type": "Car",
    "vehicle_model": "Toyota Corolla",
    "vehicle_year": 2022,
    "vehicle_color": "White",
    "vehicle_license_plate": f"TST-{RUN_ID[:4].upper()}",
    "vehicle_engine_type": "Petrol"
}, "Create vehicle for driver", expect=201)

VEHICLE_ID = vehicle_data.get("id") if vehicle_data else None
if VEHICLE_ID:
    ok(f"Vehicle ID captured: {VEHICLE_ID}")

get("/vehicles/", "List driver vehicles", params={"user_id": DRIVER_ID})
if VEHICLE_ID:
    get("/vehicles/", "Get vehicle by ID", params={"vehicle_id": VEHICLE_ID})


# ══════════════════════════════════════════════════════════════════════════
# 3. Stations
# ══════════════════════════════════════════════════════════════════════════
section("3. Stations")

station_a = post("/stations/post/", {
    "name": f"Test Alpha {RUN_ID}",
    "latitude": 31.5204,
    "longitude": 74.3587,
    "address": "Mall Road, Lahore",
    "city": "Lahore",
    "country": "Pakistan"
}, "Create Station Alpha (driver start)", expect=201)

station_b = post("/stations/post/", {
    "name": f"Test Beta {RUN_ID}",
    "latitude": 31.5497,
    "longitude": 74.3436,
    "address": "Gulberg III, Lahore",
    "city": "Lahore",
    "country": "Pakistan"
}, "Create Station Beta (driver end)", expect=201)

station_c = post("/stations/post/", {
    "name": f"Test Gamma {RUN_ID}",
    "latitude": 31.5320,
    "longitude": 74.3500,
    "address": "Liberty Market, Lahore",
    "city": "Lahore",
    "country": "Pakistan"
}, "Create Station Gamma (mid-route)", expect=201)

station_a_id = station_a.get("id") if station_a else None
station_b_id = station_b.get("id") if station_b else None
station_c_id = station_c.get("id") if station_c else None

if station_a_id: ok(f"Station Alpha ID: {station_a_id}")
if station_b_id: ok(f"Station Beta  ID: {station_b_id}")
if station_c_id: ok(f"Station Gamma ID: {station_c_id}")

get("/stations/get/", "List all stations")
if station_a_id:
    get("/stations/get/", "Get station by ID", params={"station_id": station_a_id})


# ══════════════════════════════════════════════════════════════════════════
# 4. Fare
# ══════════════════════════════════════════════════════════════════════════
section("4. Fare")

fare_data = post("/fare/fares/", {"price": "150.00"}, "Create fare", expect=201)
fare_id = fare_data.get("id") if fare_data else None
if fare_id:
    ok(f"Fare ID captured: {fare_id}")
get("/fare/fares/", "List fares")


# ══════════════════════════════════════════════════════════════════════════
# 5. Ride creation
# ══════════════════════════════════════════════════════════════════════════
section("5. Ride creation")

# Polyline: Station Alpha → Beta, passing near Station Gamma
ROUTE_PATH = [
    {"lat": 31.5204, "lng": 74.3587},
    {"lat": 31.5230, "lng": 74.3570},
    {"lat": 31.5260, "lng": 74.3550},
    {"lat": 31.5290, "lng": 74.3530},
    {"lat": 31.5320, "lng": 74.3510},  # near Station Gamma
    {"lat": 31.5350, "lng": 74.3490},
    {"lat": 31.5380, "lng": 74.3470},
    {"lat": 31.5420, "lng": 74.3455},
    {"lat": 31.5460, "lng": 74.3443},
    {"lat": 31.5497, "lng": 74.3436},
]

ride_id        = None
ride_no_path_id = None

if VEHICLE_ID and station_a_id and station_b_id and fare_id:
    base_payload = {
        "user": DRIVER_ID,
        "vehicle": VEHICLE_ID,
        "start_location": station_a_id,
        "end_location": station_b_id,
        "start_time": "2026-06-01T08:00:00Z",
        "distance": 5.2,
        "fare": fare_id,
        "seats": 3,
        "route_path": ROUTE_PATH
    }

    rd = post("/rides/create/", base_payload, "Create ride WITH route_path", expect=201)
    if rd:
        ride_id = rd.get("id")
        ok(f"Ride ID: {ride_id}")

        # Verify route_path was stored
        fetched = get("/rides/get/", "Verify route_path stored on ride", params={"ride_id": ride_id})
        if fetched:
            items = fetched if isinstance(fetched, list) else fetched.get("results", [fetched])
            ride_obj = next((r for r in items if r.get("id") == ride_id), None)
            if ride_obj and ride_obj.get("route_path"):
                ok("route_path correctly stored in DB")
            else:
                fail("route_path storage", "route_path is null or missing on fetched ride")

    rd2 = post("/rides/create/", {**base_payload, "route_path": None, "seats": 2},
               "Create ride WITHOUT route_path (backward compat)", expect=201)
    if rd2:
        ride_no_path_id = rd2.get("id")
        ok(f"Ride (no path) ID: {ride_no_path_id}")
else:
    fail("Ride creation", "Skipped — missing vehicle/station/fare IDs")

get("/rides/get/", "List all rides")
get("/rides/get/", "Filter rides by driver", params={"user_id": DRIVER_ID})


# ══════════════════════════════════════════════════════════════════════════
# 6. Ride matching
# ══════════════════════════════════════════════════════════════════════════
section("6. Ride matching — GET /rides/match/")

if station_a_id and station_b_id and ride_id:

    # Case 1 — perfect match
    r1 = get("/rides/match/", "Case 1 — perfect match (same start + end)", params={
        "rider_start_station_id": station_a_id,
        "rider_end_station_id":   station_b_id,
        "rider_user_id":          RIDER_ID
    })
    if r1:
        if r1.get("count", 0) >= 1:
            top = r1["results"][0]
            if top.get("match_zone") == "exact" and top.get("score") == 100:
                ok("Case 1 — match_zone=exact, score=100 ✓")
            else:
                fail("Case 1 score check", f"match_zone={top.get('match_zone')}, score={top.get('score')}")
        else:
            fail("Case 1", f"Expected ≥1 result, got count={r1.get('count')}")

    # Case 2 — same start, rider end on route (Station Gamma)
    if station_c_id:
        r2 = get("/rides/match/", "Case 2 — same start, rider end on route (Gamma)", params={
            "rider_start_station_id": station_a_id,
            "rider_end_station_id":   station_c_id,
            "rider_user_id":          RIDER_ID
        })
        if r2:
            if r2.get("count", 0) >= 1:
                top = r2["results"][0]
                if top.get("match_zone") == "same_start" and top.get("score") == 85:
                    ok("Case 2 — match_zone=same_start, score=85 ✓")
                else:
                    fail("Case 2 score check", f"match_zone={top.get('match_zone')}, score={top.get('score')}")
            else:
                fail("Case 2", f"Expected ≥1 result, got count={r2.get('count')}")

    # Case 3 — rider start on route, same end
    if station_c_id:
        r3 = get("/rides/match/", "Case 3 — rider start on route, same end", params={
            "rider_start_station_id": station_c_id,
            "rider_end_station_id":   station_b_id,
            "rider_user_id":          RIDER_ID
        })
        if r3:
            if r3.get("count", 0) >= 1:
                top = r3["results"][0]
                if top.get("match_zone") == "same_end" and top.get("score") == 80:
                    ok("Case 3 — match_zone=same_end, score=80 ✓")
                else:
                    fail("Case 3 score check", f"match_zone={top.get('match_zone')}, score={top.get('score')}")
            else:
                fail("Case 3", f"Expected ≥1 result, got count={r3.get('count')}")

    # Case 4 — both on route neither exact (use Gamma→Beta but driver is Alpha→Beta)
    # Gamma is mid-route, Beta is exact end — this hits same_end not both_on_route
    # For true both_on_route we need a station neither start nor end
    # Gamma (mid) → a point close to another mid point: use station_c as start only
    # Both_on_route needs neither exact match — skip if we only have 3 stations
    print(f"  {YELLOW}⚠ SKIP{RESET}  Case 4 (both_on_route) — needs 2 mid-route stations, only 1 created")

    # Case 5 — time window bonus
    r5 = get("/rides/match/", "Case 5 — time_window_minutes bonus", params={
        "rider_start_station_id": station_a_id,
        "rider_end_station_id":   station_b_id,
        "rider_user_id":          RIDER_ID,
        "time_window_minutes":    9999
    })
    if r5 and r5.get("count", 0) >= 1:
        top = r5["results"][0]
        expected_score = 100 + 10  # exact + time bonus
        if top.get("score") == expected_score:
            ok(f"Case 5 — time bonus applied, score={top.get('score')} ✓")
        else:
            fail("Case 5 time bonus", f"Expected score={expected_score}, got {top.get('score')}")

    # Case 6 — driver excluded from own rides
    r6 = get("/rides/match/", "Case 6 — rider is driver (should be excluded)", params={
        "rider_start_station_id": station_a_id,
        "rider_end_station_id":   station_b_id,
        "rider_user_id":          DRIVER_ID
    })
    if r6 is not None:
        ids = [r["id"] for r in r6.get("results", [])]
        if ride_id not in ids:
            ok("Case 6 — driver's own ride correctly excluded ✓")
        else:
            fail("Case 6", f"Ride {ride_id} appeared in driver's own match results")

    # Case 7 — missing required param → 400
    get("/rides/match/", "Case 7 — missing rider_user_id (expect 400)", expect=400, params={
        "rider_start_station_id": station_a_id,
        "rider_end_station_id":   station_b_id,
    })

    # Case 8 — invalid station → 400
    get("/rides/match/", "Case 8 — invalid station ID (expect 400)", expect=400, params={
        "rider_start_station_id": 99999,
        "rider_end_station_id":   station_b_id,
        "rider_user_id":          RIDER_ID
    })

    # Case 9 — invalid time_window → 400
    get("/rides/match/", "Case 9 — non-integer time_window (expect 400)", expect=400, params={
        "rider_start_station_id": station_a_id,
        "rider_end_station_id":   station_b_id,
        "rider_user_id":          RIDER_ID,
        "time_window_minutes":    "abc"
    })

else:
    fail("Ride matching", "Skipped — need ride_id and station IDs from earlier steps")


# ══════════════════════════════════════════════════════════════════════════
# 7. Ride requests
# ══════════════════════════════════════════════════════════════════════════
section("7. Ride requests")

if ride_id:
    # Valid request
    post("/rides/request/", {
        "ride": ride_id,
        "from_user": RIDER_ID
    }, "Rider requests a ride", expect=201)

    # Duplicate — should fail
    post("/rides/request/", {
        "ride": ride_id,
        "from_user": RIDER_ID
    }, "Duplicate request (expect 400)", expect=400)

    # Driver requests own ride — should fail
    post("/rides/request/", {
        "ride": ride_id,
        "from_user": DRIVER_ID
    }, "Driver requests own ride (expect 400)", expect=400)

    get("/rides/request/get/", "List requests — driver view", params={"user_id": DRIVER_ID})
    get("/rides/request/get/", "List requests — rider  view", params={"user_id": RIDER_ID})

    # After requesting, ride must be excluded from match results
    if station_a_id and station_b_id:
        r_excl = get("/rides/match/", "Already-requested ride excluded from match", params={
            "rider_start_station_id": station_a_id,
            "rider_end_station_id":   station_b_id,
            "rider_user_id":          RIDER_ID
        })
        if r_excl is not None:
            ids = [r["id"] for r in r_excl.get("results", [])]
            if ride_id not in ids:
                ok("Already-requested ride correctly excluded from match results ✓")
            else:
                fail("Already-requested exclusion", f"Ride {ride_id} still in results after requesting")
else:
    fail("Ride request tests", "Skipped — no ride_id")


# ══════════════════════════════════════════════════════════════════════════
# 8. Feedback
# ══════════════════════════════════════════════════════════════════════════
section("8. Ride feedback")

if ride_id:
    post("/rides/feedback/post/", {
        "ride": ride_id,
        "from_user": RIDER_ID,
        "to_user":   DRIVER_ID,
        "rating": 5,
        "comment": "Smooth ride!"
    }, "Rider gives feedback to driver", expect=201)

    get("/rides/feedback/get/", "Get feedback by ride_id",   params={"ride_id": ride_id})
    get("/rides/feedback/get/", "Get feedback by to_user",   params={"to_user_id": DRIVER_ID})
    get("/rides/feedback/get/", "Get feedback by from_user", params={"from_user_id": RIDER_ID})
else:
    fail("Feedback tests", "Skipped — no ride_id")


# ══════════════════════════════════════════════════════════════════════════
# 9. Posters
# ══════════════════════════════════════════════════════════════════════════
section("9. Posters")

post("/poster/active/get/", {
    "title": f"Test Active Banner {RUN_ID}",
    "image_url": "https://example.com/banner.jpg",
    "target_url": "https://example.com",
    "is_active": True
}, "Create active poster", expect=201)

post("/poster/active/get/", {
    "title": f"Test Inactive Banner {RUN_ID}",
    "image_url": "https://example.com/inactive.jpg",
    "target_url": "https://example.com",
    "is_active": False
}, "Create inactive poster", expect=201)

result = get("/poster/active/get/", "Get posters (only active returned)")
if result is not None:
    items = result if isinstance(result, list) else result.get("results", [])
    inactive = [p for p in items if not p.get("is_active", True)]
    if not inactive:
        ok("Only active posters in response ✓")
    else:
        fail("Active filter check", f"{len(inactive)} inactive poster(s) found in response")


# ══════════════════════════════════════════════════════════════════════════
# 10. Model data
# ══════════════════════════════════════════════════════════════════════════
section("10. Model data (ML input)")

post("/model-data/post/", {
    "user": RIDER_ID,
    "starting": "Johar Town",
    "destination": "DHA Phase 5",
    "preferred_route": "Main Boulevard",
    "choice": "fastest",
    "travel_time": "08:00:00",
    "frequency": 5
}, "Create model data entry", expect=201)

get("/model-data/get/", "List model data entries")


# ══════════════════════════════════════════════════════════════════════════
# 11. Cleanup
# ══════════════════════════════════════════════════════════════════════════
section("11. Cleanup — delete test users")

delete("/delete-user/", "Delete driver user", body={"email": DRIVER_EMAIL})
delete("/delete-user/", "Delete rider  user", body={"email": RIDER_EMAIL})

print(f"\n  {YELLOW}Note: Test stations/rides/fares remain in DB. "
      f"Clean them from Django admin if needed.{RESET}")
print(f"  {YELLOW}Station IDs: {station_a_id}, {station_b_id}, {station_c_id}{RESET}")
print(f"  {YELLOW}Ride IDs: {ride_id}, {ride_no_path_id}{RESET}")


# ══════════════════════════════════════════════════════════════════════════
# Summary
# ══════════════════════════════════════════════════════════════════════════
total = passed + failed
print(f"\n{BOLD}{'═'*60}{RESET}")
print(f"{BOLD}  Results:  {GREEN}{passed} passed{RESET}  |  {RED}{failed} failed{RESET}  |  {total} total{RESET}")
print(f"{BOLD}{'═'*60}{RESET}\n")

if failed > 0:
    sys.exit(1)
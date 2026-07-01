"""Backend regression tests for Aqari (عقاراتي) - Supabase Postgres migration.

Coverage:
- Auth: login/register/me with JWT cookies
- Properties CRUD with governorate/district
- Location-based filtering
- Admin stats (integers) and subscriptions (IQD plans)
"""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@aqari.com"
ADMIN_PASSWORD = "admin123"


# ---------- Fixtures ----------
@pytest.fixture(scope="session")
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"identifier": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    # Ensure cookies were set
    assert "access_token" in s.cookies, "access_token cookie not set on login"
    assert "refresh_token" in s.cookies, "refresh_token cookie not set on login"
    return s


@pytest.fixture(scope="session")
def agent_session():
    s = requests.Session()
    email = f"TEST_agent_{int(time.time())}_{uuid.uuid4().hex[:6]}@test.com"
    r = s.post(f"{API}/auth/register", json={
        "name": "TEST Agent",
        "email": email,
        "password": "test1234",
        "office_name": f"TEST Office {uuid.uuid4().hex[:6]}",
    })
    assert r.status_code == 200, f"Register failed: {r.status_code} {r.text}"
    assert "access_token" in s.cookies
    return s, email


@pytest.fixture(scope="session")
def second_agent_session():
    s = requests.Session()
    email = f"TEST_agent2_{int(time.time())}_{uuid.uuid4().hex[:6]}@test.com"
    r = s.post(f"{API}/auth/register", json={
        "name": "TEST Agent 2",
        "email": email,
        "password": "test1234",
    })
    assert r.status_code == 200
    return s


def _prop_payload(**overrides):
    payload = {
        "total_area": 200,
        "price": 50000000,
        "front_width": 10,
        "length": 20,
        "bedrooms": 3,
        "bathrooms": 2,
        "owner_name": "TEST مالك",
        "owner_phone": "07700000000",
        "status": "available",
        "governorate": "بغداد",
        "district": "الكرادة",
    }
    payload.update(overrides)
    return payload


# ---------- Auth ----------
class TestAuth:
    def test_admin_login_sets_cookies(self):
        s = requests.Session()
        r = s.post(f"{API}/auth/login", json={"identifier": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["email"] == ADMIN_EMAIL
        assert data["role"] == "admin"
        assert "access_token" in s.cookies
        assert "refresh_token" in s.cookies

    def test_login_invalid(self):
        r = requests.post(f"{API}/auth/login", json={"identifier": ADMIN_EMAIL, "password": "wrong"})
        assert r.status_code == 401

    def test_me_returns_admin(self, admin_session):
        r = admin_session.get(f"{API}/auth/me")
        assert r.status_code == 200
        data = r.json()
        assert data["email"] == ADMIN_EMAIL
        assert data["role"] == "admin"

    def test_me_unauthenticated(self):
        r = requests.get(f"{API}/auth/me")
        assert r.status_code == 401

    def test_register_agent_creates_office(self):
        s = requests.Session()
        email = f"TEST_reg_{uuid.uuid4().hex[:8]}@test.com"
        office = f"TEST Office {uuid.uuid4().hex[:6]}"
        r = s.post(f"{API}/auth/register", json={
            "name": "TEST Register",
            "email": email,
            "password": "test1234",
            "office_name": office,
        })
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["email"] == email.lower()
        assert data["role"] == "agent"
        assert data["office_name"] == office
        assert "access_token" in s.cookies


# ---------- Subscriptions ----------
class TestSubscriptionPlans:
    def test_get_plans_returns_three_iqd(self):
        r = requests.get(f"{API}/subscriptions/plans")
        assert r.status_code == 200
        plans = r.json()
        assert len(plans) == 3
        by_type = {p["plan_type"]: p for p in plans}
        assert by_type["monthly"]["amount"] == 25000 and by_type["monthly"]["currency"] == "IQD"
        assert by_type["quarterly"]["amount"] == 65000
        assert by_type["yearly"]["amount"] == 250000


class TestCreateSubscription:
    def test_create_monthly(self, agent_session):
        s, _ = agent_session
        r = s.post(f"{API}/subscriptions", json={"plan_type": "monthly"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["plan_type"] == "monthly"
        assert d["amount"] == 25000
        assert d["currency"] == "IQD"
        assert d["status"] == "active"
        assert d["start_date"] and d["end_date"]

    def test_invalid_plan(self, agent_session):
        s, _ = agent_session
        r = s.post(f"{API}/subscriptions", json={"plan_type": "weekly"})
        assert r.status_code == 400

    def test_unauthenticated_blocked(self):
        r = requests.post(f"{API}/subscriptions", json={"plan_type": "monthly"})
        assert r.status_code == 401


class TestSubscriptionsMe:
    def test_me_returns_own(self, agent_session):
        s, _ = agent_session
        s.post(f"{API}/subscriptions", json={"plan_type": "yearly"})
        r = s.get(f"{API}/subscriptions/me")
        assert r.status_code == 200
        subs = r.json()
        assert isinstance(subs, list) and len(subs) >= 1
        for sub in subs:
            assert sub["currency"] == "IQD"


# ---------- Properties + Governorate/District ----------
class TestPropertyLocation:
    def test_create_with_governorate_district(self, agent_session):
        s, _ = agent_session
        payload = _prop_payload(governorate="بغداد", district="الكرادة")
        r = s.post(f"{API}/properties", json=payload)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["governorate"] == "بغداد"
        assert d["district"] == "الكرادة"
        pid = d["id"]

        # GET verify persistence in Postgres
        r2 = requests.get(f"{API}/properties/{pid}")
        assert r2.status_code == 200
        assert r2.json()["governorate"] == "بغداد"
        assert r2.json()["district"] == "الكرادة"

        # cleanup
        s.delete(f"{API}/properties/{pid}")

    def test_update_governorate_district(self, agent_session):
        s, _ = agent_session
        payload = _prop_payload(governorate="بغداد", district="الكرادة")
        r = s.post(f"{API}/properties", json=payload)
        pid = r.json()["id"]

        payload["governorate"] = "البصرة"
        payload["district"] = "العشار"
        r2 = s.put(f"{API}/properties/{pid}", json=payload)
        assert r2.status_code == 200, r2.text
        assert r2.json()["governorate"] == "البصرة"
        assert r2.json()["district"] == "العشار"

        r3 = requests.get(f"{API}/properties/{pid}")
        assert r3.json()["governorate"] == "البصرة"
        assert r3.json()["district"] == "العشار"

        s.delete(f"{API}/properties/{pid}")

    def test_filter_by_governorate(self, agent_session):
        s, _ = agent_session
        marker_gov = f"TESTGOV_{uuid.uuid4().hex[:6]}"
        marker_dist = f"TESTDIST_{uuid.uuid4().hex[:6]}"
        # Create 2 properties: one matching, one not
        p1 = s.post(f"{API}/properties", json=_prop_payload(
            governorate=marker_gov, district=marker_dist, status="available")).json()
        p2 = s.post(f"{API}/properties", json=_prop_payload(
            governorate="NEG_GOV", district="NEG_DIST", status="available")).json()

        r = requests.get(f"{API}/properties",
                         params={"status": "available", "governorate": marker_gov, "limit": 100})
        assert r.status_code == 200
        ids = [p["id"] for p in r.json()]
        assert p1["id"] in ids
        assert p2["id"] not in ids
        for p in r.json():
            assert marker_gov.lower() in (p["governorate"] or "").lower()

        # District filter
        r2 = requests.get(f"{API}/properties",
                          params={"district": marker_dist, "limit": 100})
        ids2 = [p["id"] for p in r2.json()]
        assert p1["id"] in ids2
        assert p2["id"] not in ids2

        # Search endpoint
        r3 = requests.get(f"{API}/properties/search",
                          params={"governorate": marker_gov, "district": marker_dist})
        assert r3.status_code == 200
        ids3 = [p["id"] for p in r3.json()]
        assert p1["id"] in ids3

        s.delete(f"{API}/properties/{p1['id']}")
        s.delete(f"{API}/properties/{p2['id']}")

    def test_delete_permission(self, agent_session, second_agent_session):
        s, _ = agent_session
        s2 = second_agent_session
        # Create with agent 1
        r = s.post(f"{API}/properties", json=_prop_payload())
        pid = r.json()["id"]

        # Try delete with agent 2 -> 403
        r_forbid = s2.delete(f"{API}/properties/{pid}")
        assert r_forbid.status_code == 403

        # Owner can delete
        r_ok = s.delete(f"{API}/properties/{pid}")
        assert r_ok.status_code == 200

        # GET after delete -> 404
        r_missing = requests.get(f"{API}/properties/{pid}")
        assert r_missing.status_code == 404

    def test_admin_can_delete_any(self, agent_session, admin_session):
        s, _ = agent_session
        r = s.post(f"{API}/properties", json=_prop_payload())
        pid = r.json()["id"]
        r2 = admin_session.delete(f"{API}/properties/{pid}")
        assert r2.status_code == 200


# ---------- Admin Stats ----------
class TestAdminStats:
    def test_admin_stats_integer_counts(self, admin_session):
        r = admin_session.get(f"{API}/admin/stats")
        assert r.status_code == 200
        data = r.json()
        for k in ("total_properties", "available", "sold", "rented", "total_offices", "expiring_soon"):
            assert k in data
            assert isinstance(data[k], int), f"{k} not int: {type(data[k])}"

    def test_admin_stats_non_admin_forbidden(self, agent_session):
        s, _ = agent_session
        r = s.get(f"{API}/admin/stats")
        assert r.status_code == 403


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""Backend regression + data-isolation tests for Aqari (عقاراتي).

Iteration 2 focus:
- GET /api/properties, /api/properties/search, /api/properties/{id} now REQUIRE auth
- Non-admin agents see ONLY their own properties (list, get, search)
- Admin sees ALL properties across agents
- Cross-agent access returns 403 on GET/PUT/DELETE
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
    assert "access_token" in s.cookies
    return s


def _register_agent(name_prefix="TEST_agent"):
    s = requests.Session()
    email = f"{name_prefix}_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}@test.com"
    r = s.post(f"{API}/auth/register", json={
        "name": f"{name_prefix} {uuid.uuid4().hex[:4]}",
        "email": email,
        "password": "test1234",
        "office_name": f"TEST Office {uuid.uuid4().hex[:6]}",
    })
    assert r.status_code == 200, f"Register failed: {r.status_code} {r.text}"
    assert "access_token" in s.cookies
    return s, email


@pytest.fixture(scope="session")
def agent_session():
    return _register_agent("TEST_agentA")


@pytest.fixture(scope="session")
def second_agent_session():
    s, _ = _register_agent("TEST_agentB")
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


# ---------- Auth (regression) ----------
class TestAuth:
    def test_admin_login_sets_cookies(self):
        s = requests.Session()
        r = s.post(f"{API}/auth/login", json={"identifier": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        assert r.status_code == 200
        data = r.json()
        assert data["email"] == ADMIN_EMAIL
        assert data["role"] == "admin"
        assert "access_token" in s.cookies

    def test_login_invalid(self):
        r = requests.post(f"{API}/auth/login", json={"identifier": ADMIN_EMAIL, "password": "wrong"})
        assert r.status_code == 401

    def test_me_returns_admin(self, admin_session):
        r = admin_session.get(f"{API}/auth/me")
        assert r.status_code == 200
        assert r.json()["email"] == ADMIN_EMAIL

    def test_me_unauthenticated(self):
        r = requests.get(f"{API}/auth/me")
        assert r.status_code == 401

    def test_register_agent_creates_office(self):
        s = requests.Session()
        email = f"TEST_reg_{uuid.uuid4().hex[:8]}@test.com"
        office = f"TEST Office {uuid.uuid4().hex[:6]}"
        r = s.post(f"{API}/auth/register", json={
            "name": "TEST Register", "email": email,
            "password": "test1234", "office_name": office,
        })
        assert r.status_code == 200
        assert r.json()["office_name"] == office


# ---------- Subscriptions (regression) ----------
class TestSubscriptions:
    def test_plans(self):
        r = requests.get(f"{API}/subscriptions/plans")
        assert r.status_code == 200
        plans = {p["plan_type"]: p for p in r.json()}
        assert plans["monthly"]["amount"] == 25000
        assert plans["quarterly"]["amount"] == 65000
        assert plans["yearly"]["amount"] == 250000
        for p in plans.values():
            assert p["currency"] == "IQD"

    def test_create_monthly(self, agent_session):
        s, _ = agent_session
        r = s.post(f"{API}/subscriptions", json={"plan_type": "monthly"})
        assert r.status_code == 200
        d = r.json()
        assert d["amount"] == 25000 and d["status"] == "active"

    def test_invalid_plan(self, agent_session):
        s, _ = agent_session
        r = s.post(f"{API}/subscriptions", json={"plan_type": "weekly"})
        assert r.status_code == 400

    def test_sub_me_list(self, agent_session):
        s, _ = agent_session
        r = s.get(f"{API}/subscriptions/me")
        assert r.status_code == 200
        assert isinstance(r.json(), list)


# ---------- Property CRUD regression ----------
class TestPropertyCRUD:
    def test_create_and_get_own(self, agent_session):
        s, _ = agent_session
        r = s.post(f"{API}/properties", json=_prop_payload(governorate="بغداد", district="الكرادة"))
        assert r.status_code == 200
        pid = r.json()["id"]

        r2 = s.get(f"{API}/properties/{pid}")
        assert r2.status_code == 200
        assert r2.json()["governorate"] == "بغداد"

        s.delete(f"{API}/properties/{pid}")

    def test_update_own(self, agent_session):
        s, _ = agent_session
        pid = s.post(f"{API}/properties", json=_prop_payload()).json()["id"]
        payload = _prop_payload(governorate="البصرة", district="العشار")
        r = s.put(f"{API}/properties/{pid}", json=payload)
        assert r.status_code == 200
        assert r.json()["governorate"] == "البصرة"
        s.delete(f"{API}/properties/{pid}")


# ---------- NEW: Auth required on GET endpoints ----------
class TestPropertyEndpointsRequireAuth:
    def test_list_requires_auth(self):
        r = requests.get(f"{API}/properties")
        assert r.status_code == 401, f"Expected 401, got {r.status_code}: {r.text}"

    def test_search_requires_auth(self):
        r = requests.get(f"{API}/properties/search")
        assert r.status_code == 401

    def test_get_by_id_requires_auth(self, agent_session):
        s, _ = agent_session
        pid = s.post(f"{API}/properties", json=_prop_payload()).json()["id"]
        r = requests.get(f"{API}/properties/{pid}")
        assert r.status_code == 401
        s.delete(f"{API}/properties/{pid}")


# ---------- NEW: Data Isolation ----------
class TestDataIsolation:
    def test_agent_list_only_own_properties(self, agent_session, second_agent_session):
        """Agent A's GET /api/properties returns ONLY their own properties."""
        sA, _ = agent_session
        sB = second_agent_session

        # Agent B creates a property with unique governorate marker
        marker_gov = f"ISO_GOV_{uuid.uuid4().hex[:6]}"
        b_prop = sB.post(f"{API}/properties", json=_prop_payload(governorate=marker_gov)).json()
        b_pid = b_prop["id"]

        # Agent A creates their own property
        a_prop = sA.post(f"{API}/properties", json=_prop_payload(governorate=marker_gov)).json()
        a_pid = a_prop["id"]

        # Agent A lists - should see own, NOT B's
        r = sA.get(f"{API}/properties", params={"limit": 200})
        assert r.status_code == 200
        ids = [p["id"] for p in r.json()]
        assert a_pid in ids, "Agent A should see own property"
        assert b_pid not in ids, "Agent A must NOT see Agent B's property"
        # Every property returned must belong to A
        me_a = sA.get(f"{API}/auth/me").json()
        for p in r.json():
            assert p["agent_id"] == me_a["id"], f"Leak: property {p['id']} agent_id={p['agent_id']}"

        # Even with governorate filter matching B's property, A shouldn't see B's
        r2 = sA.get(f"{API}/properties", params={"governorate": marker_gov, "limit": 200})
        assert r2.status_code == 200
        ids2 = [p["id"] for p in r2.json()]
        assert b_pid not in ids2, "Governorate filter must not bypass isolation"
        assert a_pid in ids2

        # cleanup
        sA.delete(f"{API}/properties/{a_pid}")
        sB.delete(f"{API}/properties/{b_pid}")

    def test_agent_search_only_own(self, agent_session, second_agent_session):
        sA, _ = agent_session
        sB = second_agent_session
        marker_gov = f"ISO_SGOV_{uuid.uuid4().hex[:6]}"

        b_pid = sB.post(f"{API}/properties", json=_prop_payload(governorate=marker_gov)).json()["id"]
        a_pid = sA.post(f"{API}/properties", json=_prop_payload(governorate=marker_gov)).json()["id"]

        r = sA.get(f"{API}/properties/search", params={"governorate": marker_gov})
        assert r.status_code == 200
        ids = [p["id"] for p in r.json()]
        assert a_pid in ids
        assert b_pid not in ids, "Search must not leak other agents' properties"

        sA.delete(f"{API}/properties/{a_pid}")
        sB.delete(f"{API}/properties/{b_pid}")

    def test_admin_sees_all(self, agent_session, second_agent_session, admin_session):
        sA, _ = agent_session
        sB = second_agent_session
        marker_gov = f"ISO_ADMIN_{uuid.uuid4().hex[:6]}"

        a_pid = sA.post(f"{API}/properties", json=_prop_payload(governorate=marker_gov)).json()["id"]
        b_pid = sB.post(f"{API}/properties", json=_prop_payload(governorate=marker_gov)).json()["id"]

        r = admin_session.get(f"{API}/properties", params={"governorate": marker_gov, "limit": 200})
        assert r.status_code == 200
        ids = [p["id"] for p in r.json()]
        assert a_pid in ids and b_pid in ids, "Admin must see all agents' properties"

        # Admin search sees all too
        r2 = admin_session.get(f"{API}/properties/search", params={"governorate": marker_gov})
        ids2 = [p["id"] for p in r2.json()]
        assert a_pid in ids2 and b_pid in ids2

        sA.delete(f"{API}/properties/{a_pid}")
        sB.delete(f"{API}/properties/{b_pid}")

    def test_get_by_id_cross_agent_forbidden(self, agent_session, second_agent_session):
        sA, _ = agent_session
        sB = second_agent_session

        b_pid = sB.post(f"{API}/properties", json=_prop_payload()).json()["id"]

        # Agent A tries to view B's property -> 403
        r = sA.get(f"{API}/properties/{b_pid}")
        assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"

        sB.delete(f"{API}/properties/{b_pid}")

    def test_get_by_id_owner_ok(self, agent_session):
        sA, _ = agent_session
        pid = sA.post(f"{API}/properties", json=_prop_payload()).json()["id"]
        r = sA.get(f"{API}/properties/{pid}")
        assert r.status_code == 200
        assert r.json()["id"] == pid
        sA.delete(f"{API}/properties/{pid}")

    def test_get_by_id_admin_any(self, agent_session, admin_session):
        sA, _ = agent_session
        pid = sA.post(f"{API}/properties", json=_prop_payload()).json()["id"]
        r = admin_session.get(f"{API}/properties/{pid}")
        assert r.status_code == 200
        assert r.json()["id"] == pid
        sA.delete(f"{API}/properties/{pid}")

    def test_update_cross_agent_forbidden(self, agent_session, second_agent_session):
        sA, _ = agent_session
        sB = second_agent_session
        b_pid = sB.post(f"{API}/properties", json=_prop_payload()).json()["id"]
        r = sA.put(f"{API}/properties/{b_pid}", json=_prop_payload(price=1))
        assert r.status_code == 403
        sB.delete(f"{API}/properties/{b_pid}")

    def test_delete_cross_agent_forbidden(self, agent_session, second_agent_session):
        sA, _ = agent_session
        sB = second_agent_session
        b_pid = sB.post(f"{API}/properties", json=_prop_payload()).json()["id"]
        r = sA.delete(f"{API}/properties/{b_pid}")
        assert r.status_code == 403
        # Confirm still exists (B can still see it)
        r2 = sB.get(f"{API}/properties/{b_pid}")
        assert r2.status_code == 200
        sB.delete(f"{API}/properties/{b_pid}")


# ---------- Filtering regression (using own session) ----------
class TestPropertyFiltering:
    def test_filter_governorate_and_district(self, agent_session):
        s, _ = agent_session
        marker_gov = f"FLT_GOV_{uuid.uuid4().hex[:6]}"
        marker_dist = f"FLT_DIST_{uuid.uuid4().hex[:6]}"
        p1 = s.post(f"{API}/properties", json=_prop_payload(
            governorate=marker_gov, district=marker_dist)).json()
        p2 = s.post(f"{API}/properties", json=_prop_payload(
            governorate="NEG_GOV", district="NEG_DIST")).json()

        r = s.get(f"{API}/properties", params={"governorate": marker_gov, "limit": 100})
        assert r.status_code == 200
        ids = [p["id"] for p in r.json()]
        assert p1["id"] in ids and p2["id"] not in ids

        r2 = s.get(f"{API}/properties/search", params={"governorate": marker_gov, "district": marker_dist})
        assert r2.status_code == 200
        assert p1["id"] in [p["id"] for p in r2.json()]

        s.delete(f"{API}/properties/{p1['id']}")
        s.delete(f"{API}/properties/{p2['id']}")


# ---------- Admin Stats (regression) ----------
class TestAdminStats:
    def test_admin_stats_integer_counts(self, admin_session):
        r = admin_session.get(f"{API}/admin/stats")
        assert r.status_code == 200
        data = r.json()
        for k in ("total_properties", "available", "sold", "rented", "total_offices", "expiring_soon"):
            assert isinstance(data[k], int)

    def test_admin_stats_non_admin_forbidden(self, agent_session):
        s, _ = agent_session
        r = s.get(f"{API}/admin/stats")
        assert r.status_code == 403


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""Backend regression tests for Aqari Al-Muyassar - subscriptions, properties, admin"""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://elder-property.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@aqari.com"
ADMIN_PASSWORD = "admin123"


# ---------- Fixtures ----------
@pytest.fixture(scope="session")
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"identifier": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="session")
def agent_session():
    s = requests.Session()
    email = f"TEST_agent_{int(time.time())}_{uuid.uuid4().hex[:6]}@test.com"
    r = s.post(f"{API}/auth/register", json={
        "name": "TEST Agent",
        "email": email,
        "password": "test1234",
        "office_name": "TEST Office",
    })
    assert r.status_code == 200, f"Register failed: {r.status_code} {r.text}"
    return s, email


# ---------- Subscriptions ----------
class TestSubscriptionPlans:
    def test_get_plans_returns_three(self):
        r = requests.get(f"{API}/subscriptions/plans")
        assert r.status_code == 200
        plans = r.json()
        assert isinstance(plans, list)
        assert len(plans) == 3
        by_type = {p["plan_type"]: p for p in plans}
        assert by_type["monthly"]["amount"] == 25000
        assert by_type["monthly"]["currency"] == "IQD"
        assert by_type["monthly"]["days"] == 30
        assert by_type["quarterly"]["amount"] == 65000
        assert by_type["quarterly"]["days"] == 90
        assert by_type["yearly"]["amount"] == 250000
        assert by_type["yearly"]["days"] == 365


class TestCreateSubscription:
    def test_create_monthly(self, agent_session):
        s, _ = agent_session
        r = s.post(f"{API}/subscriptions", json={"plan_type": "monthly"})
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["plan_type"] == "monthly"
        assert data["amount"] == 25000
        assert data["currency"] == "IQD"
        assert data["status"] == "active"
        assert data["start_date"] and data["end_date"]

    def test_invalid_plan_type(self, agent_session):
        s, _ = agent_session
        r = s.post(f"{API}/subscriptions", json={"plan_type": "weekly"})
        assert r.status_code == 400

    def test_unauthenticated_blocked(self):
        r = requests.post(f"{API}/subscriptions", json={"plan_type": "monthly"})
        assert r.status_code == 401


class TestSubscriptionsMe:
    def test_me_returns_own_subs(self, agent_session):
        s, _ = agent_session
        # Create yearly
        r = s.post(f"{API}/subscriptions", json={"plan_type": "yearly"})
        assert r.status_code == 200
        r = s.get(f"{API}/subscriptions/me")
        assert r.status_code == 200
        subs = r.json()
        assert isinstance(subs, list)
        assert len(subs) >= 1
        for sub in subs:
            assert sub["currency"] == "IQD"


class TestAdminSubscriptions:
    def test_admin_can_list_all(self, admin_session):
        r = admin_session.get(f"{API}/admin/subscriptions")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_non_admin_forbidden(self, agent_session):
        s, _ = agent_session
        r = s.get(f"{API}/admin/subscriptions")
        assert r.status_code == 403

    def test_expiring_endpoint(self, admin_session):
        r = admin_session.get(f"{API}/admin/subscriptions/expiring")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_expiring_non_admin_forbidden(self, agent_session):
        s, _ = agent_session
        r = s.get(f"{API}/admin/subscriptions/expiring")
        assert r.status_code == 403


# ---------- Properties (owner_name) ----------
class TestPropertyOwnerName:
    def test_create_requires_owner_name(self, agent_session):
        s, _ = agent_session
        payload = {
            "total_area": 200,
            "price": 50000000,
            "front_width": 10,
            "length": 20,
            "bedrooms": 3,
            "bathrooms": 2,
            "owner_phone": "07700000000",
            # owner_name intentionally missing
            "status": "available",
        }
        r = s.post(f"{API}/properties", json=payload)
        assert r.status_code == 422, f"Expected 422 missing owner_name, got {r.status_code} {r.text}"

    def test_create_with_owner_name_and_persistence(self, agent_session):
        s, _ = agent_session
        payload = {
            "total_area": 150,
            "price": 30000000,
            "front_width": 8,
            "length": 18,
            "bedrooms": 2,
            "bathrooms": 1,
            "owner_name": "TEST مالك",
            "owner_phone": "07711111111",
            "status": "available",
        }
        r = s.post(f"{API}/properties", json=payload)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["owner_name"] == "TEST مالك"
        pid = data["id"]

        # GET verify persistence
        r2 = s.get(f"{API}/properties/{pid}")
        assert r2.status_code == 200
        assert r2.json()["owner_name"] == "TEST مالك"

        # PUT update owner_name
        payload["owner_name"] = "TEST مالك جديد"
        payload["status"] = "sold"
        r3 = s.put(f"{API}/properties/{pid}", json=payload)
        assert r3.status_code == 200
        assert r3.json()["owner_name"] == "TEST مالك جديد"
        assert r3.json()["status"] == "sold"

        # cleanup
        s.delete(f"{API}/properties/{pid}")

    def test_filter_by_status(self, agent_session):
        s, _ = agent_session
        # Create one of each
        ids = []
        for status in ["available", "sold", "rented"]:
            payload = {
                "total_area": 100, "price": 10000000, "front_width": 10, "length": 10,
                "bedrooms": 2, "bathrooms": 1,
                "owner_name": f"TEST owner {status}",
                "owner_phone": "07722222222", "status": status,
            }
            r = s.post(f"{API}/properties", json=payload)
            assert r.status_code == 200
            ids.append(r.json()["id"])

        r = requests.get(f"{API}/properties?status=available&limit=100")
        assert r.status_code == 200
        for p in r.json():
            assert p["status"] == "available"

        r = requests.get(f"{API}/properties?status=sold&limit=100")
        assert r.status_code == 200
        for p in r.json():
            assert p["status"] == "sold"

        # cleanup
        for pid in ids:
            s.delete(f"{API}/properties/{pid}")


# ---------- Admin Stats ----------
class TestAdminStats:
    def test_admin_stats_has_expiring_soon(self, admin_session):
        r = admin_session.get(f"{API}/admin/stats")
        assert r.status_code == 200
        data = r.json()
        for k in ("total_properties", "available", "sold", "rented", "total_offices", "expiring_soon"):
            assert k in data, f"Missing key {k}"
        assert isinstance(data["expiring_soon"], int)

    def test_admin_stats_non_admin_forbidden(self, agent_session):
        s, _ = agent_session
        r = s.get(f"{API}/admin/stats")
        assert r.status_code == 403


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

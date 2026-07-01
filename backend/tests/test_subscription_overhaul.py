"""Iteration 3: Subscription system overhaul tests.

Covers:
- Public /api/subscriptions/plans excludes trial and has yearly=275000
- Admin-only /api/admin/subscriptions/plans includes trial
- POST /api/subscriptions is admin-only, accepts user_id
- GET /api/subscriptions/status returns active/warning/expired/none appropriately
- POST/PUT /api/properties blocked with 402 for agents with no active subscription
- GET /api/properties allowed even when expired
- DELETE /api/subscriptions/{id} admin-only
- GET /api/admin/users admin-only
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


# ---------- Helpers ----------
def _register_agent(prefix="TEST_subagent"):
    s = requests.Session()
    email = f"{prefix}_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}@test.com"
    r = s.post(f"{API}/auth/register", json={
        "name": f"{prefix} {uuid.uuid4().hex[:4]}",
        "email": email,
        "password": "test1234",
        "office_name": f"TEST Office {uuid.uuid4().hex[:6]}",
    })
    assert r.status_code == 200, f"register failed: {r.status_code} {r.text}"
    me = s.get(f"{API}/auth/me").json()
    return s, email, me["id"]


def _prop_payload(**overrides):
    payload = {
        "total_area": 200, "price": 50000000,
        "front_width": 10, "length": 20,
        "bedrooms": 3, "bathrooms": 2,
        "owner_name": "TEST", "owner_phone": "07700000000",
        "status": "available",
        "governorate": "بغداد", "district": "الكرادة",
    }
    payload.update(overrides)
    return payload


# ---------- Fixtures ----------
@pytest.fixture(scope="session")
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"identifier": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200
    return s


@pytest.fixture(scope="session")
def fresh_agent():
    """Fresh agent WITHOUT any subscription (used for expired-state tests)."""
    return _register_agent("TEST_expiredagent")


@pytest.fixture(scope="session")
def trial_agent(admin_session):
    """Fresh agent granted a trial (7-day) subscription — should be 'warning'."""
    s, email, uid = _register_agent("TEST_trialagent")
    r = admin_session.post(f"{API}/subscriptions",
                           json={"plan_type": "trial", "user_id": uid})
    assert r.status_code == 200, f"trial grant failed: {r.status_code} {r.text}"
    return s, email, uid, r.json()["id"]


@pytest.fixture(scope="session")
def yearly_agent(admin_session):
    """Fresh agent granted a yearly subscription — should be 'active' >7d."""
    s, email, uid = _register_agent("TEST_yearlyagent")
    r = admin_session.post(f"{API}/subscriptions",
                           json={"plan_type": "yearly", "user_id": uid})
    assert r.status_code == 200
    return s, email, uid, r.json()["id"]


# ---------- Cleanup: delete subs after session ----------
_CREATED_SUB_IDS = []


@pytest.fixture(scope="session", autouse=True)
def _cleanup(admin_session, trial_agent, yearly_agent):
    _CREATED_SUB_IDS.extend([trial_agent[3], yearly_agent[3]])
    yield
    for sid in _CREATED_SUB_IDS:
        try:
            admin_session.delete(f"{API}/subscriptions/{sid}")
        except Exception:
            pass


# ---------- 1. Public plans ----------
class TestPublicPlans:
    def test_public_plans_exclude_trial_and_have_correct_prices(self):
        r = requests.get(f"{API}/subscriptions/plans")
        assert r.status_code == 200
        plans = r.json()
        assert len(plans) == 3, f"Expected exactly 3 public plans, got {len(plans)}"
        by_type = {p["plan_type"]: p for p in plans}
        assert set(by_type.keys()) == {"monthly", "quarterly", "yearly"}
        assert "trial" not in by_type
        assert by_type["monthly"]["amount"] == 25000
        assert by_type["quarterly"]["amount"] == 65000
        assert by_type["yearly"]["amount"] == 275000, \
            f"Yearly must be 275000 (was 250000). Got {by_type['yearly']['amount']}"
        for p in plans:
            assert p["currency"] == "IQD"


# ---------- 2. Admin plans (includes trial) ----------
class TestAdminPlans:
    def test_admin_plans_requires_auth(self):
        r = requests.get(f"{API}/admin/subscriptions/plans")
        assert r.status_code == 401

    def test_admin_plans_forbidden_for_agent(self, fresh_agent):
        s, _, _ = fresh_agent
        r = s.get(f"{API}/admin/subscriptions/plans")
        assert r.status_code == 403

    def test_admin_plans_returns_4_including_trial(self, admin_session):
        r = admin_session.get(f"{API}/admin/subscriptions/plans")
        assert r.status_code == 200
        plans = r.json()
        assert len(plans) == 4
        by_type = {p["plan_type"]: p for p in plans}
        assert "trial" in by_type
        assert by_type["trial"]["amount"] == 0
        assert by_type["trial"]["days"] == 7
        assert by_type["yearly"]["amount"] == 275000


# ---------- 3. POST /subscriptions admin-only ----------
class TestSubscriptionCreation:
    def test_agent_cannot_create_subscription(self, fresh_agent):
        s, _, _ = fresh_agent
        r = s.post(f"{API}/subscriptions", json={"plan_type": "monthly"})
        assert r.status_code == 403
        assert "فقط المدير" in r.json().get("detail", "")

    def test_admin_grant_trial_to_agent(self, admin_session):
        _, _, uid = _register_agent("TEST_grantee_trial")
        r = admin_session.post(f"{API}/subscriptions",
                               json={"plan_type": "trial", "user_id": uid})
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["plan_type"] == "trial"
        assert data["amount"] == 0
        assert data["user_id"] == uid
        # end_date approximately 7 days out
        from datetime import datetime
        end = datetime.fromisoformat(data["end_date"].replace("Z", "+00:00"))
        start = datetime.fromisoformat(data["start_date"].replace("Z", "+00:00"))
        diff_days = (end - start).days
        assert 6 <= diff_days <= 7, f"trial diff was {diff_days}"
        _CREATED_SUB_IDS.append(data["id"])

    def test_admin_grant_yearly_to_agent(self, admin_session):
        _, _, uid = _register_agent("TEST_grantee_year")
        r = admin_session.post(f"{API}/subscriptions",
                               json={"plan_type": "yearly", "user_id": uid})
        assert r.status_code == 200
        d = r.json()
        assert d["amount"] == 275000
        assert d["plan_type"] == "yearly"
        from datetime import datetime
        end = datetime.fromisoformat(d["end_date"].replace("Z", "+00:00"))
        start = datetime.fromisoformat(d["start_date"].replace("Z", "+00:00"))
        diff = (end - start).days
        assert 364 <= diff <= 365
        _CREATED_SUB_IDS.append(d["id"])

    def test_admin_invalid_plan_type(self, admin_session):
        r = admin_session.post(f"{API}/subscriptions", json={"plan_type": "bogus"})
        assert r.status_code == 400

    def test_admin_grant_nonexistent_user(self, admin_session):
        r = admin_session.post(f"{API}/subscriptions",
                               json={"plan_type": "monthly", "user_id": str(uuid.uuid4())})
        assert r.status_code == 404


# ---------- 4. GET /subscriptions/status ----------
class TestSubscriptionStatus:
    def test_status_unauthenticated(self):
        r = requests.get(f"{API}/subscriptions/status")
        assert r.status_code == 401

    def test_status_admin_active(self, admin_session):
        r = admin_session.get(f"{API}/subscriptions/status")
        assert r.status_code == 200
        d = r.json()
        assert d["has_active"] is True
        assert d["status"] == "active"

    def test_status_agent_no_sub_expired(self, fresh_agent):
        s, _, _ = fresh_agent
        r = s.get(f"{API}/subscriptions/status")
        assert r.status_code == 200
        d = r.json()
        assert d["has_active"] is False
        assert d["status"] == "expired"

    def test_status_yearly_agent_active_gt_7d(self, yearly_agent):
        s, _, _, _ = yearly_agent
        r = s.get(f"{API}/subscriptions/status")
        assert r.status_code == 200
        d = r.json()
        assert d["has_active"] is True
        assert d["status"] == "active"
        assert d["days_remaining"] > 7

    def test_status_trial_agent_warning_lte_7d(self, trial_agent):
        s, _, _, _ = trial_agent
        r = s.get(f"{API}/subscriptions/status")
        assert r.status_code == 200
        d = r.json()
        assert d["has_active"] is True
        assert d["status"] == "warning", f"Expected warning; got {d}"
        assert d["days_remaining"] <= 7


# ---------- 5. Property mutation gated by subscription ----------
class TestPropertyMutationGate:
    def test_agent_expired_post_property_returns_402(self, fresh_agent):
        s, _, _ = fresh_agent
        r = s.post(f"{API}/properties", json=_prop_payload())
        assert r.status_code == 402
        assert "انتهى اشتراكك" in r.json().get("detail", "")

    def test_agent_expired_get_properties_still_allowed(self, fresh_agent):
        s, _, _ = fresh_agent
        r = s.get(f"{API}/properties")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_admin_post_property_no_sub_needed(self, admin_session):
        r = admin_session.post(f"{API}/properties", json=_prop_payload(owner_name="TEST_adminprop"))
        assert r.status_code == 200
        pid = r.json()["id"]
        admin_session.delete(f"{API}/properties/{pid}")

    def test_trial_agent_can_post_property(self, trial_agent):
        s, _, _, _ = trial_agent
        r = s.post(f"{API}/properties", json=_prop_payload(owner_name="TEST_trialprop"))
        assert r.status_code == 200, f"Trial agent should be allowed: {r.status_code} {r.text}"
        pid = r.json()["id"]
        # cleanup
        s.delete(f"{API}/properties/{pid}")

    def test_expired_agent_put_property_returns_402(self, admin_session, fresh_agent):
        # Admin creates a property owned by admin, then re-owner to fresh_agent won't work.
        # Instead: use trial_agent to create, then let it expire? We simulate by having
        # a fresh agent try to PUT any property id (they don't own any) — but PUT checks
        # subscription BEFORE ownership. So we create a property as admin and try PUT as
        # fresh_agent — should still hit 402 first (before 403 ownership).
        admin_r = admin_session.post(f"{API}/properties", json=_prop_payload(owner_name="TEST_forput"))
        assert admin_r.status_code == 200
        pid = admin_r.json()["id"]
        try:
            s, _, _ = fresh_agent
            r = s.put(f"{API}/properties/{pid}", json=_prop_payload(owner_name="TEST_put_attempt"))
            assert r.status_code == 402, \
                f"Expected 402 for expired agent PUT, got {r.status_code} {r.text}"
        finally:
            admin_session.delete(f"{API}/properties/{pid}")


# ---------- 6. DELETE /subscriptions/{id} ----------
class TestDeleteSubscription:
    def test_delete_forbidden_for_agent(self, fresh_agent, admin_session):
        _, _, uid = _register_agent("TEST_delvictim")
        r = admin_session.post(f"{API}/subscriptions",
                               json={"plan_type": "monthly", "user_id": uid})
        assert r.status_code == 200
        sid = r.json()["id"]
        try:
            s, _, _ = fresh_agent
            r2 = s.delete(f"{API}/subscriptions/{sid}")
            assert r2.status_code == 403
        finally:
            admin_session.delete(f"{API}/subscriptions/{sid}")

    def test_delete_admin_success(self, admin_session):
        _, _, uid = _register_agent("TEST_delok")
        r = admin_session.post(f"{API}/subscriptions",
                               json={"plan_type": "monthly", "user_id": uid})
        sid = r.json()["id"]
        r2 = admin_session.delete(f"{API}/subscriptions/{sid}")
        assert r2.status_code == 200

    def test_delete_missing_id_404(self, admin_session):
        r = admin_session.delete(f"{API}/subscriptions/{uuid.uuid4()}")
        assert r.status_code == 404


# ---------- 7. GET /admin/users ----------
class TestAdminUsers:
    def test_admin_users_forbidden_for_agent(self, fresh_agent):
        s, _, _ = fresh_agent
        r = s.get(f"{API}/admin/users")
        assert r.status_code == 403

    def test_admin_users_unauthenticated(self):
        r = requests.get(f"{API}/admin/users")
        assert r.status_code == 401

    def test_admin_users_returns_list(self, admin_session, fresh_agent):
        r = admin_session.get(f"{API}/admin/users")
        assert r.status_code == 200
        users = r.json()
        assert isinstance(users, list) and len(users) >= 2
        u0 = users[0]
        # Contract check: fields present
        for k in ("id", "name", "email", "role", "office_name"):
            assert k in u0
        # our fresh agent should be present
        _, femail, _ = fresh_agent
        emails = [u["email"] for u in users if u.get("email")]
        assert femail.lower() in emails


# ---------- 8. Regression ----------
class TestRegression:
    def test_auth_me_admin(self, admin_session):
        r = admin_session.get(f"{API}/auth/me")
        assert r.status_code == 200 and r.json()["role"] == "admin"

    def test_admin_stats(self, admin_session):
        r = admin_session.get(f"{API}/admin/stats")
        assert r.status_code == 200
        for k in ("total_properties", "available", "sold", "rented",
                  "total_offices", "expiring_soon"):
            assert k in r.json()

    def test_admin_offices(self, admin_session):
        r = admin_session.get(f"{API}/admin/offices")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_subscriptions_me(self, trial_agent):
        s, _, _, _ = trial_agent
        r = s.get(f"{API}/subscriptions/me")
        assert r.status_code == 200
        assert len(r.json()) >= 1
        assert r.json()[0]["plan_type"] == "trial"

    def test_properties_list_agent_scoping(self, yearly_agent, admin_session):
        s, _, _, _ = yearly_agent
        pcreate = s.post(f"{API}/properties", json=_prop_payload(owner_name="TEST_yr"))
        assert pcreate.status_code == 200
        pid = pcreate.json()["id"]
        try:
            r = s.get(f"{API}/properties")
            assert r.status_code == 200
            ids = [p["id"] for p in r.json()]
            assert pid in ids
        finally:
            s.delete(f"{API}/properties/{pid}")

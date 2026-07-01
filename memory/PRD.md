# عقاراتي (Aqarati) - PRD

## Problem Statement
Integrate Supabase Postgres as primary database (replacing MongoDB). Add `governorate` and `district` columns to properties for location-based filtering. Update add-property form and search filters to include these two fields. Change app name to "عقاراتي".

## Architecture
- **Backend**: FastAPI + SQLAlchemy 2.0 (async) + asyncpg
- **Database**: Supabase Postgres (Transaction Pooler, port 6543, `statement_cache_size=0`)
- **Auth**: JWT (HTTP-only cookies) - custom (not Supabase Auth)
- **Storage**: Emergent Object Storage
- **Frontend**: React 19 + Tailwind + shadcn/ui (RTL, Arabic)

## Tables (Supabase)
- `users` (id text, office_id uuid, email, phone, name, role, password_hash, created_at)
- `offices` (id uuid, office_name text, phone_number text)
- `properties` (id text, total_area, price, front_width, length, bedrooms, bathrooms, owner_name, owner_phone, images jsonb, status, agent_id, agent_name, created_at, **governorate text, district text**)
- `subscriptions` (id text, user_id, user_name, office_name, plan_type, amount, currency, start_date, end_date, status, created_at)
- `files` (id text, storage_path, original_filename, content_type, size, user_id, is_deleted, created_at)

## Implemented (2026-07-01)
- Migrated backend from MongoDB (motor) to Supabase Postgres (SQLAlchemy async)
- Added `governorate` and `district` fields to Property model + all CRUD endpoints
- `GET /api/properties` and `GET /api/properties/search` accept `governorate` and `district` query params (case-insensitive ILIKE partial match)
- Frontend AddProperty wizard: added new step 2 "الموقع" with governorate & district text inputs (free-text)
- Frontend EditProperty: added governorate & district editable fields
- Frontend PropertyListPage: added location filter inputs (governorate & district) + display location badge on cards + search bar matches location text
- Frontend PropertyDetails: shows governorate & district tiles
- Renamed app to "عقاراتي" in header, auth page, and browser title
- Backend tests: 17/17 pass (JWT auth, property CRUD, location filter, admin stats, subscription plans)

## Iteration 3 (2026-07-01) — Subscription Overhaul
- **Admin-only subscription mutations**: `POST /api/subscriptions` restricted to admin (403 for agents); can grant plan to any user via optional `user_id` in body. `DELETE /api/subscriptions/{id}` admin-only.
- **New plan structure & pricing**: monthly=25000, quarterly=65000, **yearly=275000** (bumped from 250000), plus admin-only `trial` (0 IQD, 7 days).
- `GET /api/subscriptions/plans` returns 3 public plans (trial excluded).
- `GET /api/admin/subscriptions/plans` admin-only, returns all 4 plans.
- `GET /api/admin/users` admin-only, returns all users with office_name (for subscription assignment picker).
- `GET /api/subscriptions/status` — new endpoint returning `{has_active, days_remaining, end_date, plan_type, status}` where status ∈ `active|warning|expired`. Admin always `active`.
- **Expiry-gated property mutations**: `POST` / `PUT /api/properties` now returns **HTTP 402** with `"انتهى اشتراكك — تواصل معنا للتجديد"` for agents with no active sub. Admin bypasses. GET still works.
- Frontend: added persistent `<ContactFooter>` (WhatsApp + Instagram) on every authenticated page.
- Frontend: added `<SubscriptionBanner>` (yellow warning if ≤7 days, red expired) on Dashboard / AddProperty / Subscriptions pages.
- Frontend: `/subscriptions` page rebuilt — plan cards open `https://wa.me/7760307768?text=اود بتجديد الاشتراك باقة [PLAN_NAME]` in a new tab (no self-activation).
- Frontend: AddProperty blocked with a red "لا يمكنك إضافة عقارات" screen + WhatsApp CTA when agent's sub is expired.
- Frontend: AdminDashboard gained a "تفعيل اشتراك لمكتب" panel (user picker + plan picker including trial) + delete button on each subscription row.
- Backend tests: **30/30 pass (100%)**.

## Iteration 2 (2026-07-01)
- Moved "Made with Emergent" watermark to **top-right corner** (`top:16px; right:16px`) so it never overlaps buttons/inputs
- **Data isolation between offices/agents**:
  - `GET /api/properties`, `/properties/search`, `/properties/{id}` now require authentication
  - Non-admin agents see ONLY their own properties (filter `agent_id == current_user.id`)
  - Cross-agent GET/PUT/DELETE returns 403
  - Admin role bypasses all scoping and sees ALL properties from all agents
- Backend tests: 25/25 pass (100%) — full regression + isolation coverage

## Test Credentials
- Admin: admin@aqari.com / admin123 (see /app/memory/test_credentials.md)

## Backlog / Future
- P1: Dropdown of Iraqi governorates + districts (currently free text as requested)
- P1: Map view for properties by location
- P2: Popular locations analytics for admin
- P2: Migrate Emergent object storage → Supabase Storage
- P2: Add unit tests for office find-or-create logic during registration

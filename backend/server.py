from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, UploadFile, File, Depends
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
from pathlib import Path
from pydantic import BaseModel
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
import bcrypt
import jwt
import requests

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database import AsyncSessionLocal, engine, get_db
from models import User, Property, Subscription, FileRecord, Office

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

app = FastAPI()
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

JWT_ALGORITHM = "HS256"
JWT_SECRET = os.environ.get("JWT_SECRET", "your-secret-key-change-in-production")

STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")
APP_NAME = "aqari-almuyassar"
storage_key = None


# ---------- Password ----------
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# ---------- JWT ----------
def create_access_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id, "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
        "type": "access",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
        "type": "refresh",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        result = await db.execute(select(User).where(User.id == payload["sub"]))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ---------- Object Storage ----------
def init_storage():
    global storage_key
    if storage_key:
        return storage_key
    try:
        resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_KEY}, timeout=30)
        resp.raise_for_status()
        storage_key = resp.json()["storage_key"]
        logger.info("Storage initialized")
        return storage_key
    except Exception as e:
        logger.error(f"Storage init failed: {e}")
        return None


def put_object(path: str, data: bytes, content_type: str) -> dict:
    key = init_storage()
    if not key:
        raise HTTPException(status_code=500, detail="Storage not initialized")
    resp = requests.put(f"{STORAGE_URL}/objects/{path}",
                        headers={"X-Storage-Key": key, "Content-Type": content_type},
                        data=data, timeout=120)
    resp.raise_for_status()
    return resp.json()


def get_object(path: str) -> tuple:
    key = init_storage()
    if not key:
        raise HTTPException(status_code=500, detail="Storage not initialized")
    resp = requests.get(f"{STORAGE_URL}/objects/{path}",
                        headers={"X-Storage-Key": key}, timeout=60)
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")


# ---------- Pydantic Schemas ----------
class UserRegister(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    password: str
    office_name: Optional[str] = None


class UserLogin(BaseModel):
    identifier: str
    password: str


class UserResponse(BaseModel):
    id: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    role: str
    office_name: Optional[str] = None
    created_at: str


class PropertyCreate(BaseModel):
    total_area: float
    price: float
    front_width: float
    length: float
    bedrooms: int
    bathrooms: int
    owner_name: Optional[str] = ""
    owner_phone: str
    images: Optional[List[str]] = []
    status: str = "available"
    governorate: Optional[str] = None
    district: Optional[str] = None


class PropertyResponse(BaseModel):
    id: str
    total_area: float
    price: float
    front_width: float
    length: float
    bedrooms: int
    bathrooms: int
    owner_name: Optional[str] = ""
    owner_phone: str
    images: List[str]
    status: str
    agent_id: str
    agent_name: str
    created_at: str
    governorate: Optional[str] = None
    district: Optional[str] = None


class SubscriptionPlan(BaseModel):
    plan_type: str
    user_id: Optional[str] = None  # admin can assign to any user; if omitted, defaults to admin themselves


class SubscriptionStatusResponse(BaseModel):
    has_active: bool
    days_remaining: Optional[int] = None
    end_date: Optional[str] = None
    plan_type: Optional[str] = None
    status: str  # "active", "warning" (<=7d), "expired", "none"


class SubscriptionResponse(BaseModel):
    id: str
    user_id: str
    user_name: str
    office_name: Optional[str] = None
    plan_type: str
    amount: int
    currency: str
    start_date: str
    end_date: str
    status: str
    created_at: str


class AdminStats(BaseModel):
    total_properties: int
    available: int
    sold: int
    rented: int
    total_offices: int
    expiring_soon: int


PLAN_PRICING = {
    "monthly": {"amount": 25000, "days": 30, "label": "شهري"},
    "quarterly": {"amount": 65000, "days": 90, "label": "ربع سنوي"},
    "yearly": {"amount": 275000, "days": 365, "label": "سنوي"},
    "trial": {"amount": 0, "days": 7, "label": "تجربة مجانية - 7 أيام"},
}

# Plans exposed to non-admin offices (excludes trial)
PUBLIC_PLAN_KEYS = ["monthly", "quarterly", "yearly"]


# ---------- Serializers ----------
async def user_to_response(user: User, db: AsyncSession) -> UserResponse:
    office_name = None
    if user.office_id:
        result = await db.execute(select(Office).where(Office.id == user.office_id))
        office = result.scalar_one_or_none()
        if office:
            office_name = office.office_name
    return UserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        phone=user.phone,
        role=user.role,
        office_name=office_name,
        created_at=user.created_at.isoformat() if user.created_at else "",
    )


def prop_to_response(p: Property) -> PropertyResponse:
    return PropertyResponse(
        id=p.id, total_area=p.total_area, price=p.price,
        front_width=p.front_width, length=p.length,
        bedrooms=p.bedrooms, bathrooms=p.bathrooms,
        owner_name=p.owner_name or "", owner_phone=p.owner_phone,
        images=p.images or [], status=p.status,
        agent_id=p.agent_id, agent_name=p.agent_name,
        created_at=p.created_at.isoformat() if p.created_at else "",
        governorate=p.governorate, district=p.district,
    )


def sub_to_response(s: Subscription) -> SubscriptionResponse:
    return SubscriptionResponse(
        id=s.id, user_id=s.user_id, user_name=s.user_name,
        office_name=s.office_name, plan_type=s.plan_type,
        amount=s.amount, currency=s.currency,
        start_date=s.start_date.isoformat() if s.start_date else "",
        end_date=s.end_date.isoformat() if s.end_date else "",
        status=s.status,
        created_at=s.created_at.isoformat() if s.created_at else "",
    )


# ---------- Admin Seed ----------
async def seed_admin():
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@aqari.com")
    admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == admin_email))
        existing = result.scalar_one_or_none()
        if existing is None:
            admin = User(
                id=str(uuid.uuid4()),
                email=admin_email,
                name="المدير العام",
                role="admin",
                password_hash=hash_password(admin_password),
                created_at=datetime.now(timezone.utc),
            )
            db.add(admin)
            await db.commit()
            logger.info(f"Admin created: {admin_email}")
        elif not verify_password(admin_password, existing.password_hash):
            existing.password_hash = hash_password(admin_password)
            await db.commit()
            logger.info("Admin password updated")

    Path("/app/memory").mkdir(exist_ok=True)
    with open("/app/memory/test_credentials.md", "w", encoding="utf-8") as f:
        f.write("# Test Credentials\n\n## Admin Account\n")
        f.write(f"- Email: {admin_email}\n- Password: {admin_password}\n- Role: admin\n\n")
        f.write("## Database\n- Supabase Postgres (Transaction Pooler)\n")


# ---------- Auth ----------
def _set_cookies(response: Response, access_token: str, refresh_token: str):
    response.set_cookie(key="access_token", value=access_token,
                        httponly=True, secure=False, samesite="lax",
                        max_age=900, path="/")
    response.set_cookie(key="refresh_token", value=refresh_token,
                        httponly=True, secure=False, samesite="lax",
                        max_age=604800, path="/")


@api_router.post("/auth/register", response_model=UserResponse)
async def register(user: UserRegister, response: Response, db: AsyncSession = Depends(get_db)):
    if not user.email and not user.phone:
        raise HTTPException(status_code=400, detail="يجب إدخال البريد الإلكتروني أو رقم الهاتف")

    conds = []
    if user.email:
        conds.append(User.email == user.email.lower())
    if user.phone:
        conds.append(User.phone == user.phone)
    from sqlalchemy import or_
    result = await db.execute(select(User).where(or_(*conds)))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="المستخدم موجود بالفعل")

    # Office: find-or-create
    office_id = None
    if user.office_name:
        result = await db.execute(select(Office).where(Office.office_name == user.office_name))
        office = result.scalar_one_or_none()
        if not office:
            office = Office(id=uuid.uuid4(), office_name=user.office_name, phone_number=user.phone)
            db.add(office)
            await db.flush()
        office_id = office.id

    user_id = str(uuid.uuid4())
    new_user = User(
        id=user_id,
        name=user.name,
        email=user.email.lower() if user.email else None,
        phone=user.phone,
        role="agent",
        password_hash=hash_password(user.password),
        office_id=office_id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    access = create_access_token(user_id, user.email or user.phone)
    refresh = create_refresh_token(user_id)
    _set_cookies(response, access, refresh)
    return await user_to_response(new_user, db)


@api_router.post("/auth/login", response_model=UserResponse)
async def login(credentials: UserLogin, response: Response, db: AsyncSession = Depends(get_db)):
    identifier = credentials.identifier.lower() if "@" in credentials.identifier else credentials.identifier
    from sqlalchemy import or_
    result = await db.execute(select(User).where(or_(User.email == identifier, User.phone == identifier)))
    user = result.scalar_one_or_none()
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(status_code=401, detail="البريد الإلكتروني أو كلمة المرور غير صحيحة")

    access = create_access_token(user.id, user.email or user.phone)
    refresh = create_refresh_token(user.id)
    _set_cookies(response, access, refresh)
    return await user_to_response(user, db)


@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await user_to_response(current_user, db)


@api_router.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/")
    return {"message": "تم تسجيل الخروج بنجاح"}


async def require_active_subscription(user: User, db: AsyncSession):
    """Block property mutation for agents with expired subscription. Admins bypass."""
    if user.role == "admin":
        return
    sub = await get_active_subscription(user.id, db)
    if not sub:
        raise HTTPException(status_code=402, detail="انتهى اشتراكك — تواصل معنا للتجديد")


# ---------- Properties ----------
@api_router.post("/properties", response_model=PropertyResponse)
async def create_property(data: PropertyCreate,
                          current_user: User = Depends(get_current_user),
                          db: AsyncSession = Depends(get_db)):
    await require_active_subscription(current_user, db)
    prop = Property(
        id=str(uuid.uuid4()),
        **data.model_dump(),
        agent_id=current_user.id,
        agent_name=current_user.name,
        created_at=datetime.now(timezone.utc),
    )
    db.add(prop)
    await db.commit()
    await db.refresh(prop)
    return prop_to_response(prop)


@api_router.get("/properties", response_model=List[PropertyResponse])
async def get_properties(skip: int = 0, limit: int = 50,
                         status: Optional[str] = None,
                         governorate: Optional[str] = None,
                         district: Optional[str] = None,
                         current_user: User = Depends(get_current_user),
                         db: AsyncSession = Depends(get_db)):
    stmt = select(Property)
    conds = []
    # Data isolation: non-admin agents see only their own properties
    if current_user.role != "admin":
        conds.append(Property.agent_id == current_user.id)
    if status:
        conds.append(Property.status == status)
    if governorate:
        conds.append(Property.governorate.ilike(f"%{governorate}%"))
    if district:
        conds.append(Property.district.ilike(f"%{district}%"))
    if conds:
        stmt = stmt.where(and_(*conds))
    stmt = stmt.order_by(Property.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return [prop_to_response(p) for p in result.scalars().all()]


@api_router.get("/properties/search", response_model=List[PropertyResponse])
async def search_properties(
    query: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_area: Optional[float] = None,
    max_area: Optional[float] = None,
    bedrooms: Optional[int] = None,
    status: Optional[str] = None,
    governorate: Optional[str] = None,
    district: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conds = []
    # Data isolation: non-admin agents see only their own properties
    if current_user.role != "admin":
        conds.append(Property.agent_id == current_user.id)
    if min_price is not None:
        conds.append(Property.price >= min_price)
    if max_price is not None:
        conds.append(Property.price <= max_price)
    if min_area is not None:
        conds.append(Property.total_area >= min_area)
    if max_area is not None:
        conds.append(Property.total_area <= max_area)
    if bedrooms is not None:
        conds.append(Property.bedrooms == bedrooms)
    if status:
        conds.append(Property.status == status)
    if governorate:
        conds.append(Property.governorate.ilike(f"%{governorate}%"))
    if district:
        conds.append(Property.district.ilike(f"%{district}%"))

    stmt = select(Property)
    if conds:
        stmt = stmt.where(and_(*conds))
    stmt = stmt.limit(100)
    result = await db.execute(stmt)
    return [prop_to_response(p) for p in result.scalars().all()]


@api_router.get("/properties/{property_id}", response_model=PropertyResponse)
async def get_property(property_id: str,
                       current_user: User = Depends(get_current_user),
                       db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Property).where(Property.id == property_id))
    prop = result.scalar_one_or_none()
    if not prop:
        raise HTTPException(status_code=404, detail="العقار غير موجود")
    # Data isolation: non-admin can only view their own properties
    if current_user.role != "admin" and prop.agent_id != current_user.id:
        raise HTTPException(status_code=403, detail="غير مصرح - لا يمكنك عرض هذا العقار")
    return prop_to_response(prop)


@api_router.put("/properties/{property_id}", response_model=PropertyResponse)
async def update_property(property_id: str, data: PropertyCreate,
                          current_user: User = Depends(get_current_user),
                          db: AsyncSession = Depends(get_db)):
    await require_active_subscription(current_user, db)
    result = await db.execute(select(Property).where(Property.id == property_id))
    prop = result.scalar_one_or_none()
    if not prop:
        raise HTTPException(status_code=404, detail="العقار غير موجود")
    if current_user.role != "admin" and prop.agent_id != current_user.id:
        raise HTTPException(status_code=403, detail="غير مصرح")
    for k, v in data.model_dump().items():
        setattr(prop, k, v)
    await db.commit()
    await db.refresh(prop)
    return prop_to_response(prop)


@api_router.delete("/properties/{property_id}")
async def delete_property(property_id: str,
                          current_user: User = Depends(get_current_user),
                          db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Property).where(Property.id == property_id))
    prop = result.scalar_one_or_none()
    if not prop:
        raise HTTPException(status_code=404, detail="العقار غير موجود")
    if current_user.role != "admin" and prop.agent_id != current_user.id:
        raise HTTPException(status_code=403, detail="غير مصرح")
    await db.delete(prop)
    await db.commit()
    return {"message": "تم حذف العقار بنجاح"}


# ---------- Uploads ----------
@api_router.post("/upload")
async def upload_image(file: UploadFile = File(...),
                      current_user: User = Depends(get_current_user),
                      db: AsyncSession = Depends(get_db)):
    ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    file_id = str(uuid.uuid4())
    path = f"{APP_NAME}/properties/{current_user.id}/{file_id}.{ext}"

    data = await file.read()
    result = put_object(path, data, file.content_type or "image/jpeg")

    rec = FileRecord(
        id=file_id, storage_path=result["path"],
        original_filename=file.filename, content_type=file.content_type,
        size=result.get("size"), user_id=current_user.id,
        is_deleted=False, created_at=datetime.now(timezone.utc),
    )
    db.add(rec)
    await db.commit()

    return {"id": file_id, "path": result["path"], "url": f"/api/files/{result['path']}"}


@api_router.get("/files/{path:path}")
async def download_file(path: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(FileRecord).where(
        and_(FileRecord.storage_path == path, FileRecord.is_deleted == False)  # noqa: E712
    ))
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="الملف غير موجود")
    data, content_type = get_object(path)
    return Response(content=data, media_type=rec.content_type or content_type)


# ---------- Admin ----------
@api_router.get("/admin/stats", response_model=AdminStats)
async def get_admin_stats(current_user: User = Depends(get_current_user),
                          db: AsyncSession = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="غير مصرح - للمديرين فقط")

    total = (await db.execute(select(func.count()).select_from(Property))).scalar() or 0
    available = (await db.execute(select(func.count()).select_from(Property).where(Property.status == "available"))).scalar() or 0
    sold = (await db.execute(select(func.count()).select_from(Property).where(Property.status == "sold"))).scalar() or 0
    rented = (await db.execute(select(func.count()).select_from(Property).where(Property.status == "rented"))).scalar() or 0

    total_offices = (await db.execute(select(func.count()).select_from(Office))).scalar() or 0

    now = datetime.now(timezone.utc)
    soon = now + timedelta(days=7)
    expiring_soon = (await db.execute(
        select(func.count()).select_from(Subscription).where(and_(
            Subscription.status == "active",
            Subscription.end_date <= soon,
            Subscription.end_date >= now,
        ))
    )).scalar() or 0

    return AdminStats(total_properties=total, available=available, sold=sold,
                      rented=rented, total_offices=total_offices, expiring_soon=expiring_soon)


# ---------- Subscriptions ----------
async def get_active_subscription(user_id: str, db: AsyncSession) -> Optional[Subscription]:
    """Return the most-recent active subscription (end_date in future) for a user, or None."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(Subscription).where(and_(
            Subscription.user_id == user_id,
            Subscription.status == "active",
            Subscription.end_date >= now,
        )).order_by(Subscription.end_date.desc()).limit(1)
    )
    return result.scalar_one_or_none()


@api_router.get("/subscriptions/plans")
async def get_subscription_plans():
    # Public plans exclude "trial" (admin-only)
    return [
        {"plan_type": k, "amount": PLAN_PRICING[k]["amount"],
         "label": PLAN_PRICING[k]["label"], "days": PLAN_PRICING[k]["days"], "currency": "IQD"}
        for k in PUBLIC_PLAN_KEYS
    ]


@api_router.get("/subscriptions/status", response_model=SubscriptionStatusResponse)
async def get_my_subscription_status(current_user: User = Depends(get_current_user),
                                     db: AsyncSession = Depends(get_db)):
    # Admin is always considered "active"
    if current_user.role == "admin":
        return SubscriptionStatusResponse(has_active=True, status="active")
    sub = await get_active_subscription(current_user.id, db)
    if not sub:
        return SubscriptionStatusResponse(has_active=False, status="expired")
    now = datetime.now(timezone.utc)
    days_remaining = max(0, (sub.end_date - now).days)
    if days_remaining <= 7:
        state = "warning"
    else:
        state = "active"
    return SubscriptionStatusResponse(
        has_active=True,
        days_remaining=days_remaining,
        end_date=sub.end_date.isoformat(),
        plan_type=sub.plan_type,
        status=state,
    )


@api_router.post("/subscriptions", response_model=SubscriptionResponse)
async def create_subscription(data: SubscriptionPlan,
                              current_user: User = Depends(get_current_user),
                              db: AsyncSession = Depends(get_db)):
    # ADMIN-ONLY: agents cannot self-activate
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="غير مصرح - فقط المدير يمكنه إنشاء الاشتراكات")
    if data.plan_type not in PLAN_PRICING:
        raise HTTPException(status_code=400, detail="نوع الاشتراك غير صحيح")

    target_user_id = data.user_id or current_user.id
    target_result = await db.execute(select(User).where(User.id == target_user_id))
    target_user = target_result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")

    office_name = None
    if target_user.office_id:
        r = await db.execute(select(Office).where(Office.id == target_user.office_id))
        o = r.scalar_one_or_none()
        office_name = o.office_name if o else None

    plan = PLAN_PRICING[data.plan_type]
    now = datetime.now(timezone.utc)
    end_date = now + timedelta(days=plan["days"])

    # Mark all previously active subs for this user as 'superseded'
    prev_result = await db.execute(
        select(Subscription).where(and_(
            Subscription.user_id == target_user.id,
            Subscription.status == "active",
        ))
    )
    for prev in prev_result.scalars().all():
        prev.status = "superseded"

    sub = Subscription(
        id=str(uuid.uuid4()),
        user_id=target_user.id, user_name=target_user.name,
        office_name=office_name,
        plan_type=data.plan_type, amount=plan["amount"], currency="IQD",
        start_date=now, end_date=end_date, status="active",
        created_at=now,
    )
    db.add(sub)
    await db.commit()
    await db.refresh(sub)
    return sub_to_response(sub)


@api_router.delete("/subscriptions/{sub_id}")
async def delete_subscription(sub_id: str,
                              current_user: User = Depends(get_current_user),
                              db: AsyncSession = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="غير مصرح - فقط المدير")
    result = await db.execute(select(Subscription).where(Subscription.id == sub_id))
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="الاشتراك غير موجود")
    await db.delete(sub)
    await db.commit()
    return {"message": "تم حذف الاشتراك"}


async def _expire_stale(subs: list, db: AsyncSession):
    now = datetime.now(timezone.utc)
    for s in subs:
        if s.status == "active" and s.end_date and s.end_date < now:
            s.status = "expired"
    await db.commit()


@api_router.get("/subscriptions/me", response_model=List[SubscriptionResponse])
async def get_my_subscriptions(current_user: User = Depends(get_current_user),
                               db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Subscription).where(Subscription.user_id == current_user.id)
        .order_by(Subscription.created_at.desc())
    )
    subs = result.scalars().all()
    await _expire_stale(subs, db)
    return [sub_to_response(s) for s in subs]


@api_router.get("/admin/subscriptions", response_model=List[SubscriptionResponse])
async def get_all_subscriptions(current_user: User = Depends(get_current_user),
                                db: AsyncSession = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="غير مصرح - للمديرين فقط")
    result = await db.execute(select(Subscription).order_by(Subscription.created_at.desc()).limit(500))
    subs = result.scalars().all()
    await _expire_stale(subs, db)
    return [sub_to_response(s) for s in subs]


@api_router.get("/admin/subscriptions/expiring", response_model=List[SubscriptionResponse])
async def get_expiring_subscriptions(current_user: User = Depends(get_current_user),
                                     db: AsyncSession = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="غير مصرح - للمديرين فقط")
    now = datetime.now(timezone.utc)
    soon = now + timedelta(days=7)
    result = await db.execute(
        select(Subscription).where(and_(
            Subscription.status == "active",
            Subscription.end_date <= soon,
            Subscription.end_date >= now,
        )).order_by(Subscription.end_date.asc()).limit(100)
    )
    return [sub_to_response(s) for s in result.scalars().all()]


@api_router.get("/admin/subscriptions/plans")
async def get_admin_subscription_plans(current_user: User = Depends(get_current_user)):
    """Admin-only plans list - includes trial."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="غير مصرح - للمديرين فقط")
    return [
        {"plan_type": k, "amount": v["amount"], "label": v["label"], "days": v["days"], "currency": "IQD"}
        for k, v in PLAN_PRICING.items()
    ]


@api_router.get("/admin/users")
async def get_all_users(current_user: User = Depends(get_current_user),
                        db: AsyncSession = Depends(get_db)):
    """Admin-only: list all users (with office name) for subscription assignment."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="غير مصرح - للمديرين فقط")
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    output = []
    for u in users:
        office_name = None
        if u.office_id:
            r = await db.execute(select(Office).where(Office.id == u.office_id))
            o = r.scalar_one_or_none()
            office_name = o.office_name if o else None
        output.append({
            "id": u.id, "name": u.name, "email": u.email, "phone": u.phone,
            "role": u.role, "office_name": office_name,
        })
    return output


@api_router.get("/admin/offices")
async def get_offices(current_user: User = Depends(get_current_user),
                      db: AsyncSession = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="غير مصرح - للمديرين فقط")

    result = await db.execute(select(Office))
    offices = result.scalars().all()
    output = []
    for o in offices:
        agents_result = await db.execute(
            select(User).where(and_(User.office_id == o.id, User.role == "agent"))
        )
        agents = agents_result.scalars().all()
        output.append({
            "office_name": o.office_name,
            "agents": [{"id": a.id, "name": a.name} for a in agents],
            "agent_count": len(agents),
        })
    return output


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    await seed_admin()
    init_storage()
    logger.info("Application started with Supabase Postgres")


@app.on_event("shutdown")
async def shutdown():
    await engine.dispose()

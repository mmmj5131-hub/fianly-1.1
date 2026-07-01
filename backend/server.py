from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, UploadFile, File, Header, Query, Depends
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
import bcrypt
import jwt
import requests
import secrets

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# JWT Configuration
JWT_ALGORITHM = "HS256"
JWT_SECRET = os.environ.get("JWT_SECRET", "your-secret-key-change-in-production")

# Object Storage Configuration
STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")
APP_NAME = "aqari-almuyassar"
storage_key = None

# Password Hashing
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

# JWT Functions
def create_access_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
        "type": "access"
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
        "type": "refresh"
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

# Auth Dependency
async def get_current_user(request: Request) -> dict:
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
        user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        user.pop("password_hash", None)
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Object Storage Functions
def init_storage():
    global storage_key
    if storage_key:
        return storage_key
    try:
        resp = requests.post(
            f"{STORAGE_URL}/init",
            json={"emergent_key": EMERGENT_KEY},
            timeout=30
        )
        resp.raise_for_status()
        storage_key = resp.json()["storage_key"]
        logger.info("Storage initialized successfully")
        return storage_key
    except Exception as e:
        logger.error(f"Storage init failed: {e}")
        return None

def put_object(path: str, data: bytes, content_type: str) -> dict:
    key = init_storage()
    if not key:
        raise HTTPException(status_code=500, detail="Storage not initialized")
    resp = requests.put(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key, "Content-Type": content_type},
        data=data,
        timeout=120
    )
    resp.raise_for_status()
    return resp.json()

def get_object(path: str) -> tuple[bytes, str]:
    key = init_storage()
    if not key:
        raise HTTPException(status_code=500, detail="Storage not initialized")
    resp = requests.get(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key},
        timeout=60
    )
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")

# Pydantic Models
class UserRegister(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    password: str
    office_name: Optional[str] = None

class UserLogin(BaseModel):
    identifier: str  # email or phone
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
    owner_name: str
    owner_phone: str
    images: Optional[List[str]] = []
    status: str = "available"  # available, sold, rented

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

class SubscriptionPlan(BaseModel):
    plan_type: str  # monthly, quarterly, yearly

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
    status: str  # active, expired
    created_at: str

class AdminStats(BaseModel):
    total_properties: int
    available: int
    sold: int
    rented: int
    total_offices: int
    expiring_soon: int

PLAN_PRICING = {
    "monthly": {"amount": 25000, "days": 30, "label": "اشتراك شهري"},
    "quarterly": {"amount": 65000, "days": 90, "label": "اشتراك ثلاثة أشهر"},
    "yearly": {"amount": 250000, "days": 365, "label": "اشتراك سنوي"},
}

# Admin Seeding
async def seed_admin():
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@aqari.com")
    admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")
    
    existing = await db.users.find_one({"email": admin_email}, {"_id": 0})
    if existing is None:
        admin_user = {
            "id": str(uuid.uuid4()),
            "email": admin_email,
            "name": "المدير العام",
            "role": "admin",
            "password_hash": hash_password(admin_password),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.users.insert_one(admin_user)
        logger.info(f"Admin created: {admin_email}")
    elif not verify_password(admin_password, existing["password_hash"]):
        await db.users.update_one(
            {"email": admin_email},
            {"$set": {"password_hash": hash_password(admin_password)}}
        )
        logger.info("Admin password updated")
    
    # Write test credentials
    Path("/app/memory").mkdir(exist_ok=True)
    with open("/app/memory/test_credentials.md", "w", encoding="utf-8") as f:
        f.write("# Test Credentials\n\n")
        f.write("## Admin Account\n")
        f.write(f"- Email: {admin_email}\n")
        f.write(f"- Password: {admin_password}\n")
        f.write(f"- Role: admin\n\n")
        f.write("## API Endpoints\n")
        f.write("- POST /api/auth/register\n")
        f.write("- POST /api/auth/login\n")
        f.write("- GET /api/auth/me\n")
        f.write("- POST /api/auth/logout\n")
        f.write("- GET /api/properties\n")
        f.write("- POST /api/properties\n")
        f.write("- GET /api/admin/stats\n")

# Auth Routes
@api_router.post("/auth/register", response_model=UserResponse)
async def register(user: UserRegister, response: Response):
    if not user.email and not user.phone:
        raise HTTPException(status_code=400, detail="يجب إدخال البريد الإلكتروني أو رقم الهاتف")
    
    # Check if user exists
    query = {}
    if user.email:
        query["email"] = user.email.lower()
    if user.phone:
        query["phone"] = user.phone
    
    existing = await db.users.find_one(query, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="المستخدم موجود بالفعل")
    
    # Create user
    user_id = str(uuid.uuid4())
    new_user = {
        "id": user_id,
        "name": user.name,
        "role": "agent",
        "password_hash": hash_password(user.password),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    if user.email:
        new_user["email"] = user.email.lower()
    if user.phone:
        new_user["phone"] = user.phone
    if user.office_name:
        new_user["office_name"] = user.office_name
    
    await db.users.insert_one(new_user)
    
    # Create tokens
    access_token = create_access_token(user_id, user.email or user.phone)
    refresh_token = create_refresh_token(user_id)
    
    # Set cookies
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=900,
        path="/"
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=604800,
        path="/"
    )
    
    new_user.pop("password_hash")
    return UserResponse(**new_user)

@api_router.post("/auth/login", response_model=UserResponse)
async def login(credentials: UserLogin, response: Response):
    # Find user by email or phone
    identifier = credentials.identifier.lower() if "@" in credentials.identifier else credentials.identifier
    
    user = await db.users.find_one(
        {"$or": [{"email": identifier}, {"phone": identifier}]},
        {"_id": 0}
    )
    
    if not user:
        raise HTTPException(status_code=401, detail="البريد الإلكتروني أو كلمة المرور غير صحيحة")
    
    if not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="البريد الإلكتروني أو كلمة المرور غير صحيحة")
    
    # Create tokens
    access_token = create_access_token(user["id"], user.get("email", user.get("phone")))
    refresh_token = create_refresh_token(user["id"])
    
    # Set cookies
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=900,
        path="/"
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=604800,
        path="/"
    )
    
    user.pop("password_hash")
    return UserResponse(**user)

@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return UserResponse(**current_user)

@api_router.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/")
    return {"message": "تم تسجيل الخروج بنجاح"}

# Property Routes
@api_router.post("/properties", response_model=PropertyResponse)
async def create_property(property_data: PropertyCreate, current_user: dict = Depends(get_current_user)):
    property_id = str(uuid.uuid4())
    property_doc = {
        "id": property_id,
        **property_data.model_dump(),
        "agent_id": current_user["id"],
        "agent_name": current_user["name"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.properties.insert_one(property_doc)
    property_doc.pop("_id", None)
    return PropertyResponse(**property_doc)

@api_router.get("/properties", response_model=List[PropertyResponse])
async def get_properties(skip: int = 0, limit: int = 50, status: Optional[str] = None):
    query = {}
    if status:
        query["status"] = status
    properties = await db.properties.find(query, {"_id": 0}).skip(skip).limit(limit).to_list(limit)
    # Ensure owner_name exists for older docs
    for p in properties:
        if "owner_name" not in p:
            p["owner_name"] = ""
    return [PropertyResponse(**prop) for prop in properties]

@api_router.get("/properties/search", response_model=List[PropertyResponse])
async def search_properties(
    query: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_area: Optional[float] = None,
    max_area: Optional[float] = None,
    bedrooms: Optional[int] = None,
    status: Optional[str] = None
):
    search_filter = {}
    
    if min_price or max_price:
        search_filter["price"] = {}
        if min_price:
            search_filter["price"]["$gte"] = min_price
        if max_price:
            search_filter["price"]["$lte"] = max_price
    
    if min_area or max_area:
        search_filter["total_area"] = {}
        if min_area:
            search_filter["total_area"]["$gte"] = min_area
        if max_area:
            search_filter["total_area"]["$lte"] = max_area
    
    if bedrooms:
        search_filter["bedrooms"] = bedrooms
    
    if status:
        search_filter["status"] = status
    
    properties = await db.properties.find(search_filter, {"_id": 0}).to_list(100)
    return [PropertyResponse(**prop) for prop in properties]

@api_router.get("/properties/{property_id}", response_model=PropertyResponse)
async def get_property(property_id: str):
    property_doc = await db.properties.find_one({"id": property_id}, {"_id": 0})
    if not property_doc:
        raise HTTPException(status_code=404, detail="العقار غير موجود")
    return PropertyResponse(**property_doc)

@api_router.put("/properties/{property_id}", response_model=PropertyResponse)
async def update_property(
    property_id: str,
    property_data: PropertyCreate,
    current_user: dict = Depends(get_current_user)
):
    existing = await db.properties.find_one({"id": property_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="العقار غير موجود")
    
    # Check ownership or admin
    if current_user["role"] != "admin" and existing["agent_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="غير مصرح")
    
    update_data = property_data.model_dump()
    await db.properties.update_one({"id": property_id}, {"$set": update_data})
    
    updated = await db.properties.find_one({"id": property_id}, {"_id": 0})
    return PropertyResponse(**updated)

@api_router.delete("/properties/{property_id}")
async def delete_property(property_id: str, current_user: dict = Depends(get_current_user)):
    existing = await db.properties.find_one({"id": property_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="العقار غير موجود")
    
    # Check ownership or admin
    if current_user["role"] != "admin" and existing["agent_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="غير مصرح")
    
    await db.properties.delete_one({"id": property_id})
    return {"message": "تم حذف العقار بنجاح"}

# Upload Route
@api_router.post("/upload")
async def upload_image(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    file_id = str(uuid.uuid4())
    path = f"{APP_NAME}/properties/{current_user['id']}/{file_id}.{ext}"
    
    data = await file.read()
    result = put_object(path, data, file.content_type or "image/jpeg")
    
    # Store reference in DB
    file_doc = {
        "id": file_id,
        "storage_path": result["path"],
        "original_filename": file.filename,
        "content_type": file.content_type,
        "size": result["size"],
        "user_id": current_user["id"],
        "is_deleted": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.files.insert_one(file_doc)
    
    return {"id": file_id, "path": result["path"], "url": f"/api/files/{result['path']}"}

@api_router.get("/files/{path:path}")
async def download_file(path: str):
    record = await db.files.find_one({"storage_path": path, "is_deleted": False}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="الملف غير موجود")
    
    data, content_type = get_object(path)
    return Response(content=data, media_type=record.get("content_type", content_type))

# Admin Routes
@api_router.get("/admin/stats", response_model=AdminStats)
async def get_admin_stats(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="غير مصرح - للمديرين فقط")
    
    total_properties = await db.properties.count_documents({})
    available = await db.properties.count_documents({"status": "available"})
    sold = await db.properties.count_documents({"status": "sold"})
    rented = await db.properties.count_documents({"status": "rented"})
    
    # Count unique offices
    pipeline = [
        {"$match": {"role": "agent", "office_name": {"$exists": True}}},
        {"$group": {"_id": "$office_name"}},
        {"$count": "total"}
    ]
    office_count = await db.users.aggregate(pipeline).to_list(1)
    total_offices = office_count[0]["total"] if office_count else 0
    
    # Count expiring soon subscriptions (within 7 days)
    now = datetime.now(timezone.utc)
    soon = (now + timedelta(days=7)).isoformat()
    expiring_soon = await db.subscriptions.count_documents({
        "status": "active",
        "end_date": {"$lte": soon, "$gte": now.isoformat()}
    })
    
    return AdminStats(
        total_properties=total_properties,
        available=available,
        sold=sold,
        rented=rented,
        total_offices=total_offices,
        expiring_soon=expiring_soon
    )

# Subscription Routes
@api_router.get("/subscriptions/plans")
async def get_subscription_plans():
    return [
        {"plan_type": k, "amount": v["amount"], "label": v["label"], "days": v["days"], "currency": "IQD"}
        for k, v in PLAN_PRICING.items()
    ]

@api_router.post("/subscriptions", response_model=SubscriptionResponse)
async def create_subscription(
    data: SubscriptionPlan,
    current_user: dict = Depends(get_current_user)
):
    if data.plan_type not in PLAN_PRICING:
        raise HTTPException(status_code=400, detail="نوع الاشتراك غير صحيح")
    
    plan = PLAN_PRICING[data.plan_type]
    sub_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    end_date = now + timedelta(days=plan["days"])
    
    subscription = {
        "id": sub_id,
        "user_id": current_user["id"],
        "user_name": current_user["name"],
        "office_name": current_user.get("office_name", ""),
        "plan_type": data.plan_type,
        "amount": plan["amount"],
        "currency": "IQD",
        "start_date": now.isoformat(),
        "end_date": end_date.isoformat(),
        "status": "active",
        "created_at": now.isoformat()
    }
    
    await db.subscriptions.insert_one(subscription)
    return SubscriptionResponse(**subscription)

@api_router.get("/subscriptions/me", response_model=List[SubscriptionResponse])
async def get_my_subscriptions(current_user: dict = Depends(get_current_user)):
    subs = await db.subscriptions.find(
        {"user_id": current_user["id"]}, {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    # Auto-update expired subscriptions
    now_iso = datetime.now(timezone.utc).isoformat()
    for s in subs:
        if s["status"] == "active" and s["end_date"] < now_iso:
            await db.subscriptions.update_one({"id": s["id"]}, {"$set": {"status": "expired"}})
            s["status"] = "expired"
    
    return [SubscriptionResponse(**s) for s in subs]

@api_router.get("/admin/subscriptions", response_model=List[SubscriptionResponse])
async def get_all_subscriptions(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="غير مصرح - للمديرين فقط")
    
    subs = await db.subscriptions.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    
    # Auto-update expired
    now_iso = datetime.now(timezone.utc).isoformat()
    for s in subs:
        if s["status"] == "active" and s["end_date"] < now_iso:
            await db.subscriptions.update_one({"id": s["id"]}, {"$set": {"status": "expired"}})
            s["status"] = "expired"
    
    return [SubscriptionResponse(**s) for s in subs]

@api_router.get("/admin/subscriptions/expiring", response_model=List[SubscriptionResponse])
async def get_expiring_subscriptions(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="غير مصرح - للمديرين فقط")
    
    now = datetime.now(timezone.utc)
    soon = (now + timedelta(days=7)).isoformat()
    
    subs = await db.subscriptions.find(
        {"status": "active", "end_date": {"$lte": soon, "$gte": now.isoformat()}},
        {"_id": 0}
    ).sort("end_date", 1).to_list(100)
    
    return [SubscriptionResponse(**s) for s in subs]

@api_router.get("/admin/offices")
async def get_offices(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="غير مصرح - للمديرين فقط")
    
    pipeline = [
        {"$match": {"role": "agent", "office_name": {"$exists": True}}},
        {"$group": {
            "_id": "$office_name",
            "agents": {"$push": {"name": "$name", "id": "$id"}},
            "agent_count": {"$sum": 1}
        }}
    ]
    offices = await db.users.aggregate(pipeline).to_list(100)
    return [{"office_name": o["_id"], "agents": o["agents"], "agent_count": o["agent_count"]} for o in offices]

# Include the router in the main app
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
    # Create indexes
    await db.users.create_index("email", unique=True, sparse=True)
    await db.users.create_index("phone", unique=True, sparse=True)
    await db.properties.create_index("id", unique=True)
    logger.info("Application started")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

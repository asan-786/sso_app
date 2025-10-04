# backend/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware
import uuid

app = FastAPI(title="SSO Portal Backend - Module 2")


class LoginRequest(BaseModel):
    email: str
    password: str
    clientId: str
@app.get("/")
def home():
    return {"status": "Backend is running 🚀"}

# Allow dev React origins (add yours if different)
origins = [
    "http://localhost:3000",
    "http://localhost:3002",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3002",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------
# In-memory "database"
# ------------------------
# applications: dict mapping app_id -> app_obj
applications = {}

# sample users for admin dropdown / mapping (replace with real users later)
users = [
    {"id": 1, "name": "Aryan Swarnkar", "email": "aryan@university.edu"},
    {"id": 2, "name": "Asan Ali", "email": "asan@university.edu"},
    {"id": 3, "name": "Sankalp Sharma", "email": "sankalp@university.edu"},
    {"id": 4, "name": "Devansh Silan", "email": "devansh@university.edu"},
]

# ------------------------
# Pydantic models
# ------------------------
class ApplicationIn(BaseModel):
    name: str
    url: str
    client_id: Optional[str] = ""
    client_secret: Optional[str] = ""

class Application(BaseModel):
    id: str
    name: str
    url: str
    client_id: Optional[str] = ""
    client_secret: Optional[str] = ""
    # store authorized emails here
    authorized_emails: List[str] = Field(default_factory=list)

class MapRequest(BaseModel):
    email: str
    app_id: str

# ------------------------
# CRUD endpoints
# ------------------------
@app.post("/applications", response_model=Application)
def create_app(app_data: ApplicationIn):
    app_id = str(uuid.uuid4())
    app_obj = {
        "id": app_id,
        "name": app_data.name,
        "url": app_data.url,
        "client_id": app_data.client_id or "",
        "client_secret": app_data.client_secret or "",
        "authorized_emails": []
    }
    applications[app_id] = app_obj
    return app_obj

@app.get("/applications", response_model=List[Application])
def list_apps():
    return list(applications.values())

@app.get("/applications/{app_id}", response_model=Application)
def get_app(app_id: str):
    app_obj = applications.get(app_id)
    if not app_obj:
        raise HTTPException(status_code=404, detail="Application not found")
    return app_obj

@app.put("/applications/{app_id}", response_model=Application)
def update_app(app_id: str, app_data: ApplicationIn):
    app_obj = applications.get(app_id)
    if not app_obj:
        raise HTTPException(status_code=404, detail="Application not found")
    # preserve authorized_emails when updating
    app_obj.update({
        "name": app_data.name,
        "url": app_data.url,
        "client_id": app_data.client_id or "",
        "client_secret": app_data.client_secret or ""
    })
    applications[app_id] = app_obj
    return app_obj

@app.delete("/applications/{app_id}")
def delete_app(app_id: str):
    if app_id not in applications:
        raise HTTPException(status_code=404, detail="Application not found")
    del applications[app_id]
    return {"message": "Application deleted"}

# ------------------------
# Users endpoint (for admin UI)
# ------------------------
@app.get("/users")
def get_users():
    return users

# ------------------------
# Mapping endpoints (email-based)
# ------------------------
@app.post("/map")
def map_email_to_app(req: MapRequest):
    app_obj = applications.get(req.app_id)
    if not app_obj:
        raise HTTPException(status_code=404, detail="Application not found")
    # optionally validate email exists in users list - not required but helpful:
    known_emails = {u["email"] for u in users}
    if req.email not in known_emails:
        # We'll still allow mapping unknown emails, but warn (comment this line out if you want to enforce)
        # raise HTTPException(status_code=400, detail="Email not found in user list")
        pass

    if req.email not in app_obj["authorized_emails"]:
        app_obj["authorized_emails"].append(req.email)
    return {"message": "Mapped", "app": app_obj}

@app.post("/unmap")
def unmap_email_from_app(req: MapRequest):
    app_obj = applications.get(req.app_id)
    if not app_obj:
        raise HTTPException(status_code=404, detail="Application not found")
    if req.email in app_obj["authorized_emails"]:
        app_obj["authorized_emails"].remove(req.email)
    return {"message": "Unmapped", "app": app_obj}

@app.get("/user/email/{email}/apps", response_model=List[Application])
def get_apps_for_email(email: str):
    assigned = [a for a in applications.values() if email in a.get("authorized_emails", [])]
    return assigned

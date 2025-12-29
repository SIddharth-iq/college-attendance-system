"""
Main FastAPI application entry point
College Attendance Management System
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base
from app.routers import auth, admin, attendance
from app import models
from app.database import init_db

print("MODELS LOADED:", Base.metadata.tables.keys())

# --------------------------------------------------
# Create database tables (DEV only)
# --------------------------------------------------


# --------------------------------------------------
# Initialize FastAPI app
# --------------------------------------------------
app = FastAPI(
    title="College Attendance Management System",
    description="FastAPI-based backend for managing college attendance",
    version="1.0.0",
)


@app.on_event("startup")
def on_startup():
    init_db()


# --------------------------------------------------
# CORS Configuration
# --------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# Root & Health Endpoints
# --------------------------------------------------
@app.get("/")
async def root():
    return {
        "message": "College Attendance Management System API",
        "status": "running",
        "version": "1.0.0",
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


# --------------------------------------------------
# Register Routers
# --------------------------------------------------
print("🚀 main.py loaded")
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
print("🚀 auth.router loaded")
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
print("🚀 admin.router loaded")
app.include_router(attendance.router, prefix="/api/attendance", tags=["Attendance"])
print("🚀 attendance.router loaded")

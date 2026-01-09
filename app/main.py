"""
Main FastAPI application entry point
College Attendance Management System
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routers import auth, admin, attendance_v3, reports

# --------------------------------------------------
# Initialize FastAPI app
# --------------------------------------------------
app = FastAPI(
    title="College Attendance Management System",
    description="FastAPI-based backend for managing college attendance",
    version="1.0.0",
)


# --------------------------------------------------
# Startup
# --------------------------------------------------
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
# Root & Health
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
# ROUTERS (ONLY ONE ATTENDANCE SYSTEM)
# --------------------------------------------------
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])

# ✅ V3 ATTENDANCE (ONLY)
app.include_router(
    attendance_v3.router,
    prefix="/api/v3/attendance",
    tags=["Attendance V3"],
)

# ✅ V3 REPORTS
app.include_router(
    reports.router,
    prefix="/api/v3/reports",
    tags=["Reports V3"],
)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.applications import router as applications_router
from app.routers.certificates import router as certificates_router
from app.routers.applicants import router as applicants_router
from app.routers.documents import router as documents_router
from app.routers.comments import router as comments_router
from app.routers.objections import router as objections_router
from app.routers.timeline import router as timeline_router
# Student 3 routers
from app.routers.staff import router as staff_router
from app.routers.survey_tasks import router as survey_tasks_router
from app.routers.analytics import router as analytics_router
from app.routers.map import router as map_router
from app.routers.survey_reports import router as survey_reports_router


app = FastAPI(
    title="LRMIS API",
    description="Land Registration Management Information System API",
    version="1.0.0",
)

# CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers — Student 1 + 2
app.include_router(applications_router)
app.include_router(certificates_router)
app.include_router(applicants_router)
app.include_router(documents_router)
app.include_router(comments_router)
app.include_router(objections_router)
app.include_router(timeline_router)
# Routers — Student 3
app.include_router(staff_router)
app.include_router(survey_tasks_router)
app.include_router(analytics_router)
app.include_router(map_router)
app.include_router(survey_reports_router)


@app.get("/")
def root():
    return {
        "message": "LRMIS API is running",
        "module": "Student 1 - Land Application Management",
    }


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "LRMIS Backend",
    }
"""
Main FastAPI application entry point.
Run: uvicorn app.main:app --reload
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv("env.example")   # students: rename to .env with real keys

from app.models.database import init_db
from app.services.seeder  import seed
from app.routers.api      import router


# ── Lifespan: DB init + seed on startup ──────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await seed()
    yield


app = FastAPI(
    title       = "Clinical Documentation Validation System",
    description = "AI-powered clinical document validation using IBM Granite",
    version     = "1.0.0",
    lifespan    = lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

# Static files & templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Include API router
app.include_router(router)


# ── Page routes ───────────────────────────────────────────────────────────────
@app.get("/")
async def dashboard(request: Request):
    return templates.TemplateResponse(request, "index.html")

@app.get("/documents")
async def documents_page(request: Request):
    return templates.TemplateResponse(request, "documents.html")

@app.get("/patients")
async def patients_page(request: Request):
    return templates.TemplateResponse(request, "patients.html")

@app.get("/issues")
async def issues_page(request: Request):
    return templates.TemplateResponse(request, "issues.html")

@app.get("/new-document")
async def new_doc_page(request: Request):
    return templates.TemplateResponse(request, "new_document.html")

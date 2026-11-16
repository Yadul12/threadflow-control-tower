import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base, SessionLocal
from .seed import seed_database
from .routers import control_tower, inbound, inventory, outbound, analytics_ai_sheets

_DB_INITIALIZED = False


def init_db_and_seed() -> None:
    global _DB_INITIALIZED
    if _DB_INITIALIZED:
        return
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database(db, force_reset=False)
        _DB_INITIALIZED = True
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db_and_seed()
    yield


if os.getenv("VERCEL"):
    init_db_and_seed()


app = FastAPI(
    title="THREADFLOW — Fashion Supply Chain & Merchandising Control Tower API",
    version="2.4.0",
    description="Enterprise Supply Chain Control Tower connecting Inbound Procurement & Catalogue, Inventory Intelligence, and Outbound Fulfilment & Returns.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(control_tower.router)
app.include_router(inbound.router)
app.include_router(inventory.router)
app.include_router(outbound.router)
app.include_router(analytics_ai_sheets.router)


@app.get("/")
def root_info():
    return {
        "service": "THREADFLOW — Fashion Supply Chain & Merchandising Control Tower API",
        "version": "2.4.0",
        "docs_url": "/docs",
        "health_url": "/api/health",
        "status_url": "/api/system/status",
    }

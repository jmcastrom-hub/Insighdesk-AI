from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import load_local_env

load_local_env()

from app.database import Base, engine, migrate_sqlite_schema
from app.routers import router
from app.seed import seed_database, seed_demo_operations, seed_demo_approvals
from app.database import SessionLocal


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    migrate_sqlite_schema(engine)
    with SessionLocal() as db:
        seed_database(db)
        seed_demo_operations(db)
        seed_demo_approvals(db)
    yield


app = FastAPI(title="Insightdesk-AI", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)
app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok"}

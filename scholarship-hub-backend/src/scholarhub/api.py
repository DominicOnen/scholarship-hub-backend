"""Global Scholarship Hub API (FastAPI) – called by the phone app.

Run:  uvicorn scholarhub.api:app --host 0.0.0.0 --app-dir src
Docs: http://127.0.0.1:8000/docs
"""
import os
from typing import Literal

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from scholarhub import store

ADMIN_KEY = os.environ.get("ADMIN_KEY", "change-me")

app = FastAPI(title="Global Scholarship Hub API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
store.init_db()


class Application(BaseModel):
    """What the phone sends. Anything else gets error 422."""
    scholarship_id: int = Field(ge=1)
    full_name: str = Field(min_length=2, max_length=80)
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=120)


class StatusChange(BaseModel):
    status: Literal["pending", "accepted", "rejected"]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/scholarships")
def scholarships():
    return store.list_scholarships()


@app.get("/scholarships/{sid}")
def scholarship(sid: int):
    s = store.get_scholarship(sid)
    if s is None:
        raise HTTPException(404, "Scholarship not found")
    return s


@app.post("/applications")
def apply(a: Application):
    try:
        result, created = store.create_application(a.scholarship_id, a.full_name, a.email)
    except LookupError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(409, str(e))
    return {**result, "already_applied": not created}


@app.get("/applications/{aid}")
def application(aid: str):
    r = store.get_application(aid)
    if r is None:
        raise HTTPException(404, "Application not found")
    return r


@app.patch("/applications/{aid}")
def decide(aid: str, change: StatusChange, x_admin_key: str = Header(default="")):
    """Board decision. Needs the header  X-Admin-Key: <ADMIN_KEY>."""
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(401, "Admin key required")
    r = store.set_status(aid, change.status)
    if r is None:
        raise HTTPException(404, "Application not found")
    return r

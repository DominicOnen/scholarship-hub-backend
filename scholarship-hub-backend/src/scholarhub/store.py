"""Scholarships (read from data/scholarships.json) and applications (SQLite)."""
import json
import os
import sqlite3
import threading
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHOLARSHIP_FILE = ROOT / "data" / "scholarships.json"
DB_FILE = os.environ.get("DB_FILE", str(ROOT / "applications.db"))
# Seconds an application stays "pending" before the board accepts it (demo behaviour).
REVIEW_SECONDS = int(os.environ.get("REVIEW_SECONDS", "20"))

_lock = threading.Lock()


def _conn():
    c = sqlite3.connect(DB_FILE)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with _lock, _conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS applications (
            id TEXT PRIMARY KEY, scholarship_id INTEGER NOT NULL,
            full_name TEXT NOT NULL, email TEXT NOT NULL,
            status TEXT NOT NULL, created_at TEXT NOT NULL,
            UNIQUE (scholarship_id, email))""")


def _raw_scholarships():
    return json.loads(SCHOLARSHIP_FILE.read_text(encoding="utf-8"))


def _used_slots():
    with _conn() as c:
        rows = c.execute("SELECT scholarship_id, COUNT(*) n FROM applications "
                         "WHERE status != 'rejected' GROUP BY scholarship_id").fetchall()
    return {r["scholarship_id"]: r["n"] for r in rows}


def _shape(s, used):
    """Same field names the phone screens already use."""
    left = max(s["slots_total"] - used.get(s["id"], 0), 0)
    closes = date.fromisoformat(s["closes"])
    if left == 0:
        label = "❌ Full – no slots left"
    elif left <= 3:
        label = f"🔥 Only {left} Slot{'s' if left != 1 else ''} Left!"
    else:
        label = f"⏳ {left} Slots Left"
    return {
        "id": s["id"], "name": s["name"], "field": s["field"], "benefit": s["benefit"],
        "timeline": f"Closes: {closes.strftime('%B')} {closes.day}, {closes.year}, Intake: {s['intake']}",
        "eligibility": s["eligibility"],
        "campusLogistics": f"Learning Mode: {s['learning_mode']}, Location: {s['location']}, Duration: {s['duration']}",
        "remainingSlots": label, "slotsLeft": left, "closes": s["closes"],
    }


def list_scholarships():
    used = _used_slots()
    return [_shape(s, used) for s in _raw_scholarships()]


def get_scholarship(sid):
    used = _used_slots()
    for s in _raw_scholarships():
        if s["id"] == sid:
            return _shape(s, used)
    return None


def _status_now(row):
    """pending -> accepted after REVIEW_SECONDS, unless the board already decided."""
    if row["status"] != "pending":
        return row["status"]
    age = (datetime.now(timezone.utc) - datetime.fromisoformat(row["created_at"])).total_seconds()
    return "accepted" if age >= REVIEW_SECONDS else "pending"


def _app_dict(row):
    s = get_scholarship(row["scholarship_id"])
    return {"id": row["id"], "scholarship_id": row["scholarship_id"],
            "scholarship": s, "full_name": row["full_name"], "email": row["email"],
            "status": _status_now(row), "created_at": row["created_at"]}


def create_application(sid, full_name, email):
    """Return (application_dict, created: bool). Raises ValueError with a message."""
    s = get_scholarship(sid)
    if s is None:
        raise LookupError("Scholarship not found")
    if date.fromisoformat(s["closes"]) < date.today():
        raise ValueError("Applications for this scholarship are closed")
    email = email.strip().lower()
    with _lock, _conn() as c:
        row = c.execute("SELECT * FROM applications WHERE scholarship_id=? AND email=?",
                        (sid, email)).fetchone()
        if row:
            return _app_dict(row), False
        if s["slotsLeft"] == 0:
            raise ValueError("No slots left for this scholarship")
        aid = uuid.uuid4().hex[:10]
        c.execute("INSERT INTO applications VALUES (?,?,?,?,?,?)",
                  (aid, sid, full_name.strip(), email, "pending",
                   datetime.now(timezone.utc).isoformat()))
        row = c.execute("SELECT * FROM applications WHERE id=?", (aid,)).fetchone()
    return _app_dict(row), True


def get_application(aid):
    with _conn() as c:
        row = c.execute("SELECT * FROM applications WHERE id=?", (aid,)).fetchone()
    return _app_dict(row) if row else None


def set_status(aid, status):
    with _lock, _conn() as c:
        cur = c.execute("UPDATE applications SET status=? WHERE id=?", (status, aid))
        if cur.rowcount == 0:
            return None
    return get_application(aid)

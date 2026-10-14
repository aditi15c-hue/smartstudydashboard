import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "studydashboard.db"

app = FastAPI(title="Smart Study Dashboard")


# ---------- Database helpers ----------
@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # access columns by name
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_db() as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT NOT NULL,
                minutes INTEGER NOT NULL,
                study_date TEXT NOT NULL,
                notes TEXT DEFAULT ''
            )
            """
        )


init_db()


# ---------- Data validation ----------
class SessionIn(BaseModel):
    subject: str = Field(min_length=1, max_length=50)
    minutes: int = Field(gt=0, le=1440)
    study_date: date
    notes: str = Field(default="", max_length=300)


# ---------- API routes ----------
@app.get("/api/sessions")
def list_sessions():
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM sessions ORDER BY study_date DESC, id DESC"
        ).fetchall()
    return [dict(r) for r in rows]


@app.post("/api/sessions", status_code=201)
def add_session(session: SessionIn):
    with get_db() as db:
        cur = db.execute(
            "INSERT INTO sessions (subject, minutes, study_date, notes) VALUES (?, ?, ?, ?)",
            (
                session.subject.strip(),
                session.minutes,
                session.study_date.isoformat(),
                session.notes.strip(),
            ),
        )
        row = db.execute(
            "SELECT * FROM sessions WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
    return dict(row)


@app.delete("/api/sessions/{session_id}", status_code=204)
def delete_session(session_id: int):
    with get_db() as db:
        cur = db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Session not found")


@app.get("/api/stats")
def stats():
    with get_db() as db:
        by_subject = db.execute(
            "SELECT subject, SUM(minutes) AS minutes FROM sessions "
            "GROUP BY subject ORDER BY minutes DESC"
        ).fetchall()
        by_day = db.execute(
            "SELECT study_date, SUM(minutes) AS minutes FROM sessions "
            "GROUP BY study_date ORDER BY study_date DESC LIMIT 14"
        ).fetchall()
        totals = db.execute(
            "SELECT COALESCE(SUM(minutes), 0) AS total_minutes, "
            "COUNT(*) AS total_sessions FROM sessions"
        ).fetchone()
    return {
        "total_minutes": totals["total_minutes"],
        "total_sessions": totals["total_sessions"],
        "by_subject": [dict(r) for r in by_subject],
        "by_day": [dict(r) for r in reversed(by_day)],  # oldest to newest
    }


# ---------- Serve the frontend ----------
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.get("/")
def home():
    return FileResponse(BASE_DIR / "static" / "index.html")
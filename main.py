import os
from datetime import datetime, timedelta, date
from typing import List, Optional

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import db, create_document, get_documents
from schemas import (
    User, Employee, Team, Attendance, Leave, Task, Timesheet, Payroll, Job,
    Application, ResumeparseResult, Performance, Announcement, Ticket, Notification,
    InsightRequest, ResumeText,
)

app = FastAPI(title="Talent Ops Platform API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"status": "ok", "service": "Talent Ops API"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": [],
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections
                response["database_name"] = db.name
                response["connection_status"] = "Connected"
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:80]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"

    import os as _os
    response["database_url"] = "✅ Set" if _os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if _os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response


# -----------------------------
# Simple CRUD helpers (create & list)
# -----------------------------

class CreateResponse(BaseModel):
    id: str


def _collection_name(model_cls) -> str:
    return model_cls.__name__.lower()


@app.post("/api/{entity}", response_model=CreateResponse)
async def create_entity(entity: str, payload: dict):
    mapping = {
        "user": User,
        "employee": Employee,
        "team": Team,
        "attendance": Attendance,
        "leave": Leave,
        "task": Task,
        "timesheet": Timesheet,
        "payroll": Payroll,
        "job": Job,
        "application": Application,
        "resumeparseresult": ResumeparseResult,
        "performance": Performance,
        "announcement": Announcement,
        "ticket": Ticket,
        "notification": Notification,
    }

    if entity not in mapping:
        raise HTTPException(status_code=404, detail="Unknown entity")

    model = mapping[entity](**payload)
    inserted_id = create_document(entity, model)
    return {"id": inserted_id}


@app.get("/api/{entity}")
async def list_entities(entity: str, limit: Optional[int] = 50):
    allowed = {
        "user",
        "employee",
        "team",
        "attendance",
        "leave",
        "task",
        "timesheet",
        "payroll",
        "job",
        "application",
        "resumeparseresult",
        "performance",
        "announcement",
        "ticket",
        "notification",
    }
    if entity not in allowed:
        raise HTTPException(status_code=404, detail="Unknown entity")

    docs = get_documents(entity, limit=limit)
    # Convert ObjectId to str if present
    for d in docs:
        if "_id" in d:
            d["id"] = str(d.pop("_id"))
    return {"items": docs}


# -----------------------------
# Workforce analytics & insights
# -----------------------------

@app.post("/api/analytics/insights")
async def analytics_insights(req: InsightRequest):
    # Basic demo metrics using counts; in real-world, aggregate pipeline would be used
    today = datetime.utcnow().date()
    horizon = today + timedelta(days=req.horizon_days)

    employees = len(get_documents("employee"))
    tasks_total = len(get_documents("task"))
    tasks_done = len([t for t in get_documents("task") if t.get("status") == "done"])
    open_roles = len([j for j in get_documents("job") if j.get("status") == "open"])
    tickets_open = len([t for t in get_documents("ticket") if t.get("status") in ("open", "in_progress")])

    utilization = 0.0
    ts = get_documents("timesheet")
    if employees:
        total_hours = sum(float(x.get("hours", 0)) for x in ts)
        # naive utilization proxy: avg hours per day per employee over horizon/7 weeks
        utilization = round(min(100.0, (total_hours / max(1, employees)) / (req.horizon_days) * 100 / 8), 2)

    summary = {
        "workforce_size": employees,
        "task_completion_rate": round((tasks_done / tasks_total) * 100, 2) if tasks_total else 0,
        "open_roles": open_roles,
        "tickets_open": tickets_open,
        "utilization_pct": utilization,
        "time_horizon_days": req.horizon_days,
    }

    # Basic “AI assistant” narrative without external LLM
    narrative = (
        f"Team size is {employees}. Task completion is at {summary['task_completion_rate']}%. "
        f"Utilization estimates at {utilization}%. You have {open_roles} open roles and "
        f"{tickets_open} active tickets. Consider prioritizing hiring where utilization exceeds 85% "
        f"and triage tickets older than 7 days."
    )

    return {"summary": summary, "narrative": narrative}


# -----------------------------
# Attendance & Leave shortcuts
# -----------------------------

@app.post("/api/attendance/check-in")
async def check_in(user_id: str, time: Optional[str] = None):
    t = time or datetime.utcnow().strftime("%H:%M")
    today = datetime.utcnow().date().isoformat()
    rec = Attendance(user_id=user_id, date=date.fromisoformat(today), status="present", check_in=t)
    _id = create_document("attendance", rec)
    return {"id": _id, "message": "Checked in"}


@app.post("/api/attendance/check-out")
async def check_out(user_id: str, time: Optional[str] = None):
    t = time or datetime.utcnow().strftime("%H:%M")
    today = datetime.utcnow().date().isoformat()
    rec = Attendance(user_id=user_id, date=date.fromisoformat(today), status="present", check_out=t)
    _id = create_document("attendance", rec)
    return {"id": _id, "message": "Checked out"}


# -----------------------------
# Hiring ATS: upload resume & parse (demo rule-based parser)
# -----------------------------

@app.post("/api/ats/parse-text")
async def parse_resume_text(payload: ResumeText):
    text = payload.text
    # Very lightweight heuristic parsing
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    name = lines[0] if lines else None
    email = next((l for l in lines if "@" in l and "." in l), None)
    skills = []
    keywords = [
        "python", "javascript", "react", "node", "aws", "docker", "kubernetes", "sql",
        "fastapi", "django", "java", "c++", "ml", "nlp", "git", "linux",
    ]
    lowered = text.lower()
    for k in keywords:
        if k in lowered:
            skills.append(k)
    years = None
    for l in lines:
        if "years" in l.lower():
            # naive extraction
            for token in l.split():
                if token.replace("+", "").replace(".", "").isdigit():
                    years = float(token.replace("+", ""))
                    break
            if years:
                break
    return {
        "name": name,
        "email": email,
        "skills": sorted(list(set(skills))),
        "years_experience": years,
        "raw_summary": lines[:10],
    }


# -----------------------------
# Announcements & Tickets quick create
# -----------------------------

@app.post("/api/announce")
async def announce(payload: Announcement):
    _id = create_document("announcement", payload)
    return {"id": _id}


@app.post("/api/ticket")
async def create_ticket(payload: Ticket):
    _id = create_document("ticket", payload)
    return {"id": _id}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

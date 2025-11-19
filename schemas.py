"""
Database Schemas for Talent Ops Platform

Each Pydantic model represents a MongoDB collection. The collection name is the
lowercased class name by convention (e.g., Employee -> "employee").

These schemas cover:
- Users & Employees
- Teams
- Attendance, Leave
- Tasks & Timesheets
- Payroll
- Hiring: Jobs & Applications
- Resume Parsing Results
- Performance Reviews
- Announcements
- Support Tickets
- Notifications
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Literal
from datetime import date, datetime


class User(BaseModel):
    name: str = Field(..., description="Full name")
    email: EmailStr = Field(..., description="Email address")
    role: Literal["executive", "team_lead", "employee"] = Field(
        "employee", description="Role for access control"
    )
    department: Optional[str] = Field(None, description="Department name")
    is_active: bool = Field(True, description="Whether the user is active")


class Employee(BaseModel):
    user_id: str = Field(..., description="Reference to user _id string")
    employee_id: str = Field(..., description="HR employee ID")
    title: str = Field(..., description="Job title")
    manager_id: Optional[str] = Field(None, description="Manager user id")
    team: Optional[str] = Field(None, description="Team/Pod name")
    location: Optional[str] = Field(None, description="Work location")
    salary: Optional[float] = Field(None, ge=0, description="Base salary")


class Team(BaseModel):
    name: str
    lead_user_id: Optional[str] = None
    members: List[str] = Field(default_factory=list, description="User ids")


class Attendance(BaseModel):
    user_id: str
    date: date
    status: Literal["present", "absent", "remote", "leave"] = "present"
    check_in: Optional[str] = Field(None, description="HH:MM format")
    check_out: Optional[str] = Field(None, description="HH:MM format")


class Leave(BaseModel):
    user_id: str
    start_date: date
    end_date: date
    type: Literal["annual", "sick", "unpaid", "maternity", "paternity", "other"] = "annual"
    reason: Optional[str] = None
    status: Literal["pending", "approved", "rejected"] = "pending"


class Task(BaseModel):
    title: str
    description: Optional[str] = None
    assignee_id: str
    due_date: Optional[date] = None
    status: Literal["todo", "in_progress", "blocked", "done"] = "todo"
    tags: List[str] = Field(default_factory=list)


class Timesheet(BaseModel):
    user_id: str
    task_id: Optional[str] = None
    date: date
    hours: float = Field(..., ge=0, le=24)
    notes: Optional[str] = None


class Payroll(BaseModel):
    user_id: str
    period_start: date
    period_end: date
    gross: float = Field(..., ge=0)
    tax: float = Field(0, ge=0)
    deductions: float = Field(0, ge=0)
    net: float = Field(..., ge=0)
    status: Literal["pending", "paid", "on_hold"] = "pending"


class Job(BaseModel):
    title: str
    department: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    status: Literal["open", "paused", "closed"] = "open"


class Application(BaseModel):
    job_id: str
    name: str
    email: EmailStr
    phone: Optional[str] = None
    resume_text: Optional[str] = None
    stage: Literal["applied", "screen", "interview", "offer", "hired", "rejected"] = "applied"
    score: Optional[float] = Field(None, ge=0, le=100)


class ResumeparseResult(BaseModel):
    application_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    years_experience: Optional[float] = None
    education: Optional[str] = None
    raw_summary: Optional[str] = None


class Performance(BaseModel):
    user_id: str
    period: str = Field(..., description="e.g., 2025-Q1")
    goals: List[str] = Field(default_factory=list)
    rating: Optional[float] = Field(None, ge=1, le=5)
    feedback: Optional[str] = None


class Announcement(BaseModel):
    title: str
    message: str
    audience: Literal["all", "executive", "team_lead", "employee"] = "all"
    priority: Literal["low", "normal", "high"] = "normal"
    expires_at: Optional[datetime] = None


class Ticket(BaseModel):
    user_id: str
    subject: str
    message: str
    status: Literal["open", "in_progress", "resolved", "closed"] = "open"
    assignee_id: Optional[str] = None
    category: Optional[str] = None


class Notification(BaseModel):
    user_id: str
    type: str
    title: str
    body: str
    read: bool = False


# Additional lightweight schemas used by endpoints
class InsightRequest(BaseModel):
    horizon_days: int = Field(30, ge=1, le=365)

class ResumeText(BaseModel):
    text: str


"""
Database Schemas for SENSAI

Each Pydantic model represents a collection in MongoDB.
Collection name is the lowercase of the class name.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class User(BaseModel):
    name: str
    email: str
    avatar_url: Optional[str] = None
    provider: Optional[str] = None
    created_at: Optional[datetime] = None


class Quiz(BaseModel):
    user_id: str = Field(..., description="Client-generated or provider user id")
    score: int = Field(..., ge=0, le=100)
    total_questions: int = Field(..., ge=1)
    correct_answers: int = Field(..., ge=0)
    feedback: Optional[str] = None


class ResumeExperience(BaseModel):
    company: str
    role: str
    start: str
    end: str
    description: Optional[str] = None


class ResumeEducation(BaseModel):
    school: str
    degree: str
    start: str
    end: str
    details: Optional[str] = None


class ResumeProject(BaseModel):
    name: str
    link: Optional[str] = None
    description: Optional[str] = None


class Resume(BaseModel):
    user_id: str
    email: Optional[str] = None
    linkedin: Optional[str] = None
    twitter: Optional[str] = None
    summary: Optional[str] = None
    skills: List[str] = []
    experiences: List[ResumeExperience] = []
    education: List[ResumeEducation] = []
    projects: List[ResumeProject] = []

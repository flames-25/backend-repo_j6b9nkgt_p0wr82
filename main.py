import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timezone
import requests

from database import db, create_document, get_documents

app = FastAPI(title="SENSAI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "SENSAI API is running"}


# --------- Models ---------
class QuizIn(BaseModel):
    user_id: str
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


class ResumeIn(BaseModel):
    user_id: str
    email: Optional[str] = None
    linkedin: Optional[str] = None
    twitter: Optional[str] = None
    summary: Optional[str] = None
    skills: List[str] = []
    experiences: List[ResumeExperience] = []
    education: List[ResumeEducation] = []
    projects: List[ResumeProject] = []


class CoverLetterIn(BaseModel):
    company_name: str
    job_title: str
    job_description: str
    user_name: Optional[str] = None


# --------- Quiz Endpoints ---------
@app.post("/api/quiz")
def create_quiz_result(payload: QuizIn):
    doc = payload.model_dump()
    doc["created_at"] = datetime.now(timezone.utc)
    doc["updated_at"] = datetime.now(timezone.utc)
    inserted_id = create_document("quiz", doc)
    return {"id": inserted_id, "ok": True}


@app.get("/api/quiz/stats")
def get_quiz_stats(user_id: str):
    items = get_documents("quiz", {"user_id": user_id})
    if not items:
        return {
            "average_score": 0,
            "total_questions": 0,
            "latest_score": 0,
            "count": 0,
        }
    scores = [it.get("score", 0) for it in items]
    total_questions = sum(int(it.get("total_questions", 0)) for it in items)
    latest = sorted(items, key=lambda x: x.get("created_at", datetime.min))[-1]
    return {
        "average_score": round(sum(scores) / len(scores), 2),
        "total_questions": total_questions,
        "latest_score": latest.get("score", 0),
        "count": len(items),
    }


@app.get("/api/quiz/recent")
def get_recent_quizzes(user_id: str, limit: int = 5):
    items = get_documents("quiz", {"user_id": user_id}, limit=limit)
    # Sort by created_at desc if present
    items_sorted = sorted(items, key=lambda x: x.get("created_at", datetime.min), reverse=True)
    return items_sorted


# --------- Resume Endpoints ---------
@app.post("/api/resume")
def upsert_resume(payload: ResumeIn):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    coll = db["resume"]
    payload_dict = payload.model_dump()
    payload_dict["updated_at"] = datetime.now(timezone.utc)
    payload_dict.setdefault("created_at", datetime.now(timezone.utc))
    coll.update_one({"user_id": payload.user_id}, {"$set": payload_dict}, upsert=True)
    return {"ok": True}


@app.get("/api/resume")
def get_resume(user_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    doc = db["resume"].find_one({"user_id": user_id}, {"_id": 0})
    if not doc:
        return {}
    return doc


# --------- Cover Letter (OpenAI) ---------
@app.post("/api/cover-letter")
def generate_cover_letter(payload: CoverLetterIn):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=400, detail="OPENAI_API_KEY not set")

    system_prompt = (
        "You are SENSAI, a professional career assistant. Craft tailored, concise, compelling "
        "cover letters with a confident, friendly tone. Keep to ~250-350 words."
    )

    user_prompt = (
        f"Candidate: {payload.user_name or 'The candidate'}\n"
        f"Target Role: {payload.job_title} at {payload.company_name}.\n"
        f"Job Description:\n{payload.job_description}\n\n"
        "Write a cover letter that highlights relevant skills and impact. Use a clean structure: "
        "intro, two short body paragraphs (skills + achievements), closing with a call to action."
    )

    url = "https://api.openai.com/v1/chat/completions"
    body = {
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.7,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(url, json=body, headers=headers, timeout=30)
        if resp.status_code >= 400:
            raise HTTPException(status_code=500, detail=f"OpenAI error: {resp.text[:200]}")
        data = resp.json()
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return {"text": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --------- Insights (Mock) ---------
@app.get("/api/insights")
def get_insights():
    return {
        "market_outlook": "Positive",
        "industry_growth": 8.5,
        "demand_level": "High",
        "top_skills": [
            "Python",
            "SQL",
            "Machine Learning",
            "Data Engineering",
            "Cloud (AWS/GCP)",
            "LLMs",
        ],
        "salary_ranges": [
            {"role": "Data Scientist", "min": 110, "max": 180},
            {"role": "Data Engineer", "min": 120, "max": 190},
            {"role": "ML Engineer", "min": 130, "max": 210},
            {"role": "Analytics Engineer", "min": 105, "max": 160},
            {"role": "AI Product Manager", "min": 130, "max": 200},
        ],
        "trends": [
            "Rise of LLM applications and AI copilots",
            "Data quality and governance as differentiators",
            "Real-time analytics and streaming architectures",
            "MLOps maturity: monitoring, rollback, and evaluation",
        ],
        "recommended_skills": [
            "Vector databases",
            "Prompt engineering",
            "Airflow / Dagster",
            "dbt",
            "Kubernetes",
        ],
    }


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
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

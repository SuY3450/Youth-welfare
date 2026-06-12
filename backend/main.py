import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from contextlib import asynccontextmanager
from uuid import UUID
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import Column, Text, Integer, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from database import SessionLocal, Base
from models import UserProfile
from schemas import InterestInput, UserInput
from rag.rag_pipeline import run_pipeline, policies as ALL_POLICIES, refresh_data_and_rebuild
from pydantic import BaseModel

REFRESH_INTERVAL_SEC = 30 * 60


async def _auto_refresh_loop():
    while True:
        try:
            await asyncio.sleep(REFRESH_INTERVAL_SEC)
            await asyncio.to_thread(refresh_data_and_rebuild)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"⚠️  자동 갱신 루프 에러: {type(e).__name__}: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"🔄 자동 데이터 갱신 시작 ({REFRESH_INTERVAL_SEC // 60}분 간격)")
    task = asyncio.create_task(_auto_refresh_loop())
    try:
        yield
    finally:
        task.cancel()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RagResult(Base):
    __tablename__ = "rag_results"
    id = Column(PGUUID(as_uuid=True), primary_key=True)
    total_monthly = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    eligible_count = Column(Integer, nullable=True)
    top_recommendation = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class FeedbackModel(Base):
    __tablename__ = "feedback"
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=lambda: __import__('uuid').uuid4())
    user_id = Column(PGUUID(as_uuid=True), nullable=True)
    policy_name = Column(Text, nullable=False)
    is_helpful = Column(Boolean, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class FeedbackInput(BaseModel):
    user_id: str
    policy_name: str
    is_helpful: bool

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def root():
    return {"message": "서버 작동 중!"}

@app.post("/input")
def receive_input(data: UserInput, db: Session = Depends(get_db)):
    user_uuid = UUID(data.user_id)
    existing_profile = db.query(UserProfile).filter(UserProfile.id == user_uuid).first()
    if existing_profile:
        existing_profile.age = data.age
        existing_profile.city = data.city
        existing_profile.district = data.district
        existing_profile.income = data.income
        existing_profile.job_status = data.jobStatus
        existing_profile.education = data.education
        db.commit()
        db.refresh(existing_profile)
        profile = existing_profile
    else:
        profile = UserProfile(
            id=user_uuid,
            age=data.age,
            city=data.city,
            district=data.district,
            income=data.income,
            job_status=data.jobStatus,
            education=data.education,
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return {
        "status": "success",
        "message": "온보딩 정보 저장 완료",
        "profile_id": str(profile.id),
        "data": {
            "age": profile.age,
            "city": profile.city,
            "district": profile.district,
            "income": profile.income,
            "jobStatus": profile.job_status,
            "education": profile.education,
            "interests": profile.interests,
        },
    }

@app.post("/interest")
def receive_interest(data: InterestInput, db: Session = Depends(get_db)):
    try:
        profile_uuid = UUID(data.profile_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="profile_id 형식이 올바르지 않습니다.")
    profile = db.query(UserProfile).filter(UserProfile.id == profile_uuid).first()
    if not profile:
        raise HTTPException(status_code=404, detail="해당 프로필을 찾을 수 없습니다.")
    profile.interests = ",".join(data.interests)
    db.commit()
    db.refresh(profile)
    return {
        "status": "success",
        "message": "관심분야 저장 완료",
        "profile_id": str(profile.id),
        "interests": profile.interests.split(",") if profile.interests else [],
    }

@app.get("/profile/{profile_id}")
def get_profile_by_id(profile_id: str, db: Session = Depends(get_db)):
    try:
        profile_uuid = UUID(profile_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="profile_id 형식이 올바르지 않습니다.")
    profile = db.query(UserProfile).filter(UserProfile.id == profile_uuid).first()
    if not profile:
        raise HTTPException(status_code=404, detail="해당 프로필을 찾을 수 없습니다.")
    return {
        "id": str(profile.id),
        "age": profile.age,
        "city": profile.city,
        "district": profile.district,
        "income": profile.income,
        "jobStatus": profile.job_status,
        "education": profile.education,
        "interests": profile.interests.split(",") if profile.interests else [],
    }

@app.get("/profile")
def get_latest_profile(db: Session = Depends(get_db)):
    profile = db.query(UserProfile).order_by(UserProfile.created_at.desc()).first()
    if not profile:
        raise HTTPException(status_code=404, detail="저장된 프로필이 없습니다.")
    return {
        "id": str(profile.id),
        "age": profile.age,
        "city": profile.city,
        "district": profile.district,
        "income": profile.income,
        "jobStatus": profile.job_status,
        "education": profile.education,
        "interests": profile.interests.split(",") if profile.interests else [],
    }

@app.post("/welfare/analyze")
async def analyze(profile_id: str, db: Session = Depends(get_db)):
    try:
        profile_uuid = UUID(profile_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="profile_id 형식이 올바르지 않습니다.")

    profile = db.query(UserProfile).filter(UserProfile.id == profile_uuid).first()
    if not profile:
        raise HTTPException(status_code=404, detail="해당 프로필을 찾을 수 없습니다.")

    interests = profile.interests.split(",") if profile.interests else []
    interest_map = {
        'housing': '주거', 'finance': '금융', 'job': '일자리',
        'edu': '교육', 'startup': '창업',
    }
    interests_korean = [interest_map.get(i.strip(), i.strip()) for i in interests]

    income_map = {
        '50% 이하': '50% 이하',
        '50~100% 이하': '50~100%',
        '100~150%': '100~150%',
        '150% 초과': '150% 초과',
    }
    income_level = income_map.get(profile.income, profile.income)

    employment_map = {
        '재직': '근무',
        '구직': '미취업',
        '프리랜서': '프리랜서',
    }
    employment = employment_map.get(profile.job_status, profile.job_status)

    raw_district = (profile.district or "").strip()
    sub_region = "" if raw_district.endswith("전체") else raw_district

    user_info = {
        "age": int(profile.age),
        "region": profile.city,
        "sub_region": sub_region,
        "income_level": income_level,
        "employment": employment,
        "education": profile.education if profile.education else "",
        "housing": "",
        "interests": interests_korean,
    }

    result = run_pipeline(user_info)

    existing_rag = db.query(RagResult).filter(RagResult.id == profile_uuid).first()
    if existing_rag:
        existing_rag.total_monthly = result.get("total_monthly", "")
        existing_rag.summary = result.get("summary", "")
        existing_rag.eligible_count = len(result.get("eligible_policies", []))
        existing_rag.top_recommendation = result.get("top_recommendation", "")
        db.commit()
    else:
        rag_result = RagResult(
            id=profile_uuid,
            total_monthly=result.get("total_monthly", ""),
            summary=result.get("summary", ""),
            eligible_count=len(result.get("eligible_policies", [])),
            top_recommendation=result.get("top_recommendation", ""),
        )
        db.add(rag_result)
        db.commit()

    return result

@app.get("/rag-result/{profile_id}")
def get_rag_result(profile_id: str, db: Session = Depends(get_db)):
    try:
        profile_uuid = UUID(profile_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="profile_id 형식이 올바르지 않습니다.")
    rag = db.query(RagResult).filter(RagResult.id == profile_uuid).first()
    if not rag:
        raise HTTPException(status_code=404, detail="RAG 결과가 없습니다.")
    return {
        "total_monthly": rag.total_monthly,
        "summary": rag.summary,
        "eligible_count": rag.eligible_count,
        "top_recommendation": rag.top_recommendation,
    }

@app.get("/policy/{policy_id}")
def get_policy_by_id(policy_id: str):
    for p in ALL_POLICIES:
        if str(p.get("id", "")) == policy_id:
            return p
    raise HTTPException(status_code=404, detail="해당 정책을 찾을 수 없습니다.")

@app.post("/feedback")
def submit_feedback(data: FeedbackInput, db: Session = Depends(get_db)):
    try:
        user_uuid = UUID(data.user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="user_id 형식이 올바르지 않습니다.")
    feedback = FeedbackModel(
        user_id=user_uuid,
        policy_name=data.policy_name,
        is_helpful=data.is_helpful,
    )
    db.add(feedback)
    db.commit()
    return {"status": "success", "message": "피드백 저장 완료"}

@app.get("/feedback/stats")
def get_feedback_stats(db: Session = Depends(get_db)):
    feedbacks = db.query(FeedbackModel).all()
    stats = {}
    for f in feedbacks:
        name = f.policy_name
        if name not in stats:
            stats[name] = {"yes": 0, "no": 0}
        if f.is_helpful:
            stats[name]["yes"] += 1
        else:
            stats[name]["no"] += 1
    result = []
    for policy_name, counts in stats.items():
        total = counts["yes"] + counts["no"]
        percent = round(counts["yes"] / total * 100, 1) if total > 0 else 0
        result.append({
            "policy_name": policy_name,
            "yes": counts["yes"],
            "no": counts["no"],
            "total": total,
            "helpful_percent": percent,
        })
    return sorted(result, key=lambda x: -x["helpful_percent"])

@app.get("/result")
def get_result():
    return {
        "results": [
            {
                "id": 1,
                "rank": "1순위",
                "title": "청년 월세 한시 특별지원",
                "org": "국토교통부 · 전국",
                "tags": [
                    {"label": "주거", "type": "green"},
                    {"label": "자격 충족", "type": "green"},
                    {"label": "마감 D-7", "type": "orange"},
                ],
                "amount": "월 20만원",
                "period": "× 12개월",
                "warning": None,
            },
            {
                "id": 2,
                "rank": "2순위",
                "title": "청년도약계좌",
                "org": "금융위원회 · 전국",
                "tags": [
                    {"label": "금융", "type": "green"},
                    {"label": "자격 충족", "type": "green"},
                ],
                "amount": "최대 5,000만원",
                "period": "5년 만기",
                "warning": "청년희망적금과 중복 가입 불가 → 도약계좌가 유리",
            },
            {
                "id": 3,
                "rank": "3순위",
                "title": "청년내일저축계좌",
                "org": "보건복지부 · 전국",
                "tags": [
                    {"label": "금융", "type": "green"},
                    {"label": "자격 충족", "type": "green"},
                ],
                "amount": "최대 1,440만원",
                "period": "3년 만기",
                "warning": None,
            },
        ]
    }
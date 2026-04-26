from uuid import UUID
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import SessionLocal
from models import UserProfile
from schemas import InterestInput, UserInput

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    new_profile = UserProfile(
        age=data.age,
        city=data.city,
        district=data.district,
        income=data.income,
        job_status=data.jobStatus,
        education=data.education,
    )
    db.add(new_profile)
    db.commit()
    db.refresh(new_profile)
    return {
        "status": "success",
        "message": "온보딩 정보 저장 완료",
        "profile_id": str(new_profile.id),
        "data": {
            "age": new_profile.age,
            "city": new_profile.city,
            "district": new_profile.district,
            "income": new_profile.income,
            "jobStatus": new_profile.job_status,
            "education": new_profile.education,
            "interests": new_profile.interests,
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
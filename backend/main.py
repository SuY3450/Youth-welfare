import os
from uuid import UUID

import jwt
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from jwt import PyJWKClient
from sqlalchemy.orm import Session

from database import SessionLocal
from models import UserProfile
from schemas import InterestInput, UserInput

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
if not SUPABASE_URL:
    raise RuntimeError("SUPABASE_URL 환경변수가 설정되지 않았습니다.")

JWKS_URL = f"{SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json"
jwks_client = PyJWKClient(JWKS_URL, cache_keys=True, lifespan=300)

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


def get_current_user_id(authorization: str = Header(None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="인증 토큰이 필요합니다.")

    token = authorization.replace("Bearer ", "")
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256", "RS256", "EdDSA"],
            audience="authenticated",
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="토큰이 만료되었습니다.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다.")
    except Exception:
        raise HTTPException(status_code=401, detail="토큰 검증에 실패했습니다.")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="토큰에서 사용자 정보를 찾을 수 없습니다.")
    return user_id

@app.get("/")
def root():
    return {"message": "서버 작동 중!"}

@app.post("/input")
def receive_input(
    data: UserInput,
    verified_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        user_uuid = UUID(verified_user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="user_id 형식이 올바르지 않습니다.")

    profile = db.query(UserProfile).filter(UserProfile.id == user_uuid).first()

    if profile:
        profile.age = data.age
        profile.city = data.city
        profile.district = data.district
        profile.income = data.income
        profile.job_status = data.jobStatus
        profile.education = data.education
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
def receive_interest(
    data: InterestInput,
    verified_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        user_uuid = UUID(verified_user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="user_id 형식이 올바르지 않습니다.")

    profile = db.query(UserProfile).filter(UserProfile.id == user_uuid).first()
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
def get_profile_by_id(
    profile_id: str,
    verified_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    if profile_id != verified_user_id:
        raise HTTPException(status_code=403, detail="본인의 프로필만 조회할 수 있습니다.")

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
def get_my_profile(
    verified_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        user_uuid = UUID(verified_user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="user_id 형식이 올바르지 않습니다.")

    profile = db.query(UserProfile).filter(UserProfile.id == user_uuid).first()
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
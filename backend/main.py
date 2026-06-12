import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from contextlib import asynccontextmanager
from uuid import UUID
from fastapi import Depends, FastAPI, HTTPException, File, UploadFile, Form
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
import fitz

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

class ChatInput(BaseModel):
    message: str
    user_id: str
    pdf_context: str = ""

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_user_info_str(user_id: str, db: Session) -> str:
    try:
        user_uuid = UUID(user_id)
        profile = db.query(UserProfile).filter(UserProfile.id == user_uuid).first()
        if profile:
            interests = profile.interests.split(",") if profile.interests else []
            interest_map = {
                'housing': '주거', 'finance': '금융', 'job': '일자리',
                'edu': '교육', 'startup': '창업',
            }
            interests_korean = [interest_map.get(i.strip(), i.strip()) for i in interests]
            return f"""
사용자 정보:
- 나이: {profile.age}세
- 지역: {profile.city} {profile.district}
- 소득: {profile.income}
- 취업상태: {profile.job_status}
- 학력: {profile.education}
- 관심분야: {', '.join(interests_korean)}
"""
    except:
        pass
    return ""

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

@app.post("/welfare/chat")
async def chat(data: ChatInput, db: Session = Depends(get_db)):
    try:
        print(f"💬 챗봇 요청: {data.message[:30]}")
        user_info = get_user_info_str(data.user_id, db)

        from langchain_google_genai import ChatGoogleGenerativeAI
        from langchain_core.messages import HumanMessage

        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=os.getenv("GEMINI_API_KEY"),
            max_retries=0,
        )

        # ChromaDB에서 관련 정책 검색
        from rag.rag_pipeline import vectorstore, get_full_policy
        policy_context = ""
        try:
            scored = vectorstore.similarity_search_with_score(data.message, k=5)
            for doc, score in scored:
                similarity = round(max(0.0, 1 - score) * 100, 1)
                if similarity < 40:
                    continue
                pid = doc.metadata.get("id", "")
                full = get_full_policy(pid)
                policy_context += f"""
[{doc.metadata.get('name','')}] (유사도 {similarity}%)
- 지원금액: {doc.metadata.get('amount','정보없음')}
- 지역: {doc.metadata.get('region','')} {doc.metadata.get('sub_region','')}
- 마감: {doc.metadata.get('deadline','정보없음')}
- 정책 내용: {str(full.get('raw_text',''))[:400]}
- 추가 자격: {str(full.get('add_qlfc',''))[:200]}
- 제외 대상: {str(full.get('exclude_target',''))[:200]}
- 신청 방법: {str(full.get('apply_method',''))[:200]}
"""
            print(f"🔍 챗봇 ChromaDB 검색: {len(scored)}건")
        except Exception as e:
            print(f"⚠️ ChromaDB 검색 실패: {e}")

        # PDF 컨텍스트
        pdf_section = ""
        if data.pdf_context:
            pdf_section = f"""
[업로드된 PDF 내용]
{data.pdf_context}
위 PDF 내용을 참고하여 답변해주세요.
"""

        prompt = f"""당신은 청년 복지 정책 전문 AI 상담사입니다.

[중요 규칙 - 반드시 준수]
1. 반드시 아래 [관련 정책 데이터]에 있는 내용만 답변하세요
2. 아래 [관련 정책 데이터]가 비어있거나 질문과 관련없는 경우
   반드시 이 형식으로만 답변하세요:

"죄송해요, 해당 질문은 제가 답변드리기 어렵습니다 😢
저는 청년 복지 정책 추천과 안내만 도와드릴 수 있어요.

아래와 같이 질문해주시면 도움드릴 수 있어요!
- '주거 지원 정책 추천해줘'
- '청년 취업 관련 혜택 알려줘'
- '월세 지원 신청 방법이 뭐야?'"

3. 소득 기준/중위소득 계산/나이 기준 등
   일반 복지 상식 질문도 위 형식으로 답변하세요
4. 데이터에 없는 내용은 절대 추측하지 마세요

{user_info}
{pdf_section}

[관련 정책 데이터]
{policy_context if policy_context else "관련 정책 데이터 없음"}

사용자 질문: {data.message}

[답변 형식 - 관련 데이터 있을 때만]
- 줄글 금지! 항목별로 나눠서 답변
- 이모지 적절히 사용

📌 정책명
- 지원 대상:
- 지원 금액:
- 신청 방법:
- 신청 기간:

💡 추가 안내
- 문의: 정책 담당 기관"""

        response = llm.invoke([HumanMessage(content=prompt)])
        return {"reply": response.content}

    except Exception as e:
        print(f"❌ 챗봇 최종 에러: {type(e).__name__}: {e}")
        if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
            return {"reply": "현재 AI 서비스 이용량이 초과되었어요 😢\n잠시 후 다시 시도해주세요!"}
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/welfare/chat/pdf")
async def chat_pdf(
    file: UploadFile = File(...),
    user_id: str = Form(default=""),
    db: Session = Depends(get_db)
):
    try:
        contents = await file.read()
        doc = fitz.open(stream=contents, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()

        if not text.strip():
            raise HTTPException(status_code=400, detail="PDF에서 텍스트를 추출할 수 없습니다.")

        user_info = get_user_info_str(user_id, db)

        from langchain_google_genai import ChatGoogleGenerativeAI
        from langchain_core.messages import HumanMessage

        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=os.getenv("GEMINI_API_KEY"),
            max_retries=0,
        )

        prompt = f"""당신은 청년 복지 정책 전문 AI 상담사입니다.
아래 PDF 내용을 분석하고 다음 형식으로 정리해주세요.

{user_info}

[PDF 내용]
{text[:3000]}

[답변 형식]
📄 문서 요약
- 문서 종류:
- 주요 내용:

📌 관련 정책/혜택
- 정책명:
- 지원 금액:
- 신청 방법:

✅ 이 사용자에게 도움이 되는 정보
-

❓ 추가로 궁금한 점이 있으면 질문해주세요!"""

        response = llm.invoke([HumanMessage(content=prompt)])

        return {
            "reply": response.content,
            "pdf_text": text[:2000],
        }

    except Exception as e:
        print(f"❌ PDF 처리 에러: {type(e).__name__}: {e}")
        if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
            return {"reply": "현재 AI 서비스 이용량이 초과되었어요 😢\n잠시 후 다시 시도해주세요!", "pdf_text": ""}
        raise HTTPException(status_code=500, detail=str(e))

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
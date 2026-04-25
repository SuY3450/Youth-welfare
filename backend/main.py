from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class UserInput(BaseModel):
    age: str
    city: str
    district: str
    income: str
    jobStatus: str
    education: str

class InterestInput(BaseModel):
    interests: list[str]

@app.get("/")
def root():
    return {"message": "서버 작동 중!"}

@app.post("/input")
def receive_input(data: UserInput):
    print(f"받은 데이터: {data}")
    return {"status": "success", "data": data}

@app.post("/interest")
def receive_interest(data: InterestInput):
    print(f"받은 관심분야: {data.interests}")
    return {"status": "success", "data": data}

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

@app.get("/profile")
def get_profile():
    return {
        "name": "홍길동",
        "age": "27",
        "city": "서울특별시",
        "district": "마포구",
        "income": "50~100% 이하",
        "jobStatus": "구직",
        "education": "대학 졸업",
    }
#프론트엔드에서 FastAPI로 보내는 데이터 형식을 검사하는 파일

from pydantic import BaseModel


class UserInput(BaseModel):
    age: int
    city: str
    district: str
    income: str
    jobStatus: str
    education: str


class InterestInput(BaseModel):
    profile_id: str
    interests: list[str]
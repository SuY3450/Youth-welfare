# LLM ↔ 백엔드 연동 가이드

> 작성자: 유진 (LLM)

---

## 한줄 요약

**`rag_pipeline.py` 안에 있는 `run_pipeline(user_info)` 함수를 호출하면 추천 결과가 dict로 반환됩니다.**

---

## 필요한 파일

| 파일 | 용도 | 위치 |
|------|------|------|
| `rag_pipeline.py` | LLM 파이프라인 코드 | 깃허브 capstonecode/ |
| `clean_final.json` | 정책 데이터 344건 | 깃허브 capstonecode/ |
| `.env` | API 키 (깃허브에 올리지 마세요!) | 로컬에만 |

### .env 파일 내용

```
GEMINI_API_KEY=제미나이_API_키
```

### 필요한 패키지

```bash
pip install langchain langchain-google-genai langchain-chroma langchain-huggingface
pip install chromadb sentence-transformers python-dotenv
```

---

## 호출 방법

### 1. 함수 호출

```python
from rag_pipeline import run_pipeline

result = run_pipeline(user_info)
```

### 2. FastAPI 엔드포인트 예시

```python
from fastapi import APIRouter
from pydantic import BaseModel
from rag_pipeline import run_pipeline

router = APIRouter()

class AnalyzeRequest(BaseModel):
    age: int
    region: str
    sub_region: str = ""
    income_level: str
    employment: str
    education: str = ""
    housing: str = ""
    interests: list[str]

@router.post("/welfare/analyze")
async def analyze(req: AnalyzeRequest):
    user_info = req.dict()
    result = run_pipeline(user_info)
    return result
```

---

## 입력 형식 (user_info)

프론트에서 온보딩 완료 후 넘어오는 데이터입니다.

```json
{
  "age": 27,
  "region": "서울특별시",
  "sub_region": "서초구",
  "income_level": "100~150%",
  "employment": "근무",
  "education": "대학교 졸업",
  "housing": "월세 자취",
  "interests": ["주거", "금융"]
}
```

### 각 필드 설명

| 필드 | 필수 | 설명 | 허용값 |
|------|------|------|--------|
| age | ✅ | 만 나이 | 18~39 숫자 |
| region | ✅ | 광역시도 | 아래 목록 참고 |
| sub_region | ❌ | 시/군/구 | 없으면 "" |
| income_level | ✅ | 소득 구간 | "50% 이하" / "50~100%" / "100~150%" / "150% 초과" |
| employment | ✅ | 취업 상태 | "미취업" / "근무" / "프리랜서" |
| education | ❌ | 최종 학력 | "고등학교 졸업" / "대학교 재학" / "대학교 졸업" / "대학원 이상" |
| housing | ❌ | 주거 형태 | "월세 자취" / "전세" / "자가" / "기숙사" / "부모님 동거" |
| interests | ✅ | 관심 분야 | ["주거","금융","일자리","교육"] 중 1개 이상 |

### region 허용값

```
서울특별시 / 경기도 / 인천광역시 / 부산광역시 / 대구광역시
광주광역시 / 대전광역시 / 울산광역시 / 세종특별자치시
강원도 / 충청북도 / 충청남도 / 전라북도 / 전라남도
경상북도 / 경상남도 / 제주특별자치도
```

---

## 출력 형식 (result)

`run_pipeline()` 이 반환하는 dict 구조입니다.

```json
{
  "results": [
    {
      "name": "2026년 평택시 청년 월세 지원",
      "priority": 1,
      "fit_score": "60.5%",
      "amount": "월 20만원",
      "reason": "월세 부담을 직접 경감해주는 정책"
    },
    {
      "name": "청년 1인가구 전월세 안심계약 지원",
      "priority": 2,
      "fit_score": "52.5%",
      "amount": "",
      "reason": "전월세 계약 안전 지원"
    }
  ],
  "top_recommendation": "2026년 평택시 청년 월세 지원",
  "total_monthly": "월 20만원",
  "summary": "26세 경기도 취업준비생에게 월세 지원 정책을 추천합니다.",
  "eligible_policies": [
    {
      "name": "2026년 평택시 청년 월세 지원",
      "category": "주거",
      "amount": "월 20만원",
      "source": "경기청년포털",
      "source_url": "https://youth.gg.go.kr/...",
      "eligible": true,
      "fit_score": 60.5,
      "similarity": 2.0,
      "reasons": ["나이 ✅", "지역 ✅", "소득 ✅", "취업상태 ✅"]
    }
  ],
  "performance": {
    "total_time": 18.64,
    "searched": 15,
    "eligible": 9,
    "eligible_rate": 60.0,
    "avg_fit": 53.4
  }
}
```

### 프론트에서 필요한 필드

| 필드 | 용도 | 화면 |
|------|------|------|
| results | 추천 정책 카드 리스트 | Screen 6: 추천 결과 |
| top_recommendation | 1순위 정책 하이라이트 | Screen 6 상단 |
| total_monthly | 월 수령액 합계 | Screen 6 상단 |
| summary | 사용자 맞춤 요약 | Screen 6 상단 |
| eligible_policies[].source_url | 원본 페이지 이동 | 상세 페이지 링크 |
| performance | 디버깅용 (프론트 미노출 가능) | - |

---

## 에러 처리

| 상황 | result 값 |
|------|-----------|
| 적합 정책 0건 | `{"results": [], "summary": "조건에 맞는 정책이 없습니다."}` |
| LLM JSON 파싱 실패 | 자격 판단 결과로 자체 응답 생성 (서비스 안 죽음) |
| 필수 필드 누락 | 백엔드에서 400 에러 반환해주세요 |

---

## 데이터 업데이트 흐름

```
승현이 자동 크롤링 (매주)
    ↓
새 clean_final.json 생성
    ↓
ChromaDB 재적재 (load_to_chroma.py)
    ↓
rag_pipeline.py는 수정 없이 최신 데이터 사용
```

LLM 코드 수정 없이 데이터만 교체하면 됩니다.

---

## 주의사항

1. `.env` 파일은 깃허브에 올리지 마세요 (API 키 노출)
2. 첫 실행 시 임베딩 모델 다운로드 (약 400MB, 1회만)
3. 응답 시간 약 15~20초 (Gemini API 호출 포함)
4. ChromaDB 폴더(`chroma_db/`)는 `.gitignore`에 추가 권장

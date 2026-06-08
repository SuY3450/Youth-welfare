"""
청년 복지 정책 RAG 파이프라인 v5
=================================================
v4 대비 추가:
  ① Cosine Similarity (친구 코드에 이미 반영)
  ② AI 챗봇 상담 기능 (chat_about_policy)
  ⑤ 최적 포트폴리오 추천 (금액 최대화 조합)
  ⑥ 정책 만료 자동 제외 (deadline 기반)
  ⑦ 빈 필드를 LLM이 raw_text 읽고 채우기
  ⑧ LLM 제외 대상 정밀 판단
"""
import os, time, json, re
import urllib.request
import urllib.error
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.messages import HumanMessage
from conflict_checker import check_conflicts, get_optimal_combination, print_conflict_report

load_dotenv()

# ══════════════════════════════════════════════════════════
#  공통 LLM 인스턴스
# ══════════════════════════════════════════════════════════
def get_llm():
    return ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=os.getenv("GEMINI_API_KEY"))


# ══════════════════════════════════════════════════════════
#  시군구 사전
# ══════════════════════════════════════════════════════════
SIGUNGU_MAP = {
    "서울특별시": [
        "종로구","중구","용산구","성동구","광진구","동대문구","중랑구","성북구",
        "강북구","도봉구","노원구","은평구","서대문구","마포구","양천구","강서구",
        "구로구","금천구","영등포구","동작구","관악구","서초구","강남구","송파구","강동구",
    ],
    "경기도": [
        "수원시","성남시","의정부시","안양시","부천시","광명시","평택시","동두천시",
        "안산시","고양시","과천시","구리시","남양주시","오산시","시흥시","군포시",
        "의왕시","하남시","용인시","파주시","이천시","안성시","김포시","화성시",
        "광주시","양주시","포천시","여주시","연천군","가평군","양평군",
    ],
    "인천광역시": [
        "중구","동구","미추홀구","연수구","남동구","부평구","계양구","서구","강화군","옹진군",
    ],
    "부산광역시": [
        "중구","서구","동구","영도구","부산진구","동래구","남구","북구",
        "해운대구","사하구","금정구","강서구","연제구","수영구","사상구","기장군",
    ],
    "대구광역시": ["중구","동구","서구","남구","북구","수성구","달서구","달성군"],
    "광주광역시": ["동구","서구","남구","북구","광산구"],
    "대전광역시": ["동구","중구","서구","유성구","대덕구"],
    "울산광역시": ["중구","남구","동구","북구","울주군"],
}


def extract_sub_region_smart(raw_text: str, emb_text: str, region: str) -> str:
    candidates = SIGUNGU_MAP.get(region, [])
    if not candidates:
        return ""
    raw_found, emb_found = "", ""
    for sg in candidates:
        if sg in (raw_text or ""):
            raw_found = sg; break
    for sg in candidates:
        if sg in (emb_text or ""):
            emb_found = sg; break
    if raw_found and emb_found:
        return raw_found if raw_found == emb_found else emb_found
    return emb_found or raw_found


def extract_amount_from_text(text: str) -> str:
    if not text: return ""
    UNIT = r'(?:천\s*만\s*원|천만\s*원|억\s*원|만\s*원|만원|천만원|억원)'
    AMOUNT = rf'[\d,]+\s*{UNIT}'
    BIG_RAW_WON = r'[\d,]{5,}\s*원'
    patterns = [
        rf'(?:월|연|분기)\s*최대\s*{AMOUNT}\s*(?:지급|지원)',
        rf'(?:월|연|분기)\s*{AMOUNT}\s*(?:지급|지원)',
        rf'최대\s*{AMOUNT}\s*(?:지급|지원|한도|보조|대출|융자)',
        rf'{AMOUNT}\s*(?:지급|지원|한도|보조|대출|융자)',
        rf'{BIG_RAW_WON}\s*(?:지급|지원|한도|보조)',
        rf'(?:월|연|분기)\s*최대\s*{AMOUNT}',
        rf'(?:월|연|분기)\s*{AMOUNT}',
        rf'최대\s*{AMOUNT}',
        AMOUNT,
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match: return match.group(0).strip()
    return ""


def parse_income_condition(earn_cnd: str) -> int:
    if not earn_cnd or earn_cnd in ("무관", "제한없음"): return 0
    match = re.search(r'(\d+)\s*%', earn_cnd)
    return int(match.group(1)) if match else 0


# ══════════════════════════════════════════════════════════
#  [신규 ⑥] 정책 만료 자동 제외
# ══════════════════════════════════════════════════════════
def is_policy_expired(policy: dict) -> bool:
    """deadline 필드 기반 만료 확인. 만료 → True"""
    deadline = str(policy.get("deadline", "") or "").strip()
    if not deadline or deadline == "상시":
        return False
    # 다양한 날짜 형식 파싱
    for fmt in ["%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d", "%Y년 %m월 %d일"]:
        try:
            dl_date = datetime.strptime(deadline, fmt)
            return dl_date.date() < datetime.now().date()
        except ValueError:
            continue
    # "2026. 5. 13.(수)" 같은 형식
    match = re.search(r'(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})', deadline)
    if match:
        try:
            dl_date = datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
            return dl_date.date() < datetime.now().date()
        except:
            pass
    return False


# ══════════════════════════════════════════════════════════
#  [신규 ⑦] 빈 필드를 LLM이 raw_text 읽고 채우기
# ══════════════════════════════════════════════════════════
def llm_fill_missing_fields(policy: dict) -> dict:
    """age_min/age_max/earn_cnd/job이 비어있으면 LLM이 raw_text 읽고 추출"""
    age_min = policy.get("age_min", "")
    age_max = policy.get("age_max", "")
    earn_cnd = policy.get("earn_cnd", "")
    job = policy.get("job", "")

    needs_fill = (
        (not age_min or age_min == "0") and (not age_max or age_max == "99")
    ) or (not earn_cnd or earn_cnd in ("", "무관")) or (not job or job in ("", "제한없음"))

    if not needs_fill:
        return policy

    raw_text = str(policy.get("raw_text", ""))[:600]
    emb_text = str(policy.get("embedding_text", ""))[:300]
    if not raw_text and not emb_text:
        return policy

    try:
        llm = get_llm()
        prompt = f"""아래 정책 원문을 읽고 자격조건을 추출하세요.

[정책 원문]
{raw_text}
{emb_text}

아래 항목 중 빈 값만 추출하세요. 원문에 없으면 "미상"으로 답하세요.
JSON 형식으로만 응답 (마크다운 없이):
{{
  "age_min": "최소 나이 (숫자만, 예: 19)",
  "age_max": "최대 나이 (숫자만, 예: 39)",
  "earn_cnd": "소득 조건 (예: 중위소득 60% 이하, 무관)",
  "job": "직업/취업상태 조건 (예: 미취업, 재직자, 제한없음)"
}}"""
        response = llm.invoke([HumanMessage(content=prompt)])
        result = json.loads(response.content.replace("```json","").replace("```","").strip())

        if (not age_min or age_min == "0") and result.get("age_min","미상") != "미상":
            policy["age_min"] = result["age_min"]
        if (not age_max or age_max == "99") and result.get("age_max","미상") != "미상":
            policy["age_max"] = result["age_max"]
        if (not earn_cnd or earn_cnd in ("","무관")) and result.get("earn_cnd","미상") != "미상":
            policy["earn_cnd"] = result["earn_cnd"]
        if (not job or job in ("","제한없음")) and result.get("job","미상") != "미상":
            policy["job"] = result["job"]

        print(f"   🧠 LLM 필드 보완: {policy.get('name','')[:30]} → age:{result.get('age_min','')}-{result.get('age_max','')}, earn:{result.get('earn_cnd','')[:15]}, job:{result.get('job','')[:15]}")
    except Exception as e:
        print(f"   ⚠️ LLM 필드 보완 실패: {e}")

    return policy


# ══════════════════════════════════════════════════════════
#  [신규 ⑧] LLM 제외 대상 정밀 판단
# ══════════════════════════════════════════════════════════
def llm_check_exclude_target(policy: dict, user_info: dict) -> dict:
    """exclude_target + add_qlfc를 LLM이 사용자 정보와 대조하여 판단"""
    exclude = str(policy.get("exclude_target", "") or "")
    add_qlfc = str(policy.get("add_qlfc", "") or "")

    if not exclude and not add_qlfc:
        return {"excluded": False, "reason": ""}

    try:
        llm = get_llm()
        prompt = f"""아래 정책의 '제외 대상'과 '추가 자격'을 읽고, 이 사용자가 해당하는지 판단하세요.

[사용자 정보]
- 나이: {user_info['age']}세
- 거주지: {user_info['region']} {user_info.get('sub_region','')}
- 취업상태: {user_info['employment']}
- 소득: 중위소득 {user_info.get('income_pct',100)}%
- 주거형태: {user_info.get('housing','')}
- 학력: {user_info.get('education','')}

[제외 대상]
{exclude[:300]}

[추가 자격조건]
{add_qlfc[:300]}

JSON 형식으로만 응답 (마크다운 없이):
{{
  "excluded": true 또는 false,
  "reason": "판단 이유 한 줄"
}}"""
        response = llm.invoke([HumanMessage(content=prompt)])
        result = json.loads(response.content.replace("```json","").replace("```","").strip())
        return result
    except:
        return {"excluded": False, "reason": ""}


# ══════════════════════════════════════════════════════════
#  [신규 ⑤] 최적 포트폴리오 (금액 최대화)
# ══════════════════════════════════════════════════════════
def parse_amount_number(amount_str: str) -> int:
    """금액 문자열에서 월 기준 만원 단위 숫자 추출"""
    if not amount_str: return 0
    # "월 최대 20만원" → 20
    match = re.search(r'월\s*(?:최대\s*)?(\d+)\s*만\s*원', amount_str)
    if match: return int(match.group(1))
    # "최대 1,000만원" → 1000 (일시금이라 월 환산 안 함)
    match = re.search(r'최대\s*([\d,]+)\s*만\s*원', amount_str)
    if match: return 0  # 일시금은 월 합산에서 제외
    # "연 120만원" → 10 (12개월 나눔)
    match = re.search(r'연\s*([\d,]+)\s*만\s*원', amount_str)
    if match: return int(match.group(1).replace(",","")) // 12
    return 0


def calculate_optimal_portfolio(policies: list) -> dict:
    """금액 최대화 조합 계산"""
    total_monthly = 0
    monthly_policies = []
    onetime_policies = []

    for p in policies:
        amount_str = p.get("amount", "")
        monthly = parse_amount_number(amount_str)
        if monthly > 0:
            total_monthly += monthly
            monthly_policies.append({"name": p["name"], "monthly": monthly, "amount": amount_str})
        elif amount_str:
            onetime_policies.append({"name": p["name"], "amount": amount_str})

    return {
        "total_monthly_만원": total_monthly,
        "total_monthly_text": f"월 약 {total_monthly}만원" if total_monthly > 0 else "산정 불가",
        "monthly_policies": monthly_policies,
        "onetime_policies": onetime_policies,
    }


# ══════════════════════════════════════════════════════════
#  [신규 ②] AI 챗봇 상담
# ══════════════════════════════════════════════════════════
def chat_about_policy(user_question: str, recommended_policies: list, user_info: dict = None) -> str:
    """추천 정책에 대해 사용자 질문에 LLM이 답변"""
    context = "\n\n".join([
        f"[{p['name']}]\n"
        f"지원방식: {p.get('pvmthd','')}\n"
        f"금액: {p.get('amount','')}\n"
        f"지역: {p.get('region','')} {p.get('sub_region','')}\n"
        f"정책 내용: {p.get('raw_text','')[:400]}\n"
        f"추가 자격: {p.get('add_qlfc','')[:200]}\n"
        f"제외 대상: {p.get('exclude_target','')[:200]}\n"
        f"신청 방법: {p.get('apply_method','')[:200]}"
        for p in recommended_policies[:5]
    ])

    user_context = ""
    if user_info:
        user_context = f"""
[사용자 정보]
- {user_info.get('age','')}세 / {user_info.get('region','')} {user_info.get('sub_region','')}
- 취업: {user_info.get('employment','')} / 소득: 중위 {user_info.get('income_pct',100)}%
- 주거: {user_info.get('housing','')} / 학력: {user_info.get('education','')}
"""

    prompt = f"""당신은 청년 복지 정책 전문 상담사입니다.
아래 추천된 정책 정보를 바탕으로 사용자 질문에 친절하고 정확하게 답변하세요.

정책 원문에 없는 내용은 추측하지 말고 "해당 정보는 정책 원문에 명시되어 있지 않습니다. 관할 기관에 문의해주세요." 라고 답하세요.
{user_context}
[추천된 정책 정보]
{context}

[사용자 질문]
{user_question}

답변:"""

    try:
        llm = get_llm()
        response = llm.invoke([HumanMessage(content=prompt)])
        return response.content
    except Exception as e:
        return f"죄송합니다, 일시적으로 답변을 생성할 수 없습니다. ({e})"


# ══════════════════════════════════════════════════════════
#  1. 임베딩 + 데이터 로드
# ══════════════════════════════════════════════════════════
print("임베딩 모델 로딩 중...")
embeddings = HuggingFaceEmbeddings(
    model_name="jhgan/ko-sroberta-multitask",
    encode_kwargs={"normalize_embeddings": True},
)

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR = os.path.dirname(_THIS_DIR)
DATA_PATH = os.path.join(_ROOT_DIR, "data", "clean", "clean_final.json")
CHROMA_DIR = os.path.join(_ROOT_DIR, "chroma_db")

REMOTE_DATA_URL = os.getenv(
    "REMOTE_DATA_URL",
    "https://raw.githubusercontent.com/SuY3450/Youth-welfare/main/data/clean/clean_final.json",
)


def fetch_latest_data_from_github(target_path: str = DATA_PATH, timeout: int = 30) -> bool:
    try:
        req = urllib.request.Request(REMOTE_DATA_URL, headers={"User-Agent": "youth-welfare-backend"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
        new_data = json.loads(raw)
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(new_data, f, ensure_ascii=False, indent=2)
        print(f"📡 GitHub에서 최신 데이터 받음: {len(new_data)}건")
        return True
    except Exception as e:
        print(f"⚠️  GitHub fetch 실패 ({type(e).__name__}). 로컬 파일 사용.")
        return False


print("📡 GitHub에서 최신 데이터 가져오는 중...")
fetch_latest_data_from_github()

with open(DATA_PATH, encoding="utf-8") as f:
    policies = json.load(f)
print(f"📦 {DATA_PATH}: {len(policies)}건")

# ── [신규 ⑥] 만료 정책 제외 ────────────────────────────
expired_count = 0
active_policies = []
for p in policies:
    if is_policy_expired(p):
        expired_count += 1
    else:
        active_policies.append(p)
if expired_count > 0:
    print(f"⏰ 만료 정책 {expired_count}건 자동 제외 → 유효 {len(active_policies)}건")
    policies = active_policies

# ── 메모리 DB + 자동 보완 ────────────────────────────────
POLICY_DB = {}
sub_filled, amt_filled = 0, 0

for p in policies:
    pid = str(p.get("id", ""))
    raw = str(p.get("raw_text", ""))
    emb = str(p.get("embedding_text", ""))
    region = str(p.get("region", ""))

    if not p.get("sub_region"):
        extracted = extract_sub_region_smart(raw, emb, region)
        if extracted:
            p["sub_region"] = extracted
            sub_filled += 1
    if not p.get("amount"):
        extracted = extract_amount_from_text(raw) or extract_amount_from_text(emb)
        if extracted:
            p["amount"] = extracted
            amt_filled += 1
    POLICY_DB[pid] = p

print(f"📍 sub_region 보완: {sub_filled}건")
print(f"💰 amount 보완: {amt_filled}건")

# ── ChromaDB 저장 (Cosine Similarity) ────────────────────
vectorstore = Chroma(collection_name="welfare_policies", embedding_function=embeddings,
                     persist_directory=CHROMA_DIR, collection_metadata={"hnsw:space": "cosine"})
try: vectorstore.delete_collection()
except: pass
vectorstore = Chroma(collection_name="welfare_policies", embedding_function=embeddings,
                     persist_directory=CHROMA_DIR, collection_metadata={"hnsw:space": "cosine"})

texts, metadatas = [], []
for p in policies:
    texts.append(str(p.get("embedding_text", p.get("raw_text", p.get("name", "")))))
    metadatas.append({
        "id": str(p.get("id","")), "name": str(p.get("name","")),
        "lclsf": str(p.get("lclsf","")), "category": str(p.get("category","")),
        "region": str(p.get("region","")), "sub_region": str(p.get("sub_region","") or ""),
        "source": str(p.get("source","")), "source_url": str(p.get("source_url","")),
        "amount": str(p.get("amount","") or ""), "deadline": str(p.get("deadline","") or ""),
        "age_min": str(p.get("age_min","") or ""), "age_max": str(p.get("age_max","") or ""),
        "earn_cnd": str(p.get("earn_cnd","") or ""), "job": str(p.get("job","") or ""),
        "pvmthd": str(p.get("pvmthd","") or ""), "school": str(p.get("school","") or ""),
        "special_target": str(p.get("special_target","") or ""),
    })

for i in range(0, len(texts), 100):
    vectorstore.add_texts(texts=texts[i:i+100], metadatas=metadatas[i:i+100])
    print(f"  {min(i+100, len(texts))}/{len(texts)}건 저장...")
print(f"✅ ChromaDB 저장 완료\n")


def get_full_policy(policy_id: str) -> dict:
    return POLICY_DB.get(policy_id, {})


# ══════════════════════════════════════════════════════════
#  자동 데이터 갱신
# ══════════════════════════════════════════════════════════
_refresh_lock = threading.Lock()

def refresh_data_and_rebuild() -> bool:
    global policies, vectorstore, POLICY_DB
    if not fetch_latest_data_from_github(): return False
    try:
        with open(DATA_PATH, encoding="utf-8") as f:
            new_policies = json.load(f)
    except: return False
    if {p.get("id") for p in policies} == {p.get("id") for p in new_policies}: return False
    with _refresh_lock:
        try: vectorstore.delete_collection()
        except: pass
        vectorstore = Chroma(collection_name="welfare_policies", embedding_function=embeddings,
                             persist_directory=CHROMA_DIR, collection_metadata={"hnsw:space": "cosine"})
        # 만료 제외
        policies.clear()
        policies.extend([p for p in new_policies if not is_policy_expired(p)])
        POLICY_DB.clear()
        for p in policies:
            pid = str(p.get("id",""))
            raw, emb, region = str(p.get("raw_text","")), str(p.get("embedding_text","")), str(p.get("region",""))
            if not p.get("sub_region"):
                ext = extract_sub_region_smart(raw, emb, region)
                if ext: p["sub_region"] = ext
            if not p.get("amount"):
                ext = extract_amount_from_text(raw) or extract_amount_from_text(emb)
                if ext: p["amount"] = ext
            POLICY_DB[pid] = p
        new_texts, new_metas = [], []
        for p in policies:
            new_texts.append(str(p.get("embedding_text", p.get("raw_text", p.get("name","")))))
            new_metas.append({
                "id": str(p.get("id","")), "name": str(p.get("name","")),
                "lclsf": str(p.get("lclsf","")), "category": str(p.get("category","")),
                "region": str(p.get("region","")), "sub_region": str(p.get("sub_region","") or ""),
                "source": str(p.get("source","")), "source_url": str(p.get("source_url","")),
                "amount": str(p.get("amount","") or ""), "deadline": str(p.get("deadline","") or ""),
                "age_min": str(p.get("age_min","") or ""), "age_max": str(p.get("age_max","") or ""),
                "earn_cnd": str(p.get("earn_cnd","") or ""), "job": str(p.get("job","") or ""),
                "pvmthd": str(p.get("pvmthd","") or ""), "school": str(p.get("school","") or ""),
                "special_target": str(p.get("special_target","") or ""),
            })
        for i in range(0, len(new_texts), 100):
            vectorstore.add_texts(texts=new_texts[i:i+100], metadatas=new_metas[i:i+100])
    print(f"✅ ChromaDB 재빌드 완료: {len(policies)}건")
    return True


# ══════════════════════════════════════════════════════════
#  소득/쿼리 설정
# ══════════════════════════════════════════════════════════
INCOME_LEVEL_MAP = {"50% 이하": 50, "50~100%": 100, "100~150%": 150, "150% 초과": 200}

SYNONYM_MAP = {
    "취업준비생": ["미취업","구직자","취준생","구직단념"],
    "미취업": ["취업준비생","구직자","취준생"],
    "근무": ["재직","근로자","직장인","재직자"],
    "프리랜서": ["자영업","1인사업자"],
    "월세 자취": ["월세","임차","자취","원룸"],
    "전세": ["전세자금","임차보증금","전세대출"],
}

def expand_query(user_info, category):
    parts = [f"{user_info['age']}세 청년", f"{user_info['region']} 거주",
             user_info['employment'], user_info.get('housing',''), category, "지원 혜택 정책"]
    for key, syns in SYNONYM_MAP.items():
        if key in user_info.get("employment","") or key in user_info.get("housing",""):
            parts.extend(syns)
    return " ".join(parts)

def generate_multi_queries(user_info, category):
    return [
        expand_query(user_info, category),
        f"{category} {user_info.get('housing','')} 지원금 수당 청년 {user_info['region']}",
        f"만 {user_info['age']}세 {user_info['region']} 청년 {category} 혜택",
        f"{user_info['employment']} 청년 {user_info['region']} {category} 지원",
    ]


# ══════════════════════════════════════════════════════════
#  하이브리드 검색
# ══════════════════════════════════════════════════════════
CATEGORY_MAP = {
    "주거": ["주택 및 거주지","전월세 및 주거급여 지원","기숙사","주택 및 거주지,전월세 및 주거급여 지원"],
    "금융": ["전월세 및 주거급여 지원"],
    "취업": ["취업","재직자"],
    "창업": ["창업","창업,취업"],
    "교육": ["교육비지원"],
    "일자리": ["취업","창업","재직자","창업,취업"],
}
KOREAN_REGIONS = {
    "서울특별시","부산광역시","대구광역시","인천광역시","광주광역시",
    "대전광역시","울산광역시","세종특별자치시","경기도","강원도","강원특별자치도",
    "충청북도","충청남도","전라북도","전북특별자치도","전라남도",
    "경상북도","경상남도","제주특별자치도","전국",
}

def _build_search_filter(category, user_region):
    if category == "중앙부처":
        return {"region": {"$nin": list(KOREAN_REGIONS)}}
    mapped = CATEGORY_MAP.get(category, [category])
    cat_clause = {"category": mapped[0]} if len(mapped)==1 else {"category": {"$in": mapped}}
    region_clause = {"region": {"$in": ["전국", user_region]}} if user_region else {"region": "전국"}
    return {"$and": [cat_clause, region_clause]}

def hybrid_search(user_info, category, top_k=15):
    queries = generate_multi_queries(user_info, category)
    all_results = {}
    search_filter = _build_search_filter(category, user_info.get("region",""))
    for query in queries:
        try:
            vectorstore.max_marginal_relevance_search(query, k=top_k, fetch_k=top_k*3, lambda_mult=0.7, filter=search_filter)
        except: pass
        try:
            scored = vectorstore.similarity_search_with_score(query, k=top_k, filter=search_filter)
            for doc, score in scored:
                doc_id = doc.metadata.get("name","")
                similarity = round(max(0.0, 1 - score) * 100, 2)
                if doc_id not in all_results or all_results[doc_id][1] < similarity:
                    all_results[doc_id] = (doc, similarity)
        except: pass
    return sorted(all_results.values(), key=lambda x: -x[1])[:top_k]


# ══════════════════════════════════════════════════════════
#  적합도 점수
# ══════════════════════════════════════════════════════════
def calculate_fit_score(policy_meta, user_info, similarity):
    reasons, score, eligible = [], 0, True
    policy_id = policy_meta.get("id", "")
    full = get_full_policy(policy_id)
    full_raw = str(full.get("raw_text", ""))
    full_amount = str(full.get("amount", "") or policy_meta.get("amount", ""))
    full_sub = str(full.get("sub_region", "") or policy_meta.get("sub_region", ""))

    # 나이
    age_min = int(policy_meta.get("age_min") or 0)
    age_max = int(policy_meta.get("age_max") or 99)
    if age_min == 0 and age_max == 99:
        reasons.append("나이 ⚠️ (조건 미상 → 통과)"); score += 10
    elif age_min <= user_info["age"] <= age_max:
        reasons.append(f"나이 ✅ ({age_min}~{age_max}세)"); score += 20
    else:
        reasons.append(f"나이 ❌ ({age_min}~{age_max}세 / 현재 {user_info['age']}세)"); eligible = False

    # 지역
    policy_region = (policy_meta.get("region") or "전국").strip()
    policy_sub = full_sub.strip()
    user_region = (user_info.get("region") or "").strip()
    user_sub = (user_info.get("sub_region") or "").strip()
    if policy_region == "전국":
        reasons.append("지역 ✅ (전국)"); score += 20
    elif policy_region == user_region:
        if not policy_sub:
            reasons.append(f"지역 ✅ ({policy_region})"); score += 20
        elif not user_sub:
            reasons.append(f"지역 ✅ ({policy_region} {policy_sub} / {user_region} 전체)"); score += 20
        elif policy_sub == user_sub:
            reasons.append(f"지역 ✅ ({policy_region} {policy_sub})"); score += 25
        else:
            reasons.append(f"지역 ❌ ({policy_region} {policy_sub} / 현재 {user_region} {user_sub})"); eligible = False
    else:
        reasons.append(f"지역 ❌ ({policy_region} / 현재 {user_region})"); eligible = False

    # 소득
    earn_cnd = str(full.get("earn_cnd", "") or policy_meta.get("earn_cnd", ""))
    user_income_pct = user_info.get("income_pct", 100)
    income_limit = parse_income_condition(earn_cnd)
    if income_limit == 0:
        reasons.append("소득 ✅ (무관 또는 제한없음)"); score += 15
    elif user_income_pct <= income_limit:
        reasons.append(f"소득 ✅ (중위 {income_limit}% 이하)"); score += 15
    else:
        reasons.append(f"소득 ❌ (중위 {income_limit}% 이하 필요 / 현재 {user_income_pct}%)"); eligible = False

    # 직업
    job = str(full.get("job", "") or policy_meta.get("job", ""))
    user_emp = user_info["employment"]
    if not job or job in ["제한없음", "무관", ""]:
        reasons.append("직업 ✅ (제한없음)"); score += 15
    elif user_emp in job or job in user_emp:
        reasons.append(f"직업 ✅ ({job[:20]})"); score += 15
    elif any(kw in job for kw in ["청년", "누구나", "제한없음"]):
        reasons.append(f"직업 ✅ ({job[:20]})"); score += 15
    else:
        reasons.append(f"직업 ❌ ({job[:30]} 필요)"); eligible = False

    # 유사도
    score += round(similarity * 30 / 100, 1)

    return {
        "id": policy_id, "name": policy_meta.get("name",""),
        "lclsf": full.get("lclsf",""), "category": policy_meta.get("category",""),
        "pvmthd": str(full.get("pvmthd","") or ""), "amount": full_amount,
        "region": policy_region, "sub_region": full_sub,
        "source": policy_meta.get("source",""), "source_url": policy_meta.get("source_url",""),
        "deadline": policy_meta.get("deadline",""), "job": job, "earn_cnd": earn_cnd,
        "raw_text": full_raw,
        "add_qlfc": str(full.get("add_qlfc","") or ""),
        "exclude_target": str(full.get("exclude_target","") or ""),
        "apply_method": str(full.get("apply_method","") or ""),
        "eligible": eligible, "fit_score": round(score, 2),
        "similarity": similarity, "reasons": reasons,
    }


# ══════════════════════════════════════════════════════════
#  Gemini 최종 분석
# ══════════════════════════════════════════════════════════
def analyze_with_llm(user_info, eligible):
    llm = get_llm()
    policies_text = "\n\n".join([
        f"[{i+1}] {p['name']} (적합도 {p['fit_score']}%)\n"
        f"  분류: {p['lclsf']} > {p['category']} | 지원방식: {p['pvmthd']}\n"
        f"  금액: {p['amount'] or '미상'}\n"
        f"  지역: {p['region']} {p['sub_region']} | 직업조건: {p['job'][:30]}\n"
        f"  소득조건: {p['earn_cnd'][:30]} | 출처: {p['source']}\n"
        f"  조건 판단: {' / '.join(p['reasons'])}\n"
        f"  정책 내용: {p.get('raw_text','')[:400]}\n"
        f"  추가 자격: {p.get('add_qlfc','')[:200]}\n"
        f"  제외 대상: {p.get('exclude_target','')[:200]}"
        for i, p in enumerate(eligible[:8])
    ])

    prompt = f"""당신은 청년 복지 정책 전문가입니다.
아래 정책들의 '정책 내용', '추가 자격', '제외 대상'을 꼼꼼히 읽고 사용자에게 가장 적합한 정책을 추천하세요.

특히 주의할 점:
- '제외 대상'에 해당하면 추천하지 마세요.
- '추가 자격'이 있으면 사용자가 충족하는지 확인하세요.
- 지역(시/군/구)이 사용자와 맞는지 확인하세요.
- 지원 금액이 정책 내용에 있으면 반드시 amount에 포함하세요.
- 지원방식(보조금/대출/현물 등)을 reason에 명시하세요.

[사용자 정보]
- 나이 {user_info['age']}세 / 거주지 {user_info['region']} {user_info.get('sub_region','')}
- 취업상태 {user_info['employment']} / 소득수준 중위소득 {user_info.get('income_pct',100)}%
- 주거형태 {user_info.get('housing','')} / 학력 {user_info.get('education','')}
- 관심분야 {', '.join(user_info.get('interests',[]))}

[자격 충족 정책]
{policies_text}

JSON 형식으로만 응답 (마크다운 없이):
{{
  "results": [
    {{"name":"정책명","priority":1,"fit_score":"적합도%","amount":"실제 지원금액","pvmthd":"지원방식","region":"대상 지역","reason":"정책 내용 기반 추천 이유 2줄"}}
  ],
  "top_recommendation":"1순위 정책명",
  "total_monthly":"월 예상 수령액 합계",
  "summary":"사용자에게 맞는 혜택 요약 2~3줄"
}}"""

    start = time.time()
    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content, round(time.time()-start, 2)


# ══════════════════════════════════════════════════════════
#  성능 지표
# ══════════════════════════════════════════════════════════
def calculate_diversity(results):
    if not results: return {"region":0,"source":0}
    n = len(results)
    return {
        "region": round(len(set(r[0].metadata.get("region","") for r in results))/n*100, 1),
        "source": round(len(set(r[0].metadata.get("source","") for r in results))/n*100, 1),
    }

def print_performance(m):
    print(f"\n{'='*55}")
    print("📊 상세 성능 지표")
    print(f"{'='*55}")
    print(f"  ⏱️  RAG {m['search_time']}초 / LLM {m['llm_time']}초 / 전체 {m['total_time']}초")
    print(f"  🔍 {m['searched']}건/{m['total_db']}건 | 유사도 평균 {m['avg_similarity']}% 최고 {m['max_similarity']}%")
    print(f"  ✅ {m['eligible']}건 충족 ({m['eligible_rate']}%) | 적합도 평균 {m['avg_fit']}% 최고 {m['max_fit']}%")
    print(f"  🔄 충돌 {m['conflicts']}건 → 최적 {m['optimal']}건")
    if m.get('portfolio'):
        print(f"  💰 포트폴리오: {m['portfolio']['total_monthly_text']}")
    print(f"  🏆 추천: {m['top_policy']}")
    print(f"{'='*55}\n")


# ══════════════════════════════════════════════════════════
#  메인 파이프라인
# ══════════════════════════════════════════════════════════
def run_pipeline(user_info: dict) -> dict:
    total_start = time.time()
    interests = user_info.get("interests", ["주거","금융","일자리","교육"])
    income_pct = INCOME_LEVEL_MAP.get(user_info.get("income_level",""), 100)
    user_info["income_pct"] = income_pct

    print(f"\n{'='*55}")
    print(f"👤 {user_info['age']}세 / {user_info['region']} {user_info.get('sub_region','')}")
    print(f"   {user_info['employment']} / 중위 {income_pct}% / {user_info.get('housing','')}")
    print(f"   관심: {', '.join(interests)}")
    print(f"{'='*55}\n")

    all_eligible, all_search = [], []
    for category in interests:
        print(f"🔍 [{category}] 검색 중...")
        t0 = time.time()
        results = hybrid_search(user_info, category, top_k=10)
        st = round(time.time()-t0, 2)
        all_search.extend(results)
        print(f"   {len(results)}건 ({st}초)")
        for doc, sim in results[:5]:
            print(f"   [{sim:5.1f}%] {doc.metadata.get('name','')[:45]}")
        for doc, sim in results:
            r = calculate_fit_score(doc.metadata, user_info, sim)
            r["category"] = category
            if r["eligible"]:
                all_eligible.append(r)

    # [신규 ⑦] 빈 필드 LLM 보완 (상위 5건만, API 비용 절약)
    for r in all_eligible[:5]:
        pid = r.get("id","")
        full = get_full_policy(pid)
        if full:
            updated = llm_fill_missing_fields(full)
            POLICY_DB[pid] = updated
            # 보완된 필드로 재계산 필요하면 여기서 가능

    # [신규 ⑧] LLM 제외 대상 정밀 판단 (상위 10건만)
    final_eligible = []
    for r in all_eligible[:10]:
        if r.get("exclude_target") or r.get("add_qlfc"):
            check = llm_check_exclude_target(r, user_info)
            if check.get("excluded"):
                print(f"   🚫 LLM 제외: {r['name'][:30]} → {check.get('reason','')}")
                r["eligible"] = False
                r["reasons"].append(f"LLM 판단 ❌ ({check.get('reason','')})")
                continue
        final_eligible.append(r)
    # 나머지 정책도 추가
    final_eligible.extend(all_eligible[10:])

    # 중복 제거 + 정렬
    seen, unique = set(), []
    for r in sorted(final_eligible, key=lambda x: (-x["fit_score"], -x["similarity"])):
        if r["name"] not in seen:
            seen.add(r["name"])
            unique.append(r)

    print(f"\n⚙️  자격 충족: {len(unique)}건")
    for r in unique[:10]:
        print(f"   ✅ [{r['fit_score']:6.2f}%] [{r['category']}] {r['name']} | {r['amount'] or '금액미상'} | {r['pvmthd']}")

    if not unique:
        return {"results":[],"top_recommendation":"","total_monthly":"",
                "summary":"조건에 맞는 정책이 없습니다.","eligible_policies":[],
                "optimal_policies":[],"portfolio":{},"performance":{"total_time":round(time.time()-total_start,2)}}

    print("\n🔄 중복수혜 체크 중...")
    checked, optimal = print_conflict_report(unique)

    # [신규 ⑤] 최적 포트폴리오 계산
    portfolio = calculate_optimal_portfolio(optimal)
    print(f"💰 포트폴리오: {portfolio['total_monthly_text']}")
    if portfolio['monthly_policies']:
        for mp in portfolio['monthly_policies']:
            print(f"   📌 {mp['name'][:30]}: {mp['amount']}")

    # Gemini 분석
    print("🤖 Gemini 최종 분석 중...")
    fallback = {
        "results": [{"name":r["name"],"priority":i+1,"fit_score":f"{r['fit_score']}%",
                     "amount":r["amount"],"pvmthd":r["pvmthd"],"region":f"{r['region']} {r['sub_region']}",
                     "reason":" / ".join(r["reasons"])} for i,r in enumerate(optimal[:5])],
        "top_recommendation": optimal[0]["name"] if optimal else "",
        "total_monthly": portfolio['total_monthly_text'],
        "summary":"AI 분석 일시 불가, 자체 매칭 결과입니다.",
    }
    llm_result, llm_time = None, 0
    try:
        final_raw, llm_time = analyze_with_llm(user_info, optimal)
        print(f"\n📋 최종 추천:\n{final_raw}")
        try:
            llm_result = json.loads(final_raw.replace("```json","").replace("```","").strip())
        except:
            llm_result = fallback
    except Exception as e:
        print(f"⚠️ Gemini 실패: {e}")
        llm_result = fallback

    similarities = [s for _,s in all_search]
    fit_scores = [r["fit_score"] for r in unique]
    conflicts_count = sum(1 for p in checked if p.get("conflict_warning",""))
    top_policy = llm_result.get("top_recommendation", optimal[0]["name"] if optimal else "")
    total_time = round(time.time()-total_start, 2)

    perf = {
        "search_time": 0, "llm_time": llm_time, "total_time": total_time,
        "total_db": len(policies), "searched": len(all_search),
        "avg_similarity": round(sum(similarities)/len(similarities),1) if similarities else 0,
        "max_similarity": round(max(similarities),1) if similarities else 0,
        "eligible": len(unique),
        "eligible_rate": round(len(unique)/len(all_search)*100,1) if all_search else 0,
        "avg_fit": round(sum(fit_scores)/len(fit_scores),1) if fit_scores else 0,
        "max_fit": round(max(fit_scores),1) if fit_scores else 0,
        "conflicts": conflicts_count, "optimal": len(optimal),
        "diversity": calculate_diversity(all_search),
        "portfolio": portfolio,
        "top_policy": top_policy,
    }
    print_performance(perf)

    return {
        "results": llm_result.get("results",[]),
        "top_recommendation": llm_result.get("top_recommendation",""),
        "total_monthly": portfolio['total_monthly_text'],
        "summary": llm_result.get("summary",""),
        "eligible_policies": checked,
        "optimal_policies": optimal,
        "portfolio": portfolio,
        "performance": perf,
    }


# ══════════════════════════════════════════════════════════
#  테스트
# ══════════════════════════════════════════════════════════
if __name__ == "__main__":
    user = {
        "age": 27, "region": "인천광역시", "sub_region": "부평구",
        "income_level": "50~100%", "employment": "미취업",
        "education": "대학교 졸업", "housing": "월세 자취",
        "interests": ["주거","취업"],
    }
    result = run_pipeline(user)
    print(f"\n🔗 추천 {len(result['results'])}건 | 1순위: {result['top_recommendation']}")
    print(f"💰 포트폴리오: {result['portfolio']['total_monthly_text']}")
    print(f"⏱️  {result['performance']['total_time']}초")

    # [신규 ②] 챗봇 테스트
    print("\n" + "="*55)
    print("💬 챗봇 테스트")
    print("="*55)
    answer = chat_about_policy(
        "1순위 정책 신청 방법이 뭐야?",
        result["optimal_policies"],
        user
    )
    print(f"답변: {answer}")
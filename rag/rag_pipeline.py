"""
청년 복지 정책 RAG 파이프라인 v4
=================================================
새 데이터 구조 (36개 필드) 대응:
  - job 필드로 취업상태 판단 (employment 비어있음)
  - earn_cnd 필드로 소득 조건 판단 (income_max_pct 비어있음)
  - add_qlfc, exclude_target을 Gemini 프롬프트에 포함
  - pvmthd(지원방식) 결과에 포함
  - sub_region: raw_text vs embedding_text 스마트 추출
  - amount: raw_text + embedding_text에서 자동 추출
"""
import os, time, json, re
import urllib.request
import urllib.error
import threading
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.messages import HumanMessage
from .conflict_checker import check_conflicts, get_optimal_combination, print_conflict_report

load_dotenv()

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
    """
    raw_text와 embedding_text에서 시군구 스마트 추출.
    1. raw_text에서 추출
    2. embedding_text에서 추출
    3. 둘 다 있으면 → 일치하면 사용, 불일치하면 embedding_text 우선 (구조화 데이터)
    4. 하나만 있으면 → 그거 사용
    """
    candidates = SIGUNGU_MAP.get(region, [])
    if not candidates:
        return ""

    raw_found = ""
    emb_found = ""

    for sg in candidates:
        if sg in (raw_text or ""):
            raw_found = sg
            break

    for sg in candidates:
        if sg in (emb_text or ""):
            emb_found = sg
            break

    if raw_found and emb_found:
        if raw_found == emb_found:
            return raw_found  # 일치
        else:
            return emb_found  # 불일치 → embedding_text 우선
    elif emb_found:
        return emb_found
    elif raw_found:
        return raw_found
    return ""


def extract_amount_from_text(text: str) -> str:
    if not text:
        return ""

    # 단위: 만원 / 천만원 / 억원 / 5자리 이상 원 (welfare 규모만)
    UNIT = r'(?:천\s*만\s*원|천만\s*원|억\s*원|만\s*원|만원|천만원|억원)'
    AMOUNT = rf'[\d,]+\s*{UNIT}'
    BIG_RAW_WON = r'[\d,]{5,}\s*원'  # 10,000원 이상 (welfare 최소 규모)

    # 우선순위: 컨텍스트가 명확한 패턴부터
    patterns = [
        # 1순위: 기간 + 최대 + 금액 + 지원/지급
        rf'(?:월|연|분기)\s*최대\s*{AMOUNT}\s*(?:지급|지원)',
        # 2순위: 기간 + 금액 + 지원/지급
        rf'(?:월|연|분기)\s*{AMOUNT}\s*(?:지급|지원)',
        # 3순위: 최대 + 금액 + 지원/지급/한도/보조/대출
        rf'최대\s*{AMOUNT}\s*(?:지급|지원|한도|보조|대출|융자)',
        # 4순위: 금액 + 지원/지급/한도/보조/대출
        rf'{AMOUNT}\s*(?:지급|지원|한도|보조|대출|융자)',
        # 5순위: 큰 원 단위 (5자리 이상) + 지원/지급
        rf'{BIG_RAW_WON}\s*(?:지급|지원|한도|보조)',
        # 6순위: 기간 + 최대 + 금액 (컨텍스트 없어도)
        rf'(?:월|연|분기)\s*최대\s*{AMOUNT}',
        # 7순위: 기간 + 금액
        rf'(?:월|연|분기)\s*{AMOUNT}',
        # 8순위: 최대 + 금액
        rf'최대\s*{AMOUNT}',
        # 9순위: 단순 금액 (단위 명시된 것만)
        AMOUNT,
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0).strip()
    return ""


# ══════════════════════════════════════════════════════════
#  소득 조건 파싱 (earn_cnd → 중위소득 % 추출)
# ══════════════════════════════════════════════════════════
def parse_income_condition(earn_cnd: str) -> int:
    """earn_cnd 텍스트에서 중위소득 % 추출. 못 찾으면 0 반환 (무조건 통과)"""
    if not earn_cnd or earn_cnd == "무관" or earn_cnd == "제한없음":
        return 0
    match = re.search(r'(\d+)\s*%', earn_cnd)
    if match:
        return int(match.group(1))
    return 0


# ══════════════════════════════════════════════════════════
#  1. 임베딩 + 데이터 로드
# ══════════════════════════════════════════════════════════
print("임베딩 모델 로딩 중...")
embeddings = HuggingFaceEmbeddings(model_name="jhgan/ko-sroberta-multitask")

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

# ── 메모리 DB + 자동 보완 ────────────────────────────────
POLICY_DB = {}
sub_filled, amt_filled = 0, 0

for p in policies:
    pid = str(p.get("id", ""))
    raw = str(p.get("raw_text", ""))
    emb = str(p.get("embedding_text", ""))
    region = str(p.get("region", ""))

    # sub_region 스마트 추출 (raw vs emb 비교)
    if not p.get("sub_region"):
        extracted = extract_sub_region_smart(raw, emb, region)
        if extracted:
            p["sub_region"] = extracted
            sub_filled += 1

    # amount 추출 (raw + emb)
    if not p.get("amount"):
        extracted = extract_amount_from_text(raw) or extract_amount_from_text(emb)
        if extracted:
            p["amount"] = extracted
            amt_filled += 1

    POLICY_DB[pid] = p

print(f"📍 sub_region 보완: {sub_filled}건 (raw vs embedding 스마트 추출)")
print(f"💰 amount 보완: {amt_filled}건")

# ── ChromaDB 저장 ────────────────────────────────────────
vectorstore = Chroma(collection_name="welfare_policies", embedding_function=embeddings, persist_directory=CHROMA_DIR)
try: vectorstore.delete_collection()
except: pass
vectorstore = Chroma(collection_name="welfare_policies", embedding_function=embeddings, persist_directory=CHROMA_DIR)

texts, metadatas = [], []
for p in policies:
    texts.append(str(p.get("embedding_text", p.get("raw_text", p.get("name", "")))))
    metadatas.append({
        "id":             str(p.get("id", "")),
        "name":           str(p.get("name", "")),
        "lclsf":          str(p.get("lclsf", "")),
        "category":       str(p.get("category", "")),
        "region":         str(p.get("region", "")),
        "sub_region":     str(p.get("sub_region", "") or ""),
        "source":         str(p.get("source", "")),
        "source_url":     str(p.get("source_url", "")),
        "amount":         str(p.get("amount", "") or ""),
        "deadline":       str(p.get("deadline", "") or ""),
        "age_min":        str(p.get("age_min", "") or ""),
        "age_max":        str(p.get("age_max", "") or ""),
        "earn_cnd":       str(p.get("earn_cnd", "") or ""),
        "job":            str(p.get("job", "") or ""),
        "pvmthd":         str(p.get("pvmthd", "") or ""),
        "school":         str(p.get("school", "") or ""),
        "special_target": str(p.get("special_target", "") or ""),
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
    if not fetch_latest_data_from_github():
        return False
    try:
        with open(DATA_PATH, encoding="utf-8") as f:
            new_policies = json.load(f)
    except:
        return False
    if {p.get("id") for p in policies} == {p.get("id") for p in new_policies}:
        return False

    with _refresh_lock:
        try: vectorstore.delete_collection()
        except: pass
        vectorstore = Chroma(collection_name="welfare_policies", embedding_function=embeddings, persist_directory=CHROMA_DIR)
        policies.clear()
        policies.extend(new_policies)
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
INCOME_LEVEL_MAP = {
    "50% 이하": 50, "50~100%": 100, "100~150%": 150, "150% 초과": 200,
}

SYNONYM_MAP = {
    "취업준비생": ["미취업","구직자","취준생","구직단념"],
    "미취업":    ["취업준비생","구직자","취준생"],
    "근무":      ["재직","근로자","직장인","재직자"],
    "프리랜서":  ["자영업","1인사업자"],
    "월세 자취":  ["월세","임차","자취","원룸"],
    "전세":      ["전세자금","임차보증금","전세대출"],
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
    "주거":   ["주택 및 거주지","전월세 및 주거급여 지원","기숙사","주택 및 거주지,전월세 및 주거급여 지원"],
    "금융":   ["전월세 및 주거급여 지원"],
    "취업":   ["취업","재직자"],
    "창업":   ["창업","창업,취업"],
    "교육":   ["교육비지원"],
    "일자리": ["취업","창업","재직자","창업,취업"],
}
KOREAN_REGIONS = {
    "서울특별시","부산광역시","대구광역시","인천광역시","광주광역시",
    "대전광역시","울산광역시","세종특별자치시",
    "경기도","강원도","강원특별자치도","충청북도","충청남도",
    "전라북도","전북특별자치도","전라남도","경상북도","경상남도",
    "제주특별자치도","전국",
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
                similarity = round(1/(1+score)*100, 1)
                if doc_id not in all_results or all_results[doc_id][1] < similarity:
                    all_results[doc_id] = (doc, similarity)
        except: pass
    return sorted(all_results.values(), key=lambda x: -x[1])[:top_k]


# ══════════════════════════════════════════════════════════
#  적합도 점수 (새 데이터 구조 대응)
# ══════════════════════════════════════════════════════════
def calculate_fit_score(policy_meta, user_info, similarity):
    reasons, score, eligible = [], 0, True
    policy_id = policy_meta.get("id", "")
    full = get_full_policy(policy_id)
    full_raw = str(full.get("raw_text", ""))
    full_amount = str(full.get("amount", "") or policy_meta.get("amount", ""))
    full_sub = str(full.get("sub_region", "") or policy_meta.get("sub_region", ""))

    # ── 나이 (20점) ──
    age_min = int(policy_meta.get("age_min") or 0)
    age_max = int(policy_meta.get("age_max") or 99)
    if age_min == 0 and age_max == 99:
        reasons.append("나이 ⚠️ (조건 미상 → 통과)"); score += 10
    elif age_min <= user_info["age"] <= age_max:
        reasons.append(f"나이 ✅ ({age_min}~{age_max}세)"); score += 20
    else:
        reasons.append(f"나이 ❌ ({age_min}~{age_max}세 / 현재 {user_info['age']}세)"); eligible = False

    # ── 지역 (20점) ──
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
            # 사용자가 "○○ 전체" 선택 → 같은 시/도 내 모든 시/군/구 매칭
            reasons.append(f"지역 ✅ ({policy_region} {policy_sub} / {user_region} 전체)"); score += 20
        elif policy_sub == user_sub:
            reasons.append(f"지역 ✅ ({policy_region} {policy_sub})"); score += 25
        else:
            reasons.append(f"지역 ❌ ({policy_region} {policy_sub} / 현재 {user_region} {user_sub})"); eligible = False
    else:
        reasons.append(f"지역 ❌ ({policy_region} / 현재 {user_region})"); eligible = False

    # ── 소득 (15점) — earn_cnd 사용 ──
    earn_cnd = str(full.get("earn_cnd", "") or policy_meta.get("earn_cnd", ""))
    user_income_pct = user_info.get("income_pct", 100)
    income_limit = parse_income_condition(earn_cnd)
    if income_limit == 0:
        reasons.append(f"소득 ✅ (무관 또는 제한없음)"); score += 15
    elif user_income_pct <= income_limit:
        reasons.append(f"소득 ✅ (중위 {income_limit}% 이하)"); score += 15
    else:
        reasons.append(f"소득 ❌ (중위 {income_limit}% 이하 필요 / 현재 {user_income_pct}%)"); eligible = False

    # ── 직업/취업상태 (15점) — job 사용 ──
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

    # ── 유사도 (30점) ──
    score += round(similarity * 30 / 100, 1)

    return {
        "id": policy_id,
        "name": policy_meta.get("name",""),
        "lclsf": full.get("lclsf",""),
        "category": policy_meta.get("category",""),
        "pvmthd": str(full.get("pvmthd","") or ""),
        "amount": full_amount,
        "region": policy_region,
        "sub_region": full_sub,
        "source": policy_meta.get("source",""),
        "source_url": policy_meta.get("source_url",""),
        "deadline": policy_meta.get("deadline",""),
        "job": job,
        "earn_cnd": earn_cnd,
        "raw_text": full_raw,
        "add_qlfc": str(full.get("add_qlfc","") or ""),
        "exclude_target": str(full.get("exclude_target","") or ""),
        "submit_docs": str(full.get("submit_docs","") or ""),
        "eligible": eligible,
        "fit_score": round(score, 1),
        "similarity": similarity,
        "reasons": reasons,
    }


# ══════════════════════════════════════════════════════════
#  Gemini 최종 분석 (새 필드 포함)
# ══════════════════════════════════════════════════════════
def analyze_with_llm(user_info, eligible):
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=os.getenv("GEMINI_API_KEY"))

    policies_text = "\n\n".join([
        f"[{i+1}] {p['name']} (적합도 {p['fit_score']}%)\n"
        f"  분류: {p['lclsf']} > {p['category']} | 지원방식: {p['pvmthd']}\n"
        f"  금액: {p['amount'] or '미상'}\n"
        f"  지역: {p['region']} {p['sub_region']} | 직업조건: {p['job'][:30]}\n"
        f"  소득조건: {p['earn_cnd'][:30]} | 출처: {p['source']}\n"
        f"  조건 판단: {' / '.join(p['reasons'])}\n"
        f"  정책 내용: {p.get('raw_text','')[:400]}\n"
        f"  추가 자격: {p.get('add_qlfc','')[:200]}\n"
        f"  제외 대상: {p.get('exclude_target','')[:200]}\n"
        f"  제출 서류: {p.get('submit_docs','')[:300]}"
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

[서류 발급처 안내 규칙 - 반드시 준수]
1. '제출 서류'에 나온 서류명에 대해 발급처와 URL을 document_links로 응답하세요.

2. URL 응답 원칙 — 환각 방지가 최우선:
   - 본인이 100% 확신하는 한국 정부/공공기관 공식 도메인만 응답하세요.
   - 도메인은 확실하지만 정확한 경로를 모르면 → 반드시 도메인 루트만 응답 (예: "https://www.example.go.kr/").
   - 조금이라도 의심되면 url을 null로 두고 search_hint만 응답하세요.
   - "아마도", "추정", "비슷한 사이트" 같은 경우는 무조건 url=null.

3. 절대 금지 사항:
   - 도메인 자체를 추측해서 만들지 마세요 (예: youth-welfare.go.kr 같은 가상 도메인 금지).
   - 본인이 실제로 알지 못하는 사이트는 url=null.
   - 경로(path)를 임의로 만들지 마세요. 도메인만 확실하면 도메인 루트만 응답.
   - 마침표 뒤 한글이 붙은 URL 같은 잘못된 형식 금지.

4. URL은 반드시 https://로 시작하고 .go.kr / .or.kr / .kr / .com 등 표준 도메인 형식이어야 합니다.

5. 본인 보관 서류(통장사본, 임대차계약서, 신분증 사본 등)는 url을 null로, source를 "본인 보관"으로 응답.

6. 학교/기관 발급 서류(재학증명서, 졸업증명서 등)는 url을 null로, source를 해당 기관명(예: "○○대학교 행정실")으로 응답.

7. 모르는 발급처는 url=null + search_hint에 "○○ 검색" 같은 구체적 검색 방법 안내.

8. 제출 서류 정보가 비어있으면 document_links는 빈 배열 [].

9. 참고 — 자주 사용되는 공식 도메인 (확신 있을 때만 사용):
   - 정부24: https://www.gov.kr
   - 홈택스: https://www.hometax.go.kr
   - 국민건강보험공단: https://www.nhis.or.kr
   - 국민연금공단: https://www.nps.or.kr
   - 고용보험: https://www.ei.go.kr
   - 워크넷: https://www.work.go.kr
   - 전자가족관계등록시스템: https://efamily.scourt.go.kr
   - 위택스: https://www.wetax.go.kr
   - 인터넷등기소: https://www.iros.go.kr
   - 복지로: https://www.bokjiro.go.kr
   - 다른 사이트도 확신 있으면 사용 가능. 단 위 규칙 2~4 엄수.

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
    {{
      "name":"정책명",
      "priority":1,
      "fit_score":"적합도%",
      "amount":"실제 지원금액",
      "pvmthd":"지원방식",
      "region":"대상 지역",
      "reason":"정책 내용+추가자격+제외대상 기반 추천 이유 2줄",
      "document_links":[
        {{
          "doc_name":"서류명",
          "source":"발급기관명",
          "url":"공식 도메인 URL 또는 null",
          "search_hint":"URL이 null일 때만 검색 방법 안내",
          "fee":"수수료 정보"
        }}
      ]
    }}
  ],
  "top_recommendation":"1순위 정책명",
  "total_monthly":"월 예상 수령액 합계",
  "summary":"사용자에게 맞는 혜택 요약 2~3줄"
}}"""

    start = time.time()
    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content, round(time.time()-start, 2)


# ══════════════════════════════════════════════════════════
#  URL 검증 (Gemini 환각 차단)
# ══════════════════════════════════════════════════════════
# 응답이 너무 느린 사이트는 살아있어도 timeout으로 fail 처리
URL_VALIDATE_TIMEOUT = 2.5
URL_VALIDATE_WORKERS = 10
_URL_VALIDATE_CACHE: dict[str, bool] = {}
_URL_VALIDATE_LOCK = threading.Lock()

_URL_FORMAT_RE = re.compile(r"^https://[a-zA-Z0-9\-._~/?#%&=:+,;@!$'()*]+$")


def _looks_like_valid_url(url: str) -> bool:
    """기본 형식 검증 — http 아님/한글 포함/공백 등 차단."""
    if not url or not isinstance(url, str):
        return False
    url = url.strip()
    if not url.startswith("https://"):
        return False
    if any(ord(c) > 127 for c in url):  # 한글/특수문자 포함
        return False
    if not _URL_FORMAT_RE.match(url):
        return False
    return True


def validate_url_live(url: str, timeout: float = URL_VALIDATE_TIMEOUT) -> bool:
    """HEAD 요청으로 실제 살아있는지 확인. 캐시 사용."""
    with _URL_VALIDATE_LOCK:
        if url in _URL_VALIDATE_CACHE:
            return _URL_VALIDATE_CACHE[url]

    ok = False
    try:
        req = urllib.request.Request(
            url,
            method="HEAD",
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; youth-welfare-bot)",
                "Accept": "*/*",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            ok = resp.status < 400
    except urllib.error.HTTPError as e:
        # 일부 사이트는 HEAD 막아둠 → GET 1바이트로 재시도
        if e.code in (403, 405, 501):
            try:
                req = urllib.request.Request(
                    url,
                    method="GET",
                    headers={
                        "User-Agent": "Mozilla/5.0 (compatible; youth-welfare-bot)",
                        "Range": "bytes=0-0",
                    },
                )
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    ok = resp.status < 400
            except Exception:
                ok = False
        else:
            ok = False
    except Exception:
        ok = False

    with _URL_VALIDATE_LOCK:
        _URL_VALIDATE_CACHE[url] = ok
    return ok


def sanitize_document_links(results_list: list) -> dict:
    """Gemini 응답의 모든 document_links URL을 검증, 가짜는 null로 만듦."""
    stats = {"checked": 0, "killed_format": 0, "killed_dead": 0, "passed": 0}
    urls_to_check: list[str] = []

    for r in results_list:
        for dl in r.get("document_links", []) or []:
            url = dl.get("url")
            if url is None or url == "":
                continue
            stats["checked"] += 1
            if not _looks_like_valid_url(url):
                dl["url"] = None
                stats["killed_format"] += 1
                if not dl.get("search_hint"):
                    dl["search_hint"] = f"{dl.get('source','')} 검색 후 공식 사이트 접속"
                continue
            urls_to_check.append(url)

    unique = list(set(urls_to_check))
    if unique:
        with ThreadPoolExecutor(max_workers=URL_VALIDATE_WORKERS) as exe:
            list(exe.map(validate_url_live, unique))

    for r in results_list:
        for dl in r.get("document_links", []) or []:
            url = dl.get("url")
            if url and not _URL_VALIDATE_CACHE.get(url, False):
                dl["url"] = None
                stats["killed_dead"] += 1
                if not dl.get("search_hint"):
                    dl["search_hint"] = f"{dl.get('source','')} 검색 후 공식 사이트 접속"
            elif url:
                stats["passed"] += 1
                dl["ai_verified"] = True

    print(f"🔒 URL 검증: {stats['checked']}건 중 통과 {stats['passed']} / 형식차단 {stats['killed_format']} / 사망 {stats['killed_dead']}")
    return stats


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
    print(f"\n  ⏱️  소요시간: RAG {m['search_time']}초 / LLM {m['llm_time']}초 / 전체 {m['total_time']}초")
    print(f"  🔍 검색: {m['searched']}건/{m['total_db']}건 | 유사도 평균 {m['avg_similarity']}% 최고 {m['max_similarity']}%")
    print(f"  ✅ 자격: {m['eligible']}건 충족 ({m['eligible_rate']}%) | 적합도 평균 {m['avg_fit']}% 최고 {m['max_fit']}%")
    print(f"  🔄 중복: {m['conflicts']}건 충돌 → 최적 {m['optimal']}건")
    print(f"  💰 추천: {m['top_policy']}")
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

    seen, unique = set(), []
    for r in sorted(all_eligible, key=lambda x: -x["fit_score"]):
        if r["name"] not in seen:
            seen.add(r["name"])
            unique.append(r)

    print(f"\n⚙️  자격 충족: {len(unique)}건")
    for r in unique[:10]:
        print(f"   ✅ [{r['fit_score']:5.1f}%] [{r['category']}] {r['name']} | {r['amount'] or '금액미상'} | {r['pvmthd']}")

    if not unique:
        return {"results":[],"top_recommendation":"","total_monthly":"",
                "summary":"조건에 맞는 정책이 없습니다.","eligible_policies":[],
                "optimal_policies":[],"performance":{"total_time":round(time.time()-total_start,2)}}

    print("\n🔄 중복수혜 체크 중...")
    checked, optimal = print_conflict_report(unique)

    print("🤖 Gemini 최종 분석 중...")
    fallback = {
        "results": [{"name":r["name"],"priority":i+1,"fit_score":f"{r['fit_score']}%",
                     "amount":r["amount"],"pvmthd":r["pvmthd"],"region":f"{r['region']} {r['sub_region']}",
                     "reason":" / ".join(r["reasons"])} for i,r in enumerate(optimal[:5])],
        "top_recommendation": optimal[0]["name"] if optimal else "",
        "total_monthly":"","summary":"AI 분석 일시 불가, 자체 매칭 결과입니다.",
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

    # URL 환각 차단 — Gemini가 생성한 모든 URL 실시간 검증
    try:
        results_for_check = llm_result.get("results", [])
        if results_for_check:
            print("🔒 Gemini URL 검증 중...")
            sanitize_document_links(results_for_check)
    except Exception as e:
        print(f"⚠️  URL 검증 중 오류 (무시하고 진행): {type(e).__name__}: {e}")

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
        "top_policy": top_policy,
    }
    print_performance(perf)

    return {
        "results": llm_result.get("results",[]),
        "top_recommendation": llm_result.get("top_recommendation",""),
        "total_monthly": llm_result.get("total_monthly",""),
        "summary": llm_result.get("summary",""),
        "eligible_policies": unique,
        "optimal_policies": optimal,
        "performance": perf,
    }


if __name__ == "__main__":
    user = {
        "age": 27, "region": "서울특별시", "sub_region": "서초구",
        "income_level": "100~150%", "employment": "근무",
        "education": "대학교 졸업", "housing": "월세 자취",
        "interests": ["주거","금융"],
    }
    result = run_pipeline(user)
    print(f"\n🔗 추천 {len(result['results'])}건 | 1순위: {result['top_recommendation']} | {result['performance']['total_time']}초")
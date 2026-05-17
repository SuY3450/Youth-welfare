"""
청년 복지 정책 RAG 파이프라인 (강화 버전)
=================================================
강화 사항:
  1. raw_text/embedding_text를 Gemini 프롬프트에 포함
  2. raw_text에서 sub_region 자동 추출 (빈값 보완)
  3. raw_text에서 amount 자동 추출
  4. 중복수혜 체크 연동 (conflict_checker)
  5. POLICY_DB 메모리에서 전체 raw_text 접근
"""
import os, time, json, re
import urllib.request
import urllib.error
import threading
from collections import Counter
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.messages import HumanMessage
from conflict_checker import check_conflicts, get_optimal_combination, print_conflict_report

load_dotenv()

# ══════════════════════════════════════════════════════════
#  시군구 사전 (sub_region 자동 추출용)
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
}

def extract_sub_region_from_text(text: str, region: str) -> str:
    """raw_text에서 시군구 자동 추출"""
    candidates = SIGUNGU_MAP.get(region, [])
    for sg in candidates:
        if sg in text:
            return sg
    # 일반 패턴: "OO시", "OO구", "OO군"
    match = re.search(r'([가-힣]{1,4}(?:시|구|군))', text)
    if match:
        found = match.group(1)
        if found in candidates:
            return found
    return ""


# ══════════════════════════════════════════════════════════
#  금액 자동 추출
# ══════════════════════════════════════════════════════════
def extract_amount_from_text(text: str) -> str:
    """raw_text에서 지원 금액 자동 추출"""
    patterns = [
        r'월\s*(?:최대\s*)?[\d,]+\s*만\s*원',
        r'최대\s*[\d,]+\s*만\s*원',
        r'[\d,]+\s*만\s*원\s*(?:지급|지원)',
        r'연\s*[\d,]+\s*만\s*원',
        r'분기\s*[\d,]+\s*만\s*원',
        r'[\d,]+\s*만\s*원',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0).strip()
    return ""


# ══════════════════════════════════════════════════════════
#  1. 임베딩 + 데이터 로드 + ChromaDB
# ══════════════════════════════════════════════════════════
print("임베딩 모델 로딩 중...")
embeddings = HuggingFaceEmbeddings(model_name="jhgan/ko-sroberta-multitask")

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(_THIS_DIR, "..", "data", "clean", "clean_final.json")

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
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as e:
        print(f"⚠️  GitHub fetch 실패 ({type(e).__name__}). 로컬 파일 사용.")
        return False


print("📡 GitHub에서 최신 데이터 가져오는 중...")
fetch_latest_data_from_github()

with open(DATA_PATH, encoding="utf-8") as f:
    policies = json.load(f)
print(f"📦 {DATA_PATH}: {len(policies)}건")

# ── 전체 정책을 메모리에 보관 (raw_text 전체 접근용) ────
POLICY_DB = {}
for p in policies:
    pid = str(p.get("id", ""))
    # sub_region 비어있으면 raw_text에서 자동 추출
    if not p.get("sub_region"):
        raw = str(p.get("raw_text", ""))
        region = str(p.get("region", ""))
        extracted = extract_sub_region_from_text(raw, region)
        if extracted:
            p["sub_region"] = extracted
    # amount 비어있으면 raw_text에서 자동 추출
    if not p.get("amount"):
        raw = str(p.get("raw_text", ""))
        extracted = extract_amount_from_text(raw)
        if extracted:
            p["amount"] = extracted
    POLICY_DB[pid] = p

print(f"📍 sub_region 보완 완료: {sum(1 for p in policies if p.get('sub_region'))}건 채워짐")
print(f"💰 amount 보완 완료: {sum(1 for p in policies if p.get('amount'))}건 채워짐")

# ── ChromaDB 저장 ────────────────────────────────────────
vectorstore = Chroma(collection_name="welfare_policies", embedding_function=embeddings, persist_directory="./chroma_db")
try: vectorstore.delete_collection()
except: pass
vectorstore = Chroma(collection_name="welfare_policies", embedding_function=embeddings, persist_directory="./chroma_db")

texts, metadatas = [], []
for p in policies:
    texts.append(str(p.get("embedding_text", p.get("raw_text", p.get("name", "")))))
    metadatas.append({
        "id":             str(p.get("id", "")),
        "name":           str(p.get("name", "")),
        "category":       str(p.get("category", "")),
        "benefit_type":   str(p.get("benefit_type", "")),
        "region":         str(p.get("region", "")),
        "sub_region":     str(p.get("sub_region", "") or ""),
        "source":         str(p.get("source", "")),
        "source_url":     str(p.get("source_url", "")),
        "amount":         str(p.get("amount", "") or ""),
        "deadline":       str(p.get("deadline", "") or ""),
        "age_min":        str(p.get("age_min", "") or ""),
        "age_max":        str(p.get("age_max", "") or ""),
        "income_max_pct": str(p.get("income_max_pct", "") or ""),
        "housing":        str(p.get("housing", "") or ""),
        "employment":     str(p.get("employment", "") or ""),
    })

for i in range(0, len(texts), 100):
    vectorstore.add_texts(texts=texts[i:i+100], metadatas=metadatas[i:i+100])
    print(f"  {min(i+100, len(texts))}/{len(texts)}건 저장...")
print(f"✅ ChromaDB 저장 완료\n")


# ══════════════════════════════════════════════════════════
#  전체 raw_text 가져오기
# ══════════════════════════════════════════════════════════
def get_full_policy(policy_id: str) -> dict:
    """POLICY_DB에서 전체 정책 데이터 가져오기"""
    return POLICY_DB.get(policy_id, {})


# ══════════════════════════════════════════════════════════
#  주기적 자동 데이터 갱신
# ══════════════════════════════════════════════════════════
_refresh_lock = threading.Lock()

def refresh_data_and_rebuild() -> bool:
    global policies, vectorstore, POLICY_DB

    if not fetch_latest_data_from_github():
        return False
    try:
        with open(DATA_PATH, encoding="utf-8") as f:
            new_policies = json.load(f)
    except Exception as e:
        print(f"⚠️  새 데이터 파일 읽기 실패: {e}")
        return False

    current_ids = {p.get("id") for p in policies}
    new_ids = {p.get("id") for p in new_policies}
    if current_ids == new_ids:
        print(f"📡 데이터 변경 없음 ({len(new_policies)}건). 재빌드 스킵.")
        return False

    with _refresh_lock:
        print(f"🔄 ChromaDB 재빌드 시작 ({len(policies)}건 → {len(new_policies)}건)")
        try: vectorstore.delete_collection()
        except: pass
        vectorstore = Chroma(collection_name="welfare_policies", embedding_function=embeddings, persist_directory="./chroma_db")

        policies.clear()
        policies.extend(new_policies)
        POLICY_DB.clear()
        for p in policies:
            pid = str(p.get("id",""))
            if not p.get("sub_region"):
                extracted = extract_sub_region_from_text(str(p.get("raw_text","")), str(p.get("region","")))
                if extracted: p["sub_region"] = extracted
            if not p.get("amount"):
                extracted = extract_amount_from_text(str(p.get("raw_text","")))
                if extracted: p["amount"] = extracted
            POLICY_DB[pid] = p

        new_texts, new_metas = [], []
        for p in policies:
            new_texts.append(str(p.get("embedding_text", p.get("raw_text", p.get("name","")))))
            new_metas.append({
                "id": str(p.get("id","")), "name": str(p.get("name","")),
                "category": str(p.get("category","")), "benefit_type": str(p.get("benefit_type","")),
                "region": str(p.get("region","")), "sub_region": str(p.get("sub_region","") or ""),
                "source": str(p.get("source","")), "source_url": str(p.get("source_url","")),
                "amount": str(p.get("amount","") or ""), "deadline": str(p.get("deadline","") or ""),
                "age_min": str(p.get("age_min","") or ""), "age_max": str(p.get("age_max","") or ""),
                "income_max_pct": str(p.get("income_max_pct","") or ""),
                "housing": str(p.get("housing","") or ""), "employment": str(p.get("employment","") or ""),
            })
        for i in range(0, len(new_texts), 100):
            vectorstore.add_texts(texts=new_texts[i:i+100], metadatas=new_metas[i:i+100])
    print(f"✅ ChromaDB 재빌드 완료: {len(policies)}건")
    return True


# ══════════════════════════════════════════════════════════
#  소득 구간 변환
# ══════════════════════════════════════════════════════════
INCOME_LEVEL_MAP = {
    "50% 이하": 50, "50~100%": 100, "100~150%": 150, "150% 초과": 200,
}


# ══════════════════════════════════════════════════════════
#  2. 쿼리 확장 + 3. 다중 쿼리
# ══════════════════════════════════════════════════════════
SYNONYM_MAP = {
    "취업준비생": ["미취업","구직자","취준생","구직단념"],
    "미취업":    ["취업준비생","구직자","취준생"],
    "근무":      ["재직","근로자","직장인","재직자"],
    "프리랜서":  ["자영업","1인사업자","프리랜서"],
    "월세 자취":  ["월세","임차","자취","원룸"],
    "전세":      ["전세자금","임차보증금","전세대출"],
    "자가":      ["자가","자기소유"],
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
#  4. 하이브리드 검색
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
#  5. 적합도 점수 (raw_text + sub_region + amount 포함)
# ══════════════════════════════════════════════════════════
def calculate_fit_score(policy_meta, user_info, similarity):
    reasons, score, eligible = [], 0, True

    # 전체 정책 데이터 가져오기 (메모리 DB에서)
    policy_id = policy_meta.get("id", "")
    full_policy = get_full_policy(policy_id)
    full_raw_text = str(full_policy.get("raw_text", ""))
    full_amount = str(full_policy.get("amount", "") or policy_meta.get("amount", ""))
    full_sub_region = str(full_policy.get("sub_region", "") or policy_meta.get("sub_region", ""))

    # 나이
    age_min = int(policy_meta.get("age_min") or 0)
    age_max = int(policy_meta.get("age_max") or 99)
    if age_min == 0 and age_max == 99:
        reasons.append("나이 ⚠️ (조건 미상 → 통과)"); score += 10
    elif age_min <= user_info["age"] <= age_max:
        reasons.append(f"나이 ✅ ({age_min}~{age_max}세)"); score += 20
    else:
        reasons.append(f"나이 ❌ ({age_min}~{age_max}세 / 현재 {user_info['age']}세)"); eligible = False

    # 지역 + sub_region
    policy_region = (policy_meta.get("region") or "전국").strip()
    policy_sub = full_sub_region.strip()
    user_region = (user_info.get("region") or "").strip()
    user_sub = (user_info.get("sub_region") or "").strip()

    if policy_region == "전국":
        reasons.append("지역 ✅ (전국)"); score += 20
    elif policy_region == user_region:
        if not policy_sub:
            reasons.append(f"지역 ✅ ({policy_region})"); score += 20
        elif policy_sub == user_sub:
            reasons.append(f"지역 ✅ ({policy_region} {policy_sub})"); score += 25
        else:
            reasons.append(f"지역 ❌ ({policy_region} {policy_sub} / 현재 {user_region} {user_sub})"); eligible = False
    else:
        reasons.append(f"지역 ❌ ({policy_region} / 현재 {user_region})"); eligible = False

    # 소득
    income_str = policy_meta.get("income_max_pct", "")
    user_income_pct = user_info.get("income_pct", 100)
    if not income_str:
        reasons.append("소득 ⚠️ (조건 미상 → 통과)"); score += 7
    else:
        income_max = int(income_str)
        if user_income_pct <= income_max:
            reasons.append(f"소득 ✅ (중위 {income_max}% 이하)"); score += 15
        else:
            reasons.append(f"소득 ❌ (중위 {income_max}% 이하 필요 / 현재 {user_income_pct}%)"); eligible = False

    # 취업상태
    required = policy_meta.get("employment", "")
    user_emp = user_info["employment"]
    if not required or required == "무관":
        reasons.append("취업상태 ✅ (무관)"); score += 15
    elif required in user_emp or user_emp in required:
        reasons.append(f"취업상태 ✅ ({required})"); score += 15
    else:
        reasons.append(f"취업상태 ❌ ({required} 필요)"); eligible = False

    # 유사도
    score += round(similarity * 30 / 100, 1)

    return {
        "id":         policy_id,
        "name":       policy_meta.get("name",""),
        "category":   policy_meta.get("category",""),
        "benefit_type": policy_meta.get("benefit_type",""),
        "amount":     full_amount,
        "region":     policy_region,
        "sub_region": full_sub_region,
        "source":     policy_meta.get("source",""),
        "source_url": policy_meta.get("source_url",""),
        "deadline":   policy_meta.get("deadline",""),
        "raw_text":   full_raw_text,
        "eligible":   eligible,
        "fit_score":  round(score, 1),
        "similarity": similarity,
        "reasons":    reasons,
    }


# ══════════════════════════════════════════════════════════
#  6. Gemini 최종 분석 (raw_text 포함 프롬프트)
# ══════════════════════════════════════════════════════════
def analyze_with_llm(user_info, eligible):
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=os.getenv("GEMINI_API_KEY"))

    # 상위 8개, raw_text 500자까지 포함
    policies_text = "\n\n".join([
        f"[{i+1}] {p['name']} (적합도 {p['fit_score']}%)\n"
        f"  분류: {p['category']} / {p.get('benefit_type','')}\n"
        f"  금액: {p['amount'] or '미상'}\n"
        f"  지역: {p['region']} {p['sub_region']}\n"
        f"  출처: {p['source']}\n"
        f"  조건 판단: {' / '.join(p['reasons'])}\n"
        f"  정책 내용: {p.get('raw_text','')[:500]}"
        for i, p in enumerate(eligible[:8])
    ])

    prompt = f"""당신은 청년 복지 정책 전문가입니다.
아래 정책들의 '정책 내용'을 꼼꼼히 읽고 사용자에게 가장 적합한 정책을 추천하세요.

특히 주의할 점:
- 정책 내용(raw_text)에 나온 실제 지원 대상, 지원 금액, 신청 조건을 근거로 판단하세요.
- 지역(시/군/구)이 사용자와 맞는지 정책 내용에서 확인하세요.
- 지원 금액이 정책 내용에 있으면 반드시 amount에 포함하세요.

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
    {{"name":"정책명","priority":1,"fit_score":"적합도%","amount":"정책 내용에서 확인한 실제 지원금액","region":"대상 지역(시군구 포함)","reason":"정책 내용 기반 추천 이유 2줄"}}
  ],
  "top_recommendation":"1순위 정책명",
  "total_monthly":"월 예상 수령액 합계",
  "summary":"사용자에게 맞는 혜택 요약 2~3줄"
}}"""

    start = time.time()
    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content, round(time.time()-start, 2)


# ══════════════════════════════════════════════════════════
#  7. 성능 지표
# ══════════════════════════════════════════════════════════
def calculate_diversity(results):
    if not results: return {"region":0,"category":0,"source":0}
    n = len(results)
    return {
        "region": round(len(set(r[0].metadata.get("region","") for r in results))/n*100, 1),
        "category": round(len(set(r[0].metadata.get("category","") for r in results))/n*100, 1),
        "source": round(len(set(r[0].metadata.get("source","") for r in results))/n*100, 1),
    }

def print_performance(m):
    print(f"\n{'='*55}")
    print("📊 상세 성능 지표")
    print(f"{'='*55}")
    print(f"\n  ⏱️  소요시간")
    print(f"     RAG 검색:         {m['search_time']}초")
    print(f"     LLM 분석:         {m['llm_time']}초")
    print(f"     전체:             {m['total_time']}초")
    print(f"\n  🔍 RAG 검색 품질")
    print(f"     총 DB:            {m['total_db']}건")
    print(f"     검색됨:           {m['searched']}건")
    print(f"     평균 유사도:       {m['avg_similarity']}%")
    print(f"     최고 유사도:       {m['max_similarity']}%")
    print(f"\n  ✅ 자격 판단")
    print(f"     충족:             {m['eligible']}건 / 충족률: {m['eligible_rate']}%")
    print(f"     평균 적합도:       {m['avg_fit']}% / 최고: {m['max_fit']}%")
    print(f"\n  🔄 중복수혜")
    print(f"     충돌 감지:         {m['conflicts']}건")
    print(f"     최적 조합:         {m['optimal']}건")
    print(f"\n  💰 추천: {m['top_policy']}")
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
    print(f"👤 사용자: {user_info['age']}세 / {user_info['region']} {user_info.get('sub_region','')}")
    print(f"   취업: {user_info['employment']} / 소득: 중위 {income_pct}%")
    print(f"   주거: {user_info.get('housing','')} / 학력: {user_info.get('education','')}")
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
            r["category"] = category  # 사용자 선택 라벨로 통일
            if r["eligible"]:
                all_eligible.append(r)

    # 중복 제거 + 정렬
    seen, unique = set(), []
    for r in sorted(all_eligible, key=lambda x: -x["fit_score"]):
        if r["name"] not in seen:
            seen.add(r["name"])
            unique.append(r)

    print(f"\n⚙️  자격 충족: {len(unique)}건")
    for r in unique[:10]:
        print(f"   ✅ [{r['fit_score']:5.1f}%] [{r['category']}] {r['name']} | {r['amount'] or '금액미상'} | {r['region']} {r['sub_region']}")

    if not unique:
        print("❗ 적합한 정책이 없습니다.")
        return {"results":[],"top_recommendation":"","total_monthly":"",
                "summary":"조건에 맞는 정책이 없습니다.","eligible_policies":[],
                "optimal_policies":[],"performance":{"total_time":round(time.time()-total_start,2)}}

    # 중복수혜 체크
    print("\n🔄 중복수혜 체크 중...")
    checked, optimal = print_conflict_report(unique)

    # Gemini 분석 (최적 조합 기준)
    print("🤖 Gemini 최종 분석 중...")
    fallback_result = {
        "results": [{"name":r["name"],"priority":i+1,"fit_score":f"{r['fit_score']}%",
                     "amount":r["amount"],"region":f"{r['region']} {r['sub_region']}",
                     "reason":" / ".join(r["reasons"])} for i,r in enumerate(optimal[:5])],
        "top_recommendation": optimal[0]["name"] if optimal else "",
        "total_monthly":"","summary":"AI 분석을 일시적으로 사용할 수 없어 자체 매칭 결과를 보여드립니다.",
    }

    llm_result, llm_time = None, 0
    try:
        final_raw, llm_time = analyze_with_llm(user_info, optimal)
        print(f"\n📋 최종 추천:")
        print(final_raw)
        try:
            llm_result = json.loads(final_raw.replace("```json","").replace("```","").strip())
        except:
            print("⚠️ LLM JSON 파싱 실패, fallback 사용")
            llm_result = fallback_result
    except Exception as e:
        print(f"⚠️ Gemini API 실패: {e}")
        llm_result = fallback_result

    # 성능 지표
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


# ══════════════════════════════════════════════════════════
#  테스트
# ══════════════════════════════════════════════════════════
if __name__ == "__main__":
    user = {
        "age": 27, "region": "서울특별시", "sub_region": "서초구",
        "income_level": "100~150%", "employment": "근무",
        "education": "대학교 졸업", "housing": "월세 자취",
        "interests": ["주거","금융"],
    }
    result = run_pipeline(user)

    print("\n" + "="*55)
    print("🔗 백엔드 연동 테스트")
    print("="*55)
    print(f"  추천 수:    {len(result['results'])}건")
    print(f"  1순위:      {result['top_recommendation']}")
    print(f"  월 수령액:  {result['total_monthly']}")
    print(f"  요약:       {result['summary']}")
    print(f"  적합 수:    {len(result['eligible_policies'])}건")
    print(f"  최적 조합:  {len(result['optimal_policies'])}건")
    print(f"  소요시간:   {result['performance']['total_time']}초")
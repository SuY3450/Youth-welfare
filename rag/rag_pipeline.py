"""
청년 복지 정책 RAG 파이프라인 v4+v5 통합
"""
import os, time, json, re, traceback
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
from .conflict_checker import check_conflicts, get_optimal_combination, print_conflict_report

load_dotenv()

def get_llm():
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=os.getenv("GEMINI_API_KEY"),
        max_retries=2,
    )


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
#  [v5] 정책 만료 자동 제외 (기간 형식이면 종료일 기준)
# ══════════════════════════════════════════════════════════
def is_policy_expired(policy: dict) -> bool:
    deadline = str(policy.get("deadline", "") or "").strip()
    if not deadline or deadline == "상시":
        return False

    # "20260330 ~ 20260529" 형식 (8자리 숫자 yyyymmdd)
    compact_dates = re.findall(r'\b(\d{4})(\d{2})(\d{2})\b', deadline)
    if compact_dates:
        dates = []
        for y, m, d in compact_dates:
            try:
                dates.append(datetime(int(y), int(m), int(d)).date())
            except Exception:
                pass
        if dates:
            return max(dates) < datetime.now().date()

    # 기간(범위) 형식 대응: "2026. 6.3.~ 6. 17." 처럼 시작~종료 형식이면
    # "가장 늦은 날(종료일)" 기준으로 만료 판단 (시작일이 지났다고 만료 처리하지 않음)
    dated = re.findall(r'(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})', deadline)
    dates = []
    for y, m, d in dated:
        try:
            dates.append(datetime(int(y), int(m), int(d)).date())
        except Exception:
            pass
    # 범위 끝의 연도 없는 날짜("~ 6. 17.")는 시작 연도를 빌려서 처리
    if dated:
        year = int(dated[0][0])
        tail = re.search(r'~\s*(\d{1,2})\.\s*(\d{1,2})\.?', deadline)
        if tail:
            try:
                dates.append(datetime(year, int(tail.group(1)), int(tail.group(2))).date())
            except Exception:
                pass
    if dates:
        return max(dates) < datetime.now().date()   # 종료일(가장 늦은 날짜) 기준

    # 단일 표준 포맷
    for fmt in ["%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d", "%Y년 %m월 %d일"]:
        try:
            return datetime.strptime(deadline, fmt).date() < datetime.now().date()
        except ValueError:
            continue
    return False


# ══════════════════════════════════════════════════════════
#  [v5] 빈 필드를 LLM이 raw_text 읽고 채우기 (배치)
# ══════════════════════════════════════════════════════════
def llm_batch_fill_missing_fields(policies: list) -> list:
    """여러 정책 빈 필드를 한 번에 채우기 - API 1번만 호출"""
    if not policies:
        return policies

    needs_fill = []
    for i, p in enumerate(policies):
        age_min = p.get("age_min", "")
        age_max = p.get("age_max", "")
        earn_cnd = p.get("earn_cnd", "")
        job = p.get("job", "")
        if (
            (not age_min or age_min == "0") and (not age_max or age_max == "99")
        ) or (not earn_cnd or earn_cnd in ("", "무관")) or (not job or job in ("", "제한없음")):
            needs_fill.append((i, p))

    if not needs_fill:
        return policies

    policies_text = "\n\n".join([
        f"[정책{idx+1}] {p.get('name','')[:30]}\n"
        f"  원문: {str(p.get('raw_text',''))[:400]}\n"
        f"  임베딩: {str(p.get('embedding_text',''))[:200]}"
        for idx, (_, p) in enumerate(needs_fill)
    ])

    try:
        llm = get_llm()
        prompt = f"""아래 정책들의 원문을 읽고 각 정책의 자격조건을 추출하세요.
원문에 없으면 "미상"으로 답하세요.

[정책 목록]
{policies_text}

JSON 형식으로만 응답 (마크다운 없이):
{{
  "results": [
    {{
      "index": 1,
      "age_min": "숫자만 또는 미상",
      "age_max": "숫자만 또는 미상",
      "earn_cnd": "소득 조건 또는 미상",
      "job": "직업 조건 또는 미상"
    }}
  ]
}}"""
        response = llm.invoke([HumanMessage(content=prompt)])
        result = json.loads(response.content.replace("```json","").replace("```","").strip())

        for r in result.get("results", []):
            idx = r.get("index", 0) - 1
            if 0 <= idx < len(needs_fill):
                orig_idx, p = needs_fill[idx]
                age_min = p.get("age_min", "")
                age_max = p.get("age_max", "")
                earn_cnd = p.get("earn_cnd", "")
                job = p.get("job", "")

                if (not age_min or age_min == "0") and r.get("age_min","미상") != "미상":
                    policies[orig_idx]["age_min"] = r["age_min"]
                if (not age_max or age_max == "99") and r.get("age_max","미상") != "미상":
                    policies[orig_idx]["age_max"] = r["age_max"]
                if (not earn_cnd or earn_cnd in ("","무관")) and r.get("earn_cnd","미상") != "미상":
                    policies[orig_idx]["earn_cnd"] = r["earn_cnd"]
                if (not job or job in ("","제한없음")) and r.get("job","미상") != "미상":
                    policies[orig_idx]["job"] = r["job"]

        print(f"   🧠 LLM 배치 필드 보완: {len(needs_fill)}건 → API 1번 호출!")
    except Exception as e:
        print(f"   ⚠️ LLM 배치 필드 보완 실패: {e}")

    return policies


# ══════════════════════════════════════════════════════════
#  [v5] LLM 제외 대상 배치 판단 (5개씩 묶어서)
# ══════════════════════════════════════════════════════════
def llm_batch_check_exclude(policies: list, user_info: dict) -> tuple:
    """5개씩 묶어서 검증 - 토큰 안전 + API 최소화
    반환: (all_results, verify_stats)
      verify_stats = {
        "total_chunks": 전체 묶음 수,
        "ok_chunks": 검증 성공 묶음 수,
        "verified_indices": 실제 LLM 검증을 거친 정책 인덱스 집합,
        "last_error": 마지막으로 발생한 에러 메시지(없으면 ""),
      }
    """
    if not policies:
        return [], {"total_chunks": 0, "ok_chunks": 0, "verified_indices": set(), "last_error": ""}

    all_results = []
    chunk_size = 5
    total_chunks = (len(policies) + chunk_size - 1) // chunk_size
    ok_chunks = 0
    verified_indices = set()
    last_error = ""

    for chunk_start in range(0, len(policies), chunk_size):
        chunk = policies[chunk_start:chunk_start + chunk_size]

        policies_text = "\n\n".join([
            f"[정책{chunk_start+i+1}] {p['name']}\n"
            f"  분류: {p.get('lclsf','')} > {p.get('category','')} | 지원방식: {p.get('pvmthd','')}\n"
            f"  지역: {p.get('region','')} {p.get('sub_region','')} | 직업조건: {str(p.get('job',''))[:30]}\n"
            f"  소득조건: {str(p.get('earn_cnd',''))[:30]}\n"
            f"  조건 판단(알고리즘): {' / '.join(p.get('reasons', []))}\n"
            f"  정책 원문: {str(p.get('raw_text',''))[:500]}\n"
            f"  제외 대상: {str(p.get('exclude_target',''))[:200]}\n"
            f"  추가 자격: {str(p.get('add_qlfc',''))[:200]}"
            for i, p in enumerate(chunk)
        ])

        try:
            llm = get_llm()
            prompt = f"""아래 정책들은 알고리즘이 1차로 적합하다고 걸러낸 후보입니다.
각 정책의 '정책 원문'을 직접 읽고, 이 사용자가 실제로 신청 가능한지 최종 검증하세요.
('조건 판단(알고리즘)'은 참고용 사전 판단이며, 원문과 대조해 옳은지 다시 확인하세요.)

[사용자 정보]
- 나이: {user_info['age']}세
- 거주지: {user_info['region']} {user_info.get('sub_region','')}
- 취업상태: {user_info['employment']}
- 소득: 중위소득 {user_info.get('income_pct',100)}%
- 주거형태: {user_info.get('housing','')}
- 학력: {user_info.get('education','')}

[검증할 정책 목록]
{policies_text}

[중요] 우리 앱은 사용자에게서 '나이, 거주지(지역), 소득수준, 취업상태, 학력'만 받습니다.
부적격 판단은 반드시 이 5개 항목으로만 하세요. 그 외 조건은 우리가 정보를 모릅니다.

각 정책마다 판단하세요:
- 정책 원문에 숨어있는 조건까지 확인

- ⛔ 아래처럼 위 5개 항목 중 하나가 '명백히 어긋날 때만' excluded = true:
  · 사용자 나이가 정책 대상 연령 범위를 벗어남
  · 사용자 거주지가 정책 지역과 다름
  · 소득수준·취업상태·학력 조건에 명백히 부적합
  · '제외 대상'에 사용자가 분명히 해당함

- ✅ 위 5개 항목으로 '확인할 수 없는' 조건은 절대 제외 사유로 쓰지 마세요 → excluded = false:
  · 창업 여부, 1인가구 여부, 무주택 여부, 임차계약 예정 여부, 주거형태 등
    사용자 정보에 없는 조건은 '미충족'이 아니라 '확인 필요'로 처리
  · 이 경우 reason에 "확인 필요: ○○ 조건"이라고 명시

- 모든 조건을 충족하면 excluded = false

JSON 형식으로만 응답 (마크다운 없이):
{{
  "results": [
    {{"index": {chunk_start+1}, "excluded": false, "reason": "판단 이유"}},
    {{"index": {chunk_start+2}, "excluded": false, "reason": "판단 이유"}}
  ]
}}"""
            response = llm.invoke([HumanMessage(content=prompt)])
            result = json.loads(response.content.replace("```json","").replace("```","").strip())
            chunk_results = result.get("results", [])
            all_results.extend(chunk_results)
            for r in chunk_results:
                verified_indices.add(r.get("index", 0) - 1)
            ok_chunks += 1
            print(f"   🔍 배치 검증 {chunk_start+1}~{chunk_start+len(chunk)}번 완료")
        except Exception as e:
            # 검증 실패 시 해당 묶음 정책들은 'verified_indices'에 안 들어감 → 미검증으로 추적됨
            last_error = str(e)
            print(f"   ⚠️ 배치 검증 실패 ({chunk_start+1}~{chunk_start+len(chunk)}): {e}", flush=True)

    verify_stats = {
        "total_chunks": total_chunks,
        "ok_chunks": ok_chunks,
        "verified_indices": verified_indices,
        "last_error": last_error,
    }
    return all_results, verify_stats


# ══════════════════════════════════════════════════════════
#  [v5] 최적 포트폴리오 (금액 최대화)
# ══════════════════════════════════════════════════════════
def parse_amount_number(amount_str: str) -> int:
    if not amount_str: return 0
    match = re.search(r'월\s*(?:최대\s*)?(\d+)\s*만\s*원', amount_str)
    if match: return int(match.group(1))
    match = re.search(r'최대\s*([\d,]+)\s*만\s*원', amount_str)
    if match: return 0
    match = re.search(r'연\s*([\d,]+)\s*만\s*원', amount_str)
    if match: return int(match.group(1).replace(",","")) // 12
    return 0


def calculate_optimal_portfolio(policies: list) -> dict:
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

# [v5] 만료 정책 자동 제외
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

print(f"📍 sub_region 보완: {sub_filled}건 (raw vs embedding 스마트 추출)")
print(f"💰 amount 보완: {amt_filled}건")

vectorstore = Chroma(
    collection_name="welfare_policies",
    embedding_function=embeddings,
    persist_directory=CHROMA_DIR,
    collection_metadata={"hnsw:space": "cosine"}
)
try: vectorstore.delete_collection()
except: pass
vectorstore = Chroma(
    collection_name="welfare_policies",
    embedding_function=embeddings,
    persist_directory=CHROMA_DIR,
    collection_metadata={"hnsw:space": "cosine"}
)

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
    if not fetch_latest_data_from_github(): return False
    try:
        with open(DATA_PATH, encoding="utf-8") as f:
            new_policies = json.load(f)
    except: return False
    if {p.get("id") for p in policies} == {p.get("id") for p in new_policies}: return False
    with _refresh_lock:
        try: vectorstore.delete_collection()
        except: pass
        vectorstore = Chroma(
            collection_name="welfare_policies",
            embedding_function=embeddings,
            persist_directory=CHROMA_DIR,
            collection_metadata={"hnsw:space": "cosine"}
        )
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


CATEGORY_MAP = {
    "주거":   ["주택 및 거주지","전월세 및 주거급여 지원","기숙사","주거","주택 및 거주지,전월세 및 주거급여 지원"],
    "금융":   ["전월세 및 주거급여 지원","금융","복지"],
    "취업":   ["취업","재직자"],
    "창업":   ["창업","창업,취업"],
    "교육":   ["교육비지원","교육","문화"],
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
            vectorstore.max_marginal_relevance_search(
                query, k=top_k, fetch_k=top_k*3, lambda_mult=0.7, filter=search_filter
            )
        except: pass
        try:
            scored = vectorstore.similarity_search_with_score(query, k=top_k, filter=search_filter)
            for doc, score in scored:
                doc_id = doc.metadata.get("name","")
                similarity = round(max(0.0, 1 - score) * 100, 2)
                print(f"   [디버그] 코사인거리={score:.4f} → 유사도={similarity}% | {doc_id[:30]}")
                if doc_id not in all_results or all_results[doc_id][1] < similarity:
                    all_results[doc_id] = (doc, similarity)
        except: pass
    return sorted(all_results.values(), key=lambda x: -x[1])[:top_k]


def calculate_fit_score(policy_meta, user_info, similarity):
    reasons, score, eligible = [], 0, True
    policy_id = policy_meta.get("id", "")
    full = get_full_policy(policy_id)
    full_raw = str(full.get("raw_text", ""))
    full_amount = str(full.get("amount", "") or policy_meta.get("amount", ""))
    full_sub = str(full.get("sub_region", "") or policy_meta.get("sub_region", ""))

    age_min = int(policy_meta.get("age_min") or 0)
    age_max = int(policy_meta.get("age_max") or 99)
    if age_max == 0: age_max = 99
    if age_min == 0 and age_max == 99:
        reasons.append("나이 ⚠️ (조건 미상 → 통과)"); score += 10
    elif age_min <= user_info["age"] <= age_max:
        reasons.append(f"나이 ✅ ({age_min}~{age_max}세)"); score += 20
    else:
        reasons.append(f"나이 ❌ ({age_min}~{age_max}세 / 현재 {user_info['age']}세)"); eligible = False

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
            reasons.append(f"지역 ✅ ({policy_region} {policy_sub})"); score += 20
        else:
            reasons.append(f"지역 ❌ ({policy_region} {policy_sub} / 현재 {user_region} {user_sub})"); eligible = False
    else:
        reasons.append(f"지역 ❌ ({policy_region} / 현재 {user_region})"); eligible = False

    earn_cnd = str(full.get("earn_cnd", "") or policy_meta.get("earn_cnd", ""))
    user_income_pct = user_info.get("income_pct", 100)
    income_limit = parse_income_condition(earn_cnd)
    if income_limit == 0:
        reasons.append("소득 ✅ (무관 또는 제한없음)"); score += 15
    elif user_income_pct <= income_limit:
        reasons.append(f"소득 ✅ (중위 {income_limit}% 이하)"); score += 15
    else:
        reasons.append(f"소득 ❌ (중위 {income_limit}% 이하 필요 / 현재 {user_income_pct}%)"); eligible = False

    job = str(full.get("job", "") or policy_meta.get("job", ""))
    user_emp = user_info["employment"]
    emp_terms = [user_emp] + SYNONYM_MAP.get(user_emp, [])
    if not job or job in ["제한없음", "무관", ""]:
        reasons.append("직업 ✅ (제한없음)"); score += 15
    elif any(t in job for t in emp_terms) or job in user_emp:
        reasons.append(f"직업 ✅ ({job[:20]})"); score += 15
    elif any(kw in job for kw in ["청년", "누구나", "제한없음"]):
        reasons.append(f"직업 ✅ ({job[:20]})"); score += 15
    else:
        reasons.append(f"직업 ❌ ({job[:30]} 필요)"); eligible = False

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
        "submit_docs": str(full.get("submit_docs","") or ""),
        "apply_method": str(full.get("apply_method","") or ""),
        "eligible": eligible, "fit_score": round(score, 2),
        "similarity": similarity, "reasons": reasons,
    }


# ══════════════════════════════════════════════════════════
#  URL 검증
# ══════════════════════════════════════════════════════════
URL_VALIDATE_TIMEOUT = 2.5
URL_VALIDATE_WORKERS = 10
_URL_VALIDATE_CACHE: dict[str, bool] = {}
_URL_VALIDATE_LOCK = threading.Lock()
_URL_FORMAT_RE = re.compile(r"^https://[a-zA-Z0-9\-._~/?#%&=:+,;@!$'()*]+$")

def _looks_like_valid_url(url: str) -> bool:
    if not url or not isinstance(url, str): return False
    url = url.strip()
    if not url.startswith("https://"): return False
    if any(ord(c) > 127 for c in url): return False
    if not _URL_FORMAT_RE.match(url): return False
    return True

def validate_url_live(url: str, timeout: float = URL_VALIDATE_TIMEOUT) -> bool:
    with _URL_VALIDATE_LOCK:
        if url in _URL_VALIDATE_CACHE:
            return _URL_VALIDATE_CACHE[url]
    ok = False
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0 (compatible; youth-welfare-bot)", "Accept": "*/*"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            ok = resp.status < 400
    except urllib.error.HTTPError as e:
        if e.code in (403, 405, 501):
            try:
                req = urllib.request.Request(url, method="GET", headers={"User-Agent": "Mozilla/5.0 (compatible; youth-welfare-bot)", "Range": "bytes=0-0"})
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
    stats = {"checked": 0, "killed_format": 0, "killed_dead": 0, "passed": 0}
    urls_to_check: list[str] = []
    for r in results_list:
        for dl in r.get("document_links", []) or []:
            url = dl.get("url")
            if url is None or url == "": continue
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
#  [신규] 추천 정책 전부의 서류 발급처 배치 생성 (5개씩 묶음)
# ══════════════════════════════════════════════════════════
def llm_batch_document_links(policies: list) -> dict:
    """추천된 정책들의 서류 발급처를 5개씩 묶어 생성 (묶음당 API 1번).
    반환: {정책명: [document_links]}"""
    result_map: dict = {}
    if not policies:
        return result_map

    collected = []  # URL 검증용 (result_map과 같은 리스트 객체 공유)
    chunk_size = 5

    for chunk_start in range(0, len(policies), chunk_size):
        chunk = policies[chunk_start:chunk_start + chunk_size]
        policies_text = "\n\n".join([
            f"[정책{chunk_start+i+1}] {p.get('name','')}\n"
            f"  제출 서류: {str(p.get('submit_docs',''))[:300]}\n"
            f"  정책 원문: {str(p.get('raw_text',''))[:200]}"
            for i, p in enumerate(chunk)
        ])
        try:
            llm = get_llm()
            prompt = f"""아래 정책들의 '제출 서류'를 읽고, 각 정책마다 필요한 서류의 발급처와 공식 URL을 안내하세요.

[규칙]
- 100% 확신하는 공식 도메인만 url에 넣고, 의심되면 url=null
- 참고 도메인: 정부24(https://www.gov.kr), 홈택스(https://www.hometax.go.kr),
  국민건강보험(https://www.nhis.or.kr), 고용보험(https://www.ei.go.kr),
  워크넷(https://www.work.go.kr), 복지로(https://www.bokjiro.go.kr)

[정책 목록]
{policies_text}

JSON 형식으로만 응답 (마크다운 없이):
{{
  "results": [
    {{
      "index": {chunk_start+1},
      "document_links": [
        {{"doc_name": "서류명", "source": "발급기관명", "url": "공식 URL 또는 null", "search_hint": "url이 null일 때만 검색 안내", "fee": "수수료"}}
      ]
    }}
  ]
}}"""
            response = llm.invoke([HumanMessage(content=prompt)])
            data = json.loads(response.content.replace("```json", "").replace("```", "").strip())
            for r in data.get("results", []):
                idx = r.get("index", 0) - 1
                if 0 <= idx < len(policies):
                    name = policies[idx].get("name", "")
                    links = r.get("document_links", []) or []
                    result_map[name] = links
                    collected.append({"document_links": links})
            print(f"   📄 발급처 생성 {chunk_start+1}~{chunk_start+len(chunk)}번 완료")
        except Exception as e:
            print(f"   ⚠️ 발급처 생성 실패 ({chunk_start+1}~{chunk_start+len(chunk)}): {e}")

    # URL 환각 차단 (실제 접속 확인) - collected가 result_map과 같은 리스트 객체라 같이 정리됨
    try:
        sanitize_document_links(collected)
    except Exception as e:
        print(f"⚠️ 발급처 URL 검증 오류: {e}")

    return result_map


# ══════════════════════════════════════════════════════════
#  Gemini 최종 분석 (raw_text 기반 검증 + 부적합 제거)
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
        f"  정책 원문: {p.get('raw_text','')[:500]}\n"
        f"  추가 자격: {p.get('add_qlfc','')[:200]}\n"
        f"  제외 대상: {p.get('exclude_target','')[:200]}\n"
        f"  제출 서류: {p.get('submit_docs','')[:300]}"
        for i, p in enumerate(eligible[:5])
    ])

    prompt = f"""당신은 청년 복지 정책 전문가입니다.
아래 정책들은 이미 적합성 검증을 통과해 이 사용자에게 신청 가능한 정책들입니다.
(부적격 정책은 앞 단계에서 모두 걸러졌으니, 다시 적합/부적격을 판단하지 마세요.)

당신의 역할은 '추천 순위 정리와 요약'입니다:
   - 사용자에게 도움이 되는 순서로 우선순위(priority)를 매기세요
   - 1순위 정책(top_recommendation)을 선정하세요
   - 지원 금액이 정책 원문에 있으면 반드시 amount에 포함
   - 사용자에게 맞는 혜택을 2~3줄로 요약(summary)하세요
   (※ 서류 발급처는 별도 단계에서 모든 추천 정책에 생성됩니다)

[사용자 정보]
- 나이: {user_info['age']}세
- 거주지: {user_info['region']} {user_info.get('sub_region','')}
- 취업상태: {user_info['employment']}
- 소득: 중위소득 {user_info.get('income_pct',100)}%
- 주거형태: {user_info.get('housing','')}
- 학력: {user_info.get('education','')}
- 관심분야: {', '.join(user_info.get('interests',[]))}

[추천할 정책 목록]
{policies_text}

JSON 형식으로만 응답 (마크다운 없이):
{{
  "results": [
    {{
      "name": "정책명",
      "priority": 1,
      "fit_score": "적합도%",
      "amount": "실제 지원금액",
      "pvmthd": "지원방식",
      "region": "대상 지역"
    }}
  ],
  "top_recommendation": "1순위 정책명",
  "total_monthly": "월 예상 수령액 합계",
  "summary": "사용자에게 맞는 혜택 요약 2~3줄"
}}"""

    start = time.time()
    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content, round(time.time()-start, 2)


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

    # ① 중복 제거 + 정렬 먼저 (LLM 검증 전에 → 같은 정책 중복 검증 방지)
    seen, dedup = set(), []
    for r in sorted(all_eligible, key=lambda x: (-x["fit_score"], -x["similarity"])):
        if r["name"] not in seen:
            seen.add(r["name"])
            dedup.append(r)

    # ② 빈 필드 LLM 배치 보완 (중복 없는 것만, API 1번)
    if dedup:
        print(f"🧠 LLM 배치 필드 보완 중 ({len(dedup)}건)...")
        dedup_full = [get_full_policy(r.get("id","")) for r in dedup]
        dedup_full = llm_batch_fill_missing_fields(dedup_full)
        for i, r in enumerate(dedup):
            pid = r.get("id","")
            if dedup_full[i]:
                POLICY_DB[pid] = dedup_full[i]

    # ③ LLM 제외 대상 배치 검증 (중복 없는 것만, 5개씩 묶어서)
    print(f"🔍 LLM 배치 검증 중 ({len(dedup)}건 → 5개씩)...")
    batch_results, verify_stats = llm_batch_check_exclude(dedup, user_info)
    exclude_map = {
        r["index"] - 1: r.get("reason", "사유 미상")
        for r in batch_results
        if r.get("excluded", False)
    }
    verified_indices = verify_stats["verified_indices"]

    unique = []
    excluded_count, verified_count, unverified_count = 0, 0, 0
    for i, r in enumerate(dedup):
        if i in exclude_map:
            reason = exclude_map[i]
            print(f"   🚫 LLM 제외: {r['name'][:30]} — {reason}")
            r["eligible"] = False
            r["llm_verified"] = True
            r["reasons"].append(f"LLM 판단 ❌ ({reason})")
            excluded_count += 1
            continue
        if i in verified_indices:
            r["llm_verified"] = True
            verified_count += 1
        else:
            # LLM이 이 정책을 검증하지 못함 (API 실패/한도초과 등) → 미검증 통과
            r["llm_verified"] = False
            r["reasons"].append("⚠️ LLM 미검증 (API 실패로 검증 건너뜀)")
            unverified_count += 1
        unique.append(r)

    # ── 검증 상태 요약 로그 (검증 '됨' vs '건너뜀'을 명확히 구분) ──
    ok_chunks = verify_stats["ok_chunks"]
    total_chunks = verify_stats["total_chunks"]
    last_error = verify_stats.get("last_error", "")
    print(f"\n{'─'*55}")
    if ok_chunks == 0 and total_chunks > 0:
        print(f"🛑 LLM 검증 전부 실패! ({total_chunks}묶음 0건 성공) → 검증 안 됨")
        print(f"   ⚠️  아래 {len(unique)}건은 '검증되지 않은' 결과입니다 (API 한도/오류 확인 필요)")
        if last_error:
            print(f"   ▶ 에러 원인: {last_error}")
    elif unverified_count > 0:
        print(f"⚠️  LLM 검증 일부만 완료: {ok_chunks}/{total_chunks}묶음 성공")
        print(f"   ✅ 검증됨 {verified_count}건 / 🚫 제외 {excluded_count}건 / ⚠️ 미검증 {unverified_count}건")
        if last_error:
            print(f"   ▶ 에러 원인: {last_error}")
    else:
        print(f"✅ LLM 검증 완료: {ok_chunks}/{total_chunks}묶음 성공")
        print(f"   ✅ 검증 통과 {verified_count}건 / 🚫 제외 {excluded_count}건")
    print(f"{'─'*55}")

    print(f"\n⚙️  자격 충족: {len(unique)}건 (검증됨 {verified_count} / 미검증 {unverified_count})")
    for r in unique[:10]:
        mark = "✅" if r.get("llm_verified") else "❓"
        print(f"   {mark} [{r['fit_score']:6.2f}%] [{r['category']}] {r['name']} | {r['amount'] or '금액미상'} | {r['pvmthd']}")

    if not unique:
        return {
            "results":[], "top_recommendation":"", "total_monthly":"",
            "summary":"조건에 맞는 정책이 없습니다.", "eligible_policies":[],
            "optimal_policies":[], "portfolio":{},
            "performance":{"total_time":round(time.time()-total_start,2)}
        }

    print("\n🔄 중복수혜 체크 중...")
    checked, optimal = print_conflict_report(unique)

    # 추천된 정책 "전부"의 서류 발급처를 5개씩 묶어 생성 → 각 정책에 부착
    print(f"📄 서류 발급처 생성 중 ({len(checked)}건 → 5개씩 묶음)...")
    doc_map = llm_batch_document_links(checked)
    for p in checked:
        p["document_links"] = doc_map.get(p.get("name", ""), [])

    portfolio = calculate_optimal_portfolio(optimal)
    print(f"💰 포트폴리오: {portfolio['total_monthly_text']}")

    print("🤖 Gemini 추천 순위 정리 + 요약 중...")
    fallback = {
        "results": [{"name":r["name"],"priority":i+1,"fit_score":f"{r['fit_score']}%",
                     "amount":r["amount"],"pvmthd":r["pvmthd"],"region":f"{r['region']} {r['sub_region']}",
                     "document_links":[]} for i,r in enumerate(optimal[:5])],
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
        print(f"⚠️ Gemini 최종 분석 실패: {e}")
        llm_result = fallback

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


if __name__ == "__main__":
    user = {
        "age": 27, "region": "서울특별시", "sub_region": "서초구",
        "income_level": "100~150%", "employment": "근무",
        "education": "대학교 졸업", "housing": "월세 자취",
        "interests": ["주거","금융"],
    }
    result = run_pipeline(user)
    print(f"\n🔗 추천 {len(result['results'])}건 | 1순위: {result['top_recommendation']}")
    print(f"💰 포트폴리오: {result['portfolio']['total_monthly_text']}")
    print(f"⏱️  {result['performance']['total_time']}초")

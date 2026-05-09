"""
청년 복지 정책 RAG 파이프라인 (UI 연동 버전)
=================================================
데이터: clean_final.json (344건)
온보딩 입력: 피그마 디자인 기준
  - 나이, 거주지(시도/시군구), 소득구간, 취업상태, 학력
  - 관심분야 다중 선택 (주거/금융/교육/일자리)
"""
import os, time, json
from collections import Counter
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.messages import HumanMessage

load_dotenv()

# ══════════════════════════════════════════════════════════
#  1. 임베딩 + 데이터 로드 + ChromaDB
# ══════════════════════════════════════════════════════════
print("임베딩 모델 로딩 중...")
embeddings = HuggingFaceEmbeddings(model_name="jhgan/ko-sroberta-multitask")

DATA_PATH = "clean_final.json"
with open(DATA_PATH, encoding="utf-8") as f:
    policies = json.load(f)
print(f"📦 {DATA_PATH}: {len(policies)}건")

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
        "raw_text":       str(p.get("raw_text", ""))[:500],
    })

for i in range(0, len(texts), 100):
    vectorstore.add_texts(texts=texts[i:i+100], metadatas=metadatas[i:i+100])
    print(f"  {min(i+100, len(texts))}/{len(texts)}건 저장...")
print(f"✅ ChromaDB 저장 완료\n")


# ══════════════════════════════════════════════════════════
#  소득 구간 → 중위소득 % 변환
# ══════════════════════════════════════════════════════════
INCOME_LEVEL_MAP = {
    "50% 이하":    50,
    "50~100%":    100,
    "100~150%":   150,
    "150% 초과":   200,
}


# ══════════════════════════════════════════════════════════
#  2. 쿼리 확장
# ══════════════════════════════════════════════════════════
SYNONYM_MAP = {
    "취업준비생": ["미취업", "구직자", "취준생", "구직단념"],
    "미취업":    ["취업준비생", "구직자", "취준생"],
    "근무":      ["재직", "근로자", "직장인", "재직자"],
    "프리랜서":  ["자영업", "1인사업자", "프리랜서"],
    "월세 자취":  ["월세", "임차", "자취", "원룸"],
    "전세":      ["전세자금", "임차보증금", "전세대출"],
    "자가":      ["자가", "자기소유"],
}

def expand_query(user_info: dict, category: str) -> str:
    parts = [
        f"{user_info['age']}세 청년",
        f"{user_info['region']} 거주",
        user_info['employment'],
        user_info.get('housing', ''),
        category,
        "지원 혜택 정책",
    ]
    for key, synonyms in SYNONYM_MAP.items():
        if key in user_info.get("employment","") or key in user_info.get("housing",""):
            parts.extend(synonyms)
    return " ".join(parts)


# ══════════════════════════════════════════════════════════
#  3. 다중 쿼리
# ══════════════════════════════════════════════════════════
def generate_multi_queries(user_info: dict, category: str) -> list[str]:
    return [
        expand_query(user_info, category),
        f"{category} {user_info.get('housing','')} 지원금 수당 청년 {user_info['region']}",
        f"만 {user_info['age']}세 {user_info['region']} 청년 {category} 혜택",
        f"{user_info['employment']} 청년 {user_info['region']} {category} 지원",
    ]


# ══════════════════════════════════════════════════════════
#  4. 하이브리드 검색
# ══════════════════════════════════════════════════════════
def hybrid_search(user_info: dict, category: str, top_k: int = 15) -> list[tuple]:
    queries = generate_multi_queries(user_info, category)
    all_results = {}

    search_filter = {"category": category}

    for query in queries:
        try:
            vectorstore.max_marginal_relevance_search(
                query, k=top_k, fetch_k=top_k * 3, lambda_mult=0.7,
                filter=search_filter,
            )
        except: pass

        try:
            scored = vectorstore.similarity_search_with_score(
                query, k=top_k, filter=search_filter,
            )
            for doc, score in scored:
                doc_id = doc.metadata.get("name", "")
                similarity = round(1 / (1 + score) * 100, 1)
                if doc_id not in all_results or all_results[doc_id][1] < similarity:
                    all_results[doc_id] = (doc, similarity)
        except: pass

    return sorted(all_results.values(), key=lambda x: -x[1])[:top_k]


# ══════════════════════════════════════════════════════════
#  5. 적합도 점수
# ══════════════════════════════════════════════════════════
def calculate_fit_score(policy_meta: dict, user_info: dict, similarity: float) -> dict:
    reasons  = []
    score    = 0
    eligible = True

    age_min = int(policy_meta.get("age_min") or 0)
    age_max = int(policy_meta.get("age_max") or 99)
    if age_min == 0 and age_max == 99:
        reasons.append("나이 ⚠️ (조건 미상 → 통과)")
        score += 10
    elif age_min <= user_info["age"] <= age_max:
        reasons.append(f"나이 ✅ ({age_min}~{age_max}세)")
        score += 20
    else:
        reasons.append(f"나이 ❌ ({age_min}~{age_max}세 / 현재 {user_info['age']}세)")
        eligible = False

    policy_region = policy_meta.get("region", "전국")
    if policy_region == "전국" or policy_region == user_info["region"]:
        reasons.append(f"지역 ✅ ({policy_region})")
        score += 20
    else:
        reasons.append(f"지역 ❌ ({policy_region} / 현재 {user_info['region']})")
        eligible = False

    income_str = policy_meta.get("income_max_pct", "")
    user_income_pct = user_info.get("income_pct", 100)
    if not income_str:
        reasons.append("소득 ⚠️ (조건 미상 → 통과)")
        score += 7
    else:
        income_max = int(income_str)
        if user_income_pct <= income_max:
            reasons.append(f"소득 ✅ (중위 {income_max}% 이하)")
            score += 15
        else:
            reasons.append(f"소득 ❌ (중위 {income_max}% 이하 필요 / 현재 {user_income_pct}%)")
            eligible = False

    required = policy_meta.get("employment", "")
    user_emp = user_info["employment"]
    if not required or required == "무관":
        reasons.append("취업상태 ✅ (무관)")
        score += 15
    elif required in user_emp or user_emp in required:
        reasons.append(f"취업상태 ✅ ({required})")
        score += 15
    else:
        reasons.append(f"취업상태 ❌ ({required} 필요)")
        eligible = False

    sim_score = round(similarity * 30 / 100, 1)
    score += sim_score

    return {
        "id":         policy_meta.get("id", ""),
        "name":       policy_meta.get("name", ""),
        "category":   policy_meta.get("category", ""),
        "amount":     policy_meta.get("amount", ""),
        "source":     policy_meta.get("source", ""),
        "source_url": policy_meta.get("source_url", ""),
        "deadline":   policy_meta.get("deadline", ""),
        "region":     policy_meta.get("region", ""),
        "sub_region": policy_meta.get("sub_region", ""),
        "eligible":   eligible,
        "fit_score":  round(score, 1),
        "similarity": similarity,
        "reasons":    reasons,
    }


# ══════════════════════════════════════════════════════════
#  6. Gemini 최종 분석
# ══════════════════════════════════════════════════════════
def analyze_with_llm(user_info: dict, eligible: list) -> tuple:
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=os.getenv("GEMINI_API_KEY"))

    policies_text = "\n".join([
        f"- {p['name']} (적합도 {p['fit_score']}%, 금액: {p['amount']}, 출처: {p['source']}): "
        f"{' / '.join(p['reasons'])}"
        for p in eligible[:10]
    ])

    prompt = f"""당신은 청년 복지 정책 전문가입니다.
아래 사용자에게 최적의 정책을 추천하세요.

[사용자 정보]
- 나이 {user_info['age']}세 / 거주지 {user_info['region']} {user_info.get('sub_region','')}
- 취업상태 {user_info['employment']} / 소득수준 중위소득 {user_info.get('income_pct',100)}%
- 주거형태 {user_info.get('housing','')} / 학력 {user_info.get('education','')}
- 관심분야 {', '.join(user_info.get('interests',[]))}

[자격 충족 정책 - 적합도 순]
{policies_text}

JSON 형식으로만 응답 (마크다운 없이):
{{
  "results": [
    {{"name":"정책명","priority":1,"fit_score":"적합도%","amount":"지원금액","reason":"추천 이유 한 줄"}}
  ],
  "top_recommendation":"1순위 정책명",
  "total_monthly":"월 예상 수령액 합계",
  "summary":"사용자에게 맞는 혜택 요약 2~3줄"
}}"""

    start    = time.time()
    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content, round(time.time() - start, 2)


# ══════════════════════════════════════════════════════════
#  7. 다양성 + 성능 지표
# ══════════════════════════════════════════════════════════
def calculate_diversity(results):
    if not results: return {"region":0,"category":0,"source":0}
    n = len(results)
    return {
        "region":   round(len(set(r[0].metadata.get("region","") for r in results))/n*100, 1),
        "category": round(len(set(r[0].metadata.get("category","") for r in results))/n*100, 1),
        "source":   round(len(set(r[0].metadata.get("source","") for r in results))/n*100, 1),
    }

def print_performance(m):
    print(f"\n{'='*55}")
    print("📊 상세 성능 지표")
    print(f"{'='*55}")
    print(f"\n  ⏱️  단계별 소요시간")
    print(f"     쿼리 확장:        {m['expand_time']}초")
    print(f"     RAG 검색:         {m['search_time']}초")
    print(f"     자격 판단:        {m['reasoning_time']}초")
    print(f"     LLM 분석:         {m['llm_time']}초")
    print(f"     ─────────────────────────")
    print(f"     전체:             {m['total_time']}초")
    print(f"\n  🔍 RAG 검색 품질")
    print(f"     총 DB 정책 수:     {m['total_db']}건")
    print(f"     검색된 정책 수:    {m['searched']}건")
    print(f"     평균 유사도:       {m['avg_similarity']}%")
    print(f"     최고 유사도:       {m['max_similarity']}%")
    print(f"     최저 유사도:       {m['min_similarity']}%")
    print(f"     지역 다양성:       {m['diversity']['region']}%")
    print(f"     출처 다양성:       {m['diversity']['source']}%")
    print(f"\n  ✅ 자격 판단 결과")
    print(f"     자격 충족:         {m['eligible']}건")
    print(f"     자격 충족률:       {m['eligible_rate']}%")
    print(f"     평균 적합도:       {m['avg_fit']}%")
    print(f"     최고 적합도:       {m['max_fit']}%")
    print(f"\n  💰 추천 결과")
    print(f"     1순위 정책:        {m['top_policy']}")
    print(f"{'='*55}\n")


# ══════════════════════════════════════════════════════════
#  메인 파이프라인
# ══════════════════════════════════════════════════════════
def run_pipeline(user_info: dict) -> dict:
    """
    RAG 파이프라인 실행.

    Args:
        user_info: 사용자 온보딩 정보 dict
            - age (int): 만 나이
            - region (str): 광역시도
            - sub_region (str): 시/군/구 (선택)
            - income_level (str): "50% 이하" / "50~100%" / "100~150%" / "150% 초과"
            - employment (str): "미취업" / "근무" / "프리랜서"
            - education (str): 학력 (선택)
            - housing (str): 주거형태 (선택)
            - interests (list[str]): 관심분야 ["주거","금융","일자리","교육"]

    Returns:
        dict: 추천 결과
            - results: LLM 추천 리스트
            - top_recommendation: 1순위 정책명
            - total_monthly: 월 예상 수령액
            - summary: 요약
            - eligible_policies: 자격 충족 정책 상세 리스트
            - performance: 성능 지표
    """
    total_start = time.time()

    interests = user_info.get("interests", ["주거","금융","일자리","교육"])
    income_pct = INCOME_LEVEL_MAP.get(user_info.get("income_level",""), 100)
    user_info["income_pct"] = income_pct

    print(f"\n{'='*55}")
    print(f"👤 사용자: {user_info['age']}세 / {user_info['region']} {user_info.get('sub_region','')}")
    print(f"   취업상태: {user_info['employment']} / 소득: 중위소득 {income_pct}%")
    print(f"   주거: {user_info.get('housing','')} / 학력: {user_info.get('education','')}")
    print(f"   관심분야: {', '.join(interests)}")
    print(f"{'='*55}\n")

    all_eligible = []
    all_search_results = []

    for category in interests:
        print(f"\n{'─'*40}")
        print(f"🔍 [{category}] 분야 검색 중...")
        print(f"{'─'*40}")

        t0 = time.time()
        queries = generate_multi_queries(user_info, category)
        expand_time = round(time.time() - t0, 4)

        t0 = time.time()
        search_results = hybrid_search(user_info, category, top_k=10)
        search_time = round(time.time() - t0, 2)
        all_search_results.extend(search_results)
        print(f"   {len(search_results)}건 검색됨 ({search_time}초)")
        for doc, sim in search_results[:5]:
            print(f"   [{sim:5.1f}%] {doc.metadata.get('name','')[:40]}")
        if len(search_results) > 5:
            print(f"   ... 외 {len(search_results)-5}건")

        for doc, sim in search_results:
            result = calculate_fit_score(doc.metadata, user_info, sim)
            if result["eligible"]:
                all_eligible.append(result)

    # 적합도 순 정렬 + 중복 제거
    seen = set()
    unique_eligible = []
    for r in sorted(all_eligible, key=lambda x: -x["fit_score"]):
        if r["name"] not in seen:
            seen.add(r["name"])
            unique_eligible.append(r)

    print(f"\n{'='*55}")
    print(f"⚙️  자격 판단 결과 (적합도 순)")
    print(f"{'='*55}")
    for r in unique_eligible[:15]:
        print(f"\n   ✅ [{r['fit_score']:5.1f}%] [{r['category']}] {r['name']}")
        for reason in r["reasons"]:
            print(f"      {reason}")
    print(f"\n   자격 충족 총: {len(unique_eligible)}건\n")

    # 적합 정책 없으면 빈 결과 반환
    if not unique_eligible:
        print("❗ 적합한 정책이 없습니다.")
        return {
            "results": [],
            "top_recommendation": "",
            "total_monthly": "",
            "summary": "조건에 맞는 정책이 없습니다.",
            "eligible_policies": [],
            "performance": {
                "total_time": round(time.time() - total_start, 2),
                "searched": len(all_search_results),
                "eligible": 0,
                "eligible_rate": "0%",
                "avg_fit_score": "0%",
            },
        }

    # Gemini 분석 (실패 시 자체 결과 사용)
    print("🤖 Gemini 최종 분석 중...")
    fallback_result = {
        "results": [
            {
                "name": r["name"],
                "priority": i+1,
                "fit_score": f"{r['fit_score']}%",
                "amount": r["amount"],
                "reason": " / ".join(r["reasons"]),
            }
            for i, r in enumerate(unique_eligible[:5])
        ],
        "top_recommendation": unique_eligible[0]["name"],
        "total_monthly": "",
        "summary": "AI 분석을 일시적으로 사용할 수 없어 자체 매칭 결과를 보여드립니다.",
    }

    final_raw = ""
    llm_time = 0
    llm_result = None
    try:
        final_raw, llm_time = analyze_with_llm(user_info, unique_eligible)
        print(f"\n📋 최종 추천:")
        print(final_raw)
        try:
            llm_result = json.loads(
                final_raw.replace("```json","").replace("```","").strip()
            )
        except Exception as parse_err:
            print(f"⚠️ LLM 응답 JSON 파싱 실패: {parse_err}")
            llm_result = fallback_result
    except Exception as api_err:
        print(f"⚠️ Gemini API 호출 실패 (fallback 사용): {api_err}")
        llm_result = fallback_result

    # 성능 지표
    similarities = [s for _, s in all_search_results]
    fit_scores   = [r["fit_score"] for r in unique_eligible]
    top_policy   = llm_result.get("top_recommendation", unique_eligible[0]["name"])
    total_time   = round(time.time() - total_start, 2)

    performance = {
        "expand_time":    expand_time,
        "search_time":    search_time,
        "reasoning_time": 0,
        "llm_time":       llm_time,
        "total_time":     total_time,
        "total_db":       len(policies),
        "searched":       len(all_search_results),
        "avg_similarity": round(sum(similarities)/len(similarities), 1) if similarities else 0,
        "max_similarity": round(max(similarities), 1) if similarities else 0,
        "min_similarity": round(min(similarities), 1) if similarities else 0,
        "diversity":      calculate_diversity(all_search_results),
        "eligible":       len(unique_eligible),
        "eligible_rate":  round(len(unique_eligible)/len(all_search_results)*100, 1) if all_search_results else 0,
        "avg_fit":        round(sum(fit_scores)/len(fit_scores), 1) if fit_scores else 0,
        "max_fit":        round(max(fit_scores), 1) if fit_scores else 0,
        "top_policy":     top_policy,
    }

    # 콘솔 출력 (디버깅용)
    print_performance(performance)

    # 최종 결과 dict 반환 (백엔드 연동용)
    return {
        "results":             llm_result.get("results", []),
        "top_recommendation":  llm_result.get("top_recommendation", ""),
        "total_monthly":       llm_result.get("total_monthly", ""),
        "summary":             llm_result.get("summary", ""),
        "eligible_policies":   unique_eligible,
        "performance":         performance,
    }


# ══════════════════════════════════════════════════════════
#  테스트
# ══════════════════════════════════════════════════════════
if __name__ == "__main__":
    user = {
        "age":          27,
        "region":       "서울특별시",
        "sub_region":   "서초구",
        "income_level": "100~150%",
        "employment":   "근무",
        "education":    "대학교 졸업",
        "housing":      "월세 자취",
        "interests":    ["주거", "금융"],
    }

    # 파이프라인 실행 → dict 반환
    result = run_pipeline(user)

    # 백엔드 연동 테스트
    print("\n" + "="*55)
    print("🔗 백엔드 연동 테스트")
    print("="*55)
    print(f"  result 타입:   {type(result)}")
    print(f"  추천 정책 수:  {len(result['results'])}건")
    print(f"  1순위:         {result['top_recommendation']}")
    print(f"  월 수령액:     {result['total_monthly']}")
    print(f"  요약:          {result['summary']}")
    print(f"  적합 정책 수:  {len(result['eligible_policies'])}건")
    print(f"  소요시간:      {result['performance']['total_time']}초")

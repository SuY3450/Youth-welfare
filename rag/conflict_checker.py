"""
중복수혜 체크 모듈 v4
=========================================
감지 방식:
  1. 정책명 기반 충돌 테이블 (CONFLICT_MAP) — 원문에 안 드러나는 외부 제도지식, 확실한 것만
  2. AI 원문 분석 — rag_pipeline.llm_detect_and_judge_conflicts()가 raw_text/exclude_target을
     직접 읽고 감지·판별·이유 생성 (정규식 1차 감지를 대체)
  3. 정규식(extract_conflict_info) — AI 호출 실패 시 fallback 으로만 사용

이 모듈은 LLM에 의존하지 않는다(순수 룰). AI 감지는 rag_pipeline 쪽에서 수행한 뒤
그 결과(conflict_warning 등)를 정책 객체에 채워 넣는다.
"""
import re


# ══════════════════════════════════════════════════════════
#  1. 정책명 기반 충돌
# ══════════════════════════════════════════════════════════
CONFLICT_MAP = {
    "(국토부) 26년 청년월세 지원사업": [
        "2026년 청년월세 지원사업", "2026년 평택시 청년 월세 지원",
        "청년월세 지원사업", "(계양구) 인천시 청년월세 지원사업",
    ],
    "2026년 청년월세 지원사업": ["(국토부) 26년 청년월세 지원사업"],
    "2026년 평택시 청년 월세 지원": ["(국토부) 26년 청년월세 지원사업"],
    "청년월세 지원사업": ["(국토부) 26년 청년월세 지원사업"],
    "(계양구) 인천시 청년월세 지원사업": ["(국토부) 26년 청년월세 지원사업"],
    "청년층을 위한 매입임대주택 공급": [
        "청년·신혼부부 공공임대주택 주거비 지원사업",
        "다가구 등 기존주택 매입임대 사업",
    ],
    "학자금대출 장기연체자 신용회복 지원": [],
}


# ══════════════════════════════════════════════════════════
#  2. [fallback] raw_text + exclude_target 정규식 감지
#     평소엔 AI(llm_detect_and_judge_conflicts)가 감지하고,
#     AI 호출이 실패했을 때만 이 정규식이 대신 감지한다.
# ══════════════════════════════════════════════════════════
CONFLICT_PATTERNS = [
    r"타\s*지자체.*(?:지원|사업).*(?:중복|동시).*불가",
    r"(?:중복|동시)\s*(?:수혜|지원|수급|신청)\s*불가",
    r"(?:중복|동시)\s*(?:수혜|지원|수급|신청).*(?:안|불가|제한|제외)",
    r"다른\s*(?:월세|주거|금융).*(?:지원|사업).*(?:받고|수급|수혜).*(?:불가|안|제외)",
    r"주거급여\s*수급자.*제외",
    r"타\s*(?:지원|사업).*중복.*불가",
]

FALSE_POSITIVE_PATTERNS = [
    r"접수\s*불가", r"우편.*불가", r"변경\s*불가",
    r"태블릿\s*불가", r"공동\s*제안\s*불가", r"영업적.*목적\s*불가",
]


def extract_conflict_info(raw_text: str, exclude_target: str = "") -> dict:
    """raw_text + exclude_target에서 중복수혜 불가 문구 찾기"""
    # 두 텍스트 합쳐서 검색
    combined = (raw_text or "") + " " + (exclude_target or "")

    if not combined.strip():
        return {"has_conflict": False, "conflict_text": "", "conflict_type": ""}

    # 거짓 양성 제거
    for fp in FALSE_POSITIVE_PATTERNS:
        combined = re.sub(fp, "", combined)

    for pattern in CONFLICT_PATTERNS:
        match = re.search(pattern, combined)
        if match:
            start = max(0, match.start() - 30)
            end = min(len(combined), match.end() + 50)
            # 단어·괄호 중간에서 잘리지 않도록 공백/문장부호 경계까지 확장
            boundary = " \n\r\t.。!?"
            start_limit = max(0, start - 40)
            while start > start_limit and combined[start - 1] not in boundary:
                start -= 1
            end_limit = min(len(combined), end + 40)
            while end < end_limit and combined[end] not in boundary:
                end += 1
            context = combined[start:end].strip()

            conflict_type = ""
            if any(kw in context for kw in ["월세", "주거", "임차"]):
                conflict_type = "주거지원"
            elif any(kw in context for kw in ["지자체", "타 지원"]):
                conflict_type = "타지자체"
            elif any(kw in context for kw in ["주거급여", "수급자"]):
                conflict_type = "주거급여"
            else:
                conflict_type = "기타"

            return {"has_conflict": True, "conflict_text": context, "conflict_type": conflict_type}

    return {"has_conflict": False, "conflict_text": "", "conflict_type": ""}


# ══════════════════════════════════════════════════════════
#  3. 충돌 감지 (정책명 테이블 기반)
#     ※ 원문 기반 감지는 rag_pipeline의 AI 단계가 담당한다.
#       호출 순서: check_conflicts() → llm_detect_and_judge_conflicts() → get_optimal_combination()
# ══════════════════════════════════════════════════════════
def check_conflicts(policies: list) -> list:
    names = [p["name"] for p in policies]

    for policy in policies:
        policy["conflict_with"] = []
        policy["conflict_warning"] = ""
        policy["conflict_source"] = ""

    # 정책명 기반 (CONFLICT_MAP) — 원문에 안 드러나는 확실한 충돌만
    for policy in policies:
        name = policy["name"]
        if name in CONFLICT_MAP:
            conflicts_found = [c for c in CONFLICT_MAP[name] if c in names]
            if conflicts_found:
                policy["conflict_with"] = conflicts_found
                policy["conflict_warning"] = f"⚠️ '{conflicts_found[0]}'와 동시 수혜 불가"
                policy["conflict_reason"] = f"'{conflicts_found[0]}' 사업과는 동시에 받을 수 없어요."
                policy["conflict_source"] = "정책명 기반"

    return policies


# ══════════════════════════════════════════════════════════
#  4. 최적 조합
# ══════════════════════════════════════════════════════════
def get_optimal_combination(policies: list) -> list:
    sorted_policies = sorted(policies, key=lambda x: -x.get("fit_score", 0))
    selected, selected_names = [], set()

    for policy in sorted_policies:
        name = policy["name"]

        if not policy.get("conflict_warning"):
            selected.append(policy)
            selected_names.add(name)
            continue

        has_conflict = False
        if name in CONFLICT_MAP:
            if any(c in selected_names for c in CONFLICT_MAP[name]):
                has_conflict = True
        if not has_conflict and policy.get("conflict_with"):
            if any(c in selected_names for c in policy["conflict_with"]):
                has_conflict = True

        if not has_conflict:
            selected.append(policy)
            selected_names.add(name)

    return selected


# ══════════════════════════════════════════════════════════
#  5. 출력
# ══════════════════════════════════════════════════════════
def print_conflict_report(checked: list, optimal: list) -> None:
    """충돌/최적 조합 결과를 출력만 한다(계산 X).
    호출 전에 check_conflicts → AI 감지 → get_optimal_combination 을 끝내고
    그 결과(checked, optimal)를 넘겨야 한다."""
    conflicts = [p for p in checked if p["conflict_warning"]]

    print(f"\n{'='*55}")
    print("🔄 중복수혜 체크 결과")
    print(f"{'='*55}")

    if not conflicts:
        print("  ✅ 충돌 없음! 모든 정책 동시 수혜 가능")
    else:
        print(f"  ⚠️ {len(conflicts)}건 충돌 감지\n")
        for p in conflicts:
            print(f"  ⚠️ {p['name'][:40]}")
            print(f"     {p['conflict_warning']}")
            print(f"     감지: {p.get('conflict_source','')}")

    print(f"\n  최적 조합 ({len(optimal)}건):")
    for i, p in enumerate(optimal, 1):
        print(f"    {i}. [{p.get('fit_score',0):.1f}%] {p['name'][:40]}")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    test = [
        {"name": "2026년 평택시 청년 월세 지원", "category": "주거", "fit_score": 60.5,
         "amount": "월 20만원", "raw_text": "타 지자체 월세 지원사업과 중복 수혜 불가.",
         "exclude_target": ""},
        {"name": "(국토부) 26년 청년월세 지원사업", "category": "주거", "fit_score": 55.0,
         "amount": "월 20만원", "raw_text": "주거급여 수급자의 경우 주거급여액 중 월차임분 제외",
         "exclude_target": ""},
        {"name": "청년 이사비 지원사업", "category": "주거", "fit_score": 50.0,
         "amount": "최대 50만원", "raw_text": "이사비 및 부동산 중개수수료 지원.",
         "exclude_target": ""},
    ]
    # 이 모듈 단독 실행 테스트는 정책명 테이블(CONFLICT_MAP) 기반 충돌만 검증한다.
    # (원문 기반 AI 감지는 rag_pipeline 실행 시에만 동작)
    checked = check_conflicts(test)
    optimal = get_optimal_combination(test)
    print_conflict_report(checked, optimal)
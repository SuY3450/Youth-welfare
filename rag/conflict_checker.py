"""
중복수혜 체크 모듈 v3
=========================================
감지 방식:
  1. raw_text에서 "중복 불가" 문구 자동 감지
  2. exclude_target 필드 활용 (새 데이터 구조)
  3. 정책명 기반 충돌 테이블 (확실한 것만)
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
#  2. raw_text + exclude_target에서 중복 문구 감지
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
#  3. 충돌 감지
# ══════════════════════════════════════════════════════════
def check_conflicts(policies: list) -> list:
    names = [p["name"] for p in policies]

    for policy in policies:
        policy["conflict_with"] = []
        policy["conflict_warning"] = ""
        policy["conflict_source"] = ""

    # A. 정책명 기반
    for policy in policies:
        name = policy["name"]
        if name in CONFLICT_MAP:
            conflicts_found = [c for c in CONFLICT_MAP[name] if c in names]
            if conflicts_found:
                policy["conflict_with"] = conflicts_found
                policy["conflict_warning"] = f"⚠️ '{conflicts_found[0]}'와 동시 수혜 불가"
                policy["conflict_source"] = "정책명 기반"

    # B. raw_text + exclude_target 기반
    for policy in policies:
        if policy["conflict_warning"]:
            continue

        raw_text = policy.get("raw_text", "")
        exclude_target = policy.get("exclude_target", "")
        conflict_info = extract_conflict_info(raw_text, exclude_target)

        if conflict_info["has_conflict"]:
            policy["conflict_warning"] = "⚠️ 중복수혜 불가"
            policy["conflict_text_raw"] = conflict_info["conflict_text"].strip()
            policy["conflict_source"] = "raw_text/exclude_target 기반"

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
def print_conflict_report(policies: list) -> tuple:
    checked = check_conflicts(policies)
    conflicts = [p for p in checked if p["conflict_warning"]]
    optimal = get_optimal_combination(policies)

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
            print(f"     감지: {p['conflict_source']}")

    print(f"\n  최적 조합 ({len(optimal)}건):")
    for i, p in enumerate(optimal, 1):
        print(f"    {i}. [{p.get('fit_score',0):.1f}%] {p['name'][:40]}")
    print(f"{'='*55}\n")

    return checked, optimal


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
    checked, optimal = print_conflict_report(test)
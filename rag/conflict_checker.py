"""
중복수혜 체크 모듈 (program_conflicts)
=========================================
동시에 받을 수 없는 정책 조합을 감지하고,
최적 조합을 자동으로 추천합니다.

사용법:
    from conflict_checker import check_conflicts, get_optimal_combination, print_conflict_report
"""


# ══════════════════════════════════════════════════════════
#  1. 정책명 기반 충돌 테이블
# ══════════════════════════════════════════════════════════
CONFLICT_MAP = {
    # 주거 — 월세 지원 간 중복 불가
    "(국토부) 26년 청년월세 지원사업": [
        "2026년 청년월세 지원사업",
        "2026년 평택시 청년 월세 지원",
        "청년월세 지원사업",
        "고령군 청년 월세 주거비 지원사업",
        "(계양구) 인천시 청년월세 지원사업",
    ],
    "2026년 평택시 청년 월세 지원": [
        "(국토부) 26년 청년월세 지원사업",
        "2026년 청년월세 지원사업",
        "청년월세 지원사업",
        "청년신혼부부 월세지원 사업",
        "2026년도 청년 신혼부부 월세지원사업",
    ],
    "2026년 청년월세 지원사업": [
        "(국토부) 26년 청년월세 지원사업",
        "2026년 평택시 청년 월세 지원",
        "청년월세 지원사업",
    ],
    "청년월세 지원사업": [
        "(국토부) 26년 청년월세 지원사업",
        "2026년 평택시 청년 월세 지원",
        "2026년 청년월세 지원사업",
    ],

    # 주거 — 임대주택 간 중복 불가
    "청년층을 위한 매입임대주택 공급": [
        "청년·신혼부부 공공임대주택 주거비 지원사업",
        "청년쉐어하우스 조성 및 운영",
        "경기도 공공기숙사 운영",
    ],
    "청년·신혼부부 공공임대주택 주거비 지원사업": [
        "청년층을 위한 매입임대주택 공급",
    ],

    # 주거 — 임대주택 입주 시 월세 지원 불가
    "경기도 공공기숙사 운영": [
        "(국토부) 26년 청년월세 지원사업",
        "2026년 평택시 청년 월세 지원",
        "청년월세 지원사업",
        "청년층을 위한 매입임대주택 공급",
    ],

    # 주거 — 전세 대출이자 지원 간 중복
    "2026년 군포시 신혼부부 및 청년 전월세 보증금 대출이자 지원": [
        "신혼부부·다자녀·청년가구 전·월세 보증금 대출이자 지원",
    ],
    "신혼부부·다자녀·청년가구 전·월세 보증금 대출이자 지원": [
        "2026년 군포시 신혼부부 및 청년 전월세 보증금 대출이자 지원",
    ],

    # 금융 — 저축 매칭 간 중복
    "경기청년 기회사다리 금융": [
        "청년내일저축계좌",
    ],
    "청년내일저축계좌": [
        "경기청년 기회사다리 금융",
    ],

    # 일자리 — 구직활동 지원 간 중복
    "국민취업지원제도": [
        "청년도전 지원사업",
    ],
    "청년도전 지원사업": [
        "국민취업지원제도",
    ],
}


# ══════════════════════════════════════════════════════════
#  2. 유형 기반 충돌 (같은 유형끼리 자동 감지)
# ══════════════════════════════════════════════════════════
CONFLICT_TYPES = {
    "월세지원": {
        "keywords": ["청년월세", "월세 지원", "월세지원"],
        "max_count": 1,
        "message": "월세 지원 정책은 1개만 받을 수 있어요",
    },
    "임대주택": {
        "keywords": ["매입임대", "공공임대", "임대주택"],
        "max_count": 1,
        "message": "임대주택은 1곳만 입주 가능해요",
    },
    "기숙사": {
        "keywords": ["기숙사", "생활관"],
        "max_count": 1,
        "message": "기숙사/생활관은 1곳만 입주 가능해요",
    },
}


# ══════════════════════════════════════════════════════════
#  3. 충돌 감지 함수
# ══════════════════════════════════════════════════════════
def _get_policy_type(name: str) -> str:
    for type_name, info in CONFLICT_TYPES.items():
        if any(kw in name for kw in info["keywords"]):
            return type_name
    return ""


def check_conflicts(policies: list) -> list:
    names = [p["name"] for p in policies]

    for policy in policies:
        policy["conflict_with"] = []
        policy["conflict_warning"] = ""

    # A. 정책명 기반 충돌
    for policy in policies:
        name = policy["name"]
        if name in CONFLICT_MAP:
            conflicts_found = [c for c in CONFLICT_MAP[name] if c in names]
            if conflicts_found:
                policy["conflict_with"] = conflicts_found
                policy["conflict_warning"] = f"⚠️ '{conflicts_found[0]}'와 동시 수혜 불가"

    # B. 유형 기반 충돌
    type_groups = {}
    for policy in policies:
        ptype = _get_policy_type(policy["name"])
        if ptype:
            if ptype not in type_groups:
                type_groups[ptype] = []
            type_groups[ptype].append(policy)

    for type_name, group in type_groups.items():
        max_count = CONFLICT_TYPES[type_name]["max_count"]
        if len(group) > max_count:
            message = CONFLICT_TYPES[type_name]["message"]
            sorted_group = sorted(group, key=lambda x: -x.get("fit_score", 0))
            for policy in sorted_group[max_count:]:
                if not policy["conflict_warning"]:
                    better = sorted_group[0]["name"]
                    policy["conflict_with"].append(better)
                    policy["conflict_warning"] = f"⚠️ {message} ('{better}' 우선 추천)"

    return policies


# ══════════════════════════════════════════════════════════
#  4. 최적 조합 (충돌 없는 조합)
# ══════════════════════════════════════════════════════════
def get_optimal_combination(policies: list) -> list:
    sorted_policies = sorted(policies, key=lambda x: -x.get("fit_score", 0))
    selected = []
    selected_names = set()
    selected_types = {}

    for policy in sorted_policies:
        name = policy["name"]
        ptype = _get_policy_type(name)

        # 정책명 기반 충돌
        has_name_conflict = False
        if name in CONFLICT_MAP:
            if any(c in selected_names for c in CONFLICT_MAP[name]):
                has_name_conflict = True

        # 유형 기반 충돌
        has_type_conflict = False
        if ptype and ptype in selected_types:
            if selected_types[ptype] >= CONFLICT_TYPES[ptype]["max_count"]:
                has_type_conflict = True

        if not has_name_conflict and not has_type_conflict:
            selected.append(policy)
            selected_names.add(name)
            if ptype:
                selected_types[ptype] = selected_types.get(ptype, 0) + 1

    return selected


# ══════════════════════════════════════════════════════════
#  5. 출력 함수
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

    print(f"\n  최적 조합 ({len(optimal)}건):")
    for i, p in enumerate(optimal, 1):
        print(f"    {i}. [{p.get('fit_score',0):.1f}%] {p['name'][:40]}")
    print(f"{'='*55}\n")

    return checked, optimal


# ══════════════════════════════════════════════════════════
#  테스트
# ══════════════════════════════════════════════════════════
if __name__ == "__main__":
    test_policies = [
        {"name": "2026년 평택시 청년 월세 지원", "category": "주거", "fit_score": 60.5, "amount": "월 20만원"},
        {"name": "(국토부) 26년 청년월세 지원사업", "category": "주거", "fit_score": 55.0, "amount": "월 20만원"},
        {"name": "청년층을 위한 매입임대주택 공급", "category": "주거", "fit_score": 52.4, "amount": "시세 40~50%"},
        {"name": "경기도 공공기숙사 운영", "category": "주거", "fit_score": 50.0, "amount": "저렴한 임대료"},
        {"name": "청년 1인가구 전월세 안심계약 지원", "category": "주거", "fit_score": 48.0, "amount": ""},
        {"name": "자립준비청년 주거비 지원사업", "category": "주거", "fit_score": 45.0, "amount": "월 20만원"},
    ]

    print("테스트 정책:")
    for p in test_policies:
        print(f"  [{p['fit_score']}%] {p['name']}")

    checked, optimal = print_conflict_report(test_policies)
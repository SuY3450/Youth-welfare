import json
import hashlib
import os
import re

# 여러 raw 소스를 함께 전처리 (온통청년 + 서울청년몽땅 자치구)
RAW_PATHS = [
    "data/raw/승현_온통청년.json",
    "data/raw/seoulyouth.json",          # seoulyouth.py 결과
]
CLEAN_PATH = "data/clean/clean_final.json"   # 누적 저장본
NEW_PATH   = "data/clean/new_policies.json"  # 이번에 새로 추가된 것만 (ChromaDB upsert용)


def make_id(policy: dict) -> str:
    key = f"{policy['source']}_{policy['name']}"
    return hashlib.md5(key.encode()).hexdigest()[:12]


def name_key(item: dict):
    """공고명 + 자치구 기준 중복 식별 (연도·공백만 제거, '구'는 유지해 강남/강서 구분)"""
    n = re.sub(r"\s+", "", re.sub(r"\d{4}", "", item.get("name", "")))
    return (n, item.get("sub_region", ""))


def load_raw() -> list:
    """RAW_PATHS의 모든 파일을 읽어 하나의 리스트로 합침"""
    raw = []
    for path in RAW_PATHS:
        if not os.path.exists(path):
            print(f"⚠️  없음, 건너뜀: {path}")
            continue
        with open(path, encoding="utf-8") as f:
            items = json.load(f)
        print(f"  · {path}: {len(items)}건")
        raw.extend(items)
    return raw


def make_embedding_text(p: dict) -> str:
    parts = [
        p.get("name", ""),
        p.get("lclsf", ""),
        p.get("category", ""),
        p.get("region", ""),
        p.get("sub_region", ""),
    ]
    age_min = p.get("age_min", "")
    age_max = p.get("age_max", "")
    if age_min and age_max:
        parts.append(f"나이 {age_min}세~{age_max}세")
    earn_cnd = p.get("earn_cnd", "")
    if earn_cnd and earn_cnd not in ("무관", "제한없음", ""):
        earn_max = p.get("earn_max_amt", "")
        earn_etc = p.get("earn_etc", "")
        if earn_max and earn_max != "0":
            parts.append(f"소득 {earn_cnd} 최대 {earn_max}원")
        elif earn_etc:
            parts.append(f"소득 {earn_etc}")
        else:
            parts.append(f"소득 {earn_cnd}")
    for field in ("mrg_stts", "job", "school", "major", "special_target", "pvmthd"):
        val = p.get(field, "")
        if val and val not in ("제한없음", "기타", ""):
            parts.append(val)
    parts.append(p.get("raw_text", ""))
    add_qlfc = p.get("add_qlfc", "")
    if add_qlfc:
        parts.append(add_qlfc)
    return " | ".join(part for part in parts if part).strip()

# ──────────────────────────────────────────
# 4개 필드 추출 함수 (원본 그대로)
# ──────────────────────────────────────────
def extract_employment(p: dict) -> str:
    job = p.get("job", "")
    text = p.get("raw_text", "")
    results = set()
    job_map = {
        "미취업자": "미취업", "(예비)창업자": "창업", "재직자": "재직",
        "자영업자": "자영업", "프리랜서": "프리랜서", "영농종사자": "영농",
        "일용근로자": "일용직", "단기근로자": "단기근로",
    }
    for key, val in job_map.items():
        if key in job:
            results.add(val)
    if not results or job in ("제한없음", "기타", ""):
        if re.search(r'미취업|미취업자|비취업', text): results.add("미취업")
        if re.search(r'재직자?|재직\s*중|현직', text): results.add("재직")
        if re.search(r'구직\s*활동|구직자|구직\s*중', text): results.add("구직")
        if re.search(r'(예비\s*)?창업자?|창업\s*준비', text): results.add("창업")
        if re.search(r'자영업자?', text): results.add("자영업")
        if re.search(r'프리랜서', text): results.add("프리랜서")
    return "제한없음" if not results else ", ".join(sorted(results))

def extract_benefit_type(p: dict) -> str:
    combined = p.get("name", "") + " " + p.get("raw_text", "")
    results = set()
    if re.search(r'현금|지원금|수당|장학금|급여|포인트|상품권|바우처|교육비\s*지원|훈련\s*수당|활동비|생활비\s*지원', combined):
        results.add("현금성")
    if re.search(r'월세\s*지원|주거비\s*지원|임차료\s*지원', combined):
        results.add("현금성")
    if re.search(r'대출|융자|보증|이자\s*지원|보증료', combined):
        results.add("대출·보증")
    if re.search(r'무료\s*(제공|지원|이용)|서비스|상담|교육|프로그램|공간|입주|대여|취업\s*연수|일경험', combined):
        results.add("현물·서비스")
    if not results:
        return ""
    if len(results) > 1:
        return "혼합(" + ", ".join(sorted(results)) + ")"
    return list(results)[0]

def extract_income_max_pct(p: dict) -> str:
    if p.get("earn_cnd", "") == "무관":
        return "무관"
    text = p.get("earn_etc", "") + " " + p.get("raw_text", "")
    matches = re.findall(r'(?:기준\s*)?중위소득\s*(\d+)\s*%', text)
    if matches:
        return str(max(int(m) for m in matches)) + "%"
    m = re.search(r'연\s*소득\s*([\d,]+)\s*(만\s*원|천\s*원)', text)
    if m:
        return m.group(0).strip()
    return ""

def extract_housing(p: dict) -> str:
    text = p.get("raw_text", "")
    results = set()
    if re.search(r'무주택', text): results.add("무주택")
    if re.search(r'전세', text): results.add("전세")
    if re.search(r'월세', text): results.add("월세")
    if re.search(r'임차|임대\s*주택|공공임대', text): results.add("임차")
    if re.search(r'자가|자기\s*소유|주택\s*소유', text): results.add("자가")
    return "" if not results else ", ".join(sorted(results))

# ──────────────────────────────────────────

def preprocess():
    raw = load_raw()
    print(f"전처리 시작: 총 {len(raw)}건")

    results = []
    seen_ids = set()

    for p in raw:
        pid = make_id(p)
        if pid in seen_ids:
            continue
        seen_ids.add(pid)

        results.append({
            "id":              pid,
            "name":            p.get("name", ""),
            "lclsf":           p.get("lclsf", ""),
            "category":        p.get("category", ""),
            "region":          p.get("region", ""),
            "sub_region":      p.get("sub_region", ""),
            "source":          p.get("source", ""),
            "source_url":      p.get("source_url", ""),
            "raw_text":        p.get("raw_text", ""),
            "amount":          p.get("amount", ""),
            "deadline":        p.get("deadline", ""),
            "registered_at":   p.get("registered_at", ""),
            "collected_at":    p.get("collected_at", ""),
            "aply_prd_type":   p.get("aply_prd_type", ""),
            "biz_prd_type":    p.get("biz_prd_type", ""),
            "age_min":         p.get("age_min", ""),
            "age_max":         p.get("age_max", ""),
            "earn_cnd":        p.get("earn_cnd", ""),
            "earn_min_amt":    p.get("earn_min_amt", ""),
            "earn_max_amt":    p.get("earn_max_amt", ""),
            "earn_etc":        p.get("earn_etc", ""),
            "mrg_stts":        p.get("mrg_stts", ""),
            "job":             p.get("job", ""),
            "school":          p.get("school", ""),
            "major":           p.get("major", ""),
            "special_target":  p.get("special_target", ""),
            "pvmthd":          p.get("pvmthd", ""),
            "add_qlfc":        p.get("add_qlfc", ""),
            "exclude_target":  p.get("exclude_target", ""),
            "apply_method":    p.get("apply_method", ""),
            "select_method":   p.get("select_method", ""),
            "submit_docs":     p.get("submit_docs", ""),
            "embedding_text":  make_embedding_text(p),
            # 4개 필드 — 빈값 대신 바로 추출
            "benefit_type":    extract_benefit_type(p),
            "income_max_pct":  extract_income_max_pct(p),
            "housing":         extract_housing(p),
            "employment":      extract_employment(p),
        })

    # ── 기존 clean_final 에 신규만 병합 (id + 공고명+자치구 중복 차단) ──
    os.makedirs("data/clean", exist_ok=True)

    if os.path.exists(CLEAN_PATH):
        with open(CLEAN_PATH, encoding="utf-8") as f:
            existing = json.load(f)
    else:
        existing = []

    existing_ids   = {e["id"] for e in existing}
    existing_names = {name_key(e) for e in existing}

    new_items = []
    for r in results:
        if r["id"] in existing_ids:
            continue
        if name_key(r) in existing_names:
            continue
        existing_ids.add(r["id"])
        existing_names.add(name_key(r))
        new_items.append(r)

    merged = existing + new_items

    with open(CLEAN_PATH, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    with open(NEW_PATH, "w", encoding="utf-8") as f:
        json.dump(new_items, f, ensure_ascii=False, indent=2)

    print(f"전처리 완료: 신규 {len(new_items)}건 추가 → 전체 {len(merged)}건")
    print(f"   → {CLEAN_PATH}")
    print(f"   → {NEW_PATH} (신규만, ChromaDB upsert용)")
    return new_items


if __name__ == "__main__":
    preprocess()
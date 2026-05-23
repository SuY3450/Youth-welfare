import json
import hashlib
import os

RAW_PATH   = "data/raw/승현_온통청년.json"
CLEAN_PATH = "data/clean/clean_final.json"

def make_id(policy: dict) -> str:
    key = f"{policy['source']}_{policy['name']}"
    return hashlib.md5(key.encode()).hexdigest()[:12]

def make_embedding_text(p: dict) -> str:
    """ChromaDB 검색에 쓸 자연어 텍스트 생성. 코드 디코딩값 포함."""
    parts = [
        p.get("name", ""),
        p.get("lclsf", ""),
        p.get("category", ""),
        p.get("region", ""),
        p.get("sub_region", ""),
    ]

    # 나이 조건
    age_min = p.get("age_min", "")
    age_max = p.get("age_max", "")
    if age_min and age_max:
        parts.append(f"나이 {age_min}세~{age_max}세")

    # 소득 조건
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

    # 코드 디코딩값 (제한없음은 임베딩에서 제외 — 노이즈)
    for field in ("mrg_stts", "job", "school", "major", "special_target", "pvmthd"):
        val = p.get(field, "")
        if val and val not in ("제한없음", "기타", ""):
            parts.append(val)

    # 본문
    parts.append(p.get("raw_text", ""))

    # 추가 자격 조건
    add_qlfc = p.get("add_qlfc", "")
    if add_qlfc:
        parts.append(add_qlfc)

    return " | ".join(part for part in parts if part).strip()

def preprocess():
    with open(RAW_PATH, encoding="utf-8") as f:
        raw = json.load(f)

    print(f"전처리 시작: {len(raw)}건")

    results = []
    seen_ids = set()

    for p in raw:
        pid = make_id(p)
        if pid in seen_ids:
            continue
        seen_ids.add(pid)

        results.append({
            # 식별
            "id":              pid,
            # 기본 정보
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
            # 신청 기간 타입
            "aply_prd_type":   p.get("aply_prd_type", ""),  # 특정기간 / 상시 / 마감
            "biz_prd_type":    p.get("biz_prd_type", ""),
            # 나이
            "age_min":         p.get("age_min", ""),
            "age_max":         p.get("age_max", ""),
            # 소득
            "earn_cnd":        p.get("earn_cnd", ""),        # 무관 / 연소득 / 기타
            "earn_min_amt":    p.get("earn_min_amt", ""),
            "earn_max_amt":    p.get("earn_max_amt", ""),
            "earn_etc":        p.get("earn_etc", ""),
            # 자격 조건 (디코딩된 텍스트)
            "mrg_stts":        p.get("mrg_stts", ""),        # 기혼 / 미혼 / 제한없음
            "job":             p.get("job", ""),             # 재직자 / 미취업자 / ...
            "school":          p.get("school", ""),          # 대학 재학 / 고졸 / ...
            "major":           p.get("major", ""),           # 공학계열 / 제한없음 / ...
            "special_target":  p.get("special_target", ""),  # 한부모가정 / 장애인 / ...
            "pvmthd":          p.get("pvmthd", ""),          # 보조금 / 바우처 / ...
            # 추가 자격 조건 텍스트
            "add_qlfc":        p.get("add_qlfc", ""),
            "exclude_target":  p.get("exclude_target", ""),
            # 신청 방법
            "apply_method":    p.get("apply_method", ""),
            "select_method":   p.get("select_method", ""),
            "submit_docs":     p.get("submit_docs", ""),  #제출서류 추가
            # 임베딩용 텍스트
            "embedding_text":  make_embedding_text(p),
            # 파이프라인 호환 필드 (다른 소스와 공통)
            "benefit_type":    "",
            "income_max_pct":  "",
            "housing":         "",
            "employment":      "",
        })

    os.makedirs("data/clean", exist_ok=True)
    with open(CLEAN_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"전처리 완료: {len(results)}건 → {CLEAN_PATH}")
    return results

if __name__ == "__main__":
    preprocess()
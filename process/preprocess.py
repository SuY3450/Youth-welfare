import json
import hashlib
import os

RAW_PATH   = "data/raw/승현_온통청년.json"
CLEAN_PATH = "data/clean/clean_final.json"

def make_id(policy: dict) -> str:
    key = f"{policy['source']}_{policy['name']}"
    return hashlib.md5(key.encode()).hexdigest()[:12]

def make_embedding_text(policy: dict) -> str:
    parts = [
        policy.get("name", ""),
        policy.get("category", ""),
        policy.get("region", ""),
        policy.get("raw_text", ""),
        policy.get("deadline", ""),
    ]
    return " | ".join(p for p in parts if p).strip()

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
            "id":             pid,
            "name":           p.get("name", ""),
            "category":       p.get("category", ""),
            "region":         p.get("region", ""),
            "sub_region":     p.get("sub_region", ""),
            "source":         p.get("source", ""),
            "source_url":     p.get("source_url", ""),
            "raw_text":       p.get("raw_text", ""),
            "amount":         p.get("amount", ""),
            "deadline":       p.get("deadline", ""),
            "registered_at":  p.get("registered_at", ""),
            "collected_at":   p.get("collected_at", ""),
            "embedding_text": make_embedding_text(p),
            "benefit_type":   "",
            "age_min":        "",
            "age_max":        "",
            "income_max_pct": "",
            "housing":        "",
            "employment":     "",
        })

    os.makedirs("data/clean", exist_ok=True)
    with open(CLEAN_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"전처리 완료: {len(results)}건 -> {CLEAN_PATH}")
    return results

if __name__ == "__main__":
    preprocess()

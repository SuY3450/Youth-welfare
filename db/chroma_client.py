import json
import chromadb
from chromadb.utils import embedding_functions

CHROMA_DIR      = "./chroma_db"
COLLECTION_NAME = "welfare_policies"

def load_to_chroma(json_path: str) -> int:
    with open(json_path, encoding="utf-8") as f:
        policies = json.load(f)

    print(f"ChromaDB 적재 시작: {len(policies)}건")

    client = chromadb.PersistentClient(path=CHROMA_DIR)
    emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="jhgan/ko-sroberta-multitask"
    )
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=emb_fn,
        metadata={"hnsw:space": "cosine"},
    )

    ids, documents, metadatas = [], [], []

    for p in policies:
        ids.append(str(p["id"]))
        documents.append(str(p.get("embedding_text", p.get("name", ""))))
        metadatas.append({
            # 기본 정보
            "name":            str(p.get("name", "")),
            "lclsf":           str(p.get("lclsf", "")),
            "category":        str(p.get("category", "")),
            "region":          str(p.get("region", "")),
            "sub_region":      str(p.get("sub_region", "")),
            "source":          str(p.get("source", "")),
            "source_url":      str(p.get("source_url", "")),
            "amount":          str(p.get("amount", "")),
            "deadline":        str(p.get("deadline", "")),
            "registered_at":   str(p.get("registered_at", "")),
            "aply_prd_type":   str(p.get("aply_prd_type", "")),  # 상시 / 특정기간 / 마감
            # 나이
            "age_min":         str(p.get("age_min", "")),
            "age_max":         str(p.get("age_max", "")),
            # 소득
            "earn_cnd":        str(p.get("earn_cnd", "")),        # 무관 / 연소득 / 기타
            "earn_min_amt":    str(p.get("earn_min_amt", "")),
            "earn_max_amt":    str(p.get("earn_max_amt", "")),
            "earn_etc":        str(p.get("earn_etc", "")),
            # 자격 조건 (디코딩된 텍스트)
            "mrg_stts":        str(p.get("mrg_stts", "")),        # 기혼 / 미혼 / 제한없음
            "job":             str(p.get("job", "")),             # 재직자 / 미취업자 / ...
            "school":          str(p.get("school", "")),          # 대학 재학 / 고졸 / ...
            "major":           str(p.get("major", "")),
            "special_target":  str(p.get("special_target", "")),  # 한부모가정 / 장애인 / ...
            "pvmthd":          str(p.get("pvmthd", "")),          # 보조금 / 바우처 / ...
            # 추가 조건 텍스트 (500자 제한 — ChromaDB metadata 크기 제한)
            "add_qlfc":        str(p.get("add_qlfc", ""))[:500],
            "exclude_target":  str(p.get("exclude_target", ""))[:500],
            "apply_method":    str(p.get("apply_method", ""))[:500],
            # 파이프라인 호환 필드
            "benefit_type":    str(p.get("benefit_type", "")),
            "income_max_pct":  str(p.get("income_max_pct", "")),
            "housing":         str(p.get("housing", "")),
            "employment":      str(p.get("employment", "")),
            # 본문 (500자 제한)
            "raw_text":        str(p.get("raw_text", ""))[:500],
        })

    batch_size = 100
    for i in range(0, len(ids), batch_size):
        collection.upsert(
            ids=ids[i:i+batch_size],
            documents=documents[i:i+batch_size],
            metadatas=metadatas[i:i+batch_size],
        )
        print(f"  {min(i+batch_size, len(ids))}/{len(ids)}건 저장...")

    total = collection.count()
    print(f"✅ ChromaDB 적재 완료! 총 {total}건")
    return total
import json
import os
import chromadb
from chromadb.utils import embedding_functions

# ===== 설정 =====
JSON_PATH  = "data/clean/clean_final.json"
CHROMA_DIR = "./chroma_db"

# ===== ChromaDB 로컬 저장 =====
client = chromadb.PersistentClient(path=CHROMA_DIR)

# 한국어 임베딩 모델
emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="jhgan/ko-sroberta-multitask"
)

# 기존 컬렉션 있으면 삭제 후 재생성
try:
    client.delete_collection("welfare_policies")
    print("기존 컬렉션 삭제")
except:
    pass

collection = client.create_collection(
    name="welfare_policies",
    embedding_function=emb_fn,
)

# ===== 데이터 로드 =====
with open(JSON_PATH, encoding="utf-8") as f:
    policies = json.load(f)

print(f"총 {len(policies)}건 적재 시작...")

ids       = []
documents = []
metadatas = []

for p in policies:
    ids.append(str(p["id"]))
    documents.append(str(p.get("embedding_text", p.get("name", ""))))
    metadatas.append({
        "name":           str(p.get("name", "")),
        "category":       str(p.get("category", "")),
        "benefit_type":   str(p.get("benefit_type", "")),
        "region":         str(p.get("region", "")),
        "sub_region":     str(p.get("sub_region", "")),
        "amount":         str(p.get("amount", "")),
        "deadline":       str(p.get("deadline", "")),
        "source":         str(p.get("source", "")),
        "source_url":     str(p.get("source_url", "")),
        "age_min":        str(p.get("age_min", "")),
        "age_max":        str(p.get("age_max", "")),
        "income_max_pct": str(p.get("income_max_pct", "")),
        "housing":        str(p.get("housing", "")),
        "employment":     str(p.get("employment", "")),
        "raw_text":       str(p.get("raw_text", ""))[:500],  # 500자 제한
    })

# ===== 100개씩 배치 저장 =====
batch_size = 100
for i in range(0, len(ids), batch_size):
    collection.add(
        ids=ids[i:i+batch_size],
        documents=documents[i:i+batch_size],
        metadatas=metadatas[i:i+batch_size],
    )
    print(f"  {min(i+batch_size, len(ids))}/{len(ids)}건 저장...")

print(f"\n✅ ChromaDB 적재 완료!")
print(f"   저장 위치: {CHROMA_DIR}")
print(f"   총 {collection.count()}건")

# ===== 테스트 검색 =====
print("\n🔍 테스트 검색: '26세 서울 무직 월세 지원'")
results = collection.query(
    query_texts=["26세 서울 무직 월세 지원"],
    n_results=5,
)
print("\n검색 결과:")
for i, (meta, dist) in enumerate(zip(
    results["metadatas"][0],
    results["distances"][0]
)):
    print(f"  {i+1}. [{meta['category']}] {meta['name']}")
    print(f"     지역: {meta['region']} | 혜택: {meta['benefit_type']}")
    print(f"     유사도: {round((1-dist)*100, 1)}%")
    print()
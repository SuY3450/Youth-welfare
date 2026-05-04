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
            "raw_text":       str(p.get("raw_text", ""))[:500],
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
    print(f"ChromaDB 적재 완료! 총 {total}건")
    return total

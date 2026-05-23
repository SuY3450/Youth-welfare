import chromadb
from chromadb.utils import embedding_functions

# ===== ChromaDB 연결 =====
client = chromadb.PersistentClient(path="./chroma_db")

emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="jhgan/ko-sroberta-multitask"
)

collection = client.get_collection(
    name="welfare_policies",
    embedding_function=emb_fn,
)

# ===== 1. 기본 정보 확인 =====
print("=" * 50)
print("📊 기본 정보")
print("=" * 50)
print(f"총 저장 건수: {collection.count()}건")

# ===== 2. 샘플 데이터 확인 =====
print("\n" + "=" * 50)
print("📋 샘플 데이터 (첫 5건)")
print("=" * 50)
sample = collection.get(limit=5)
for i, (id_, meta) in enumerate(zip(sample['ids'], sample['metadatas'])):
    print(f"\n{i+1}. [{id_}] {meta['name']}")
    print(f"   카테고리: {meta['category']} | 혜택유형: {meta['benefit_type']}")
    print(f"   지역: {meta['region']} | 출처: {meta['source']}")
    print(f"   나이: {meta['age_min']}~{meta['age_max']}세 | 소득: {meta['income_max_pct']}%")

# ===== 3. 카테고리별 건수 =====
print("\n" + "=" * 50)
print("📂 카테고리별 건수")
print("=" * 50)
all_data = collection.get()
category_count = {}
for meta in all_data['metadatas']:
    cat = meta.get('category', '미분류')
    category_count[cat] = category_count.get(cat, 0) + 1
for cat, cnt in sorted(category_count.items(), key=lambda x: -x[1]):
    print(f"  {cat}: {cnt}건")

# ===== 4. 지역별 건수 =====
print("\n" + "=" * 50)
print("🗺️  지역별 건수 (상위 10)")
print("=" * 50)
region_count = {}
for meta in all_data['metadatas']:
    region = meta.get('region', '미분류')
    region_count[region] = region_count.get(region, 0) + 1
for region, cnt in sorted(region_count.items(), key=lambda x: -x[1])[:10]:
    print(f"  {region}: {cnt}건")

# ===== 5. 검색 테스트 3가지 =====
print("\n" + "=" * 50)
print("🔍 검색 테스트")
print("=" * 50)

test_queries = [
    "26세 서울 무직 월세 지원",
    "취준생 교통비 지원",
    "경기도 청년 저축 통장",
]

for query in test_queries:
    print(f"\n질문: '{query}'")
    results = collection.query(
        query_texts=[query],
        n_results=3,
    )
    for i, (meta, dist) in enumerate(zip(
        results['metadatas'][0],
        results['distances'][0]
    )):
        print(f"  {i+1}. [{meta['category']}] {meta['name']}")
        print(f"     지역: {meta['region']} | 유사도: {round((1-dist)*100, 1)}%")

print("\n✅ DB 확인 완료!")
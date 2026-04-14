import requests
import xml.etree.ElementTree as ET
import json
import time
import os
import csv
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("ONTONG_API_KEY")

BASE_URL = "https://www.youthcenter.go.kr/go/ythip/getPlcy"

TARGET_LCLSF = ["일자리", "주거", "교육", "복지문화"]

EXCLUDE_MCLSF = [
    "온·오프라인교육", "미래역량강화", "정책인프라구축",
    "청년참여", "청년국제교류", "권익보호",
]

REGION_MAP = {
    "서울": "서울특별시",
    "부산": "부산광역시",
    "대구": "대구광역시",
    "인천": "인천광역시",
    "광주": "광주광역시",
    "대전": "대전광역시",
    "울산": "울산광역시",
    "세종": "세종특별자치시",
    "경기": "경기도",
    "강원": "강원도",
    "충북": "충청북도",
    "충남": "충청남도",
    "전북": "전라북도",
    "전남": "전라남도",
    "경북": "경상북도",
    "경남": "경상남도",
    "제주": "제주특별자치도",
}

# 3개월 기준일
THREE_MONTHS_AGO = datetime.now() - timedelta(days=90)

def normalize_region(raw: str) -> str:
    if not raw:
        return "전국"
    raw = raw.strip()
    if raw in REGION_MAP.values():
        return raw
    for short, full in REGION_MAP.items():
        if raw.startswith(short):
            return full
    return raw

def extract_sub_region(up_inst: str, hghk_inst: str) -> str:
    if not up_inst:
        return ""
    up = up_inst.strip()
    hghk = hghk_inst.strip() if hghk_inst else ""
    if hghk and up.startswith(hghk):
        sub = up[len(hghk):].strip()
        return sub if sub else ""
    return up

def is_target(lclsf, mclsf):
    lclsf_ok = any(t in lclsf for t in TARGET_LCLSF)
    mclsf_ok = not any(e in mclsf for e in EXCLUDE_MCLSF)
    return lclsf_ok and mclsf_ok

def is_recent(frstRegDt: str) -> bool:
    """등록일이 3개월 이내인지 확인"""
    if not frstRegDt:
        return True
    try:
        reg_date = datetime.strptime(frstRegDt[:10], "%Y-%m-%d")
        return reg_date >= THREE_MONTHS_AGO
    except:
        return True

def fetch_page(page):
    params = {
        "apiKeyNm": API_KEY,
        "pageNum":  page,
        "pageSize": 100,
        "pageType": "1",
        "rtnType":  "xml",
    }
    res = requests.get(BASE_URL, params=params, timeout=15)
    res.encoding = "utf-8"
    return ET.fromstring(res.text)

def crawl():
    all_results = []
    seen = set()
    page = 1

    print("🔍 전체 수집 시작 (3개월 이내 + 대분류 필터)...")

    while True:
        print(f"  p{page}...", end=" ", flush=True)

        try:
            root = fetch_page(page)
        except Exception as e:
            print(f"에러: {e}")
            break

        policies = root.findall(".//youthPolicyList")
        if not policies:
            print("완료")
            break

        count = 0
        for p in policies:
            name      = p.findtext("plcyNm", "")
            lclsf     = p.findtext("lclsfNm", "")
            mclsf     = p.findtext("mclsfNm", "")
            content   = p.findtext("plcyExplnCn", "")
            sprt      = p.findtext("plcySprtCn", "")
            url       = p.findtext("aplyUrlAddr", "") or p.findtext("refUrlAddr1", "")
            period    = p.findtext("aplyYmd", "")
            frstRegDt = p.findtext("frstRegDt", "")
            hghk      = p.findtext("rgtrHghrkInstCdNm", "")
            up_inst   = p.findtext("rgtrUpInstCdNm", "")

            region     = normalize_region(hghk)
            sub_region = extract_sub_region(up_inst, hghk)

            if not is_target(lclsf, mclsf):
                continue
            if not is_recent(frstRegDt):
                continue
            if name in seen:
                continue

            seen.add(name)
            all_results.append({
                "name":         name,
                "category":     mclsf.strip(),
                "region":       region,
                "sub_region":   sub_region,
                "source":       "온통청년",
                "source_url":   url or "https://www.youthcenter.go.kr",
                "raw_text":     f"{content} {sprt}".strip(),
                "amount":       "",
                "deadline":     period,
                "registered_at": frstRegDt[:10] if frstRegDt else "",
                "collected_at": datetime.now().strftime("%Y-%m-%d"),
            })
            count += 1

        total = int(root.findtext(".//totCount", "0") or 0)
        print(f"{count}건 추가 (누적 {len(all_results)}건 / 전체 {total}건)")

        if total == 0 or page * 100 >= total:
            break
        page += 1
        time.sleep(0.5)

    os.makedirs("data/raw", exist_ok=True)

    json_path = "data/raw/승현_온통청년.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    csv_path = "data/raw/승현_온통청년.csv"
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "name", "category", "region", "sub_region",
            "source", "source_url", "raw_text", "amount",
            "deadline", "registered_at", "collected_at"
        ])
        writer.writeheader()
        writer.writerows(all_results)

    print(f"\n✅ 완료! 총 {len(all_results)}건")
    print(f"   → {json_path}")
    print(f"   → {csv_path}")

if __name__ == "__main__":
    crawl()
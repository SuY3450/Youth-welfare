"""
서울청년몽땅 자치구 정책 크롤러 (seoulyouth.py)
─────────────────────────────────────────────
- 온통청년 크롤러(승현_온통청년.py)와 동일한 스키마로 출력 → preprocess 병합 호환
- 마감(신청기간 종료) 공고 제외
- 카테고리(정책 유형) 필터: 주거 / 금융 / 취업 / 교육 / 창업
  └ 자치구 정책은 5개 대분류만 태깅됨(일자리/주거/금융복지/교육문화/참여소통)
    · 취업·창업 → '일자리'  · 금융 → '금융복지'  · 교육 → '교육문화'
    → '참여소통'만 제외하고 나머지 4개 대분류를 유지

[macOS 실행]  python3 seoulyouth.py
[필요 패키지] pip3 install requests beautifulsoup4
[출력]        data/raw/seoulyouth.json , data/raw/seoulyouth.csv
"""
import requests
import json
import re
import time
import os
import csv
from datetime import datetime
from bs4 import BeautifulSoup

LIST_URL   = "https://youth.seoul.go.kr/infoData/plcyInfo/guList.do"
DETAIL_URL = "https://youth.seoul.go.kr/infoData/plcyInfo/view.do"
KEY        = "2309150002"
TAB_KIND   = "003"   # 003 = 자치구 정책

HEADERS = {"User-Agent": "Mozilla/5.0 (capstone-research-crawler)"}

# 원하는 카테고리 → 자치구 '정책 유형' 매핑 (참여소통만 제외)
TARGET_TYPES = ["일자리", "주거", "금융복지", "교육문화"]

TODAY = datetime.now().strftime("%Y%m%d")

# 상세 라벨 → 임시 키
LABEL_MAP = {
    "정책 유형": "policy_type", "주관 기관": "org",
    "정책 소개": "intro", "지원 내용": "support",
    "사업운영기간": "operate_period", "사업신청기간": "apply_period",
    "지원규모": "scale", "관련 사이트": "ref_site",
    "연령": "age_raw", "학력": "school", "전공요건": "major",
    "취업상태": "job", "특화분야 요건": "special",
    "추가단서 사항": "add_qlfc", "참여제한 대상": "exclude",
    "신청절차": "apply_method", "심사 및 발표": "select_method",
    "제출서류": "submit_docs", "신청 사이트": "apply_site",
    "기타사항": "etc_matter", "운영기관": "oper_inst",
    "참고 사이트 Ⅰ": "ref1", "참고 사이트 Ⅱ": "ref2",
}


def get_list(page):
    """자치구 정책 목록 1페이지 → [{plcy_no, name}, ...]"""
    params = {"key": KEY, "tabKind": TAB_KIND, "pageIndex": page,
              "orderBy": "regYmd desc", "blueWorksYn": "N", "sw": ""}
    r = requests.get(LIST_URL, params=params, headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    items = []
    for a in soup.select("a.tit[onclick]"):
        m = re.search(r"goView\('(\d+)'\)", a.get("onclick", ""))
        if m:
            items.append({"plcy_no": m.group(1), "name": a.get_text(strip=True)})
    return items


def get_detail(plcy_no):
    """상세 라벨 테이블 → {임시키: 값}"""
    params = {"key": KEY, "tabKind": TAB_KIND, "plcyBizId": plcy_no}
    r = requests.get(DETAIL_URL, params=params, headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    raw = {v: "" for v in LABEL_MAP.values()}
    for th in soup.select("table th"):
        label = th.get_text(strip=True)
        if label in LABEL_MAP:
            td = th.find_next("td")
            raw[LABEL_MAP[label]] = td.get_text(" ", strip=True) if td else ""
    return raw


def parse_age(text):
    m = re.search(r"(\d{1,2})\s*세\s*[~∼\-]\s*(?:만\s*)?(\d{1,2})\s*세", text or "")
    return (m.group(1), m.group(2)) if m else ("", "")


def parse_apply_period(text):
    """'20260202 ~ 20261210' → ('20260202', '20261210'). 끝날짜 없으면 빈값"""
    nums = re.findall(r"\d{8}", text or "")
    if len(nums) >= 2:
        return nums[0], nums[1]
    if len(nums) == 1:
        return nums[0], ""
    return "", ""


def is_expired(apply_end):
    """신청 종료일이 과거면 True. 끝날짜 불명확하면 False(상시/예산소진 등 유지)"""
    return bool(apply_end) and apply_end < TODAY


def is_target_category(policy_type):
    return any(t in policy_type for t in TARGET_TYPES)


def build_record(item, d):
    sub_m = re.search(r"([가-힣]+구|[가-힣]+군)", d.get("org", ""))
    sub_region = sub_m.group(1) if sub_m else ""
    age_min, age_max = parse_age(d.get("age_raw", ""))
    scale = re.sub(r"[^\d]", "", d.get("scale", "") or "")
    # raw_text: 정책소개 + 지원내용 + 추가단서(소득·자격 조건이 여기 묻혀있어 함께 넣음)
    raw_text = " ".join(t for t in [
        d.get("intro", ""), d.get("support", ""), d.get("add_qlfc", "")
    ] if t).strip()
    return {
        "plcy_no":          item["plcy_no"],
        "name":             item["name"],
        "lclsf":            d.get("policy_type", ""),
        "category":         "",
        "keyword":          "",
        "region":           "서울특별시",
        "sub_region":       sub_region,
        "source":           "서울청년몽땅(자치구)",
        "source_url":       f"{DETAIL_URL}?plcyBizId={item['plcy_no']}&key={KEY}&tabKind={TAB_KIND}",
        "ref_url2":         d.get("ref2", ""),
        "raw_text":         raw_text,
        "amount":           "",
        "deadline":         d.get("apply_period", ""),
        "registered_at":    "",
        "last_modified_at": "",
        "collected_at":     datetime.now().strftime("%Y-%m-%d"),
        "aply_prd_type":    "",
        "biz_prd_type":     "",
        "biz_start_ymd":    "",
        "biz_end_ymd":      "",
        "biz_prd_etc":      d.get("operate_period", ""),
        "age_min":          age_min,
        "age_max":          age_max,
        "age_limit_yn":     "",
        "earn_cnd":         "",
        "earn_min_amt":     "",
        "earn_max_amt":     "",
        "earn_etc":         "",
        "mrg_stts":         "",
        "job":              d.get("job", ""),
        "school":           d.get("school", ""),
        "major":            d.get("major", ""),
        "special_target":   d.get("special", ""),
        "pvmthd":           "",
        "pvmthd_group":     "지자체",
        "sprt_scl_cnt":     scale,
        "sprt_scl_lmt_yn":  "",
        "sprt_arvl_seq_yn": "",
        "add_qlfc":         d.get("add_qlfc", ""),
        "exclude_target":   d.get("exclude", ""),
        "apply_method":     d.get("apply_method", ""),
        "select_method":    d.get("select_method", ""),
        "submit_docs":      d.get("submit_docs", ""),
        "etc_matter":       d.get("etc_matter", ""),
        "sprvsn_inst_nm":   d.get("org", ""),
        "oper_inst_nm":     d.get("oper_inst", ""),
        "rgtr_inst_nm":     "",
        "zip_cd":           "",
        "inq_cnt":          "",
        "aprvl_stts":       "",
    }


# 온통청년 크롤러와 동일한 CSV 컬럼 순서 (병합 호환)
FIELDNAMES = [
    "plcy_no", "name", "lclsf", "category", "keyword",
    "region", "sub_region", "source", "source_url", "ref_url2",
    "raw_text", "amount", "deadline", "registered_at", "last_modified_at", "collected_at",
    "aply_prd_type", "biz_prd_type", "biz_start_ymd", "biz_end_ymd", "biz_prd_etc",
    "age_min", "age_max", "age_limit_yn",
    "earn_cnd", "earn_min_amt", "earn_max_amt", "earn_etc",
    "mrg_stts", "job", "school", "major", "special_target",
    "pvmthd", "pvmthd_group",
    "sprt_scl_cnt", "sprt_scl_lmt_yn", "sprt_arvl_seq_yn",
    "add_qlfc", "exclude_target",
    "apply_method", "select_method", "submit_docs", "etc_matter",
    "sprvsn_inst_nm", "oper_inst_nm", "rgtr_inst_nm",
    "zip_cd", "inq_cnt", "aprvl_stts",
]


def crawl(max_pages=200, sleep=0.4):
    rows, seen, page = [], set(), 1
    skip_cat, skip_exp = 0, 0
    print("🔍 서울청년몽땅 자치구 정책 수집 시작 (마감 제외 + 카테고리 필터)...")
    while page <= max_pages:
        try:
            items = get_list(page)
        except Exception as e:
            print(f"  목록 p{page} 에러: {e}")
            break
        if not items:
            print("  목록 끝")
            break

        for it in items:
            if it["plcy_no"] in seen:        # plcy_no 기준 1차 중복 차단
                continue
            seen.add(it["plcy_no"])
            try:
                d = get_detail(it["plcy_no"])
            except Exception as e:
                print(f"  상세 실패 {it['plcy_no']}: {e}")
                continue

            if not is_target_category(d.get("policy_type", "")):  # 카테고리 필터
                skip_cat += 1
                time.sleep(sleep)
                continue

            _, apply_end = parse_apply_period(d.get("apply_period", ""))
            if is_expired(apply_end):                              # 마감 필터
                skip_exp += 1
                time.sleep(sleep)
                continue

            rows.append(build_record(it, d))
            time.sleep(sleep)

        print(f"  p{page} 완료 (누적 {len(rows)}건 / 제외: 카테고리 {skip_cat}, 마감 {skip_exp})")
        page += 1
        time.sleep(sleep)

    os.makedirs("data/raw", exist_ok=True)
    json_path = "data/raw/seoulyouth.json"
    csv_path  = "data/raw/seoulyouth.csv"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n✅ 완료! 총 {len(rows)}건 (카테고리 제외 {skip_cat} / 마감 제외 {skip_exp})")
    print(f"   → {json_path}")
    print(f"   → {csv_path}")


if __name__ == "__main__":
    crawl()
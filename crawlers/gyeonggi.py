"""
경기청년포털 시군정책 크롤러 (gyeonggi.py)
─────────────────────────────────────────────
- youth.gg.go.kr 정책 아카이브(archive-policy-search-map.do)에서 '시군' 정책만 수집
  · [경기도] = 도 단위 → 제외 (온통청년에 이미 있음) / [부천시] 등 시군명만 수집
- 온통청년/서울과 동일한 스키마로 출력 → preprocess 병합 호환
- lclsf 는 제목+본문 키워드로 추정 → preprocess 의 infer_category 가 중분류 자동 채움
- 신청방법 등 <li> 안의 <a href> 링크 수집 → 신청 링크는 ref_url2 에 저장

[macOS 실행]  python3 gyeonggi.py
[필요 패키지] pip3 install requests beautifulsoup4
[출력]        data/raw/gyeonggi.json , data/raw/gyeonggi.csv
"""
import requests
import json
import re
import time
import os
import csv
from datetime import datetime
from bs4 import BeautifulSoup

BASE = "https://youth.gg.go.kr/gg/info/archive-policy-search-map.do"
HEADERS = {"User-Agent": "Mozilla/5.0 (capstone-research-crawler)"}
TODAY = datetime.now().strftime("%Y%m%d")

L_DEADLINE = ["신청기간", "지원기간", "모집기간", "접수기간"]
L_TARGET   = ["모집대상", "지원대상", "참여대상", "신청자격"]
L_CONTENT  = ["모집내용", "지원내용", "교육내용", "활동내용", "참여내용", "사업내용"]
L_APPLY    = ["신청방법", "접수방법", "신청절차"]


def get_list(offset=0, limit=8):
    """목록 1페이지 → [{arcNo, sigun, title}, ...] (시군명 있는 것만)"""
    params = {"pager.offset": offset, "pagerLimit": limit}
    r = requests.get(BASE, params=params, headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    items = []
    for a in soup.select("a.text[href*='arcNo=']"):
        m = re.search(r"arcNo=(\d+)", a.get("href", ""))
        if not m:
            continue
        tit = a.select_one("p.tit")
        full = tit.get_text(" ", strip=True) if tit else ""
        gm = re.search(r"\[([가-힣]+[시군])\]", full)        # [부천시] 만 (도 단위 [경기도] 제외)
        if not gm:
            continue
        sigun = gm.group(1)
        title = re.sub(r"\[[가-힣]+[시군구]\]", "", full).strip()
        items.append({"arcNo": m.group(1), "sigun": sigun, "title": title})
    return items


def get_detail(arc_no):
    """상세 fr-view → ({라벨: 값}, {라벨: 링크})"""
    params = {"mode": "view", "arcNo": arc_no}
    r = requests.get(BASE, params=params, headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    view = soup.select_one("div.fr-view")
    fields, links = {}, {}
    if not view:
        return fields, links
    for li in view.select("li"):
        strong = li.find("strong")
        if not strong:
            continue
        label = strong.get_text(strip=True).rstrip(":").strip()
        if not label:
            continue
        full = li.get_text(" ", strip=True)
        val = full.replace(strong.get_text(strip=True), "", 1).strip().lstrip(":").strip()
        if val:
            fields[label] = val
        a = li.find("a", href=True)          # 라벨 li 안의 링크 (네이버폼 등)
        if a and a["href"].startswith("http"):
            links[label] = a["href"]
    return fields, links


def pick(fields, candidates):
    for c in candidates:
        if fields.get(c):
            return fields[c]
    return ""


def pick_link(links, candidates):
    for c in candidates:
        if links.get(c):
            return links[c]
    return ""


def parse_age(text):
    # '만 19세 ~ 만 39세', '19~39세' 등 모두 처리 (두 번째 '만 ' 허용)
    m = re.search(r"(\d{1,2})\s*세?\s*[~∼\-]\s*(?:만\s*)?(\d{1,2})\s*세", text or "")
    return (m.group(1), m.group(2)) if m else ("", "")


def parse_period_end(text):
    """'2026. 5.20.~ 6. 9.' → '20260609' (best effort). 상시/불명확이면 ''"""
    if not text or "상시" in text:
        return ""
    t = re.sub(r"\s", "", text)
    ym = re.search(r"(20\d\d)", t)
    year = ym.group(1) if ym else ""
    tail = t.split("~")[-1]
    md = re.findall(r"(\d{1,2})\.(\d{1,2})", tail)
    if year and md:
        mm, dd = md[-1]
        return f"{year}{int(mm):02d}{int(dd):02d}"
    return ""


def guess_lclsf(text):
    """제목+본문 키워드로 대분류 추정 (온통청년 lclsf 어휘에 맞춤)"""
    if re.search(r"취업|채용|일자리|구직|면접|인턴|창업|스타트업", text):
        return "일자리"
    if re.search(r"주거|주택|전월세|임대|월세|전세|기숙사|집수리|보증금", text):
        return "주거"
    if re.search(r"금융|대출|이자|자산|적금|통장|부채|신용|법률|법무", text):
        return "금융복지"
    if re.search(r"교육|강의|클래스|특강|아카데미|멘토링|진로|역량|자기개발|학습|체험|문화|예술", text):
        return "교육문화"
    return ""


def is_expired(end):
    return bool(end) and end < TODAY


def build_record(item, d, links):
    target  = pick(d, L_TARGET)
    content = pick(d, L_CONTENT)
    apply_m = pick(d, L_APPLY)
    deadline = pick(d, L_DEADLINE)
    apply_link = pick_link(links, L_APPLY)            # 신청 링크 (네이버폼 등)
    raw_text = " ".join(t for t in [target, content] if t).strip()
    age_min, age_max = parse_age(raw_text)            # 본문 전체에서 나이 추출
    return {
        "plcy_no":          item["arcNo"],
        "name":             item["title"],
        "lclsf":            guess_lclsf(f"{item['title']} {raw_text}"),
        "category":         "",
        "keyword":          "",
        "region":           "경기도",
        "sub_region":       item["sigun"],
        "source":           "경기청년포털(시군)",
        "source_url":       f"{BASE}?mode=view&arcNo={item['arcNo']}",
        "ref_url2":         apply_link,
        "raw_text":         raw_text,
        "amount":           "",
        "deadline":         deadline,
        "registered_at":    "",
        "last_modified_at": "",
        "collected_at":     datetime.now().strftime("%Y-%m-%d"),
        "aply_prd_type":    "",
        "biz_prd_type":     "",
        "biz_start_ymd":    "",
        "biz_end_ymd":      "",
        "biz_prd_etc":      "",
        "age_min":          age_min,
        "age_max":          age_max,
        "age_limit_yn":     "",
        "earn_cnd":         "",
        "earn_min_amt":     "",
        "earn_max_amt":     "",
        "earn_etc":         "",
        "mrg_stts":         "",
        "job":              "",
        "school":           "",
        "major":            "",
        "special_target":   "",
        "pvmthd":           "",
        "pvmthd_group":     "지자체",
        "sprt_scl_cnt":     "",
        "sprt_scl_lmt_yn":  "",
        "sprt_arvl_seq_yn": "",
        "add_qlfc":         target,
        "exclude_target":   "",
        "apply_method":     apply_m,
        "select_method":    "",
        "submit_docs":      "",
        "etc_matter":       "",
        "sprvsn_inst_nm":   "",
        "oper_inst_nm":     "",
        "rgtr_inst_nm":     "",
        "zip_cd":           "",
        "inq_cnt":          "",
        "aprvl_stts":       "",
    }


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


def crawl(limit=8, sleep=1.0, max_pages=300):
    rows, seen, offset, page = [], set(), 0, 1
    skip_exp = 0
    print("🔍 경기청년포털 시군정책 수집 시작...")
    while page <= max_pages:
        try:
            items = get_list(offset, limit)
        except Exception as e:
            print(f"  목록 offset={offset} 에러: {e}")
            break
        if not items:
            probe = get_list(offset, limit)
            if not probe:
                print("  목록 끝")
                break

        for it in items:
            if it["arcNo"] in seen:
                continue
            seen.add(it["arcNo"])
            try:
                d, links = get_detail(it["arcNo"])
            except Exception as e:
                print(f"  상세 실패 {it['arcNo']}: {e}")
                continue
            rec = build_record(it, d, links)
            if is_expired(parse_period_end(rec["deadline"])):
                skip_exp += 1
                time.sleep(sleep)
                continue
            rows.append(rec)
            time.sleep(sleep)

        print(f"  p{page} (offset={offset}) 완료 (누적 {len(rows)}건 / 마감제외 {skip_exp})")
        offset += limit
        page += 1
        time.sleep(sleep)

    os.makedirs("data/raw", exist_ok=True)
    json_path = "data/raw/gyeonggi.json"
    csv_path  = "data/raw/gyeonggi.csv"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES)
        w.writeheader()
        w.writerows(rows)
    print(f"\n✅ 완료! 총 {len(rows)}건 (마감 제외 {skip_exp})")
    print(f"   → {json_path}")
    print(f"   → {csv_path}")


if __name__ == "__main__":
    crawl()
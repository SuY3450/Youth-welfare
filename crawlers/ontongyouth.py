import requests
import json
import re
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
    "서울": "서울특별시", "부산": "부산광역시", "대구": "대구광역시",
    "인천": "인천광역시", "광주": "광주광역시", "대전": "대전광역시",
    "울산": "울산광역시", "세종": "세종특별자치시", "경기": "경기도",
    "강원": "강원도", "충북": "충청북도", "충남": "충청남도",
    "전북": "전라북도", "전남": "전라남도", "경북": "경상북도",
    "경남": "경상남도", "제주": "제주특별자치도",
}

# 전국 시군구 → 상위 광역시도 매핑
SIGUNGU_TO_SIDO = {
    # 서울특별시
    "종로구": "서울특별시", "중구": "서울특별시", "용산구": "서울특별시",
    "성동구": "서울특별시", "광진구": "서울특별시", "동대문구": "서울특별시",
    "중랑구": "서울특별시", "성북구": "서울특별시", "강북구": "서울특별시",
    "도봉구": "서울특별시", "노원구": "서울특별시", "은평구": "서울특별시",
    "서대문구": "서울특별시", "마포구": "서울특별시", "양천구": "서울특별시",
    "강서구": "서울특별시", "구로구": "서울특별시", "금천구": "서울특별시",
    "영등포구": "서울특별시", "동작구": "서울특별시", "관악구": "서울특별시",
    "서초구": "서울특별시", "강남구": "서울특별시", "송파구": "서울특별시",
    "강동구": "서울특별시",
    # 부산광역시
    "영도구": "부산광역시", "부산진구": "부산광역시", "동래구": "부산광역시",
    "해운대구": "부산광역시", "사하구": "부산광역시", "금정구": "부산광역시",
    "연제구": "부산광역시", "수영구": "부산광역시", "사상구": "부산광역시",
    "기장군": "부산광역시",
    # 대구광역시
    "수성구": "대구광역시", "달서구": "대구광역시", "달성군": "대구광역시",
    "군위군": "대구광역시",
    # 인천광역시
    "미추홀구": "인천광역시", "연수구": "인천광역시", "남동구": "인천광역시",
    "부평구": "인천광역시", "계양구": "인천광역시", "강화군": "인천광역시",
    "옹진군": "인천광역시",
    # 광주광역시
    "광산구": "광주광역시",
    # 대전광역시
    "유성구": "대전광역시", "대덕구": "대전광역시",
    # 울산광역시
    "울주군": "울산광역시",
    # 경기도
    "수원시": "경기도", "성남시": "경기도", "의정부시": "경기도",
    "안양시": "경기도", "부천시": "경기도", "광명시": "경기도",
    "평택시": "경기도", "동두천시": "경기도", "안산시": "경기도",
    "고양시": "경기도", "과천시": "경기도", "구리시": "경기도",
    "남양주시": "경기도", "오산시": "경기도", "시흥시": "경기도",
    "군포시": "경기도", "의왕시": "경기도", "하남시": "경기도",
    "용인시": "경기도", "파주시": "경기도", "이천시": "경기도",
    "안성시": "경기도", "김포시": "경기도", "화성시": "경기도",
    "광주시": "경기도", "양주시": "경기도", "포천시": "경기도",
    "여주시": "경기도", "연천군": "경기도", "가평군": "경기도",
    "양평군": "경기도",
    # 강원도
    "춘천시": "강원도", "원주시": "강원도", "강릉시": "강원도",
    "동해시": "강원도", "태백시": "강원도", "속초시": "강원도",
    "삼척시": "강원도", "홍천군": "강원도", "횡성군": "강원도",
    "영월군": "강원도", "평창군": "강원도", "정선군": "강원도",
    "철원군": "강원도", "화천군": "강원도", "양구군": "강원도",
    "인제군": "강원도", "고성군": "강원도", "양양군": "강원도",
    # 충청북도
    "청주시": "충청북도", "충주시": "충청북도", "제천시": "충청북도",
    "보은군": "충청북도", "옥천군": "충청북도", "영동군": "충청북도",
    "증평군": "충청북도", "진천군": "충청북도", "괴산군": "충청북도",
    "음성군": "충청북도", "단양군": "충청북도",
    # 충청남도
    "천안시": "충청남도", "공주시": "충청남도", "보령시": "충청남도",
    "아산시": "충청남도", "서산시": "충청남도", "논산시": "충청남도",
    "계룡시": "충청남도", "당진시": "충청남도", "금산군": "충청남도",
    "부여군": "충청남도", "서천군": "충청남도", "청양군": "충청남도",
    "홍성군": "충청남도", "예산군": "충청남도", "태안군": "충청남도",
    # 전라북도
    "전주시": "전라북도", "군산시": "전라북도", "익산시": "전라북도",
    "정읍시": "전라북도", "남원시": "전라북도", "김제시": "전라북도",
    "완주군": "전라북도", "진안군": "전라북도", "무주군": "전라북도",
    "장수군": "전라북도", "임실군": "전라북도", "순창군": "전라북도",
    "고창군": "전라북도", "부안군": "전라북도",
    # 전라남도
    "목포시": "전라남도", "여수시": "전라남도", "순천시": "전라남도",
    "나주시": "전라남도", "광양시": "전라남도", "담양군": "전라남도",
    "곡성군": "전라남도", "구례군": "전라남도", "고흥군": "전라남도",
    "보성군": "전라남도", "화순군": "전라남도", "장흥군": "전라남도",
    "강진군": "전라남도", "해남군": "전라남도", "영암군": "전라남도",
    "무안군": "전라남도", "함평군": "전라남도", "영광군": "전라남도",
    "장성군": "전라남도", "완도군": "전라남도", "진도군": "전라남도",
    "신안군": "전라남도",
    # 경상북도
    "포항시": "경상북도", "경주시": "경상북도", "김천시": "경상북도",
    "안동시": "경상북도", "구미시": "경상북도", "영주시": "경상북도",
    "영천시": "경상북도", "상주시": "경상북도", "문경시": "경상북도",
    "경산시": "경상북도", "의성군": "경상북도", "청송군": "경상북도",
    "영양군": "경상북도", "영덕군": "경상북도", "청도군": "경상북도",
    "고령군": "경상북도", "성주군": "경상북도", "칠곡군": "경상북도",
    "예천군": "경상북도", "봉화군": "경상북도", "울진군": "경상북도",
    "울릉군": "경상북도",
    # 경상남도
    "창원시": "경상남도", "진주시": "경상남도", "통영시": "경상남도",
    "사천시": "경상남도", "김해시": "경상남도", "밀양시": "경상남도",
    "거제시": "경상남도", "양산시": "경상남도", "의령군": "경상남도",
    "함안군": "경상남도", "창녕군": "경상남도", "남해군": "경상남도",
    "하동군": "경상남도", "산청군": "경상남도", "함양군": "경상남도",
    "거창군": "경상남도", "합천군": "경상남도",
    # 제주특별자치도
    "제주시": "제주특별자치도", "서귀포시": "제주특별자치도",
}

# zip_cd 앞 3자리 → (광역시도, 시군구)
ZIPCODE_PREFIX_MAP = {
    # 서울
    "030": ("서울특별시", "종로구"), "040": ("서울특별시", "중구"),
    "042": ("서울특별시", "용산구"), "044": ("서울특별시", "성동구"),
    "046": ("서울특별시", "광진구"), "048": ("서울특별시", "동대문구"),
    "050": ("서울특별시", "중랑구"), "012": ("서울특별시", "성북구"),
    "014": ("서울특별시", "강북구"), "016": ("서울특별시", "도봉구"),
    "018": ("서울특별시", "노원구"), "020": ("서울특별시", "은평구"),
    "022": ("서울특별시", "서대문구"), "024": ("서울특별시", "마포구"),
    "026": ("서울특별시", "양천구"), "028": ("서울특별시", "강서구"),
    "152": ("서울특별시", "구로구"), "154": ("서울특별시", "금천구"),
    "070": ("서울특별시", "영등포구"), "072": ("서울특별시", "동작구"),
    "074": ("서울특별시", "관악구"), "060": ("서울특별시", "서초구"),
    "062": ("서울특별시", "강남구"), "064": ("서울특별시", "송파구"),
    "066": ("서울특별시", "강동구"),
    # 부산
    "600": ("부산광역시", "중구"), "602": ("부산광역시", "서구"),
    "604": ("부산광역시", "동구"), "606": ("부산광역시", "영도구"),
    "608": ("부산광역시", "부산진구"), "610": ("부산광역시", "동래구"),
    "612": ("부산광역시", "남구"), "614": ("부산광역시", "북구"),
    "616": ("부산광역시", "해운대구"), "618": ("부산광역시", "사하구"),
    "620": ("부산광역시", "금정구"), "622": ("부산광역시", "강서구"),
    "624": ("부산광역시", "연제구"), "626": ("부산광역시", "수영구"),
    "628": ("부산광역시", "사상구"), "630": ("부산광역시", "기장군"),
    # 대구
    "700": ("대구광역시", "중구"), "701": ("대구광역시", "동구"),
    "703": ("대구광역시", "서구"), "705": ("대구광역시", "남구"),
    "702": ("대구광역시", "북구"), "706": ("대구광역시", "수성구"),
    "704": ("대구광역시", "달서구"), "711": ("대구광역시", "달성군"),
    # 인천
    "400": ("인천광역시", "중구"), "402": ("인천광역시", "동구"),
    "404": ("인천광역시", "미추홀구"), "406": ("인천광역시", "연수구"),
    "405": ("인천광역시", "남동구"), "403": ("인천광역시", "부평구"),
    "407": ("인천광역시", "계양구"), "408": ("인천광역시", "서구"),
    "417": ("인천광역시", "강화군"), "415": ("인천광역시", "옹진군"),
    # 광주
    "500": ("광주광역시", "동구"), "502": ("광주광역시", "서구"),
    "503": ("광주광역시", "남구"), "501": ("광주광역시", "북구"),
    "506": ("광주광역시", "광산구"),
    # 대전
    "300": ("대전광역시", "동구"), "301": ("대전광역시", "중구"),
    "302": ("대전광역시", "서구"), "305": ("대전광역시", "유성구"),
    "306": ("대전광역시", "대덕구"),
    # 울산
    "680": ("울산광역시", "중구"), "682": ("울산광역시", "남구"),
    "684": ("울산광역시", "동구"), "683": ("울산광역시", "북구"),
    "689": ("울산광역시", "울주군"),
    # 세종
    "339": ("세종특별자치시", ""),
    # 경기
    "440": ("경기도", "수원시"), "441": ("경기도", "수원시"),
    "442": ("경기도", "수원시"), "443": ("경기도", "수원시"),
    "463": ("경기도", "성남시"), "462": ("경기도", "성남시"),
    "461": ("경기도", "성남시"), "480": ("경기도", "의정부시"),
    "430": ("경기도", "안양시"), "431": ("경기도", "안양시"),
    "420": ("경기도", "부천시"), "421": ("경기도", "부천시"),
    "423": ("경기도", "광명시"), "450": ("경기도", "평택시"),
    "459": ("경기도", "평택시"), "483": ("경기도", "동두천시"),
    "425": ("경기도", "안산시"), "426": ("경기도", "안산시"),
    "410": ("경기도", "고양시"), "411": ("경기도", "고양시"),
    "412": ("경기도", "고양시"), "427": ("경기도", "과천시"),
    "471": ("경기도", "구리시"), "472": ("경기도", "남양주시"),
    "447": ("경기도", "오산시"), "429": ("경기도", "시흥시"),
    "435": ("경기도", "군포시"), "437": ("경기도", "의왕시"),
    "465": ("경기도", "하남시"), "448": ("경기도", "용인시"),
    "449": ("경기도", "용인시"), "446": ("경기도", "용인시"),
    "413": ("경기도", "파주시"), "467": ("경기도", "이천시"),
    "456": ("경기도", "안성시"), "415": ("경기도", "김포시"),
    "445": ("경기도", "화성시"), "464": ("경기도", "광주시"),
    "482": ("경기도", "양주시"), "487": ("경기도", "포천시"),
    "469": ("경기도", "여주시"), "484": ("경기도", "연천군"),
    "477": ("경기도", "가평군"), "476": ("경기도", "양평군"),
    # 강원
    "200": ("강원도", "춘천시"), "220": ("강원도", "원주시"),
    "210": ("강원도", "강릉시"), "240": ("강원도", "동해시"),
    "245": ("강원도", "태백시"), "217": ("강원도", "속초시"),
    "250": ("강원도", "삼척시"), "430": ("강원도", "홍천군"),
    "225": ("강원도", "횡성군"), "230": ("강원도", "영월군"),
    "232": ("강원도", "평창군"), "233": ("강원도", "정선군"),
    "269": ("강원도", "철원군"), "263": ("강원도", "화천군"),
    "265": ("강원도", "양구군"), "267": ("강원도", "인제군"),
    "219": ("강원도", "고성군"), "215": ("강원도", "양양군"),
    # 충북
    "360": ("충청북도", "청주시"), "361": ("충청북도", "청주시"),
    "362": ("충청북도", "청주시"), "363": ("충청북도", "청주시"),
    "380": ("충청북도", "충주시"), "390": ("충청북도", "제천시"),
    "376": ("충청북도", "보은군"), "373": ("충청북도", "옥천군"),
    "370": ("충청북도", "영동군"), "368": ("충청북도", "증평군"),
    "365": ("충청북도", "진천군"), "367": ("충청북도", "괴산군"),
    "369": ("충청북도", "음성군"), "395": ("충청북도", "단양군"),
    # 충남
    "330": ("충청남도", "천안시"), "331": ("충청남도", "천안시"),
    "314": ("충청남도", "공주시"), "355": ("충청남도", "보령시"),
    "336": ("충청남도", "아산시"), "356": ("충청남도", "서산시"),
    "320": ("충청남도", "논산시"), "320": ("충청남도", "계룡시"),
    "343": ("충청남도", "당진시"), "312": ("충청남도", "금산군"),
    "323": ("충청남도", "부여군"), "325": ("충청남도", "서천군"),
    "345": ("충청남도", "청양군"), "350": ("충청남도", "홍성군"),
    "340": ("충청남도", "예산군"), "357": ("충청남도", "태안군"),
    "448": ("충청남도", "태안군"),
    "442": ("충청남도", "계룡시"),
    # 전북
    "560": ("전라북도", "전주시"), "561": ("전라북도", "전주시"),
    "573": ("전라북도", "군산시"), "570": ("전라북도", "익산시"),
    "580": ("전라북도", "정읍시"), "590": ("전라북도", "남원시"),
    "576": ("전라북도", "김제시"), "565": ("전라북도", "완주군"),
    "567": ("전라북도", "진안군"), "568": ("전라북도", "무주군"),
    "597": ("전라북도", "장수군"), "595": ("전라북도", "임실군"),
    "596": ("전라북도", "순창군"), "585": ("전라북도", "고창군"),
    "579": ("전라북도", "부안군"),
    # 전남
    "530": ("전라남도", "목포시"), "550": ("전라남도", "여수시"),
    "540": ("전라남도", "순천시"), "520": ("전라남도", "나주시"),
    "545": ("전라남도", "광양시"), "517": ("전라남도", "담양군"),
    "515": ("전라남도", "곡성군"), "516": ("전라남도", "구례군"),
    "548": ("전라남도", "고흥군"), "546": ("전라남도", "보성군"),
    "519": ("전라남도", "화순군"), "529": ("전라남도", "장흥군"),
    "527": ("전라남도", "강진군"), "535": ("전라남도", "해남군"),
    "526": ("전라남도", "영암군"), "534": ("전라남도", "무안군"),
    "512": ("전라남도", "함평군"), "513": ("전라남도", "영광군"),
    "514": ("전라남도", "장성군"), "537": ("전라남도", "완도군"),
    "533": ("전라남도", "진도군"), "525": ("전라남도", "신안군"),
    # 경북
    "790": ("경상북도", "포항시"), "791": ("경상북도", "포항시"),
    "780": ("경상북도", "경주시"), "740": ("경상북도", "김천시"),
    "760": ("경상북도", "안동시"), "730": ("경상북도", "구미시"),
    "750": ("경상북도", "영주시"), "770": ("경상북도", "영천시"),
    "742": ("경상북도", "상주시"), "745": ("경상북도", "문경시"),
    "712": ("경상북도", "경산시"), "769": ("경상북도", "의성군"),
    "755": ("경상북도", "청송군"), "768": ("경상북도", "영양군"),
    "766": ("경상북도", "영덕군"), "714": ("경상북도", "청도군"),
    "716": ("경상북도", "고령군"), "719": ("경상북도", "성주군"),
    "718": ("경상북도", "칠곡군"), "757": ("경상북도", "예천군"),
    "754": ("경상북도", "봉화군"), "767": ("경상북도", "울진군"),
    "799": ("경상북도", "울릉군"),
    # 경남
    "642": ("경상남도", "창원시"), "641": ("경상남도", "창원시"),
    "660": ("경상남도", "진주시"), "650": ("경상남도", "통영시"),
    "664": ("경상남도", "사천시"), "621": ("경상남도", "김해시"),
    "627": ("경상남도", "밀양시"), "656": ("경상남도", "거제시"),
    "626": ("경상남도", "양산시"), "638": ("경상남도", "의령군"),
    "637": ("경상남도", "함안군"), "635": ("경상남도", "창녕군"),
    "672": ("경상남도", "고성군"), "668": ("경상남도", "남해군"),
    "667": ("경상남도", "하동군"), "666": ("경상남도", "산청군"),
    "670": ("경상남도", "함양군"), "673": ("경상남도", "거창군"),
    "678": ("경상남도", "합천군"),
    # 제주
    "630": ("제주특별자치도", "제주시"), "631": ("제주특별자치도", "제주시"),
    "632": ("제주특별자치도", "제주시"), "690": ("제주특별자치도", "서귀포시"),
    "697": ("제주특별자치도", "서귀포시"),
}

# source_url 도메인 키워드 → 광역시도 (or 시군구)
URL_DOMAIN_MAP = {
    "seoul":     ("서울특별시", ""),
    "busan":     ("부산광역시", ""),
    "daegu":     ("대구광역시", ""),
    "incheon":   ("인천광역시", ""),
    "gwangju":   ("광주광역시", ""),
    "daejeon":   ("대전광역시", ""),
    "ulsan":     ("울산광역시", ""),
    "sejong":    ("세종특별자치시", ""),
    "gyeonggi":  ("경기도", ""),
    "gangwon":   ("강원도", ""),
    "chungbuk":  ("충청북도", ""),
    "chungnam":  ("충청남도", ""),
    "jeonbuk":   ("전라북도", ""),
    "jeonnam":   ("전라남도", ""),
    "gyeongbuk": ("경상북도", ""),
    "gyeongnam": ("경상남도", ""),
    "jeju":      ("제주특별자치도", ""),
    # 시군구 도메인
    "gyeryong":  ("충청남도", "계룡시"),
    "asan":      ("충청남도", "아산시"),
    "taean":     ("충청남도", "태안군"),
    "cheonan":   ("충청남도", "천안시"),
    "suwon":     ("경기도", "수원시"),
    "seongnam":  ("경기도", "성남시"),
    "goyang":    ("경기도", "고양시"),
    "yongin":    ("경기도", "용인시"),
    "hwaseong":  ("경기도", "화성시"),
    "changwon":  ("경상남도", "창원시"),
    "jeonju":    ("전라북도", "전주시"),
    "cheongju":  ("충청북도", "청주시"),
}

CODE_MAP = {
    "mrgSttsCd":      {"55001": "기혼", "55002": "미혼", "55003": "제한없음"},
    "earnCndSeCd":    {"43001": "무관", "43002": "연소득", "43003": "기타"},
    "jobCd":          {
        "13001": "재직자", "13002": "자영업자", "13003": "미취업자",
        "13004": "프리랜서", "13005": "일용근로자", "13006": "(예비)창업자",
        "13007": "단기근로자", "13008": "영농종사자", "13009": "기타", "13010": "제한없음",
    },
    "schoolCd":       {
        "49001": "고졸 미만", "49002": "고교 재학", "49003": "고졸 예정",
        "49004": "고교 졸업", "49005": "대학 재학", "49006": "대졸 예정",
        "49007": "대학 졸업", "49008": "석·박사", "49009": "기타", "49010": "제한없음",
    },
    "plcyMajorCd":    {
        "11001": "인문계열", "11002": "사회계열", "11003": "상경계열",
        "11004": "이학계열", "11005": "공학계열", "11006": "예체능계열",
        "11007": "농산업계열", "11008": "기타", "11009": "제한없음",
    },
    "sbizCd":         {
        "14001": "중소기업", "14002": "여성", "14003": "기초생활수급자",
        "14004": "한부모가정", "14005": "장애인", "14006": "농업인",
        "14007": "군인", "14008": "지역인재", "14009": "기타", "14010": "제한없음",
    },
    "aplyPrdSeCd":    {"57001": "특정기간", "57002": "상시", "57003": "마감"},
    "bizPrdSeCd":     {"56001": "특정기간", "56002": "기타"},
    "plcyPvsnMthdCd": {
        "42001": "인프라 구축", "42002": "프로그램", "42003": "직접대출",
        "42004": "공공기관", "42005": "계약(위탁운영)", "42006": "보조금",
        "42007": "대출보증", "42008": "공적보험", "42009": "조세지출",
        "42010": "바우처", "42011": "정보제공", "42012": "경제적 규제", "42013": "기타",
    },
    "pvsnInstGroupCd": {"54001": "중앙부처", "54002": "지자체"},
    "plcyAprvSttsCd":  {"44001": "신청", "44002": "승인", "44003": "반려", "44004": "임시저장"},
}

THREE_MONTHS_AGO = datetime.now() - timedelta(days=90)


def decode_code(field: str, raw_code: str) -> str:
    """코드값 디코딩. 쉼표로 다중 코드도 처리 (예: '0049005,0049006' → '대학 재학, 대졸 예정')"""
    if not raw_code or not raw_code.strip():
        return ""
    codes = [c.strip() for c in raw_code.split(",")]
    results = []
    for code in codes:
        if not code:
            continue
        normalized = str(int(code)) if code.isdigit() else code
        decoded = CODE_MAP.get(field, {}).get(normalized, code)
        results.append(decoded)
    return ", ".join(results)

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

# 시군구 short name 매핑: "홍성군" → key "홍성", val ("충청남도", "홍성군")
# 3글자 이상 시군구만 (2글자 short name은 오탐 위험: "중구"→"중" 등)
SIGUNGU_SHORT_MAP = {
    sub[:-1]: (sido, sub)
    for sub, sido in SIGUNGU_TO_SIDO.items()
    if len(sub) >= 3
}

def extract_region_from_name(name: str) -> tuple:
    """공고명에서 (region, sub_region) 추출. 못 찾으면 ('', '') 반환"""
    if not name:
        return "", ""

    # 1. 괄호 패턴: (홍성군), (충남 홍성), (경기 수원시)
    bracket_tokens = re.findall(r"[(\[（]([^)\]）]{1,20})[)\]）]", name)
    for token in bracket_tokens:
        token = token.strip()
        for sub, sido in SIGUNGU_TO_SIDO.items():
            if sub in token:
                return sido, sub
        for short, full in REGION_MAP.items():
            if token.startswith(short) or token.startswith(full):
                remainder = token.replace(full, "").replace(short, "").strip()
                return full, remainder

    head = name[:30]

    # 2. 공고명 앞 30자 내 시군구 풀네임 탐색
    for sub, sido in SIGUNGU_TO_SIDO.items():
        if sub in head:
            return sido, sub

    # 3. 공고명 앞 30자 내 시군구 short name 탐색 (예: "홍성", "태안", "아산")
    for short_name, (sido, full_sub) in SIGUNGU_SHORT_MAP.items():
        if short_name in head:
            return sido, full_sub

    # 4. 광역시도 탐색
    for short, full in REGION_MAP.items():
        if short in name[:20] or full in name[:20]:
            return full, ""

    return "", ""

def region_from_zipcode(zip_cd: str) -> tuple:
    """zip_cd 앞 3자리로 (region, sub_region) 반환. 못 찾으면 ('', '')"""
    if not zip_cd or len(zip_cd) < 3:
        return "", ""
    prefix = zip_cd[:3]
    return ZIPCODE_PREFIX_MAP.get(prefix, ("", ""))

def region_from_url(url: str) -> tuple:
    """source_url 도메인에서 (region, sub_region) 추출. 못 찾으면 ('', '')"""
    if not url:
        return "", ""
    try:
        domain = url.split("//")[-1].split("/")[0].lower()
        for key, val in URL_DOMAIN_MAP.items():
            if key in domain:
                return val
    except:
        pass
    return "", ""

def is_target(lclsf, mclsf):
    return (
        any(t in lclsf for t in TARGET_LCLSF) and
        not any(e in mclsf for e in EXCLUDE_MCLSF)
    )

def is_recent(frstRegDt: str) -> bool:
    if not frstRegDt:
        return True
    try:
        return datetime.strptime(frstRegDt[:10], "%Y-%m-%d") >= THREE_MONTHS_AGO
    except:
        return True

def fetch_page(page):
    params = {
        "apiKeyNm": API_KEY,
        "pageNum":  page,
        "pageSize": 100,
        "pageType": "1",
        "rtnType":  "json",
    }
    res = requests.get(BASE_URL, params=params, timeout=15)
    res.encoding = "utf-8"
    data = res.json()
    if data.get("resultCode") != 200:
        raise Exception(f"API 오류: {data.get('resultMessage', '')}")
    return data["result"]


def crawl():
    all_results = []
    seen = set()
    page = 1

    print("🔍 전체 수집 시작 (3개월 이내 + 대분류 필터)...")

    while True:
        print(f"  p{page}...", end=" ", flush=True)

        try:
            result = fetch_page(page)
        except Exception as e:
            print(f"에러: {e}")
            break

        policies = result.get("youthPolicyList", [])
        total    = int(result.get("pagging", {}).get("totCount", 0))

        if not policies:
            print("완료")
            break

        count = 0
        for p in policies:
            plcy_no   = p.get("plcyNo", "")
            name      = p.get("plcyNm", "")
            lclsf     = p.get("lclsfNm", "")
            mclsf     = p.get("mclsfNm", "")
            content   = p.get("plcyExplnCn", "")
            sprt      = p.get("plcySprtCn", "")
            url       = p.get("aplyUrlAddr", "") or p.get("refUrlAddr1", "")
            frstRegDt = p.get("frstRegDt", "")
            hghk      = p.get("rgtrHghrkInstCdNm", "")
            up_inst   = p.get("rgtrUpInstCdNm", "")
            zip_cd    = p.get("zipCd", "")

            if not is_target(lclsf, mclsf):
                continue
            if not is_recent(frstRegDt):
                continue

            dedup_key = plcy_no or name
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            # ── 지역 결정 (4단계 우선순위) ──────────────────
            # 1순위: API 기관 필드
            region     = normalize_region(hghk)
            sub_region = extract_sub_region(up_inst, hghk)

            # 2순위: 공고명에서 추출
            if region == "전국" or not sub_region:
                name_region, name_sub = extract_region_from_name(name)
                if region == "전국" and name_region:
                    region = name_region
                if not sub_region and name_sub:
                    sub_region = name_sub

            # 3순위: zip_cd
            if region == "전국" or not sub_region:
                zip_region, zip_sub = region_from_zipcode(zip_cd)
                if region == "전국" and zip_region:
                    region = zip_region
                if not sub_region and zip_sub:
                    sub_region = zip_sub

            # 4순위: source_url 도메인
            if region == "전국" or not sub_region:
                url_region, url_sub = region_from_url(url)
                if region == "전국" and url_region:
                    region = url_region
                if not sub_region and url_sub:
                    sub_region = url_sub

            # 전부 실패하면 원래값 유지 (전국 / 빈값)
            # ────────────────────────────────────────────────

            all_results.append({
                "plcy_no":          plcy_no,
                "name":             name,
                "lclsf":            lclsf.strip(),
                "category":         mclsf.strip(),
                "keyword":          p.get("plcyKywdNm", ""),
                "region":           region,
                "sub_region":       sub_region,
                "source":           "온통청년",
                "source_url":       url or "https://www.youthcenter.go.kr",
                "ref_url2":         p.get("refUrlAddr2", ""),
                "raw_text":         f"{content} {sprt}".strip(),
                "amount":           "",
                "deadline":         p.get("aplyYmd", ""),
                "registered_at":    frstRegDt[:10] if frstRegDt else "",
                "last_modified_at": p.get("lastMdfcnDt", "")[:10] if p.get("lastMdfcnDt", "").strip() else "",
                "collected_at":     datetime.now().strftime("%Y-%m-%d"),
                "aply_prd_type":    decode_code("aplyPrdSeCd",    p.get("aplyPrdSeCd", "")),
                "biz_prd_type":     decode_code("bizPrdSeCd",     p.get("bizPrdSeCd", "")),
                "biz_start_ymd":    p.get("bizPrdBgngYmd", "").strip(),
                "biz_end_ymd":      p.get("bizPrdEndYmd", "").strip(),
                "biz_prd_etc":      p.get("bizPrdEtcCn", "").strip(),
                "age_min":          p.get("sprtTrgtMinAge", ""),
                "age_max":          p.get("sprtTrgtMaxAge", ""),
                "age_limit_yn":     p.get("sprtTrgtAgeLmtYn", ""),
                "earn_cnd":         decode_code("earnCndSeCd",    p.get("earnCndSeCd", "")),
                "earn_min_amt":     p.get("earnMinAmt", ""),
                "earn_max_amt":     p.get("earnMaxAmt", ""),
                "earn_etc":         p.get("earnEtcCn", ""),
                "mrg_stts":         decode_code("mrgSttsCd",      p.get("mrgSttsCd", "")),
                "job":              decode_code("jobCd",           p.get("jobCd", "")),
                "school":           decode_code("schoolCd",        p.get("schoolCd", "")),
                "major":            decode_code("plcyMajorCd",     p.get("plcyMajorCd", "")),
                "special_target":   decode_code("sbizCd",          p.get("sbizCd", "")),
                "pvmthd":           decode_code("plcyPvsnMthdCd",  p.get("plcyPvsnMthdCd", "")),
                "pvmthd_group":     decode_code("pvsnInstGroupCd", p.get("pvsnInstGroupCd", "")),
                "sprt_scl_cnt":     p.get("sprtSclCnt", ""),
                "sprt_scl_lmt_yn":  p.get("sprtSclLmtYn", ""),
                "sprt_arvl_seq_yn": p.get("sprtArvlSeqYn", ""),
                "add_qlfc":         p.get("addAplyQlfcCndCn", ""),
                "exclude_target":   p.get("ptcpPrpTrgtCn", ""),
                "apply_method":     p.get("plcyAplyMthdCn", ""),
                "select_method":    p.get("srngMthdCn", ""),
                "submit_docs":      p.get("sbmsnDcmntCn", ""),
                "etc_matter":       p.get("etcMttrCn", ""),
                "sprvsn_inst_nm":   p.get("sprvsnInstCdNm", ""),
                "oper_inst_nm":     p.get("operInstCdNm", ""),
                "rgtr_inst_nm":     p.get("rgtrInstCdNm", ""),
                "zip_cd":           zip_cd,
                "inq_cnt":          p.get("inqCnt", ""),
                "aprvl_stts":       decode_code("plcyAprvSttsCd", p.get("plcyAprvSttsCd", "")),
            })
            count += 1

        print(f"{count}건 추가 (누적 {len(all_results)}건 / 전체 {total}건)")

        if total == 0 or page * 100 >= total or not policies:
            break
        page += 1
        time.sleep(0.5)

    os.makedirs("data/raw", exist_ok=True)

    json_path = "data/raw/승현_온통청년.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    fieldnames = [
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

    csv_path = "data/raw/승현_온통청년.csv"
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_results)

    print(f"\n✅ 완료! 총 {len(all_results)}건")
    print(f"   → {json_path}")
    print(f"   → {csv_path}")


if __name__ == "__main__":
    crawl()
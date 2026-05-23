import { Ionicons } from '@expo/vector-icons';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { ActivityIndicator, Linking, ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { API_URL } from '../constants/api';

interface PolicyFull {
  id: string;
  name: string;
  category: string;
  benefit_type?: string;
  region?: string;
  sub_region?: string | null;
  source?: string;
  source_url?: string;
  raw_text?: string;
  amount?: string | null;
  deadline?: string | null;
  registered_at?: string | null;
  collected_at?: string | null;
  age_min?: string;
  age_max?: string;
  income_max_pct?: string;
  housing?: string;
  employment?: string;
  submit_docs?: string;
  pvmthd?: string;
  exclude_target?: string;
  add_qlfc?: string;
  select_method?: string;
}

interface DocumentLink {
  doc_name: string;
  source: string;
  url: string | null;
  search_hint?: string;
  fee?: string;
  ai_verified?: boolean;
}

type SectionKey = 'content' | 'target' | 'method' | 'period' | 'documents' | 'contact';

const SECTION_HEADERS: { key: SectionKey; pattern: string }[] = [
  // 지원 내용
  { key: 'content', pattern: '지원\\s*내용' },
  { key: 'content', pattern: '지원\\s*범위' },
  { key: 'content', pattern: '지원\\s*혜택' },
  { key: 'content', pattern: '주요\\s*내용' },
  { key: 'content', pattern: '사업\\s*내용' },
  { key: 'content', pattern: '혜택\\s*내용' },
  // 지원 대상
  { key: 'target', pattern: '지원\\s*대상' },
  { key: 'target', pattern: '신청\\s*대상' },
  { key: 'target', pattern: '신청\\s*자격' },
  { key: 'target', pattern: '지원\\s*자격' },
  { key: 'target', pattern: '대상\\s*요건' },
  { key: 'target', pattern: '참가\\s*대상' },
  // 신청 방법
  { key: 'method', pattern: '신청\\s*방법' },
  { key: 'method', pattern: '지원\\s*방법' },
  { key: 'method', pattern: '신청\\s*절차' },
  { key: 'method', pattern: '접수\\s*방법' },
  // 모집 일정 / 신청 기간
  { key: 'period', pattern: '신청\\s*기간' },
  { key: 'period', pattern: '모집\\s*기간' },
  { key: 'period', pattern: '접수\\s*기간' },
  { key: 'period', pattern: '사업\\s*기간' },
  { key: 'period', pattern: '추진\\s*일정' },
  { key: 'period', pattern: '운영\\s*기간' },
  // 필요 서류
  { key: 'documents', pattern: '제출\\s*서류' },
  { key: 'documents', pattern: '구비\\s*서류' },
  { key: 'documents', pattern: '필요\\s*서류' },
  { key: 'documents', pattern: '신청\\s*서류' },
  { key: 'documents', pattern: '첨부\\s*서류' },
  // 문의
  { key: 'contact', pattern: '문의\\s*처' },
  { key: 'contact', pattern: '문의' },
  { key: 'contact', pattern: '연락처' },
];

const SECTION_TITLE: Record<SectionKey, string> = {
  content: '지원 내용',
  target: '지원 대상',
  method: '신청 방법',
  period: '모집 일정',
  documents: '필요 서류',
  contact: '문의처',
};

const parseSections = (rawText?: string): Record<SectionKey, string> => {
  const result: Record<SectionKey, string> = {
    content: '',
    target: '',
    method: '',
    period: '',
    documents: '',
    contact: '',
  };
  if (!rawText) return result;

  type Hit = { key: SectionKey; headerStart: number; contentStart: number };
  const hits: Hit[] = [];

  for (const { key, pattern } of SECTION_HEADERS) {
    const re = new RegExp(`(?:^|[\\s○■▶◆◇▣◎·▣\\-])(${pattern})\\s*[:：]`, 'g');
    let m: RegExpExecArray | null;
    while ((m = re.exec(rawText)) !== null) {
      const headerStart = m.index + m[0].indexOf(m[1]);
      const contentStart = m.index + m[0].length;
      hits.push({ key, headerStart, contentStart });
    }
  }

  hits.sort((a, b) => a.headerStart - b.headerStart);

  // 같은 위치에 여러 패턴 매칭 시 첫 번째만
  const dedup: Hit[] = [];
  for (const h of hits) {
    if (dedup.length === 0 || h.headerStart > dedup[dedup.length - 1].headerStart + 2) {
      dedup.push(h);
    }
  }

  for (let i = 0; i < dedup.length; i++) {
    const cur = dedup[i];
    const nxt = dedup[i + 1];
    const start = cur.contentStart;
    const end = nxt ? nxt.headerStart : rawText.length;
    let chunk = rawText.slice(start, end).trim();
    chunk = chunk.replace(/관심 정책정보 목록.*$/s, '').replace(/유관기관 사이트.*$/s, '').replace(/본 정보는 제공기관의[^.]*\./g, '').trim();
    if (chunk && !result[cur.key]) {
      result[cur.key] = chunk;
    } else if (chunk && result[cur.key]) {
      result[cur.key] += '\n\n' + chunk;
    }
  }

  return result;
};

const cleanRawText = (text?: string) => {
  if (!text) return '';
  return text.replace(/관심 정책정보 목록.*$/s, '').replace(/유관기관 사이트.*$/s, '').replace(/본 정보는 제공기관의[^.]*\./g, '').trim();
};

const parseReason = (reason: string) => {
  let status: 'pass' | 'fail' | 'warn' = 'pass';
  if (reason.includes('❌')) status = 'fail';
  else if (reason.includes('⚠️')) status = 'warn';
  const cleaned = reason.replace(/[✅❌⚠️]/g, '').trim();
  const colonIdx = cleaned.indexOf(' ');
  const label = colonIdx > 0 ? cleaned.slice(0, colonIdx) : cleaned;
  const detail = colonIdx > 0 ? cleaned.slice(colonIdx + 1).trim() : '';
  return { status, label, detail };
};

const parseDeadlineDate = (deadline: string) => {
  const all: { y: string; m: string; d: string }[] = [];
  const dashedRe = /(\d{4})-(\d{1,2})-(\d{1,2})/g;
  const compactRe = /(\d{4})(\d{2})(\d{2})/g;
  let mm: RegExpExecArray | null;
  while ((mm = dashedRe.exec(deadline)) !== null) {
    all.push({ y: mm[1], m: mm[2], d: mm[3] });
  }
  if (all.length === 0) {
    while ((mm = compactRe.exec(deadline)) !== null) {
      all.push({ y: mm[1], m: mm[2], d: mm[3] });
    }
  }
  return all.length > 0 ? all[all.length - 1] : null;
};

const formatDeadline = (deadline?: string | null) => {
  if (!deadline) return null;
  const parts = parseDeadlineDate(deadline);
  if (!parts) return { text: deadline, urgent: false, expired: false };
  const pretty = `${parts.y}-${parts.m.padStart(2, '0')}-${parts.d.padStart(2, '0')}`;
  const target = new Date(parseInt(parts.y), parseInt(parts.m) - 1, parseInt(parts.d));
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const diff = Math.ceil((target.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
  if (diff < 0) return { text: `마감됨 (${pretty})`, urgent: false, expired: true };
  if (diff === 0) return { text: `오늘 마감 (${pretty})`, urgent: true, expired: false };
  if (diff <= 30) return { text: `D-${diff} (${pretty})`, urgent: true, expired: false };
  return { text: pretty, urgent: false, expired: false };
};

const KOREAN_REGIONS = new Set([
  '서울특별시', '부산광역시', '대구광역시', '인천광역시', '광주광역시',
  '대전광역시', '울산광역시', '세종특별자치시',
  '경기도', '강원도', '강원특별자치도', '충청북도', '충청남도',
  '전라북도', '전북특별자치도', '전라남도', '경상북도', '경상남도',
  '제주특별자치도',
]);

const formatRegion = (region?: string, subRegion?: string | null) => {
  const r = region?.trim();
  const sub = subRegion?.trim();
  if (r && KOREAN_REGIONS.has(r)) {
    return sub ? `${r} ${sub}` : r;
  }
  return '전국';
};

// ──────────────────────────────────────────
// 서류 파싱 + 발급처 매칭
// ──────────────────────────────────────────
interface ResolvedDoc {
  name: string;
  source: string;
  url: string | null;
  fee?: string;
  hint?: string;
  origin?: 'ai' | 'pattern' | 'none';
}

const KNOWN_DOC_SOURCES: { pattern: RegExp; source: string; url: string | null; fee?: string }[] = [
  { pattern: /주민등록(등본|초본|표)|등초본/, source: '정부24', url: 'https://www.gov.kr', fee: '무료' },
  { pattern: /가족관계증명|혼인관계증명|기본증명|입양관계증명|친양자/, source: '전자가족관계등록시스템', url: 'https://efamily.scourt.go.kr', fee: '무료' },
  { pattern: /소득금액증명|근로소득.*원천징수|소득세|사업자등록증/, source: '홈택스', url: 'https://www.hometax.go.kr', fee: '무료' },
  { pattern: /건강보험(자격|증|료)|4대\s*보험|보험료\s*납부/, source: '국민건강보험공단', url: 'https://www.nhis.or.kr', fee: '무료' },
  { pattern: /국민연금/, source: '국민연금공단', url: 'https://www.nps.or.kr', fee: '무료' },
  { pattern: /고용보험.*피보험|이직확인서|실업급여\s*수급/, source: '고용보험', url: 'https://www.ei.go.kr', fee: '무료' },
  { pattern: /구직(등록|신청)|워크넷|구직활동/, source: '워크넷', url: 'https://www.work.go.kr', fee: '무료' },
  { pattern: /통장사본|입출(통장|금)|계좌사본|예금주/, source: '본인 보관 · 은행 앱', url: null, hint: '거래 은행 앱에서 계좌 사본 발급 가능' },
  { pattern: /신분증|주민등록증|운전면허증|여권/, source: '본인 보관', url: null },
  { pattern: /(임대차|월세|전세)계약(서)?|월세\s*이체|임차/, source: '본인 보관 · 계약 시 받음', url: null, hint: '집주인/공인중개사에게 받은 원본 또는 사본' },
  { pattern: /재학증명|졸업증명|성적증명|수료증|학적|재적/, source: '학교 행정실 또는 학교 포털', url: null, hint: '대학정보공시(인터넷증명발급) 가능 학교 多' },
  { pattern: /(신청서|서약서|동의서|확약서|개인정보\s*수집)/, source: '신청 기관 양식', url: null, hint: '공고문 첨부파일 또는 신청 페이지에서 다운로드' },
  { pattern: /지방세\s*납세|세목별\s*과세/, source: '위택스', url: 'https://www.wetax.go.kr', fee: '무료' },
  { pattern: /등기부등본|등기사항/, source: '인터넷등기소', url: 'https://www.iros.go.kr', fee: '유료 (700~1,000원)' },
];

const parseDocItems = (submitDocs?: string): string[] => {
  if (!submitDocs) return [];
  const cleaned = submitDocs
    .replace(/☞[^,\n]*/g, '')
    .replace(/붙임\s*파일[^,\n]*/g, '')
    .replace(/자세한\s*내용은[^,\n]*/g, '')
    .replace(/[•○●○●·]/g, '')
    .replace(/\([^)]*\)/g, '')
    .replace(/\s+/g, ' ')
    .trim();
  const items = cleaned
    .split(/[,，、]/)
    .map((s) => s.trim())
    .filter((s) => s.length >= 2 && s.length <= 100 && !/^[\d.\-:]+$/.test(s));
  return Array.from(new Set(items));
};

const findAiMatch = (docName: string, aiDocs: DocumentLink[]): DocumentLink | undefined => {
  const norm = (s: string) => s.replace(/\s+/g, '');
  const nd = norm(docName);
  return aiDocs.find((d) => {
    const na = norm(d.doc_name);
    return na === nd || nd.includes(na) || na.includes(nd);
  });
};

const resolveDoc = (docName: string, aiDocs: DocumentLink[]): ResolvedDoc => {
  const ai = findAiMatch(docName, aiDocs);
  if (ai) {
    return {
      name: docName,
      source: ai.source,
      url: ai.url,
      fee: ai.fee,
      hint: ai.search_hint,
      origin: 'ai',
    };
  }
  for (const k of KNOWN_DOC_SOURCES) {
    if (k.pattern.test(docName)) {
      return {
        name: docName,
        source: k.source,
        url: k.url,
        fee: k.fee,
        hint: (k as any).hint,
        origin: 'pattern',
      };
    }
  }
  return {
    name: docName,
    source: '신청 기관 확인',
    url: null,
    hint: '공고문 안내 또는 담당자 문의',
    origin: 'none',
  };
};

const formatAge = (min?: string, max?: string) => {
  const hasMin = min && min !== '';
  const hasMax = max && max !== '';
  if (hasMin && hasMax) return `만 ${min}~${max}세`;
  if (hasMin) return `만 ${min}세 이상`;
  if (hasMax) return `만 ${max}세 이하`;
  return null;
};

export default function PolicyDetailScreen() {
  const router = useRouter();
  const { policy_id, rank, fit_score, reasons, document_links } = useLocalSearchParams<{
    policy_id?: string;
    rank?: string;
    fit_score?: string;
    reasons?: string;
    document_links?: string;
  }>();

  const [policy, setPolicy] = useState<PolicyFull | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchPolicy = async () => {
      if (!policy_id) {
        setError('정책 ID가 전달되지 않았습니다.');
        setLoading(false);
        return;
      }
      try {
        const response = await fetch(`${API_URL}/policy/${policy_id}`);
        if (!response.ok) {
          setError('정책 정보를 불러올 수 없습니다.');
          setLoading(false);
          return;
        }
        const data = await response.json();
        setPolicy(data);
      } catch (e) {
        setError('네트워크 오류가 발생했습니다.');
      } finally {
        setLoading(false);
      }
    };
    fetchPolicy();
  }, [policy_id]);

  const reasonItems: { status: 'pass' | 'fail' | 'warn'; label: string; detail: string }[] = (() => {
    if (!reasons) return [];
    try {
      const arr: string[] = JSON.parse(reasons);
      return arr.map(parseReason);
    } catch {
      return [];
    }
  })();

  const docLinks: DocumentLink[] = (() => {
    if (!document_links) return [];
    try {
      return JSON.parse(document_links);
    } catch {
      return [];
    }
  })();

  if (loading) {
    return (
      <SafeAreaView style={styles.wrap} edges={['top']}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
            <Ionicons name="chevron-back" size={26} color="#111" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>정책 상세</Text>
          <View style={{ width: 26 }} />
        </View>
        <ActivityIndicator size="large" color="#00C49A" style={{ flex: 1 }} />
      </SafeAreaView>
    );
  }

  if (error || !policy) {
    return (
      <SafeAreaView style={styles.wrap} edges={['top']}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
            <Ionicons name="chevron-back" size={26} color="#111" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>정책 상세</Text>
          <View style={{ width: 26 }} />
        </View>
        <View style={styles.emptyBox}>
          <Text style={styles.emptyText}>{error || '정책 정보를 불러올 수 없습니다.'}</Text>
        </View>
      </SafeAreaView>
    );
  }

  const handleOpenSource = () => {
    if (policy.source_url) Linking.openURL(policy.source_url);
  };

  const sections = parseSections(policy.raw_text);
  const deadline = formatDeadline(policy.deadline);
  const ageRange = formatAge(policy.age_min, policy.age_max);
  const regionLabel = formatRegion(policy.region, policy.sub_region);

  // 구조화된 지원 대상 정보 (clean_final.json 칼럼)
  const targetItems: { label: string; value: string }[] = [];
  targetItems.push({ label: '지역', value: regionLabel });
  if (ageRange) targetItems.push({ label: '연령', value: ageRange });
  if (policy.income_max_pct) targetItems.push({ label: '소득기준', value: `중위소득 ${policy.income_max_pct}% 이하` });
  if (policy.employment) targetItems.push({ label: '취업상태', value: policy.employment });
  if (policy.housing) targetItems.push({ label: '주거형태', value: policy.housing });

  const hasAnySection =
    sections.content || sections.target || sections.method || sections.period || sections.documents || sections.contact;

  return (
    <SafeAreaView style={styles.wrap} edges={['top']}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
          <Ionicons name="chevron-back" size={26} color="#111" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>정책 상세</Text>
        <View style={{ width: 26 }} />
      </View>

      <ScrollView style={styles.container} contentContainerStyle={{ paddingBottom: 40 }} showsVerticalScrollIndicator={false}>
        <View style={styles.titleSection}>
          {rank ? (
            <View style={styles.rankBadge}>
              <Text style={styles.rankText}>{rank}순위</Text>
            </View>
          ) : null}
          <Text style={styles.policyTitle}>{policy.name}</Text>
          {policy.source ? <Text style={styles.policySource}>{policy.source}</Text> : null}
        </View>

        <View style={styles.tagRow}>
          <View style={styles.tagGreen}>
            <Text style={styles.tagGreenText}>{policy.category}</Text>
          </View>
          {(() => {
            const r = policy.region?.trim();
            const sub = policy.sub_region?.trim();
            const isValidRegion = r && KOREAN_REGIONS.has(r);
            return (
              <>
                <View style={styles.tagGray}>
                  <Text style={styles.tagGrayText}>{isValidRegion ? r : '전국'}</Text>
                </View>
                {isValidRegion && sub ? (
                  <View style={styles.tagGray}>
                    <Text style={styles.tagGrayText}>{sub}</Text>
                  </View>
                ) : null}
              </>
            );
          })()}
          {fit_score ? (
            <View style={styles.tagBlue}>
              <Text style={styles.tagBlueText}>적합도 {fit_score}%</Text>
            </View>
          ) : null}
        </View>

        <View style={styles.amountCard}>
          <Text style={styles.amountLabel}>지원 금액</Text>
          <Text style={styles.amountValue}>{policy.amount || '금액 정보 없음 (원문 확인)'}</Text>
          {policy.pvmthd && policy.pvmthd !== '기타' ? (
            <View style={styles.pvmthdChip}>
              <Ionicons name="cash-outline" size={13} color="#3367D6" />
              <Text style={styles.pvmthdText}>지원 방식 · {policy.pvmthd}</Text>
            </View>
          ) : null}
        </View>

        {/* 모집 일정 */}
        {(deadline || policy.registered_at || sections.period) ? (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>모집 일정</Text>
            <View style={styles.infoCard}>
              {policy.registered_at ? (
                <View style={styles.infoRow}>
                  <Text style={styles.infoRowLabel}>등록일</Text>
                  <Text style={styles.infoRowValue}>{policy.registered_at}</Text>
                </View>
              ) : null}
              {deadline ? (
                <View
                  style={[
                    styles.infoRow,
                    !sections.period && { borderBottomWidth: 0 },
                  ]}
                >
                  <Text style={styles.infoRowLabel}>마감일</Text>
                  <Text
                    style={[
                      styles.infoRowValue,
                      deadline.urgent && { color: '#FF8C00' },
                      deadline.expired && { color: '#999' },
                    ]}
                  >
                    {deadline.text}
                  </Text>
                </View>
              ) : null}
              {sections.period ? (
                <View style={styles.infoBlock}>
                  <Text style={styles.infoBlockLabel}>신청 기간</Text>
                  <Text style={styles.infoBlockValue}>{sections.period}</Text>
                </View>
              ) : null}
            </View>
          </View>
        ) : null}

        {/* 지원 대상 */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>지원 대상</Text>
          <View style={styles.infoCard}>
            {targetItems.map((it, i) => (
              <View
                key={i}
                style={[
                  styles.infoRow,
                  i === targetItems.length - 1 && !sections.target && { borderBottomWidth: 0 },
                ]}
              >
                <Text style={styles.infoRowLabel}>{it.label}</Text>
                <Text style={styles.infoRowValue}>{it.value}</Text>
              </View>
            ))}
            {sections.target ? (
              <View style={styles.infoBlock}>
                <Text style={styles.infoBlockLabel}>상세 자격</Text>
                <Text style={styles.infoBlockValue}>{sections.target}</Text>
              </View>
            ) : null}
            {policy.add_qlfc ? (
              <View style={styles.infoBlock}>
                <Text style={styles.infoBlockLabel}>추가 자격 요건</Text>
                <Text style={styles.infoBlockValue}>{policy.add_qlfc}</Text>
              </View>
            ) : null}
          </View>

          {policy.exclude_target ? (
            <View style={styles.warnBox}>
              <View style={styles.warnHeader}>
                <Ionicons name="warning" size={16} color="#D85B4A" />
                <Text style={styles.warnTitle}>제외 대상 · 신청 전 확인</Text>
              </View>
              <Text style={styles.warnText}>{policy.exclude_target}</Text>
            </View>
          ) : null}
        </View>

        {/* 정책 내용 — 지원 대상 바로 밑. sections.content 우선, 없으면 raw_text fallback */}
        {(sections.content || policy.raw_text) ? (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>정책 내용</Text>
            <View style={styles.descBox}>
              <Text style={styles.descText}>
                {sections.content || cleanRawText(policy.raw_text)}
              </Text>
            </View>
          </View>
        ) : null}

        {/* 신청 방법 */}
        {sections.method ? (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>{SECTION_TITLE.method}</Text>
            <View style={styles.descBox}>
              <Text style={styles.descText}>{sections.method}</Text>
            </View>
          </View>
        ) : null}

        {/* 선정 방법 */}
        {policy.select_method ? (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>선정 방법</Text>
            <View style={styles.descBox}>
              <Text style={styles.descText}>{policy.select_method}</Text>
            </View>
          </View>
        ) : null}

        {/* 필요 서류 */}
        {(() => {
          const rawDocsText = sections.documents || policy.submit_docs || '';
          const parsedNames = parseDocItems(rawDocsText);
          const docs: ResolvedDoc[] = parsedNames.length > 0
            ? parsedNames.map((n) => resolveDoc(n, docLinks))
            : docLinks.map((d) => ({
                name: d.doc_name,
                source: d.source,
                url: d.url,
                fee: d.fee,
                hint: d.search_hint,
              }));
          if (docs.length === 0 && !rawDocsText) return null;
          return (
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>{SECTION_TITLE.documents}</Text>
              {docs.length > 0 ? (
                <View style={styles.docsCard}>
                  {docs.map((doc, idx) => (
                    <View
                      key={idx}
                      style={[styles.docItemRow, idx === docs.length - 1 && { borderBottomWidth: 0 }]}
                    >
                      <View style={styles.docItemTextWrap}>
                        <View style={styles.docItemNameRow}>
                          <Text style={styles.docItemName}>{doc.name}</Text>
                          {doc.origin === 'ai' && doc.url ? (
                            <View style={styles.aiBadge}>
                              <Ionicons name="sparkles" size={10} color="#7B3FE4" />
                              <Text style={styles.aiBadgeText}>AI 추천</Text>
                            </View>
                          ) : null}
                        </View>
                        <Text style={styles.docItemSource}>
                          {doc.source}
                          {doc.fee ? ` · ${doc.fee}` : ''}
                        </Text>
                        {doc.hint ? <Text style={styles.docItemHint}>{doc.hint}</Text> : null}
                      </View>
                      {doc.url ? (
                        <TouchableOpacity
                          style={styles.docIssueBtn}
                          onPress={() => Linking.openURL(doc.url!)}
                          activeOpacity={0.7}
                        >
                          <Ionicons name="open-outline" size={13} color="#fff" />
                          <Text style={styles.docIssueBtnText}>발급</Text>
                        </TouchableOpacity>
                      ) : (
                        <View style={styles.docSelfBadge}>
                          <Text style={styles.docSelfBadgeText}>
                            {doc.source.includes('본인') ? '본인 준비' : '직접 발급'}
                          </Text>
                        </View>
                      )}
                    </View>
                  ))}
                </View>
              ) : rawDocsText ? (
                <View style={styles.descBox}>
                  <Text style={styles.docsText}>{rawDocsText}</Text>
                </View>
              ) : null}
            </View>
          );
        })()}

        {/* 문의처 */}
        {sections.contact ? (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>{SECTION_TITLE.contact}</Text>
            <View style={styles.descBox}>
              <Text style={styles.descText}>{sections.contact}</Text>
            </View>
          </View>
        ) : null}

        {/* 자격 매칭 */}
        {reasonItems.length > 0 ? (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>내 정보 매칭 결과</Text>
            <View style={styles.reasonList}>
              {reasonItems.map((item, idx) => (
                <View
                  key={idx}
                  style={[styles.reasonRow, idx === reasonItems.length - 1 && { borderBottomWidth: 0 }]}
                >
                  <View
                    style={[
                      styles.reasonIcon,
                      item.status === 'pass' && styles.reasonIconPass,
                      item.status === 'fail' && styles.reasonIconFail,
                      item.status === 'warn' && styles.reasonIconWarn,
                    ]}
                  >
                    <Ionicons
                      name={
                        item.status === 'pass'
                          ? 'checkmark'
                          : item.status === 'fail'
                          ? 'close'
                          : 'alert'
                      }
                      size={14}
                      color="#fff"
                    />
                  </View>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.reasonLabel}>{item.label}</Text>
                    {item.detail ? <Text style={styles.reasonDetail}>{item.detail}</Text> : null}
                  </View>
                </View>
              ))}
            </View>
          </View>
        ) : null}

        {policy.source_url ? (
          <TouchableOpacity style={styles.sourceBtn} onPress={handleOpenSource}>
            <Ionicons name="open-outline" size={18} color="#fff" style={{ marginRight: 8 }} />
            <Text style={styles.sourceBtnText}>원문 보기 / 신청하기</Text>
          </TouchableOpacity>
        ) : null}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: '#F7FDFB' },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 12,
    paddingVertical: 10,
    backgroundColor: '#F7FDFB',
  },
  backBtn: { padding: 4 },
  headerTitle: { fontSize: 18, fontWeight: '700', color: '#111' },
  container: { flex: 1, paddingHorizontal: 20 },
  emptyBox: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  emptyText: { color: '#888', fontSize: 15 },
  titleSection: { marginTop: 8, marginBottom: 18 },
  rankBadge: {
    alignSelf: 'flex-start',
    backgroundColor: '#00C49A',
    paddingHorizontal: 12,
    paddingVertical: 5,
    borderRadius: 20,
    marginBottom: 12,
  },
  rankText: { color: '#fff', fontWeight: '800', fontSize: 13 },
  policyTitle: { fontSize: 24, fontWeight: '800', color: '#111', lineHeight: 32 },
  policySource: { fontSize: 14, color: '#888', marginTop: 6 },
  tagRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 18 },
  tagGreen: { backgroundColor: '#e6f9f4', paddingHorizontal: 12, paddingVertical: 5, borderRadius: 20 },
  tagGreenText: { color: '#00C49A', fontSize: 13, fontWeight: '700' },
  tagBlue: { backgroundColor: '#E8F0FE', paddingHorizontal: 12, paddingVertical: 5, borderRadius: 20 },
  tagBlueText: { color: '#3367D6', fontSize: 13, fontWeight: '700' },
  tagGray: { backgroundColor: '#F0F2F1', paddingHorizontal: 12, paddingVertical: 5, borderRadius: 20 },
  tagGrayText: { color: '#666', fontSize: 13, fontWeight: '600' },
  amountCard: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 18,
    marginBottom: 20,
    shadowColor: '#000',
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  amountLabel: { fontSize: 14, color: '#888', marginBottom: 6, fontWeight: '600' },
  amountValue: { fontSize: 24, fontWeight: '800', color: '#00C49A' },
  pvmthdChip: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
    backgroundColor: '#E8F0FE',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 16,
    marginTop: 12,
    gap: 5,
  },
  pvmthdText: { color: '#3367D6', fontSize: 13, fontWeight: '700' },
  warnBox: {
    marginTop: 12,
    backgroundColor: '#FFF4F1',
    borderRadius: 12,
    padding: 14,
    borderWidth: 1,
    borderColor: '#FAD4CC',
  },
  warnHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 8, gap: 6 },
  warnTitle: { fontSize: 14, fontWeight: '800', color: '#D85B4A' },
  warnText: { fontSize: 14, color: '#5C2F27', lineHeight: 22 },
  section: { marginBottom: 22 },
  sectionTitle: { fontSize: 17, fontWeight: '800', color: '#111', marginBottom: 10 },
  infoCard: {
    backgroundColor: '#fff',
    borderRadius: 16,
    paddingHorizontal: 16,
    paddingVertical: 4,
    shadowColor: '#000',
    shadowOpacity: 0.04,
    shadowRadius: 6,
    elevation: 1,
  },
  infoRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    paddingVertical: 13,
    borderBottomWidth: 1,
    borderBottomColor: '#F2F4F3',
  },
  infoRowLabel: { width: 84, fontSize: 14, color: '#888', fontWeight: '600' },
  infoRowValue: { flex: 1, fontSize: 15, color: '#222', fontWeight: '600', lineHeight: 22 },
  infoBlock: { paddingVertical: 13, borderTopWidth: 1, borderTopColor: '#F2F4F3' },
  infoBlockLabel: { fontSize: 13, color: '#888', fontWeight: '600', marginBottom: 6 },
  infoBlockValue: { fontSize: 14, color: '#333', lineHeight: 22 },
  descBox: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 16,
    shadowColor: '#000',
    shadowOpacity: 0.04,
    shadowRadius: 6,
    elevation: 1,
  },
  descText: { fontSize: 15, color: '#333', lineHeight: 24 },
  expandBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#fff',
    borderRadius: 12,
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderWidth: 1,
    borderColor: '#E8EAEA',
  },
  expandBtnText: { color: '#666', fontSize: 14, fontWeight: '600', marginRight: 4 },
  reasonList: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 16,
    shadowColor: '#000',
    shadowOpacity: 0.04,
    shadowRadius: 6,
    elevation: 1,
  },
  reasonRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#F2F4F3',
  },
  reasonIcon: {
    width: 24,
    height: 24,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
    marginTop: 1,
  },
  reasonIconPass: { backgroundColor: '#00C49A' },
  reasonIconFail: { backgroundColor: '#E76F51' },
  reasonIconWarn: { backgroundColor: '#F4A261' },
  reasonLabel: { fontSize: 15, fontWeight: '700', color: '#222' },
  reasonDetail: { fontSize: 13, color: '#777', marginTop: 3, lineHeight: 19 },
  sourceBtn: {
    backgroundColor: '#00C49A',
    paddingVertical: 16,
    borderRadius: 30,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 10,
  },
  sourceBtnText: { color: '#fff', fontSize: 17, fontWeight: '700' },
  docLinksBox: {
    marginTop: 12,
    backgroundColor: '#F0FBF7',
    borderRadius: 12,
    padding: 14,
    borderWidth: 1,
    borderColor: '#C8EDE3',
  },
  docLinksHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 10,
  },
  docLinksTitle: { fontSize: 14, fontWeight: '700', color: '#00A582', marginLeft: 5 },
  docLinkRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#C8EDE3',
  },
  docLinkName: { fontSize: 15, fontWeight: '700', color: '#222', marginBottom: 3 },
  docLinkSource: { fontSize: 13, color: '#666' },
  docLinkHint: { fontSize: 12, color: '#999', marginTop: 3, lineHeight: 18 },
  docLinkBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#E6F9F4',
    paddingHorizontal: 12,
    paddingVertical: 7,
    borderRadius: 8,
    marginLeft: 10,
    gap: 3,
  },
  docLinkBtnText: { color: '#00C49A', fontSize: 13, fontWeight: '700' },
  docsText: { fontSize: 15, color: '#333', lineHeight: 24 },
  docsCard: {
    backgroundColor: '#fff',
    borderRadius: 16,
    paddingHorizontal: 16,
    paddingVertical: 4,
    shadowColor: '#000',
    shadowOpacity: 0.04,
    shadowRadius: 6,
    elevation: 1,
  },
  docItemRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: '#F2F4F3',
  },
  docItemTextWrap: { flex: 1, marginRight: 10 },
  docItemNameRow: { flexDirection: 'row', alignItems: 'center', flexWrap: 'wrap', marginBottom: 3, gap: 6 },
  docItemName: { fontSize: 15, fontWeight: '700', color: '#222', lineHeight: 21 },
  aiBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#F2EAFF',
    paddingHorizontal: 7,
    paddingVertical: 3,
    borderRadius: 8,
    gap: 3,
  },
  aiBadgeText: { color: '#7B3FE4', fontSize: 10, fontWeight: '800' },
  docItemSource: { fontSize: 13, color: '#666', lineHeight: 18 },
  docItemHint: { fontSize: 12, color: '#999', marginTop: 3, lineHeight: 17 },
  docIssueBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#00C49A',
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 10,
    gap: 4,
  },
  docIssueBtnText: { color: '#fff', fontSize: 13, fontWeight: '700' },
  docSelfBadge: {
    backgroundColor: '#F0F2F1',
    paddingHorizontal: 10,
    paddingVertical: 7,
    borderRadius: 10,
  },
  docSelfBadgeText: { color: '#666', fontSize: 12, fontWeight: '700' },
});

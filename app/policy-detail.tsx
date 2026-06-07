import { Ionicons } from '@expo/vector-icons';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { ActivityIndicator, Linking, Modal, ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
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
  { key: 'content', pattern: '지원\\s*내용' },
  { key: 'content', pattern: '지원\\s*범위' },
  { key: 'content', pattern: '지원\\s*혜택' },
  { key: 'content', pattern: '주요\\s*내용' },
  { key: 'content', pattern: '사업\\s*내용' },
  { key: 'content', pattern: '혜택\\s*내용' },
  { key: 'target', pattern: '지원\\s*대상' },
  { key: 'target', pattern: '신청\\s*대상' },
  { key: 'target', pattern: '신청\\s*자격' },
  { key: 'target', pattern: '지원\\s*자격' },
  { key: 'target', pattern: '대상\\s*요건' },
  { key: 'target', pattern: '참가\\s*대상' },
  { key: 'method', pattern: '신청\\s*방법' },
  { key: 'method', pattern: '지원\\s*방법' },
  { key: 'method', pattern: '신청\\s*절차' },
  { key: 'method', pattern: '접수\\s*방법' },
  { key: 'period', pattern: '신청\\s*기간' },
  { key: 'period', pattern: '모집\\s*기간' },
  { key: 'period', pattern: '접수\\s*기간' },
  { key: 'period', pattern: '사업\\s*기간' },
  { key: 'period', pattern: '추진\\s*일정' },
  { key: 'period', pattern: '운영\\s*기간' },
  { key: 'documents', pattern: '제출\\s*서류' },
  { key: 'documents', pattern: '구비\\s*서류' },
  { key: 'documents', pattern: '필요\\s*서류' },
  { key: 'documents', pattern: '신청\\s*서류' },
  { key: 'documents', pattern: '첨부\\s*서류' },
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
    content: '', target: '', method: '', period: '', documents: '', contact: '',
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
  const dedup: Hit[] = [];
  for (const h of hits) {
    if (dedup.length === 0 || h.headerStart > dedup[dedup.length - 1].headerStart + 2) dedup.push(h);
  }
  for (let i = 0; i < dedup.length; i++) {
    const cur = dedup[i];
    const nxt = dedup[i + 1];
    let chunk = rawText.slice(cur.contentStart, nxt ? nxt.headerStart : rawText.length).trim();
    chunk = chunk
      .replace(/관심 정책정보 목록.*$/s, '')
      .replace(/유관기관 사이트.*$/s, '')
      .replace(/본 정보는 제공기관의[^.]*\./g, '')
      .replace(/[\s○■▶◆◇▣◎·\-]+$/u, '')
      .replace(/^[\s○■▶◆◇▣◎·\-]+/u, '')
      .trim();
    if (chunk && !result[cur.key]) result[cur.key] = chunk;
    else if (chunk && result[cur.key]) result[cur.key] += '\n\n' + chunk;
  }
  return result;
};

const cleanRawText = (text?: string) => {
  if (!text) return '';
  return text
    .replace(/관심 정책정보 목록.*$/s, '')
    .replace(/유관기관 사이트.*$/s, '')
    .replace(/본 정보는 제공기관의[^.]*\./g, '')
    .replace(/\n{3,}/g, '\n\n')
    .replace(/[ \t]+\n/g, '\n')
    .replace(/\n[ \t]+/g, '\n')
    .replace(/□/g, '\n□')
    .replace(/○/g, '\n○')
    .replace(/◇/g, '\n◇')
    .replace(/▶/g, '\n▶')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
};

const cleanPeriodText = (text: string) => {
  return text
    .replace(/\n{3,}/g, '\n\n')
    .replace(/[ \t]+\n/g, '\n')
    .replace(/\n[ \t]+/g, '\n')
    .replace(/□/g, '\n□')
    .replace(/○/g, '\n○')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
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
  while ((mm = dashedRe.exec(deadline)) !== null) all.push({ y: mm[1], m: mm[2], d: mm[3] });
  if (all.length === 0) while ((mm = compactRe.exec(deadline)) !== null) all.push({ y: mm[1], m: mm[2], d: mm[3] });
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
  '전라북도', '전북특별자치도', '전라남도', '경상북도', '경상남도', '제주특별자치도',
]);

const formatRegion = (region?: string, subRegion?: string | null) => {
  const r = region?.trim();
  const sub = subRegion?.trim();
  if (r && KOREAN_REGIONS.has(r)) return sub ? `${r} ${sub}` : r;
  return '전국';
};

interface ResolvedDoc {
  name: string;
  source: string;
  url: string | null;
  fee?: string;
  hint?: string;
  origin?: 'ai' | 'pattern' | 'none';
  required?: 'required' | 'optional' | null;
  ifNeeded?: boolean;
}

interface ParsedDocItem {
  name: string;
  required: 'required' | 'optional' | null;
  ifNeeded: boolean;
}

const KNOWN_DOC_SOURCES: { pattern: RegExp; source: string; url: string | null; fee?: string; hint?: string }[] = [
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

const splitOutsideParens = (text: string): string[] => {
  const items: string[] = [];
  let buf = '';
  let depth = 0;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (c === '(' || c === '（' || c === '[' || c === '【') depth++;
    else if (c === ')' || c === '）' || c === ']' || c === '】') depth = Math.max(0, depth - 1);
    if (depth === 0 && (c === '\n' || c === ',' || c === '，' || c === '、')) {
      if (buf.trim().length > 0) items.push(buf);
      buf = '';
    } else buf += c;
  }
  if (buf.trim().length > 0) items.push(buf);
  return items;
};

const parseDocItems = (submitDocs?: string): { items: ParsedDocItem[]; notes: string[] } => {
  if (!submitDocs) return { items: [], notes: [] };
  const cleaned = submitDocs
    .replace(/☞[^\n]*/g, '')
    .replace(/붙임\s*파일[^\n]*/g, '')
    .replace(/자세한\s*내용은[^\n]*/g, '')
    .replace(/[•○●·]/g, '');
  let contextRequired: 'required' | 'optional' | null = null;
  const items: ParsedDocItem[] = [];
  const notes: string[] = [];
  for (const line of cleaned.split(/\n/)) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    if (/^※/.test(trimmed)) { notes.push(trimmed); continue; }
    if (/^[\[<【［＜]\s*필수(?:\s*서류)?\s*[\]>】］＞]\s*$/.test(trimmed)) { contextRequired = 'required'; continue; }
    if (/^[\[<【［＜]\s*선택(?:\s*서류)?\s*[\]>】］＞]\s*$/.test(trimmed)) { contextRequired = 'optional'; continue; }
    const lineItems = splitOutsideParens(line);
    for (const raw of lineItems) {
      const itemTrim = raw.trim();
      if (!itemTrim || /^※/.test(itemTrim)) continue;
      let required: 'required' | 'optional' | null = contextRequired;
      if (/[(（]\s*필수\s*[)）]/.test(raw)) required = 'required';
      else if (/[(（]\s*선택\s*[)）]/.test(raw)) required = 'optional';
      const ifNeeded = /[(（]\s*필요시\s*[)）]/.test(raw);
      const name = raw
        .replace(/[(（]\s*필수\s*[)）]/g, '')
        .replace(/[(（]\s*선택\s*[)）]/g, '')
        .replace(/[(（]\s*필요시\s*[)）]/g, '')
        .replace(/\s+/g, ' ').trim();
      if (name.length >= 2 && name.length <= 300 && !/^[\d.\-:]+$/.test(name)) items.push({ name, required, ifNeeded });
    }
  }
  const seen = new Map<string, ParsedDocItem>();
  for (const item of items) {
    const key = item.name.replace(/\s+/g, '');
    const existing = seen.get(key);
    if (!existing) seen.set(key, item);
    else seen.set(key, { name: existing.name, required: existing.required === 'required' || item.required === 'required' ? 'required' : (existing.required ?? item.required), ifNeeded: existing.ifNeeded || item.ifNeeded });
  }
  return { items: Array.from(seen.values()), notes: Array.from(new Set(notes.map(n => n.replace(/\s+/g, ' ').trim()))) };
};

const findAiMatch = (docName: string, aiDocs: DocumentLink[]): DocumentLink | undefined => {
  const norm = (s: string) => s.replace(/\s+/g, '');
  const nd = norm(docName);
  return aiDocs.find((d) => { const na = norm(d.doc_name); return na === nd || nd.includes(na) || na.includes(nd); });
};

const resolveDoc = (item: ParsedDocItem, aiDocs: DocumentLink[]): ResolvedDoc => {
  const ai = findAiMatch(item.name, aiDocs);
  if (ai) return { name: item.name, source: ai.source, url: ai.url, fee: ai.fee, hint: ai.search_hint, origin: 'ai', required: item.required, ifNeeded: item.ifNeeded };
  for (const k of KNOWN_DOC_SOURCES) {
    if (k.pattern.test(item.name)) return { name: item.name, source: k.source, url: k.url, fee: k.fee, hint: k.hint, origin: 'pattern', required: item.required, ifNeeded: item.ifNeeded };
  }
  return { name: item.name, source: '신청 기관 확인', url: null, hint: '공고문 안내 또는 담당자 문의', origin: 'none', required: item.required, ifNeeded: item.ifNeeded };
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
    policy_id?: string; rank?: string; fit_score?: string; reasons?: string; document_links?: string;
  }>();

  const [policy, setPolicy] = useState<PolicyFull | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedbackDone, setFeedbackDone] = useState(false);

  useEffect(() => {
    const fetchPolicy = async () => {
      if (!policy_id) { setError('정책 ID가 전달되지 않았습니다.'); setLoading(false); return; }
      try {
        const response = await fetch(`${API_URL}/policy/${policy_id}`);
        if (!response.ok) { setError('정책 정보를 불러올 수 없습니다.'); setLoading(false); return; }
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

  useEffect(() => {
    const checkViewCount = async () => {
      try {
        const count = await AsyncStorage.getItem('policy_view_count');
        const newCount = count ? parseInt(count) + 1 : 1;
        await AsyncStorage.setItem('policy_view_count', String(newCount));
        if (newCount % 5 === 0) setTimeout(() => setShowFeedback(true), 1000);
      } catch (e) { console.error(e); }
    };
    checkViewCount();
  }, []);

  const handleFeedback = async (helpful: boolean) => {
    setFeedbackDone(true);
    setTimeout(() => { setShowFeedback(false); setFeedbackDone(false); }, 1200);
  };

  const reasonItems = (() => {
    if (!reasons) return [];
    try { return (JSON.parse(reasons) as string[]).map(parseReason); }
    catch { return []; }
  })();

  const docLinks: DocumentLink[] = (() => {
    if (!document_links) return [];
    try { return JSON.parse(document_links); }
    catch { return []; }
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

  const sections = parseSections(policy.raw_text);
  const deadline = formatDeadline(policy.deadline);
  const ageRange = formatAge(policy.age_min, policy.age_max);
  const regionLabel = formatRegion(policy.region, policy.sub_region);

  const targetItems: { label: string; value: string }[] = [];
  targetItems.push({ label: '지역', value: regionLabel });
  if (ageRange) targetItems.push({ label: '연령', value: ageRange });
  if (policy.income_max_pct) targetItems.push({ label: '소득기준', value: `중위소득 ${policy.income_max_pct}% 이하` });
  if (policy.employment) targetItems.push({ label: '취업상태', value: policy.employment });
  if (policy.housing) targetItems.push({ label: '주거형태', value: policy.housing });

  return (
    <SafeAreaView style={styles.wrap} edges={['top']}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
          <Ionicons name="chevron-back" size={26} color="#111" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>정책 상세</Text>
        <View style={{ width: 26 }} />
      </View>

      <ScrollView style={styles.container} contentContainerStyle={{ paddingBottom: 48 }} showsVerticalScrollIndicator={false}>

        {/* 헤더 섹션 */}
        <View style={styles.heroSection}>
          <View style={styles.heroTop}>
            {rank ? <View style={styles.rankBadge}><Text style={styles.rankText}>{rank}순위</Text></View> : null}
            {policy.category ? <View style={styles.categoryBadge}><Text style={styles.categoryText}>{policy.category}</Text></View> : null}
          </View>
          <Text style={styles.policyTitle}>{policy.name}</Text>
          {policy.source ? (
            <View style={styles.sourceRow}>
              <Ionicons name="business-outline" size={13} color="#888" />
              <Text style={styles.policySource}>{policy.source}</Text>
            </View>
          ) : null}
          <View style={styles.tagRow}>
            {(() => {
              const r = policy.region?.trim();
              const sub = policy.sub_region?.trim();
              const isValidRegion = r && KOREAN_REGIONS.has(r);
              return (
                <>
                  <View style={styles.tagGray}>
                    <Ionicons name="location-outline" size={11} color="#666" />
                    <Text style={styles.tagGrayText}>{isValidRegion ? r : '전국'}</Text>
                  </View>
                  {isValidRegion && sub ? <View style={styles.tagGray}><Text style={styles.tagGrayText}>{sub}</Text></View> : null}
                </>
              );
            })()}
            {fit_score ? (
              <View style={styles.tagBlue}>
                <Ionicons name="analytics-outline" size={11} color="#3367D6" />
                <Text style={styles.tagBlueText}>적합도 {fit_score}%</Text>
              </View>
            ) : null}
          </View>
        </View>

        {/* 지원 금액 카드 */}
        <View style={styles.amountCard}>
          <View style={styles.amountLeft}>
            <Text style={styles.amountLabel}>💰 지원 금액</Text>
            <Text style={styles.amountValue}>{policy.amount || '금액 정보 없음'}</Text>
          </View>
          {policy.pvmthd && policy.pvmthd !== '기타' ? (
            <View style={styles.pvmthdChip}>
              <Text style={styles.pvmthdText}>{policy.pvmthd}</Text>
            </View>
          ) : null}
        </View>

        {/* 모집 일정 */}
        {(deadline || policy.registered_at || sections.period) ? (
          <View style={styles.section}>
            <View style={styles.sectionTitleRow}>
              <View style={styles.sectionDot} />
              <Text style={styles.sectionTitle}>모집 일정</Text>
            </View>
            <View style={styles.infoCard}>
              {policy.registered_at ? (
                <View style={styles.infoRow}>
                  <Text style={styles.infoRowLabel}>등록일</Text>
                  <Text style={styles.infoRowValue}>{policy.registered_at}</Text>
                </View>
              ) : null}
              {deadline ? (
                <View style={[styles.infoRow, !sections.period && { borderBottomWidth: 0 }]}>
                  <Text style={styles.infoRowLabel}>마감일</Text>
                  <View style={styles.deadlineRow}>
                    {deadline.urgent && !deadline.expired ? <View style={styles.urgentDot} /> : null}
                    <Text style={[styles.infoRowValue, deadline.urgent && { color: '#FF6B35', fontWeight: '800' }, deadline.expired && { color: '#bbb' }]}>
                      {deadline.text}
                    </Text>
                  </View>
                </View>
              ) : null}
              {sections.period ? (
                <View style={styles.infoBlock}>
                  <Text style={styles.infoBlockLabel}>신청 기간</Text>
                  <Text style={styles.infoBlockValue}>{cleanPeriodText(sections.period)}</Text>
                </View>
              ) : null}
            </View>
          </View>
        ) : null}

        {/* 지원 대상 */}
        <View style={styles.section}>
          <View style={styles.sectionTitleRow}>
            <View style={styles.sectionDot} />
            <Text style={styles.sectionTitle}>지원 대상</Text>
          </View>
          <View style={styles.infoCard}>
            {targetItems.map((it, i) => (
              <View key={i} style={[styles.infoRow, i === targetItems.length - 1 && !sections.target && !policy.add_qlfc && { borderBottomWidth: 0 }]}>
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
              <View style={[styles.infoBlock, { borderTopWidth: sections.target ? 1 : 0 }]}>
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

        {/* 정책 내용 */}
        {(sections.content || policy.raw_text) ? (
          <View style={styles.section}>
            <View style={styles.sectionTitleRow}>
              <View style={styles.sectionDot} />
              <Text style={styles.sectionTitle}>정책 내용</Text>
            </View>
            <View style={styles.descBox}>
              <Text style={styles.descText}>{sections.content || cleanRawText(policy.raw_text)}</Text>
            </View>
          </View>
        ) : null}

        {/* 신청 방법 */}
        {sections.method ? (
          <View style={styles.section}>
            <View style={styles.sectionTitleRow}>
              <View style={styles.sectionDot} />
              <Text style={styles.sectionTitle}>{SECTION_TITLE.method}</Text>
            </View>
            <View style={styles.descBox}>
              <Text style={styles.descText}>{sections.method}</Text>
            </View>
          </View>
        ) : null}

        {/* 선정 방법 */}
        {policy.select_method ? (
          <View style={styles.section}>
            <View style={styles.sectionTitleRow}>
              <View style={styles.sectionDot} />
              <Text style={styles.sectionTitle}>선정 방법</Text>
            </View>
            <View style={styles.descBox}>
              <Text style={styles.descText}>{policy.select_method}</Text>
            </View>
          </View>
        ) : null}

        {/* 필요 서류 */}
        {(() => {
          const rawDocsText = sections.documents || policy.submit_docs || '';
          const parsed = parseDocItems(rawDocsText);
          const docs: ResolvedDoc[] = parsed.items.length > 0
            ? parsed.items.map((n) => resolveDoc(n, docLinks))
            : docLinks.map((d) => ({ name: d.doc_name, source: d.source, url: d.url, fee: d.fee, hint: d.search_hint }));
          if (docs.length === 0 && parsed.notes.length === 0 && !rawDocsText) return null;
          return (
            <View style={styles.section}>
              <View style={styles.sectionTitleRow}>
                <View style={styles.sectionDot} />
                <Text style={styles.sectionTitle}>{SECTION_TITLE.documents}</Text>
              </View>
              {parsed.notes.length > 0 ? (
                <View style={styles.docNotesCard}>
                  {parsed.notes.map((note, idx) => <Text key={idx} style={styles.docNoteText}>{note}</Text>)}
                </View>
              ) : null}
              {docs.length > 0 ? (
                <View style={styles.docsCard}>
                  {docs.map((doc, idx) => (
                    <View key={idx} style={[styles.docItemRow, idx === docs.length - 1 && { borderBottomWidth: 0 }]}>
                      <View style={styles.docItemTextWrap}>
                        {(doc.required || doc.ifNeeded || (doc.origin === 'ai' && doc.url)) ? (
                          <View style={styles.docBadgeRow}>
                            {doc.required === 'required' ? <View style={styles.requiredBadge}><Text style={styles.requiredBadgeText}>필수</Text></View> : null}
                            {doc.ifNeeded ? <View style={styles.ifNeededBadge}><Text style={styles.ifNeededBadgeText}>필요시</Text></View> : null}
                            {doc.required === 'optional' ? <View style={styles.optionalBadge}><Text style={styles.optionalBadgeText}>선택</Text></View> : null}
                            {doc.origin === 'ai' && doc.url ? (
                              <View style={styles.aiBadge}>
                                <Ionicons name="sparkles" size={10} color="#7B3FE4" />
                                <Text style={styles.aiBadgeText}>AI 추천</Text>
                              </View>
                            ) : null}
                          </View>
                        ) : null}
                        <Text style={styles.docItemName}>{doc.name}</Text>
                        <Text style={styles.docItemSource}>{doc.source}{doc.fee ? ` · ${doc.fee}` : ''}</Text>
                        {doc.hint ? <Text style={styles.docItemHint}>{doc.hint}</Text> : null}
                      </View>
                      {doc.url ? (
                        <TouchableOpacity style={styles.docIssueBtn} onPress={() => Linking.openURL(doc.url!)} activeOpacity={0.7}>
                          <Ionicons name="open-outline" size={13} color="#fff" />
                          <Text style={styles.docIssueBtnText}>발급</Text>
                        </TouchableOpacity>
                      ) : (
                        <View style={styles.docSelfBadge}>
                          <Text style={styles.docSelfBadgeText}>{doc.source.includes('본인') ? '본인 준비' : '직접 발급'}</Text>
                        </View>
                      )}
                    </View>
                  ))}
                </View>
              ) : rawDocsText ? (
                <View style={styles.descBox}><Text style={styles.descText}>{rawDocsText}</Text></View>
              ) : null}
            </View>
          );
        })()}

        {/* 문의처 */}
        {sections.contact ? (
          <View style={styles.section}>
            <View style={styles.sectionTitleRow}>
              <View style={styles.sectionDot} />
              <Text style={styles.sectionTitle}>{SECTION_TITLE.contact}</Text>
            </View>
            <View style={styles.descBox}>
              <Text style={styles.descText}>{sections.contact}</Text>
            </View>
          </View>
        ) : null}

        {/* 내 정보 매칭 결과 */}
        {reasonItems.length > 0 ? (
          <View style={styles.section}>
            <View style={styles.sectionTitleRow}>
              <View style={styles.sectionDot} />
              <Text style={styles.sectionTitle}>내 정보 매칭 결과</Text>
            </View>
            <View style={styles.reasonList}>
              {reasonItems.map((item, idx) => (
                <View key={idx} style={[styles.reasonRow, idx === reasonItems.length - 1 && { borderBottomWidth: 0 }]}>
                  <View style={[styles.reasonIcon, item.status === 'pass' && styles.reasonIconPass, item.status === 'fail' && styles.reasonIconFail, item.status === 'warn' && styles.reasonIconWarn]}>
                    <Ionicons name={item.status === 'pass' ? 'checkmark' : item.status === 'fail' ? 'close' : 'alert'} size={14} color="#fff" />
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
          <TouchableOpacity style={styles.sourceBtn} onPress={() => Linking.openURL(policy.source_url!)}>
            <Ionicons name="open-outline" size={18} color="#fff" style={{ marginRight: 8 }} />
            <Text style={styles.sourceBtnText}>원문 보기 / 신청하기</Text>
          </TouchableOpacity>
        ) : null}
      </ScrollView>

      {/* 피드백 모달 */}
      <Modal visible={showFeedback} transparent animationType="fade" onRequestClose={() => {}}>
        <View style={styles.feedbackOverlay}>
          <View style={styles.feedbackCard}>
            {feedbackDone ? (
              <View style={styles.feedbackDoneWrap}>
                <Ionicons name="checkmark-circle" size={56} color="#00C49A" />
                <Text style={styles.feedbackDoneText}>소중한 의견 감사해요! 😊</Text>
              </View>
            ) : (
              <>
                <View style={styles.feedbackIconWrap}>
                  <Ionicons name="chatbubble-ellipses-outline" size={32} color="#00C49A" />
                </View>
                <Text style={styles.feedbackTitle}>이 공고가 도움이 되었나요?</Text>
                <View style={styles.feedbackPolicyBox}>
                  <Text style={styles.feedbackPolicyText}>{policy.name}</Text>
                </View>
                <Text style={styles.feedbackSub}>소중한 의견을 남겨주세요 😊</Text>
                <View style={styles.feedbackBtnRow}>
                  <TouchableOpacity style={styles.feedbackBtnYes} onPress={() => handleFeedback(true)}>
                    <Ionicons name="thumbs-up" size={18} color="#fff" />
                    <Text style={styles.feedbackBtnYesText}>도움됐어요</Text>
                  </TouchableOpacity>
                  <TouchableOpacity style={styles.feedbackBtnNo} onPress={() => handleFeedback(false)}>
                    <Ionicons name="thumbs-down" size={18} color="#888" />
                    <Text style={styles.feedbackBtnNoText}>아니요</Text>
                  </TouchableOpacity>
                </View>
              </>
            )}
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: '#F7FDFB' },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 16, paddingVertical: 12, backgroundColor: '#F7FDFB', borderBottomWidth: 1, borderBottomColor: '#EEF2F0' },
  backBtn: { padding: 4 },
  headerTitle: { fontSize: 17, fontWeight: '700', color: '#111' },
  container: { flex: 1, paddingHorizontal: 20 },
  emptyBox: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  emptyText: { color: '#888', fontSize: 15 },
  heroSection: { paddingTop: 20, paddingBottom: 16, borderBottomWidth: 1, borderBottomColor: '#EEF2F0', marginBottom: 20 },
  heroTop: { flexDirection: 'row', gap: 8, marginBottom: 12 },
  rankBadge: { backgroundColor: '#00C49A', paddingHorizontal: 12, paddingVertical: 5, borderRadius: 20 },
  rankText: { color: '#fff', fontWeight: '800', fontSize: 13 },
  categoryBadge: { backgroundColor: '#E6F9F4', paddingHorizontal: 12, paddingVertical: 5, borderRadius: 20 },
  categoryText: { color: '#00A582', fontWeight: '700', fontSize: 13 },
  policyTitle: { fontSize: 22, fontWeight: '800', color: '#111', lineHeight: 30, marginBottom: 8 },
  sourceRow: { flexDirection: 'row', alignItems: 'center', gap: 4, marginBottom: 12 },
  policySource: { fontSize: 13, color: '#888' },
  tagRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  tagBlue: { flexDirection: 'row', alignItems: 'center', gap: 4, backgroundColor: '#E8F0FE', paddingHorizontal: 10, paddingVertical: 5, borderRadius: 20 },
  tagBlueText: { color: '#3367D6', fontSize: 12, fontWeight: '700' },
  tagGray: { flexDirection: 'row', alignItems: 'center', gap: 4, backgroundColor: '#F0F2F1', paddingHorizontal: 10, paddingVertical: 5, borderRadius: 20 },
  tagGrayText: { color: '#555', fontSize: 12, fontWeight: '600' },
  amountCard: { backgroundColor: '#fff', borderRadius: 16, padding: 18, marginBottom: 24, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', shadowColor: '#000', shadowOpacity: 0.06, shadowRadius: 10, elevation: 3 },
  amountLeft: {},
  amountLabel: { fontSize: 13, color: '#888', marginBottom: 6, fontWeight: '600' },
  amountValue: { fontSize: 26, fontWeight: '800', color: '#00C49A' },
  pvmthdChip: { backgroundColor: '#E8F0FE', paddingHorizontal: 12, paddingVertical: 8, borderRadius: 12 },
  pvmthdText: { color: '#3367D6', fontSize: 13, fontWeight: '700' },
  section: { marginBottom: 24 },
  sectionTitleRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 12 },
  sectionDot: { width: 4, height: 18, backgroundColor: '#00C49A', borderRadius: 2 },
  sectionTitle: { fontSize: 17, fontWeight: '800', color: '#111' },
  infoCard: { backgroundColor: '#fff', borderRadius: 16, paddingHorizontal: 16, paddingVertical: 4, shadowColor: '#000', shadowOpacity: 0.04, shadowRadius: 8, elevation: 2 },
  infoRow: { flexDirection: 'row', alignItems: 'flex-start', paddingVertical: 14, borderBottomWidth: 1, borderBottomColor: '#F2F4F3' },
  infoRowLabel: { width: 80, fontSize: 14, color: '#888', fontWeight: '600' },
  infoRowValue: { flex: 1, fontSize: 15, color: '#222', fontWeight: '600', lineHeight: 22 },
  deadlineRow: { flex: 1, flexDirection: 'row', alignItems: 'center', gap: 6 },
  urgentDot: { width: 7, height: 7, borderRadius: 4, backgroundColor: '#FF6B35' },
  infoBlock: { paddingVertical: 14, borderTopWidth: 1, borderTopColor: '#F2F4F3' },
  infoBlockLabel: { fontSize: 13, color: '#888', fontWeight: '600', marginBottom: 6 },
  infoBlockValue: { fontSize: 14, color: '#333', lineHeight: 22 },
  warnBox: { marginTop: 12, backgroundColor: '#FFF4F1', borderRadius: 14, padding: 14, borderWidth: 1, borderColor: '#FAD4CC' },
  warnHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 8, gap: 6 },
  warnTitle: { fontSize: 14, fontWeight: '800', color: '#D85B4A' },
  warnText: { fontSize: 14, color: '#5C2F27', lineHeight: 22 },
  descBox: { backgroundColor: '#fff', borderRadius: 16, padding: 16, shadowColor: '#000', shadowOpacity: 0.04, shadowRadius: 8, elevation: 2 },
  descText: { fontSize: 15, color: '#333', lineHeight: 26 },
  docNotesCard: { backgroundColor: '#FFF8E5', borderRadius: 12, paddingVertical: 10, paddingHorizontal: 14, marginBottom: 10, borderLeftWidth: 3, borderLeftColor: '#E5B844' },
  docNoteText: { fontSize: 13, color: '#7A5C00', lineHeight: 20, marginVertical: 2 },
  docsCard: { backgroundColor: '#fff', borderRadius: 16, paddingHorizontal: 16, paddingVertical: 4, shadowColor: '#000', shadowOpacity: 0.04, shadowRadius: 8, elevation: 2 },
  docItemRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 14, borderBottomWidth: 1, borderBottomColor: '#F2F4F3' },
  docItemTextWrap: { flex: 1, marginRight: 10 },
  docBadgeRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginBottom: 6 },
  docItemName: { fontSize: 15, fontWeight: '700', color: '#222', lineHeight: 22, marginBottom: 4 },
  docItemSource: { fontSize: 13, color: '#666', lineHeight: 18 },
  docItemHint: { fontSize: 12, color: '#999', marginTop: 3, lineHeight: 17 },
  aiBadge: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#F2EAFF', paddingHorizontal: 7, paddingVertical: 3, borderRadius: 8, gap: 3 },
  aiBadgeText: { color: '#7B3FE4', fontSize: 10, fontWeight: '800' },
  requiredBadge: { backgroundColor: '#FFE9E5', paddingHorizontal: 8, paddingVertical: 3, borderRadius: 8 },
  requiredBadgeText: { color: '#D85B4A', fontSize: 11, fontWeight: '800' },
  optionalBadge: { backgroundColor: '#FFF1DC', paddingHorizontal: 8, paddingVertical: 3, borderRadius: 8 },
  optionalBadgeText: { color: '#C77810', fontSize: 11, fontWeight: '800' },
  ifNeededBadge: { backgroundColor: '#F0F2F1', paddingHorizontal: 8, paddingVertical: 3, borderRadius: 8 },
  ifNeededBadgeText: { color: '#777', fontSize: 11, fontWeight: '800' },
  docIssueBtn: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#00C49A', paddingHorizontal: 14, paddingVertical: 8, borderRadius: 10, gap: 4 },
  docIssueBtnText: { color: '#fff', fontSize: 13, fontWeight: '700' },
  docSelfBadge: { backgroundColor: '#F0F2F1', paddingHorizontal: 10, paddingVertical: 7, borderRadius: 10 },
  docSelfBadgeText: { color: '#666', fontSize: 12, fontWeight: '700' },
  reasonList: { backgroundColor: '#fff', borderRadius: 16, padding: 16, shadowColor: '#000', shadowOpacity: 0.04, shadowRadius: 8, elevation: 2 },
  reasonRow: { flexDirection: 'row', alignItems: 'flex-start', paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: '#F2F4F3' },
  reasonIcon: { width: 26, height: 26, borderRadius: 13, justifyContent: 'center', alignItems: 'center', marginRight: 12, marginTop: 1 },
  reasonIconPass: { backgroundColor: '#00C49A' },
  reasonIconFail: { backgroundColor: '#E76F51' },
  reasonIconWarn: { backgroundColor: '#F4A261' },
  reasonLabel: { fontSize: 15, fontWeight: '700', color: '#222' },
  reasonDetail: { fontSize: 13, color: '#777', marginTop: 3, lineHeight: 19 },
  sourceBtn: { backgroundColor: '#00C49A', paddingVertical: 16, borderRadius: 30, flexDirection: 'row', justifyContent: 'center', alignItems: 'center', marginTop: 8, shadowColor: '#00C49A', shadowOpacity: 0.3, shadowRadius: 10, elevation: 4 },
  sourceBtnText: { color: '#fff', fontSize: 17, fontWeight: '700' },
  feedbackOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.55)', justifyContent: 'center', alignItems: 'center', paddingHorizontal: 24 },
  feedbackCard: { backgroundColor: '#fff', borderRadius: 24, padding: 28, width: '100%', alignItems: 'center', shadowColor: '#000', shadowOpacity: 0.15, shadowRadius: 20, elevation: 10 },
  feedbackIconWrap: { width: 64, height: 64, borderRadius: 32, backgroundColor: '#E6F9F4', justifyContent: 'center', alignItems: 'center', marginBottom: 16 },
  feedbackTitle: { fontSize: 18, fontWeight: '800', color: '#111', marginBottom: 14, textAlign: 'center' },
  feedbackPolicyBox: { backgroundColor: '#F0FBF7', borderRadius: 12, paddingHorizontal: 16, paddingVertical: 12, marginBottom: 10, width: '100%', borderLeftWidth: 3, borderLeftColor: '#00C49A' },
  feedbackPolicyText: { fontSize: 14, fontWeight: '700', color: '#00A582', textAlign: 'center', lineHeight: 20 },
  feedbackSub: { fontSize: 13, color: '#999', marginBottom: 20 },
  feedbackBtnRow: { flexDirection: 'row', gap: 12, width: '100%' },
  feedbackBtnYes: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', backgroundColor: '#00C49A', paddingVertical: 14, borderRadius: 14, gap: 8 },
  feedbackBtnYesText: { color: '#fff', fontSize: 15, fontWeight: '800' },
  feedbackBtnNo: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', backgroundColor: '#F0F2F1', paddingVertical: 14, borderRadius: 14, gap: 8 },
  feedbackBtnNoText: { color: '#888', fontSize: 15, fontWeight: '800' },
  feedbackDoneWrap: { alignItems: 'center', paddingVertical: 20 },
  feedbackDoneText: { fontSize: 17, fontWeight: '700', color: '#111', marginTop: 16 },
});

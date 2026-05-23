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
}

interface DocumentLink {
  doc_name: string;
  source: string;
  url: string | null;
  search_hint?: string;
  fee?: string;
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
  const [showFullText, setShowFullText] = useState(false);

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
          </View>
        </View>

        {/* 지원 내용 */}
        {sections.content ? (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>{SECTION_TITLE.content}</Text>
            <View style={styles.descBox}>
              <Text style={styles.descText}>{sections.content}</Text>
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

        {/* 필요 서류 */}
        {(sections.documents || policy.submit_docs) ? (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>{SECTION_TITLE.documents}</Text>
            <View style={styles.descBox}>
              <Text style={styles.descText}>{sections.documents || policy.submit_docs}</Text>
            </View>

            {/* AI 발급처 링크 */}
            {docLinks.length > 0 ? (
              <View style={[styles.docLinksBox]}>
                <View style={styles.docLinksHeader}>
                  <Ionicons name="link-outline" size={14} color="#00A582" />
                  <Text style={styles.docLinksTitle}>서류 발급처 (AI 안내)</Text>
                </View>
                {docLinks.map((dl, idx) => (
                  <View key={idx} style={[styles.docLinkRow, idx === docLinks.length - 1 && { borderBottomWidth: 0 }]}>
                    <View style={{ flex: 1 }}>
                      <Text style={styles.docLinkName}>{dl.doc_name}</Text>
                      <Text style={styles.docLinkSource}>{dl.source}{dl.fee ? ` · ${dl.fee}` : ''}</Text>
                      {dl.search_hint ? <Text style={styles.docLinkHint}>{dl.search_hint}</Text> : null}
                    </View>
                    {dl.url ? (
                      <TouchableOpacity
                        style={styles.docLinkBtn}
                        onPress={() => Linking.openURL(dl.url!)}
                        activeOpacity={0.7}
                      >
                        <Text style={styles.docLinkBtnText}>발급</Text>
                        <Ionicons name="open-outline" size={12} color="#00C49A" />
                      </TouchableOpacity>
                    ) : null}
                  </View>
                ))}
              </View>
            ) : null}
          </View>
        ) : null}

        {/* 문의처 */}
        {sections.contact ? (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>{SECTION_TITLE.contact}</Text>
            <View style={styles.descBox}>
              <Text style={styles.descText}>{sections.contact}</Text>
            </View>
          </View>
        ) : null}

        {/* 섹션 추출 실패 시 fallback: 원문 전체 */}
        {!hasAnySection && policy.raw_text ? (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>정책 안내</Text>
            <View style={styles.descBox}>
              <Text style={styles.descText}>{cleanRawText(policy.raw_text)}</Text>
            </View>
          </View>
        ) : null}

        {/* 원문 보기 토글 (섹션 분리 잘 되어도 원문 통째로 보고 싶은 경우) */}
        {hasAnySection && policy.raw_text ? (
          <View style={styles.section}>
            <TouchableOpacity
              style={styles.expandBtn}
              onPress={() => setShowFullText(!showFullText)}
              activeOpacity={0.7}
            >
              <Text style={styles.expandBtnText}>
                {showFullText ? '원문 접기' : '원문 전체 보기'}
              </Text>
              <Ionicons
                name={showFullText ? 'chevron-up' : 'chevron-down'}
                size={16}
                color="#666"
              />
            </TouchableOpacity>
            {showFullText ? (
              <View style={[styles.descBox, { marginTop: 10 }]}>
                <Text style={styles.descText}>{cleanRawText(policy.raw_text)}</Text>
              </View>
            ) : null}
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
  headerTitle: { fontSize: 17, fontWeight: '700', color: '#111' },
  container: { flex: 1, paddingHorizontal: 20 },
  emptyBox: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  emptyText: { color: '#888', fontSize: 14 },
  titleSection: { marginTop: 8, marginBottom: 18 },
  rankBadge: {
    alignSelf: 'flex-start',
    backgroundColor: '#00C49A',
    paddingHorizontal: 12,
    paddingVertical: 5,
    borderRadius: 20,
    marginBottom: 12,
  },
  rankText: { color: '#fff', fontWeight: '800', fontSize: 12 },
  policyTitle: { fontSize: 22, fontWeight: '800', color: '#111', lineHeight: 30 },
  policySource: { fontSize: 13, color: '#888', marginTop: 6 },
  tagRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 18 },
  tagGreen: { backgroundColor: '#e6f9f4', paddingHorizontal: 12, paddingVertical: 5, borderRadius: 20 },
  tagGreenText: { color: '#00C49A', fontSize: 12, fontWeight: '700' },
  tagBlue: { backgroundColor: '#E8F0FE', paddingHorizontal: 12, paddingVertical: 5, borderRadius: 20 },
  tagBlueText: { color: '#3367D6', fontSize: 12, fontWeight: '700' },
  tagGray: { backgroundColor: '#F0F2F1', paddingHorizontal: 12, paddingVertical: 5, borderRadius: 20 },
  tagGrayText: { color: '#666', fontSize: 12, fontWeight: '600' },
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
  amountLabel: { fontSize: 13, color: '#888', marginBottom: 6, fontWeight: '600' },
  amountValue: { fontSize: 22, fontWeight: '800', color: '#00C49A' },
  section: { marginBottom: 22 },
  sectionTitle: { fontSize: 15, fontWeight: '800', color: '#111', marginBottom: 10 },
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
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#F2F4F3',
  },
  infoRowLabel: { width: 80, fontSize: 13, color: '#888', fontWeight: '600' },
  infoRowValue: { flex: 1, fontSize: 14, color: '#222', fontWeight: '600', lineHeight: 20 },
  infoBlock: { paddingVertical: 12, borderTopWidth: 1, borderTopColor: '#F2F4F3' },
  infoBlockLabel: { fontSize: 12, color: '#888', fontWeight: '600', marginBottom: 6 },
  infoBlockValue: { fontSize: 13, color: '#333', lineHeight: 20 },
  descBox: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 16,
    shadowColor: '#000',
    shadowOpacity: 0.04,
    shadowRadius: 6,
    elevation: 1,
  },
  descText: { fontSize: 14, color: '#333', lineHeight: 22 },
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
  expandBtnText: { color: '#666', fontSize: 13, fontWeight: '600', marginRight: 4 },
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
    width: 22,
    height: 22,
    borderRadius: 11,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
    marginTop: 1,
  },
  reasonIconPass: { backgroundColor: '#00C49A' },
  reasonIconFail: { backgroundColor: '#E76F51' },
  reasonIconWarn: { backgroundColor: '#F4A261' },
  reasonLabel: { fontSize: 14, fontWeight: '700', color: '#222' },
  reasonDetail: { fontSize: 12, color: '#777', marginTop: 2, lineHeight: 18 },
  sourceBtn: {
    backgroundColor: '#00C49A',
    paddingVertical: 16,
    borderRadius: 30,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 10,
  },
  sourceBtnText: { color: '#fff', fontSize: 16, fontWeight: '700' },
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
  docLinksTitle: { fontSize: 12, fontWeight: '700', color: '#00A582', marginLeft: 5 },
  docLinkRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#C8EDE3',
  },
  docLinkName: { fontSize: 13, fontWeight: '700', color: '#222', marginBottom: 2 },
  docLinkSource: { fontSize: 12, color: '#666' },
  docLinkHint: { fontSize: 11, color: '#999', marginTop: 2, lineHeight: 16 },
  docLinkBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#E6F9F4',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 8,
    marginLeft: 10,
    gap: 3,
  },
  docLinkBtnText: { color: '#00C49A', fontSize: 12, fontWeight: '700' },
});

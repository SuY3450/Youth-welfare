import { Ionicons } from '@expo/vector-icons';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { ActivityIndicator, ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

interface Policy {
  id: string;
  name: string;
  category: string;
  amount: string;
  source: string;
  source_url: string;
  deadline?: string;
  region?: string;
  sub_region?: string | null;
  eligible: boolean;
  fit_score: number;
  similarity: number;
  reasons: string[];
}

const KOREAN_REGIONS = new Set([
  '서울특별시', '부산광역시', '대구광역시', '인천광역시', '광주광역시',
  '대전광역시', '울산광역시', '세종특별자치시',
  '경기도', '강원도', '강원특별자치도', '충청북도', '충청남도',
  '전라북도', '전북특별자치도', '전라남도', '경상북도', '경상남도',
  '제주특별자치도',
]);

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

const formatDeadline = (deadline?: string) => {
  if (!deadline) return null;
  const parts = parseDeadlineDate(deadline);
  if (!parts) return { text: deadline, urgent: false, expired: false };
  const pretty = `${parts.y}-${parts.m.padStart(2, '0')}-${parts.d.padStart(2, '0')}`;
  const target = new Date(parseInt(parts.y), parseInt(parts.m) - 1, parseInt(parts.d));
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const diff = Math.ceil((target.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
  if (diff < 0) return { text: '마감됨', urgent: false, expired: true };
  if (diff === 0) return { text: '오늘 마감', urgent: true, expired: false };
  if (diff <= 30) return { text: `D-${diff}`, urgent: true, expired: false };
  return { text: `~ ${pretty}`, urgent: false, expired: false };
};

interface DocumentLink {
  doc_name: string;
  source: string;
  url: string | null;
  search_hint?: string;
  fee?: string;
}

interface LlmResult {
  name: string;
  priority: number;
  fit_score: string;
  amount: string;
  reason: string;
  document_links?: DocumentLink[];
}

interface ResultData {
  results?: LlmResult[];
  top_recommendation?: string;
  total_monthly?: string;
  summary?: string;
  eligible_policies?: Policy[];
}

export default function ResultScreen() {
  const router = useRouter();
  const { resultData } = useLocalSearchParams<{ resultData?: string }>();
  const [data, setData] = useState<ResultData | null>(null);

  useEffect(() => {
    if (resultData) {
      try {
        setData(JSON.parse(resultData));
      } catch (e) {
        console.error('결과 파싱 오류:', e);
      }
    }
  }, [resultData]);

  if (!data) {
    return (
      <SafeAreaView style={styles.wrap}>
        <ActivityIndicator size="large" color="#00C49A" style={{ flex: 1 }} />
      </SafeAreaView>
    );
  }

  const policies = data.eligible_policies || [];
  const llmReasons = new Map<string, string>();
  const llmDocLinks = new Map<string, DocumentLink[]>();
  (data.results || []).forEach((r) => {
    if (r.name && r.reason) llmReasons.set(r.name, r.reason);
    if (r.name && r.document_links?.length) llmDocLinks.set(r.name, r.document_links);
  });

  const goToDetail = (policy: Policy, rank: number) => {
    const docLinks = llmDocLinks.get(policy.name);
    router.push({
      pathname: '/policy-detail',
      params: {
        policy_id: policy.id || policy.name,
        rank: String(rank),
        fit_score: String(policy.fit_score),
        eligible: policy.eligible ? '1' : '0',
        reasons: JSON.stringify(policy.reasons || []),
        document_links: docLinks ? JSON.stringify(docLinks) : '',
      },
    });
  };

  return (
    <SafeAreaView style={styles.wrap} edges={['top']}>
      <ScrollView style={styles.container} contentContainerStyle={{ paddingBottom: 30 }} showsVerticalScrollIndicator={false}>
        <Text style={styles.pageTitle}>추천 결과</Text>

        <View style={styles.aiCard}>
          <View style={styles.aiCardHeader}>
            <View style={styles.dot} />
            <Text style={styles.aiCardHeaderText}>AI 분석 완료</Text>
          </View>
          {data.summary ? <Text style={styles.aiCardDesc}>{data.summary}</Text> : null}
          <View style={styles.aiCardBottom}>
            <Text style={styles.aiCardLabel}>예상 총 수혜 금액</Text>
            <Text style={styles.aiCardAmount}>{data.total_monthly || '분석 중'}</Text>
          </View>
        </View>

        <View style={styles.totalRow}>
          <Text style={styles.totalCount}>맞춤 정책 {policies.length}건</Text>
          <Text style={styles.totalHint}>탭하여 자세히 보기</Text>
        </View>

        {policies.map((item, index) => {
          const rank = index + 1;
          const friendlyReason = llmReasons.get(item.name);
          const deadline = formatDeadline(item.deadline);
          return (
            <TouchableOpacity
              key={`${item.name}-${index}`}
              style={styles.card}
              activeOpacity={0.85}
              onPress={() => goToDetail(item, rank)}
            >
              <View style={styles.cardTop}>
                <View style={styles.rankBadge}>
                  <Text style={styles.rankText}>{rank}순위</Text>
                </View>
                <View style={styles.fitBox}>
                  <Text style={styles.fitLabel}>적합도</Text>
                  <Text style={styles.fitValue}>{item.fit_score}%</Text>
                </View>
              </View>

              <Text style={styles.cardTitle} numberOfLines={2}>{item.name}</Text>
              <Text style={styles.cardSource} numberOfLines={1}>{item.source}</Text>

              <View style={styles.tagRow}>
                <View style={styles.tagGreen}>
                  <Text style={styles.tagGreenText}>{item.category}</Text>
                </View>
                {(() => {
                  const r = item.region?.trim();
                  const sub = item.sub_region?.trim();
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
                {deadline ? (
                  <View style={[styles.tagOrange, (deadline.expired || !deadline.urgent) && styles.tagGray]}>
                    <Ionicons name="time-outline" size={11} color={deadline.urgent ? '#FF8C00' : '#666'} style={{ marginRight: 3 }} />
                    <Text style={[styles.tagOrangeText, (deadline.expired || !deadline.urgent) && styles.tagGrayText]}>
                      {deadline.text}
                    </Text>
                  </View>
                ) : null}
              </View>

              <View style={styles.amountBox}>
                <Text style={styles.amountText}>{item.amount || '금액 정보 없음'}</Text>
              </View>

              {friendlyReason ? (
                <View style={styles.reasonBox}>
                  <View style={styles.reasonBoxHeader}>
                    <Ionicons name="bulb" size={13} color="#00A582" />
                    <Text style={styles.reasonBoxTitle}>추천 이유</Text>
                  </View>
                  <Text style={styles.reasonBoxText}>{friendlyReason}</Text>
                </View>
              ) : null}

              <View style={styles.detailHint}>
                <Text style={styles.detailHintText}>자세히 보기</Text>
                <Ionicons name="chevron-forward" size={14} color="#00C49A" />
              </View>
            </TouchableOpacity>
          );
        })}
      </ScrollView>

      <View style={styles.bottomTab}>
        <TouchableOpacity style={styles.tabItem}>
          <Ionicons name="home" size={24} color="#67B292" />
          <Text style={[styles.tabText, { color: '#67B292' }]}>홈</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.tabItem}>
          <Ionicons name="grid-outline" size={24} color="#999" />
          <Text style={styles.tabText}>일정</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.tabItem} onPress={() => router.push('/mypage')}>
          <Ionicons name="person-circle" size={24} color="#999" />
          <Text style={[styles.tabText, { color: '#999' }]}>마이</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: '#F7FDFB' },
  container: { flex: 1, paddingHorizontal: 20 },
  pageTitle: { fontSize: 26, fontWeight: '800', color: '#111', marginTop: 16, marginBottom: 16 },
  aiCard: { backgroundColor: '#00C49A', borderRadius: 16, padding: 18, marginBottom: 22 },
  aiCardHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 10 },
  dot: { width: 8, height: 8, borderRadius: 4, backgroundColor: '#fff', marginRight: 6 },
  aiCardHeaderText: { color: '#fff', fontWeight: '700', fontSize: 14 },
  aiCardDesc: { color: '#fff', fontSize: 14, lineHeight: 22, marginBottom: 14 },
  aiCardBottom: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', borderTopWidth: 1, borderTopColor: 'rgba(255,255,255,0.25)', paddingTop: 12 },
  aiCardLabel: { color: '#d0f5ec', fontSize: 12, fontWeight: '600' },
  aiCardAmount: { color: '#fff', fontWeight: '800', fontSize: 18 },
  totalRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 },
  totalCount: { fontSize: 14, color: '#222', fontWeight: '700' },
  totalHint: { fontSize: 12, color: '#999' },
  card: { backgroundColor: '#fff', borderRadius: 16, padding: 18, marginBottom: 14, shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 8, elevation: 2 },
  cardTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 },
  rankBadge: { backgroundColor: '#00C49A', paddingHorizontal: 12, paddingVertical: 4, borderRadius: 20 },
  rankText: { color: '#fff', fontWeight: '800', fontSize: 12 },
  fitBox: { flexDirection: 'row', alignItems: 'baseline' },
  fitLabel: { fontSize: 11, color: '#888', marginRight: 4, fontWeight: '600' },
  fitValue: { fontSize: 16, color: '#00C49A', fontWeight: '800' },
  cardTitle: { fontSize: 17, fontWeight: '800', color: '#111', marginBottom: 4, lineHeight: 24 },
  cardSource: { fontSize: 12, color: '#888', marginBottom: 10 },
  tagRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginBottom: 12, alignItems: 'center' },
  tagGreen: { backgroundColor: '#e6f9f4', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 20 },
  tagGreenText: { color: '#00C49A', fontSize: 12, fontWeight: '700' },
  tagOrange: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#FFF3E0', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 20 },
  tagOrangeText: { color: '#FF8C00', fontSize: 12, fontWeight: '700' },
  tagGray: { backgroundColor: '#F0F2F1', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 20 },
  tagGrayText: { color: '#666', fontSize: 12, fontWeight: '600' },
  amountBox: { backgroundColor: '#f0faf5', borderRadius: 10, paddingVertical: 12, paddingHorizontal: 14, marginBottom: 10 },
  amountText: { color: '#00C49A', fontWeight: '800', fontSize: 18 },
  reasonBox: { backgroundColor: '#F0FBF7', borderLeftWidth: 3, borderLeftColor: '#00C49A', borderRadius: 8, paddingVertical: 10, paddingHorizontal: 12, marginTop: 4, marginBottom: 10 },
  reasonBoxHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 6 },
  reasonBoxTitle: { fontSize: 12, fontWeight: '700', color: '#00A582', marginLeft: 4, letterSpacing: 0.2 },
  reasonBoxText: { fontSize: 13.5, color: '#333', lineHeight: 21 },
  detailHint: { flexDirection: 'row', justifyContent: 'flex-end', alignItems: 'center', marginTop: 4 },
  detailHintText: { color: '#00C49A', fontSize: 13, fontWeight: '700', marginRight: 2 },
  bottomTab: { flexDirection: 'row', height: 80, backgroundColor: '#FFF', borderTopWidth: 1, borderTopColor: '#EEE', paddingBottom: 20 },
  tabItem: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  tabText: { fontSize: 12, marginTop: 4, color: '#999', fontWeight: '600' },
});
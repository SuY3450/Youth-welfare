import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';

// 복지 카드 데이터
const welfareList = [
  {
    id: 1,
    rank: '1순위',
    title: '청년 월세 한시 특별지원',
    org: '국토교통부 · 전국',
    tags: [
      { label: '주거', type: 'green' },
      { label: '자격 충족', type: 'green' },
      { label: '마감 D-7', type: 'orange' },
    ],
    amount: '월 20만원',
    period: '× 12개월',
    warning: null,
  },
  {
    id: 2,
    rank: '2순위',
    title: '청년도약계좌',
    org: '금융위원회 · 전국',
    tags: [
      { label: '금융', type: 'green' },
      { label: '자격 충족', type: 'green' },
    ],
    amount: '최대 5,000만원',
    period: '5년 만기',
    warning: '청년희망적금과 중복 가입 불가 → 도약계좌가 유리',
  },
  {
    id: 3,
    rank: '3순위',
    title: '청년내일저축계좌',
    org: '보건복지부 · 전국',
    tags: [
      { label: '금융', type: 'green' },
      { label: '자격 충족', type: 'green' },
    ],
    amount: '최대 1,440만원',
    period: '3년 만기',
    warning: null,
  },
];

export default function ResultScreen() {
  const router = useRouter();

  return (
    <SafeAreaView style={styles.wrap} edges={['top']}>
      <ScrollView style={styles.container} showsVerticalScrollIndicator={false}>

        {/* 제목 */}
        <Text style={styles.pageTitle}>추천 결과</Text>

        {/* AI 분석 완료 카드 */}
        <View style={styles.aiCard}>
          <View style={styles.aiCardHeader}>
            <View style={styles.dot} />
            <Text style={styles.aiCardHeaderText}>AI 분석 완료</Text>
          </View>
          <Text style={styles.aiCardDesc}>
            주거·취업·금융 3개 분야에서 12개 사업이 매칭됐어요.{'\n'}
            중복 불가 항목을 제외한 최적 조합을 추천드려요.
          </Text>
          <View style={styles.aiCardBottom}>
            <Text style={styles.aiCardLabel}>예상 총 수혜 금액</Text>
            <Text style={styles.aiCardAmount}>연간 최대 780만원</Text>
          </View>
        </View>

        {/* 총 건수 */}
        <Text style={styles.totalCount}>총 12건</Text>

        {/* 복지 카드 목록 */}
        {welfareList.map((item) => (
          <View key={item.id} style={styles.card}>

            {/* 카드 헤더 */}
            <View style={styles.cardHeader}>
              <View style={styles.cardHeaderLeft}>
                <Text style={styles.cardTitle}>{item.title}</Text>
                <Text style={styles.cardSub}>{item.org}</Text>
                {/* 태그 */}
                <View style={styles.tagRow}>
                  {item.tags.map((tag, index) => (
                    <View
                      key={index}
                      style={[styles.tag, tag.type === 'orange' ? styles.tagOrange : styles.tagGreen]}
                    >
                      <Text style={tag.type === 'orange' ? styles.tagOrangeText : styles.tagGreenText}>
                        {tag.label}
                      </Text>
                    </View>
                  ))}
                </View>
              </View>
              {/* 순위 뱃지 */}
              <View style={styles.rankBadge}>
                <Text style={styles.rankText}>{item.rank}</Text>
              </View>
            </View>

            {/* 금액 박스 */}
            <View style={styles.amountBox}>
              <Text style={styles.amountText}>{item.amount}</Text>
              <Text style={styles.amountSub}>{item.period}</Text>
            </View>

            {/* 경고 메시지 */}
            {item.warning && (
              <View style={styles.warningBox}>
                <Text style={styles.warningText}>⚠ {item.warning}</Text>
              </View>
            )}

          </View>
        ))}

        <View style={{ height: 20 }} />
      </ScrollView>

      {/* 하단 탭바 */}
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

  // 제목
  pageTitle: { fontSize: 26, fontWeight: '800', color: '#111', marginTop: 16, marginBottom: 16 },

  // AI 카드
  aiCard: { backgroundColor: '#00C49A', borderRadius: 16, padding: 18, marginBottom: 20 },
  aiCardHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 10 },
  dot: { width: 8, height: 8, borderRadius: 4, backgroundColor: '#fff', marginRight: 6 },
  aiCardHeaderText: { color: '#fff', fontWeight: 'bold', fontSize: 14 },
  aiCardDesc: { color: '#fff', fontSize: 14, lineHeight: 22, marginBottom: 14 },
  aiCardBottom: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  aiCardLabel: { color: '#d0f5ec', fontSize: 12 },
  aiCardAmount: { color: '#fff', fontWeight: 'bold', fontSize: 18 },

  // 총 건수
  totalCount: { fontSize: 14, color: '#555', marginBottom: 14, fontWeight: '600' },

  // 카드
  card: { backgroundColor: '#fff', borderRadius: 16, padding: 16, marginBottom: 16, shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 8, elevation: 2 },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 14 },
  cardHeaderLeft: { flex: 1, marginRight: 10 },
  cardTitle: { fontSize: 16, fontWeight: 'bold', color: '#111', marginBottom: 4 },
  cardSub: { fontSize: 12, color: '#888', marginBottom: 8 },

  // 태그
  tagRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  tag: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 20 },
  tagGreen: { backgroundColor: '#e6f9f4' },
  tagGreenText: { color: '#00C49A', fontSize: 12, fontWeight: '600' },
  tagOrange: { backgroundColor: '#fff3e0' },
  tagOrangeText: { color: '#FF8C00', fontSize: 12, fontWeight: '600' },

  // 순위 뱃지
  rankBadge: { backgroundColor: '#00C49A', borderRadius: 20, paddingHorizontal: 12, paddingVertical: 5 },
  rankText: { color: '#fff', fontSize: 12, fontWeight: 'bold' },

  // 금액 박스
  amountBox: { backgroundColor: '#f0faf5', borderRadius: 10, padding: 14, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  amountText: { color: '#00C49A', fontWeight: 'bold', fontSize: 20 },
  amountSub: { color: '#888', fontSize: 13 },

  // 경고 박스
  warningBox: { backgroundColor: '#fff8e1', borderRadius: 10, padding: 12, marginTop: 10 },
  warningText: { color: '#cc7700', fontSize: 12, lineHeight: 18 },

  // 하단 탭바
  bottomTab: { flexDirection: 'row', height: 80, backgroundColor: '#FFF', borderTopWidth: 1, borderTopColor: '#EEE', paddingBottom: 20 },
  tabItem: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  tabText: { fontSize: 12, marginTop: 4, color: '#999', fontWeight: '600' },
});

import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { ActivityIndicator, ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { API_URL } from '../constants/api';

type TagType = 'green' | 'orange' | 'red';

interface WelfareTag {
  label: string;
  type: TagType;
}

interface WelfareItem {
  id: number;
  rank: string;
  title: string;
  org: string;
  tags: WelfareTag[];
  amount: string;
  period: string;
  warning: string | null;
}

export default function ResultScreen() {
  const router = useRouter();
  const [welfareList, setWelfareList] = useState<WelfareItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    fetch(`${API_URL}/result`)
      .then((res) => res.json())
      .then((data: { results: WelfareItem[] }) => {
        setWelfareList(data.results);
        setLoading(false);
      })
      .catch((err) => {
        console.error('결과 불러오기 실패:', err);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <SafeAreaView style={styles.wrap}>
        <ActivityIndicator size="large" color="#00C49A" style={{ flex: 1 }} />
      </SafeAreaView>
    );
  }

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
          <View style={styles.aiCardBody}>
            <View style={styles.aiCardBodyLeft}>
              <Text style={styles.aiCardMainText}>주거·취업·금융 12개 매칭</Text>
              <Text style={styles.aiCardSubText}>중복 불가 항목 자동 제외</Text>
            </View>
            <View style={styles.aiCardBodyRight}>
              <Text style={styles.aiCardLabel}>예상 총 수혜</Text>
              <Text style={styles.aiCardAmount}>연 780만원</Text>
            </View>
          </View>
        </View>

        {/* 총 건수 */}
        <Text style={styles.totalCount}>총 {welfareList.length}건</Text>

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
                  {item.tags.map((tag, index) => {
                    let tagStyle = styles.tagGreen;
                    let tagTextStyle = styles.tagGreenText;
                    if (tag.type === 'orange') {
                      tagStyle = styles.tagOrange;
                      tagTextStyle = styles.tagOrangeText;
                    } else if (tag.type === 'red') {
                      tagStyle = styles.tagRed;
                      tagTextStyle = styles.tagRedText;
                    }
                    return (
                      <View key={index} style={[styles.tag, tagStyle]}>
                        <Text style={tagTextStyle}>{tag.label}</Text>
                      </View>
                    );
                  })}
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
              {item.period ? <Text style={styles.amountSub}>{item.period}</Text> : null}

              {/* 경고 메시지 (금액 박스 안쪽) */}
              {item.warning && (
                <View style={styles.warningBox}>
                  <Text style={styles.warningText}>⚠ {item.warning}</Text>
                </View>
              )}
            </View>

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
          <Ionicons name="person-circle-outline" size={24} color="#999" />
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
  aiCardHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 14 },
  dot: { width: 8, height: 8, borderRadius: 4, backgroundColor: '#fff', marginRight: 6 },
  aiCardHeaderText: { color: '#fff', fontWeight: 'bold', fontSize: 14 },
  aiCardBody: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-end' },
  aiCardBodyLeft: { flex: 1 },
  aiCardBodyRight: { alignItems: 'flex-end' },
  aiCardMainText: { color: '#fff', fontSize: 16, fontWeight: 'bold', marginBottom: 4 },
  aiCardSubText: { color: '#d0f5ec', fontSize: 12 },
  aiCardLabel: { color: '#d0f5ec', fontSize: 12, marginBottom: 4 },
  aiCardAmount: { color: '#fff', fontWeight: 'bold', fontSize: 20 },

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
  tagRed: { backgroundColor: '#FFE5E5' },
  tagRedText: { color: '#E53935', fontSize: 12, fontWeight: '600' },

  // 순위 뱃지
  rankBadge: { backgroundColor: '#00C49A', borderRadius: 20, paddingHorizontal: 12, paddingVertical: 5 },
  rankText: { color: '#fff', fontSize: 12, fontWeight: 'bold' },

  // 금액 박스
  amountBox: { backgroundColor: '#E8F8F0', borderRadius: 10, padding: 14, flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center' },
  amountText: { color: '#111', fontWeight: 'bold', fontSize: 20 },
  amountSub: { color: '#888', fontSize: 13 },

  // 경고 박스
  warningBox: { backgroundColor: '#FFF8E1', borderRadius: 10, padding: 10, marginTop: 12, width: '100%' },
  warningText: { color: '#B07A00', fontSize: 12, lineHeight: 18 },

  // 하단 탭바
  bottomTab: { flexDirection: 'row', height: 80, backgroundColor: '#FFF', borderTopWidth: 1, borderTopColor: '#EEE', paddingBottom: 20 },
  tabItem: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  tabText: { fontSize: 12, marginTop: 4, color: '#999', fontWeight: '600' },
});

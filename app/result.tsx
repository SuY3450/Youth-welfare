import { Ionicons } from '@expo/vector-icons';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { ActivityIndicator, ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

export default function ResultScreen() {
  const router = useRouter();
  const { resultData } = useLocalSearchParams();
  const [data, setData] = useState(null);

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

  const results = data.eligible_policies || [];

  return (
    <SafeAreaView style={styles.wrap} edges={['top']}>
      <ScrollView style={styles.container} showsVerticalScrollIndicator={false}>

        <Text style={styles.pageTitle}>추천 결과</Text>

        {/* AI 분석 완료 카드 */}
        <View style={styles.aiCard}>
          <View style={styles.aiCardHeader}>
            <View style={styles.dot} />
            <Text style={styles.aiCardHeaderText}>AI 분석 완료</Text>
          </View>
          <Text style={styles.aiCardDesc}>{data.summary}</Text>
          <View style={styles.aiCardBottom}>
            <Text style={styles.aiCardLabel}>예상 총 수혜 금액</Text>
            <Text style={styles.aiCardAmount}>{data.total_monthly || '분석 중'}</Text>
          </View>
        </View>

        <Text style={styles.totalCount}>총 {results.length}건</Text>

        {results.map((item, index) => (
          <View key={index} style={styles.card}>
            <View style={styles.cardHeader}>
              <View style={styles.cardHeaderLeft}>
                <Text style={styles.cardTitle}>{item.name}</Text>
                <Text style={styles.cardSub}>{item.source}</Text>
                <View style={styles.tagRow}>
                  <View style={styles.tagGreen}>
                    <Text style={styles.tagGreenText}>{item.category}</Text>
                  </View>
                  <View style={styles.tagGreen}>
                    <Text style={styles.tagGreenText}>자격 충족</Text>
                  </View>
                  <View style={styles.tagGreen}>
                    <Text style={styles.tagGreenText}>적합도 {item.fit_score}%</Text>
                  </View>
                </View>
              </View>
              <View style={styles.rankBadge}>
                <Text style={styles.rankText}>{index + 1}순위</Text>
              </View>
            </View>

            <View style={styles.amountBox}>
              <Text style={styles.amountText}>{item.amount || '금액 정보 없음'}</Text>
            </View>

            {item.reasons && (
              <View style={styles.warningBox}>
                <Text style={styles.warningText}>{item.reasons.join(' ')}</Text>
              </View>
            )}

            {item.source_url ? (
              <TouchableOpacity style={styles.linkButton}>
                <Text style={styles.linkButtonText}>자세히 보기 →</Text>
              </TouchableOpacity>
            ) : null}
          </View>
        ))}

        <View style={{ height: 20 }} />
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
  aiCard: { backgroundColor: '#00C49A', borderRadius: 16, padding: 18, marginBottom: 20 },
  aiCardHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 10 },
  dot: { width: 8, height: 8, borderRadius: 4, backgroundColor: '#fff', marginRight: 6 },
  aiCardHeaderText: { color: '#fff', fontWeight: 'bold', fontSize: 14 },
  aiCardDesc: { color: '#fff', fontSize: 14, lineHeight: 22, marginBottom: 14 },
  aiCardBottom: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  aiCardLabel: { color: '#d0f5ec', fontSize: 12 },
  aiCardAmount: { color: '#fff', fontWeight: 'bold', fontSize: 18 },
  totalCount: { fontSize: 14, color: '#555', marginBottom: 14, fontWeight: '600' },
  card: { backgroundColor: '#fff', borderRadius: 16, padding: 16, marginBottom: 16, shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 8, elevation: 2 },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 14 },
  cardHeaderLeft: { flex: 1, marginRight: 10 },
  cardTitle: { fontSize: 16, fontWeight: 'bold', color: '#111', marginBottom: 4 },
  cardSub: { fontSize: 12, color: '#888', marginBottom: 8 },
  tagRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  tag: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 20 },
  tagGreen: { backgroundColor: '#e6f9f4', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 20 },
  tagGreenText: { color: '#00C49A', fontSize: 12, fontWeight: '600' },
  tagOrange: { backgroundColor: '#fff3e0', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 20 },
  tagOrangeText: { color: '#FF8C00', fontSize: 12, fontWeight: '600' },
  rankBadge: { backgroundColor: '#00C49A', borderRadius: 20, paddingHorizontal: 12, paddingVertical: 5 },
  rankText: { color: '#fff', fontSize: 12, fontWeight: 'bold' },
  amountBox: { backgroundColor: '#f0faf5', borderRadius: 10, padding: 14, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  amountText: { color: '#00C49A', fontWeight: 'bold', fontSize: 20 },
  amountSub: { color: '#888', fontSize: 13 },
  warningBox: { backgroundColor: '#f0faf5', borderRadius: 10, padding: 12, marginTop: 10 },
  warningText: { color: '#00C49A', fontSize: 12, lineHeight: 18 },
  linkButton: { marginTop: 10, alignItems: 'flex-end' },
  linkButtonText: { color: '#00C49A', fontSize: 13, fontWeight: '600' },
  bottomTab: { flexDirection: 'row', height: 80, backgroundColor: '#FFF', borderTopWidth: 1, borderTopColor: '#EEE', paddingBottom: 20 },
  tabItem: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  tabText: { fontSize: 12, marginTop: 4, color: '#999', fontWeight: '600' },
});
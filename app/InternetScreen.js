import { useRouter } from 'expo-router';
import { SafeAreaView, ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';

const interestData = [
  { id: 'central', label: '중앙부처', emoji: '🤝' },
  { id: 'housing', label: '주거', emoji: '🏠' },
  { id: 'finance', label: '금융', emoji: '💰' },
  { id: 'job', label: '취업', emoji: '💼' },
  { id: 'edu', label: '교육', emoji: '📚' },
  { id: 'startup', label: '창업', emoji: '🚀' },
];

export default function InternetScreen() {
  const router = useRouter();

  const handleStartMatching = () => {
    router.push('/loading');
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.header}>
          <Text style={styles.headerTitle}>관심 분야</Text>
          <Text style={styles.stepText}>2 / 2</Text>
        </View>
        <View style={styles.progressBarBg}><View style={styles.progressBarFill} /></View>

        <Text style={styles.subTitle}>받고 싶은 지원 분야를 선택해주세요 (복수 선택 가능)</Text>

        <View style={styles.grid}>
          {interestData.map((item) => {
            const isSelected = item.id === 'housing'; 
            return (
              <TouchableOpacity 
                key={item.id} 
                style={[styles.card, isSelected && styles.activeCard]} 
                onPress={() => {}} 
                activeOpacity={isSelected ? 0.7 : 1}
              >
                <Text style={styles.emoji}>{item.emoji}</Text>
                <Text style={[styles.cardLabel, isSelected && styles.activeCardLabel]}>{item.label}</Text>
              </TouchableOpacity>
            );
          })}
        </View>
      </ScrollView>

      {/* 하단 고정 영역 (핀 요약 박스 + 버튼) */}
      <View style={styles.bottomFixedArea}>
        <View style={styles.summaryBox}>
          <Text style={styles.summaryText}>📌 선택한 분야: 주거</Text>
        </View>

        <TouchableOpacity style={styles.nextButton} onPress={handleStartMatching}>
          <Text style={styles.nextButtonText}>AI 매칭 시작 →</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F7FDFB' },
  scrollContent: { padding: 25, paddingTop: 40, paddingBottom: 20 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 10 },
  headerTitle: { fontSize: 26, fontWeight: '800', color: '#111' },
  stepText: { fontSize: 16, color: '#999', fontWeight: '600' },
  progressBarBg: { height: 5, backgroundColor: '#E0E0E0', borderRadius: 10, marginBottom: 20 },
  progressBarFill: { width: '100%', height: '100%', backgroundColor: '#67B292', borderRadius: 10 },
  subTitle: { fontSize: 15, color: '#666', marginBottom: 30, fontWeight: '500' },
  grid: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between' },
  card: { width: '48%', backgroundColor: '#FFF', aspectRatio: 1, borderRadius: 20, borderWidth: 1, borderColor: '#EEE', justifyContent: 'center', alignItems: 'center', marginBottom: 15, elevation: 2 },
  activeCard: { backgroundColor: '#E8F5EF', borderColor: '#67B292', borderWidth: 2 },
  emoji: { fontSize: 32, marginBottom: 10 },
  cardLabel: { fontSize: 16, fontWeight: '700', color: '#333' },
  activeCardLabel: { color: '#67B292' },
  bottomFixedArea: { paddingHorizontal: 25, paddingBottom: 30, backgroundColor: '#F7FDFB' },
  summaryBox: { backgroundColor: '#EBF7F0', padding: 18, borderRadius: 15, marginBottom: 20, flexDirection: 'row', alignItems: 'center' },
  summaryText: { color: '#67B292', fontSize: 15, fontWeight: '700' },
  nextButton: { backgroundColor: '#67B292', paddingVertical: 18, borderRadius: 35, alignItems: 'center' },
  nextButtonText: { color: '#FFF', fontSize: 18, fontWeight: '800' },
});
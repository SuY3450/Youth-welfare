import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import React from 'react';
import { SafeAreaView, ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';

export default function HomeScreen() {
  const router = useRouter();

  const handleStart = () => {
    router.push('/login/login1');
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar style="dark" />
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <Text style={styles.topLabel}>AI 맞춤 혜택 추천</Text>

        <View style={styles.titleArea}>
          <Text style={styles.mainTitle}>AI가 분석한</Text>
          <View style={styles.titleRow}>
            <Text style={styles.mainTitle}>나만의 </Text>
            <View style={styles.highlightWrapper}>
              <View style={styles.highlightBg} />
              <Text style={styles.mainTitle}>청년 혜택</Text>
            </View>
          </View>
          <Text style={styles.subTitle}>
            기본 정보만 입력하면{"\n"}AI가 내 조건에 맞는 혜택을 찾아드려요
          </Text>
        </View>

        <View style={styles.contentArea}>
          <View style={styles.guideCard}>
            <View style={styles.cardIconBackground}>
              <Ionicons name="checkmark" size={22} color="#00C49A" />
            </View>
            <View style={styles.cardTextContent}>
              <Text style={styles.cardTitle}>자동 자격 매칭</Text>
              <Text style={styles.cardSubText}>내 조건에 맞는 것만 필터링</Text>
            </View>
          </View>

          <View style={styles.guideCard}>
            <View style={styles.cardIconBackground}>
              <Ionicons name="star" size={20} color="#00C49A" />
            </View>
            <View style={styles.cardTextContent}>
              <Text style={styles.cardTitle}>AI 최적 순위 추천</Text>
              <Text style={styles.cardSubText}>중복 불가 고려한 최적 조합</Text>
            </View>
          </View>

          <View style={styles.guideCard}>
            <View style={styles.cardIconBackground}>
              <Ionicons name="clipboard-outline" size={20} color="#00C49A" />
            </View>
            <View style={styles.cardTextContent}>
              <Text style={styles.cardTitle}>신청 서류 체크리스트</Text>
              <Text style={styles.cardSubText}>필요한 서류를 한눈에 정리</Text>
            </View>
          </View>
        </View>

        <TouchableOpacity style={styles.startButton} onPress={handleStart}>
          <Text style={styles.buttonText}>시작하기</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F7FDFB' },
  scrollContent: { padding: 28, paddingTop: 60, paddingBottom: 40 },
  topLabel: { fontSize: 13, color: '#046451', fontWeight: '600', marginBottom: 24 },
  titleArea: { alignItems: 'flex-start', marginBottom: 36 },
  mainTitle: { fontSize: 36, fontWeight: '900', textAlign: 'left', color: '#111', lineHeight: 48 },
  titleRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 16 },
  highlightWrapper: { position: 'relative' },
  highlightBg: { position: 'absolute', left: 0, right: 0, bottom: 4, height: 14, backgroundColor: '#A8E6C9' },
  subTitle: { fontSize: 14, color: '#666', textAlign: 'left', lineHeight: 17 },
  contentArea: { width: '100%', marginBottom: 40 },
  guideCard: { flexDirection: 'row', backgroundColor: '#FFFFFF', padding: 18, borderRadius: 16, marginBottom: 14, alignItems: 'center', borderWidth: 1, borderColor: '#00B894' },
  cardIconBackground: { width: 44, height: 44, borderRadius: 12, alignItems: 'center', justifyContent: 'center', marginRight: 14, backgroundColor: '#E8F8F0' },
  cardTextContent: { flex: 1 },
  cardTitle: { fontSize: 16, fontWeight: '700', color: '#222', marginBottom: 4 },
  cardSubText: { fontSize: 13, color: '#888' },
  startButton: { backgroundColor: '#1DB88E', width: '100%', paddingVertical: 18, borderRadius: 14, alignItems: 'center', marginTop: 20 },
  buttonText: { color: '#FFF', fontSize: 17, fontWeight: 'bold' },
});

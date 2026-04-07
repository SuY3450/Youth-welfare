import { useRouter } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import React from 'react';
import { Alert, SafeAreaView, ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';

export default function HomeScreen() {
  const router = useRouter();

  const handleStart = () => {
    Alert.alert(
      "알림",
      "기본 정보를 입력할까요?",
      [
        { text: "취소", style: "cancel" },
        { text: "확인", onPress: () => router.push('/input') } // input.tsx로 이동
      ]
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar style="dark" />
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.logoContainer}>
          <View style={styles.iconBackground}>
            <Text style={{ fontSize: 40 }}>🎯</Text>
          </View>
        </View>

        <View style={styles.titleArea}>
          <Text style={styles.mainTitle}>나에게 딱 맞는{"\n"}청년 지원사업</Text>
          <Text style={styles.subTitle}>
            기본 정보만 입력하면{"\n"}AI가 받을 수 있는 지원사업을 찾아드려요
          </Text>
        </View>

        <View style={styles.contentArea}>
          <View style={styles.guideCard}>
            <View style={[styles.cardIconBackground, { backgroundColor: '#E8F5E9' }]}>
              <Text style={{ fontSize: 20 }}>✔️</Text>
            </View>
            <View style={styles.cardTextContent}>
              <Text style={styles.cardTitle}>자동 자격 매칭</Text>
              <Text style={styles.cardSubText}>내 조건에 맞는 것만 필터링</Text>
            </View>
          </View>

          <View style={styles.guideCard}>
            <View style={[styles.cardIconBackground, { backgroundColor: '#FFFDE7' }]}>
              <Text style={{ fontSize: 20 }}>⭐</Text>
            </View>
            <View style={styles.cardTextContent}>
              <Text style={styles.cardTitle}>AI 최적 순위 추천</Text>
              <Text style={styles.cardSubText}>중복 불가 고려한 최적 조합</Text>
            </View>
          </View>

          <View style={styles.guideCard}>
            <View style={[styles.cardIconBackground, { backgroundColor: '#EFEBE9' }]}>
              <Text style={{ fontSize: 20 }}>📋</Text>
            </View>
            <View style={styles.cardTextContent}>
              <Text style={styles.cardTitle}>신청 서류 체크리스트</Text>
              <Text style={styles.cardSubText}>필요한 서류를 한눈에 정리</Text>
            </View>
          </View>
        </View>

        <TouchableOpacity style={styles.startButton} onPress={handleStart}>
          <Text style={styles.buttonText}>시작하기 →</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F7FDFB' },
  scrollContent: { alignItems: 'center', padding: 25, paddingTop: 60 },
  logoContainer: { marginBottom: 30 },
  iconBackground: { backgroundColor: '#82C0A5', width: 90, height: 90, borderRadius: 25, alignItems: 'center', justifyContent: 'center' },
  titleArea: { alignItems: 'center', marginBottom: 40 },
  mainTitle: { fontSize: 26, fontWeight: '800', textAlign: 'center', color: '#111', lineHeight: 36, marginBottom: 12 },
  subTitle: { fontSize: 15, color: '#666', textAlign: 'center', lineHeight: 22 },
  contentArea: { width: '100%', marginBottom: 50, paddingHorizontal: 10 },
  guideCard: { flexDirection: 'row', backgroundColor: '#FFFFFF', padding: 18, borderRadius: 20, marginBottom: 15, alignItems: 'center', borderWidth: 1, borderColor: '#EEEEEE' },
  cardIconBackground: { width: 45, height: 45, borderRadius: 12, alignItems: 'center', justifyContent: 'center', marginRight: 15 },
  cardTextContent: { flex: 1 },
  cardTitle: { fontSize: 16, fontWeight: '700', color: '#222', marginBottom: 4 },
  cardSubText: { fontSize: 13, color: '#777' },
  startButton: { backgroundColor: '#67B292', width: '100%', paddingVertical: 18, borderRadius: 30, alignItems: 'center' },
  buttonText: { color: '#FFF', fontSize: 18, fontWeight: 'bold' },
});
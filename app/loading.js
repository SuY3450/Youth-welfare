import { Feather, Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { Animated, Easing, SafeAreaView, StyleSheet, Text, View } from 'react-native';

export default function LoadingScreen() {
  const router = useRouter();

  // 체크리스트 상태 (나중에 실제 로직과 연결 가능)
  const [steps, setSteps] = useState([
    { id: 1, text: '정책 데이터베이스 검색 중...', completed: false },
    { id: 2, text: '자격 조건 매칭 중...', completed: false },
    { id: 3, text: '중복 수혜 분석 중...', completed: false },
    { id: 4, text: '최적 조합 계산 중...', completed: false },
  ]);

  // 중앙 원 애니메이션 (빙글빙글 도는 효과)
  const spinValue = new Animated.Value(0);

  useEffect(() => {
    // 스피너 애니메이션
    Animated.loop(
      Animated.timing(spinValue, {
        toValue: 1,
        duration: 2000,
        easing: Easing.linear,
        useNativeDriver: true,
      })
    ).start();

    // 체크리스트 순서대로 완료 표시
    const timers = [
      setTimeout(() => setSteps(s => s.map((item, i) => i === 0 ? { ...item, completed: true } : item)), 600),
      setTimeout(() => setSteps(s => s.map((item, i) => i === 1 ? { ...item, completed: true } : item)), 1200),
      setTimeout(() => setSteps(s => s.map((item, i) => i === 2 ? { ...item, completed: true } : item)), 1800),
      setTimeout(() => setSteps(s => s.map((item, i) => i === 3 ? { ...item, completed: true } : item)), 2400),
      // 모든 분석 완료 후 결과 화면으로 이동
      setTimeout(() => router.push('/result'), 3200),
    ];

    return () => timers.forEach(clearTimeout);
  }, []);

  const spin = spinValue.interpolate({
    inputRange: [0, 1],
    outputRange: ['0deg', '360deg'],
  });

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        {/* 중앙 로딩 애니메이션 부분 */}
        <View style={styles.loaderContainer}>
          <Animated.View style={[styles.outerCircle, { transform: [{ rotate: spin }] }]}>
            <View style={styles.innerCircle} />
          </Animated.View>
          {/* 중앙의 검은 원 (이미지처럼 표현) */}
          <View style={styles.centerDot} />
        </View>

        <Text style={styles.title}>AI가 분석하고 있어요</Text>

        {/* 체크리스트 섹션 */}
        <View style={styles.listContainer}>
          {steps.map((step) => (
            <View key={step.id} style={styles.listItem}>
              <Feather 
                name="check" 
                size={18} 
                color={step.completed ? "#67B292" : "#DDD"} 
                style={styles.checkIcon} 
              />
              <Text style={styles.listText}>{step.text}</Text>
            </View>
          ))}
        </View>
      </View>

      {/* 하단 탭바 (더미) */}
      <View style={styles.bottomTab}>
        <View style={styles.tabItem}>
          <Ionicons name="home-outline" size={24} color="#67B292" />
          <Text style={[styles.tabText, { color: '#67B292' }]}>홈</Text>
        </View>
        <View style={styles.tabItem}>
          <Ionicons name="grid-outline" size={24} color="#999" />
          <Text style={styles.tabText}>일정</Text>
        </View>
        <View style={styles.tabItem}>
          <Ionicons name="ellipse-outline" size={24} color="#999" />
          <Text style={styles.tabText}>마이</Text>
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F7FDFB' },
  content: { flex: 1, justifyContent: 'center', alignItems: 'center', paddingBottom: 100 },
  
  // 로더 스타일
  loaderContainer: { justifyContent: 'center', alignItems: 'center', marginBottom: 40 },
  outerCircle: {
    width: 120,
    height: 120,
    borderRadius: 60,
    borderWidth: 4,
    borderColor: '#67B292',
    borderTopColor: 'transparent', // 회전하는 느낌을 위해 한쪽을 투명하게
    justifyContent: 'center',
    alignItems: 'center',
  },
  centerDot: {
    position: 'absolute',
    width: 90,
    height: 90,
    borderRadius: 45,
    backgroundColor: '#111', // 이미지 속 검은 원
  },

  title: { fontSize: 24, fontWeight: '800', color: '#111', marginBottom: 35 },

  // 리스트 스타일
  listContainer: { alignItems: 'flex-start' },
  listItem: { flexDirection: 'row', alignItems: 'center', marginBottom: 15 },
  checkIcon: { marginRight: 10 },
  listText: { fontSize: 16, color: '#67B292', fontWeight: '500' },

  // 하단 탭바 스타일
  bottomTab: {
    flexDirection: 'row',
    height: 80,
    backgroundColor: '#FFF',
    borderTopWidth: 1,
    borderTopColor: '#EEE',
    paddingBottom: 20,
  },
  tabItem: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  tabText: { fontSize: 12, marginTop: 4, color: '#999', fontWeight: '600' },
});
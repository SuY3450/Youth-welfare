import { Feather } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import { Animated, Easing, SafeAreaView, StyleSheet, Text, View } from 'react-native';

interface Step {
  id: number;
  text: string;
  completed: boolean;
}

export default function LoadingScreen() {
  const router = useRouter();

  const [steps, setSteps] = useState<Step[]>([
    { id: 1, text: '정책 데이터베이스 검색 중...', completed: false },
    { id: 2, text: '자격 조건 매칭 중...', completed: false },
    { id: 3, text: '중복 수혜 분석 중...', completed: false },
    { id: 4, text: '최적 조합 계산 중...', completed: false },
  ]);

  const spinValue = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.loop(
      Animated.timing(spinValue, {
        toValue: 1,
        duration: 2000,
        easing: Easing.linear,
        useNativeDriver: true,
      })
    ).start();

    const timers: ReturnType<typeof setTimeout>[] = [
      setTimeout(() => setSteps((s) => s.map((item, i) => (i === 0 ? { ...item, completed: true } : item))), 600),
      setTimeout(() => setSteps((s) => s.map((item, i) => (i === 1 ? { ...item, completed: true } : item))), 1200),
      setTimeout(() => setSteps((s) => s.map((item, i) => (i === 2 ? { ...item, completed: true } : item))), 1800),
      setTimeout(() => setSteps((s) => s.map((item, i) => (i === 3 ? { ...item, completed: true } : item))), 2400),
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
          {/* 중앙의 검은 원 */}
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
                color={step.completed ? '#67B292' : '#DDD'}
                style={styles.checkIcon}
              />
              <Text style={styles.listText}>{step.text}</Text>
            </View>
          ))}
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F7FDFB' },
  content: { flex: 1, justifyContent: 'center', alignItems: 'center' },

  loaderContainer: { justifyContent: 'center', alignItems: 'center', marginBottom: 40 },
  outerCircle: {
    width: 120,
    height: 120,
    borderRadius: 60,
    borderWidth: 4,
    borderColor: '#67B292',
    borderTopColor: 'transparent',
    justifyContent: 'center',
    alignItems: 'center',
  },
  innerCircle: {},
  centerDot: {
    position: 'absolute',
    width: 90,
    height: 90,
    borderRadius: 45,
    backgroundColor: '#111',
  },

  title: { fontSize: 24, fontWeight: '800', color: '#111', marginBottom: 35 },

  listContainer: { alignItems: 'flex-start' },
  listItem: { flexDirection: 'row', alignItems: 'center', marginBottom: 15 },
  checkIcon: { marginRight: 10 },
  listText: { fontSize: 16, color: '#67B292', fontWeight: '500' },
});

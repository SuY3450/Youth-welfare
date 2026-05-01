import { useRouter } from 'expo-router';
import React, { useEffect, useRef, useState } from 'react';
import { Keyboard, SafeAreaView, StyleSheet, Text, TextInput, TouchableOpacity, View } from 'react-native';

export default function Forgot2Screen() {
  const router = useRouter();
  const [code, setCode] = useState(['', '', '', '', '', '']);
  const inputs = useRef<(TextInput | null)[]>([]);
  const [timeLeft, setTimeLeft] = useState(300);

  useEffect(() => {
    const timer = setInterval(() => {
      setTimeLeft(prev => {
        if (prev <= 1) {
          clearInterval(timer);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, '0')} 남음`;
  };

  const handleCode = (text: string, index: number) => {
    if (timeLeft === 0) return;
    const newCode = [...code];
    newCode[index] = text;
    setCode(newCode);
    if (text && index < 5) {
      inputs.current[index + 1]?.focus();
    }
    if (text && index === 5) {
      Keyboard.dismiss();
    }
  };

  const handleFocus = (index: number) => {
    const firstEmpty = code.findIndex(c => c === '');
    if (firstEmpty !== -1 && index > firstEmpty) {
      inputs.current[firstEmpty]?.focus();
    }
  };

  const handleResend = () => {
    setTimeLeft(300);
    setCode(['', '', '', '', '', '']);
    setTimeout(() => inputs.current[0]?.focus(), 100);
  };

  const isComplete = code.every(c => c !== '') && timeLeft > 0;

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        <TouchableOpacity onPress={() => router.back()}>
          <Text style={styles.back}>〈 이전</Text>
        </TouchableOpacity>

        <View style={styles.stepRow}>
          <View style={styles.stepDone}><Text style={styles.stepDoneText}>✓</Text></View>
          <View style={[styles.stepLine, { backgroundColor: '#1DB88E' }]} />
          <View style={styles.stepActive}><Text style={styles.stepActiveText}>2</Text></View>
          <View style={styles.stepLine} />
          <View style={styles.stepInactive}><Text style={styles.stepInactiveText}>3</Text></View>
        </View>

        <Text style={styles.title}>이메일을 확인해주세요</Text>
        <Text style={styles.subtitle}>6자리 인증 코드를 보내드렸어요</Text>

        <Text style={styles.label}>인증 코드</Text>
        <View style={styles.codeRow}>
          {code.map((c, i) => (
            <TextInput
              key={i}
              ref={(ref) => { inputs.current[i] = ref; }}
              style={[styles.codeInput, timeLeft === 0 && styles.codeInputDisabled]}
              value={c}
              onChangeText={(text) => handleCode(text, i)}
              onFocus={() => handleFocus(i)}
              maxLength={1}
              keyboardType="numeric"
              textAlign="center"
              editable={timeLeft > 0}
            />
          ))}
        </View>

        <View style={styles.timerRow}>
          <Text style={[styles.timer, timeLeft === 0 && styles.timerExpired]}>
            {timeLeft > 0 ? formatTime(timeLeft) : ''}
          </Text>
          <TouchableOpacity onPress={handleResend}>
            <Text style={styles.resend}>코드 재발송</Text>
          </TouchableOpacity>
        </View>

        {timeLeft === 0 && (
          <View style={styles.expiredBox}>
            <Text style={styles.expiredText}>
              인증 코드 입력 시간이 만료되었습니다.{'\n'}코드를 재발송 해주세요.
            </Text>
          </View>
        )}

        <View style={styles.spacer} />

        <TouchableOpacity
          style={[styles.nextButton, !isComplete && styles.disabledButton]}
          onPress={() => router.push('/login/forgot3')}
          disabled={!isComplete}
        >
          <Text style={styles.nextButtonText}>다음</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  content: { flex: 1, paddingHorizontal: 24, paddingTop: 20 },
  back: { color: '#333', marginBottom: 24, fontSize: 14 },
  stepRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 32 },
  stepDone: { width: 32, height: 32, borderRadius: 16, backgroundColor: '#1DB88E', alignItems: 'center', justifyContent: 'center' },
  stepDoneText: { color: '#fff', fontWeight: 'bold' },
  stepActive: { width: 32, height: 32, borderRadius: 16, backgroundColor: '#1DB88E', alignItems: 'center', justifyContent: 'center' },
  stepActiveText: { color: '#fff', fontWeight: 'bold' },
  stepInactive: { width: 32, height: 32, borderRadius: 16, backgroundColor: '#eee', alignItems: 'center', justifyContent: 'center' },
  stepInactiveText: { color: '#999' },
  stepLine: { flex: 1, height: 2, backgroundColor: '#eee' },
  title: { fontSize: 22, fontWeight: 'bold', marginBottom: 8 },
  subtitle: { fontSize: 14, color: '#666', marginBottom: 24, lineHeight: 22 },
  label: { fontSize: 14, marginBottom: 12, color: '#333' },
  codeRow: { flexDirection: 'row', gap: 8, marginBottom: 16 },
  codeInput: { flex: 1, borderWidth: 1, borderColor: '#ddd', borderRadius: 8, padding: 16, fontSize: 20, fontWeight: 'bold' },
  codeInputDisabled: { backgroundColor: '#f5f5f5', borderColor: '#eee', color: '#ccc' },
  timerRow: { flexDirection: 'row', justifyContent: 'space-between' },
  timer: { color: '#FF6B6B', fontSize: 14 },
  timerExpired: { color: '#999' },
  resend: { color: '#999', fontSize: 14 },
  expiredBox: { backgroundColor: '#E8F8F3', borderRadius: 8, padding: 14, marginTop: 16 },
  expiredText: { color: '#111', fontSize: 14, lineHeight: 22, textAlign: 'center' },
  spacer: { flex: 1 },
  nextButton: { backgroundColor: '#1DB88E', borderRadius: 8, padding: 16, alignItems: 'center', marginBottom: 24 },
  disabledButton: { backgroundColor: '#ccc' },
  nextButtonText: { color: '#fff', fontSize: 16, fontWeight: 'bold' },
});
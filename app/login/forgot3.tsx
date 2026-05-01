import { useRouter } from 'expo-router';
import React, { useState } from 'react';
import { SafeAreaView, StyleSheet, Text, TextInput, TouchableOpacity, View } from 'react-native';

export default function Forgot3Screen() {
  const router = useRouter();
  const [password, setPassword] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');

  const isMatch = password.length > 0 && password === passwordConfirm;

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        <TouchableOpacity onPress={() => router.back()}>
          <Text style={styles.back}>〈 이전</Text>
        </TouchableOpacity>

        <View style={styles.stepRow}>
          <View style={styles.stepDone}><Text style={styles.stepDoneText}>✓</Text></View>
          <View style={[styles.stepLine, { backgroundColor: '#1DB88E' }]} />
          <View style={styles.stepDone}><Text style={styles.stepDoneText}>✓</Text></View>
          <View style={[styles.stepLine, { backgroundColor: '#1DB88E' }]} />
          <View style={styles.stepActive}><Text style={styles.stepActiveText}>3</Text></View>
        </View>

        <Text style={styles.title}>새 비밀번호를 설정해주세요</Text>
        <Text style={styles.subtitle}>안전한 비밀번호로 계정을 보호하세요</Text>

        <Text style={styles.label}>새 비밀번호</Text>
        <TextInput
          style={styles.input}
          placeholder="••••••••"
          value={password}
          onChangeText={setPassword}
          secureTextEntry
        />
        <Text style={styles.hint}>영문, 숫자, 특수문자 포함 8자 이상</Text>

        <Text style={styles.label}>비밀번호 확인</Text>
        <View style={styles.inputRow}>
          <TextInput
            style={[styles.inputWithCheck, isMatch && styles.inputSuccess]}
            placeholder="••••••••"
            value={passwordConfirm}
            onChangeText={setPasswordConfirm}
            secureTextEntry
          />
          {isMatch && <Text style={styles.checkMark}>✓</Text>}
        </View>

        <View style={styles.spacer} />

        <TouchableOpacity
          style={[styles.nextButton, !isMatch && styles.disabledButton]}
          onPress={() => router.push('/login/login1')}
          disabled={!isMatch}
        >
          <Text style={styles.nextButtonText}>변경 완료</Text>
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
  stepLine: { flex: 1, height: 2, backgroundColor: '#eee' },
  title: { fontSize: 22, fontWeight: 'bold', marginBottom: 8 },
  subtitle: { fontSize: 14, color: '#666', marginBottom: 32 },
  label: { fontSize: 14, marginBottom: 6, color: '#333' },
  input: { borderWidth: 1, borderColor: '#ddd', borderRadius: 8, padding: 12, marginBottom: 8, fontSize: 14 },
  inputRow: { flexDirection: 'row', alignItems: 'center', borderWidth: 1, borderColor: '#ddd', borderRadius: 8, marginBottom: 8 },
  inputWithCheck: { flex: 1, padding: 12, fontSize: 14 },
  inputSuccess: { borderColor: '#1DB88E' },
  checkMark: { color: '#1DB88E', fontSize: 18, paddingRight: 12, fontWeight: 'bold' },
  hint: { fontSize: 12, color: '#1DB88E', marginBottom: 16 },
  spacer: { flex: 1 },
  nextButton: { backgroundColor: '#1DB88E', borderRadius: 8, padding: 16, alignItems: 'center', marginBottom: 24 },
  disabledButton: { backgroundColor: '#ccc' },
  nextButtonText: { color: '#fff', fontSize: 16, fontWeight: 'bold' },
});
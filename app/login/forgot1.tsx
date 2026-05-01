import { useRouter } from 'expo-router';
import React, { useState } from 'react';
import { SafeAreaView, StyleSheet, Text, TextInput, TouchableOpacity, View } from 'react-native';

export default function Forgot1Screen() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);

  const isValidEmail = (email: string) => {
    return /^[^\s@]+@[^\s@]+\.(com|net|org|co\.kr|kr)$/.test(email);
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        <TouchableOpacity onPress={() => router.back()}>
          <Text style={styles.back}>〈 로그인</Text>
        </TouchableOpacity>

        <View style={styles.stepRow}>
          <View style={styles.stepActive}><Text style={styles.stepActiveText}>1</Text></View>
          <View style={styles.stepLine} />
          <View style={styles.stepInactive}><Text style={styles.stepInactiveText}>2</Text></View>
          <View style={styles.stepLine} />
          <View style={styles.stepInactive}><Text style={styles.stepInactiveText}>3</Text></View>
        </View>

        <Text style={styles.title}>비밀번호를 잊으셨나요?</Text>
        <Text style={styles.subtitle}>가입하신 이메일을 입력하시면{'\n'}인증 코드를 보내드릴게요</Text>

        <Text style={styles.label}>가입한 이메일 <Text style={styles.required}>*</Text></Text>
        <View style={styles.emailRow}>
          <TextInput
            style={styles.emailInput}
            placeholder="example@email.com"
            value={email}
            onChangeText={(text) => { setEmail(text); setSent(false); }}
            keyboardType="email-address"
          />
          <TouchableOpacity
            style={[styles.sendButton, !isValidEmail(email) && styles.disabledButton]}
            onPress={() => { if (isValidEmail(email)) setSent(true); }}
            disabled={!isValidEmail(email)}
          >
            <Text style={styles.sendButtonText}>코드 발송</Text>
          </TouchableOpacity>
        </View>
        {sent && <Text style={styles.sentText}>✓ {email}으로 코드가 발송됐어요</Text>}

        <View style={styles.spacer} />

        <TouchableOpacity
          style={[styles.nextButton, !sent && styles.disabledButton]}
          onPress={() => router.push('/login/forgot2')}
          disabled={!sent}
        >
          <Text style={styles.nextButtonText}>인증 코드 받기</Text>
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
  stepActive: { width: 32, height: 32, borderRadius: 16, backgroundColor: '#1DB88E', alignItems: 'center', justifyContent: 'center' },
  stepActiveText: { color: '#fff', fontWeight: 'bold' },
  stepInactive: { width: 32, height: 32, borderRadius: 16, backgroundColor: '#eee', alignItems: 'center', justifyContent: 'center' },
  stepInactiveText: { color: '#999' },
  stepLine: { flex: 1, height: 2, backgroundColor: '#eee' },
  title: { fontSize: 22, fontWeight: 'bold', marginBottom: 8 },
  subtitle: { fontSize: 14, color: '#666', marginBottom: 24, lineHeight: 22 },
  label: { fontSize: 14, marginBottom: 6, color: '#333' },
  required: { color: 'red' },
  emailRow: { flexDirection: 'row', gap: 8, marginBottom: 8 },
  emailInput: { flex: 1, borderWidth: 1, borderColor: '#ddd', borderRadius: 8, padding: 12, fontSize: 14 },
  sendButton: { backgroundColor: '#1DB88E', borderRadius: 8, paddingHorizontal: 16, justifyContent: 'center' },
  disabledButton: { backgroundColor: '#ccc' },
  sendButtonText: { color: '#fff', fontWeight: 'bold' },
  sentText: { color: '#1DB88E', fontSize: 12, marginBottom: 8 },
  spacer: { flex: 1 },
  nextButton: { backgroundColor: '#1DB88E', borderRadius: 8, padding: 16, alignItems: 'center', marginBottom: 24 },
  nextButtonText: { color: '#fff', fontSize: 16, fontWeight: 'bold' },
});
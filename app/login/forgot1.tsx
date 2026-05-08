import { useRouter } from 'expo-router';
import React, { useState } from 'react';
import { Alert, SafeAreaView, StyleSheet, Text, TextInput, TouchableOpacity, View } from 'react-native';
import { supabase } from '../../constants/supabase';

export default function Forgot1Screen() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [emailFocused, setEmailFocused] = useState(false);

  const isValidEmail = (email: string) => {
    return /^[^\s@]+@[^\s@]+\.(com|net|org|co\.kr|kr)$/.test(email);
  };

  const handleSendCode = async () => {
    setLoading(true);
    const { error } = await supabase.auth.resetPasswordForEmail(email);
    setLoading(false);
    if (error) {
      Alert.alert('오류', '이메일 발송에 실패했습니다. 다시 시도해주세요.');
    } else {
      setSent(true);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        <TouchableOpacity onPress={() => router.back()}>
          <Text style={styles.back}>〈 로그인</Text>
        </TouchableOpacity>

        <Text style={styles.title}>비밀번호를 잊으셨나요?</Text>
        <Text style={styles.subtitle}>가입하신 이메일을 입력하시면{'\n'}비밀번호 재설정 링크를 보내드릴게요</Text>

        <Text style={styles.label}>가입한 이메일 <Text style={styles.required}>*</Text></Text>
        <View style={styles.emailRow}>
          <TextInput
            style={[styles.emailInput, emailFocused && styles.emailInputFocused]}
            placeholder="example@email.com"
            value={email}
            onChangeText={(text) => { setEmail(text); setSent(false); }}
            keyboardType="email-address"
            autoCapitalize="none"
            onFocus={() => setEmailFocused(true)}
            onBlur={() => setEmailFocused(false)}
          />
          <TouchableOpacity
            style={[styles.sendButton, (!isValidEmail(email) || loading) && styles.disabledButton]}
            onPress={handleSendCode}
            disabled={!isValidEmail(email) || loading}
          >
            <Text style={styles.sendButtonText}>{loading ? '발송 중...' : '링크 발송'}</Text>
          </TouchableOpacity>
        </View>

        {sent && (
          <View style={styles.sentBox}>
            <Text style={styles.sentText}>✓ {email}으로 비밀번호 재설정 링크를 보냈어요!</Text>
            <Text style={styles.sentSubText}>이메일을 확인하고 링크를 클릭해주세요.</Text>
          </View>
        )}

        <View style={styles.spacer} />

        <TouchableOpacity
          style={[styles.backButton]}
          onPress={() => router.push('/login/login1')}
        >
          <Text style={styles.backButtonText}>로그인으로 돌아가기</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  content: { flex: 1, paddingHorizontal: 24, paddingTop: 20 },
  back: { color: '#333', marginBottom: 24, fontSize: 14 },
  title: { fontSize: 35, fontWeight: 'bold', marginBottom: 8 },
  subtitle: { fontSize: 14, color: '#666', marginBottom: 30, lineHeight: 17 },
  label: { fontSize: 15, marginBottom: 8, color: '#222', fontWeight: '700' },
  required: { color: 'red' },
  emailRow: { flexDirection: 'row', gap: 8, marginBottom: 8 },
  emailInput: { flex: 1, borderWidth: 1, borderColor: '#D1D5DB', borderRadius: 10, paddingVertical: 16, paddingHorizontal: 14, fontSize: 15 },
  emailInputFocused: { borderColor: '#00B894' },
  sendButton: { backgroundColor: '#1DB88E', borderRadius: 10, paddingHorizontal: 18, justifyContent: 'center' },
  disabledButton: { backgroundColor: '#ccc' },
  sendButtonText: { color: '#fff', fontWeight: 'bold' },
  sentBox: { backgroundColor: '#E8F8F3', borderRadius: 8, padding: 14, marginTop: 8 },
  sentText: { color: '#111', fontSize: 14, marginBottom: 4 },
  sentSubText: { color: '#555', fontSize: 12 },
  spacer: { flex: 1 },
  backButton: { backgroundColor: '#1DB88E', borderRadius: 8, padding: 16, alignItems: 'center', marginBottom: 24 },
  backButtonText: { color: '#fff', fontSize: 16, fontWeight: 'bold' },
});
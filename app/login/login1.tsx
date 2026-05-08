import { useRouter } from 'expo-router';
import React, { useState } from 'react';
import {
  Alert,
  SafeAreaView,
  StyleSheet,
  Text, TextInput, TouchableOpacity,
  View
} from 'react-native';
import { supabase } from '../../constants/supabase';

export default function LoginScreen() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [focusedField, setFocusedField] = useState<'email' | 'password' | null>(null);

  const isValidEmail = (email: string) => {
    return /^[^\s@]+@[^\s@]+\.(com|net|org|co\.kr|kr)$/.test(email);
  };

  const canLogin = isValidEmail(email) && password.length > 0;

  const handleLogin = async () => {
    setLoading(true);
    const { error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });
    setLoading(false);
    if (error) {
      Alert.alert('로그인 실패', '이메일 또는 비밀번호를 확인해주세요.');
    } else {
      router.push('/input');
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        <Text style={styles.topLabel}>AI 맞춤 혜택 추천</Text>

        <Text style={styles.title}>환영합니다</Text>
        <Text style={styles.subtitle}>
          <Text style={styles.link}>로그인</Text>하고 내 혜택을 확인하세요
        </Text>

        <Text style={styles.label}>이메일</Text>
        <TextInput
          style={[styles.input, focusedField === 'email' && styles.inputFocused]}
          placeholder="example@email.com"
          value={email}
          onChangeText={setEmail}
          keyboardType="email-address"
          autoCapitalize="none"
          onFocus={() => setFocusedField('email')}
          onBlur={() => setFocusedField(null)}
        />

        <Text style={styles.label}>비밀번호</Text>
        <TextInput
          style={[styles.input, focusedField === 'password' && styles.inputFocused]}
          placeholder="••••••••"
          value={password}
          onChangeText={setPassword}
          secureTextEntry
          onFocus={() => setFocusedField('password')}
          onBlur={() => setFocusedField(null)}
        />

        <TouchableOpacity onPress={() => router.push('/login/forgot1')}>
          <Text style={styles.forgotPassword}>비밀번호 찾기</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.loginButton, (!canLogin || loading) && styles.disabledButton]}
          onPress={handleLogin}
          disabled={!canLogin || loading}
        >
          <Text style={styles.loginButtonText}>{loading ? '로그인 중...' : '로그인'}</Text>
        </TouchableOpacity>

        <View style={styles.registerContainer}>
          <Text style={styles.registerText}>아직 계정이 없으신가요? </Text>
          <TouchableOpacity onPress={() => router.push('/login/register')}>
            <Text style={styles.link}>회원가입하기</Text>
          </TouchableOpacity>
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  content: { flex: 1, paddingHorizontal: 24, paddingTop: 60 },
  topLabel: { fontSize: 13, color: '#046451', fontWeight: '600', marginBottom: 28 },
  title: { fontSize: 36, fontWeight: 'bold', marginBottom: 8, color: '#111' },
  subtitle: { fontSize: 14, color: '#666', marginBottom: 32 },
  link: { color: '#1DB88E', fontWeight: 'bold' },
  label: { fontSize: 15, marginBottom: 8, color: '#222', fontWeight: '700' },
  input: { borderWidth: 1, borderColor: '#D1D5DB', borderRadius: 10, paddingVertical: 16, paddingHorizontal: 14, marginBottom: 18, fontSize: 15 },
  inputFocused: { borderColor: '#00B894' },
  forgotPassword: { color: '#1DB88E', textAlign: 'right', marginBottom: 20, fontWeight: '600', textDecorationLine: 'underline' },
  loginButton: { backgroundColor: '#1DB88E', borderRadius: 10, paddingVertical: 16, alignItems: 'center', marginBottom: 24 },
  disabledButton: { backgroundColor: '#A8E6C9' },
  loginButtonText: { color: '#fff', fontSize: 16, fontWeight: 'bold' },
  registerContainer: { flexDirection: 'row', justifyContent: 'center' },
  registerText: { color: '#888' },
});

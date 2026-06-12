import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import React, { useState } from 'react';
import {
  Alert,
  SafeAreaView,
  StyleSheet,
  Text, TextInput, TouchableOpacity,
  View
} from 'react-native';
import { API_URL } from '../../constants/api';
import { supabase } from '../../constants/supabase';

export default function LoginScreen() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const isValidEmail = (email: string) => {
    return /^[^\s@]+@[^\s@]+\.(com|net|org|co\.kr|kr)$/.test(email);
  };

  const canLogin = isValidEmail(email) && password.length > 0;

  const handleLogin = async () => {
    setLoading(true);
    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });
    if (error) {
      setLoading(false);
      Alert.alert('로그인 실패', '이메일 또는 비밀번호를 확인해주세요.');
      return;
    }

    try {
      const response = await fetch(`${API_URL}/profile/${data.user.id}`);
      if (response.ok) {
        const profileData = await response.json();
        router.push({ pathname: '/loading', params: { profile_id: profileData.id } });
      } else {
        router.push('/input');
      }
    } catch (e) {
      router.push('/input');
    }
    setLoading(false);
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        <Text style={styles.title}>나만의 청년 혜택,{'\n'}AI가 찾아드려요</Text>
        <Text style={styles.subtitle}>
          <Text style={styles.link}>로그인</Text>하고 맞춤 정책을 확인하세요
        </Text>

        <Text style={styles.label}>이메일</Text>
        <TextInput
          style={styles.input}
          placeholder="example@email.com"
          value={email}
          onChangeText={setEmail}
          keyboardType="email-address"
        />

        <Text style={styles.label}>비밀번호</Text>
        <View style={styles.passwordRow}>
          <TextInput
            style={styles.passwordInput}
            placeholder="••••••••"
            value={password}
            onChangeText={setPassword}
            secureTextEntry={!showPassword}
          />
          <TouchableOpacity onPress={() => setShowPassword(!showPassword)} style={styles.eyeButton}>
            <Ionicons name={showPassword ? 'eye' : 'eye-off'} size={20} color="#999" />
          </TouchableOpacity>
        </View>

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
  title: { fontSize: 26, fontWeight: 'bold', marginBottom: 8 },
  subtitle: { fontSize: 14, color: '#666', marginBottom: 32 },
  link: { color: '#1DB88E', fontWeight: 'bold' },
  label: { fontSize: 14, marginBottom: 6, color: '#333' },
  input: { borderWidth: 1, borderColor: '#ddd', borderRadius: 8, padding: 12, marginBottom: 16, fontSize: 14 },
  passwordRow: { flexDirection: 'row', alignItems: 'center', borderWidth: 1, borderColor: '#ddd', borderRadius: 8, marginBottom: 16 },
  passwordInput: { flex: 1, padding: 12, fontSize: 14 },
  eyeButton: { paddingHorizontal: 12 },
  forgotPassword: { color: '#1DB88E', textAlign: 'right', marginBottom: 24 },
  loginButton: { backgroundColor: '#1DB88E', borderRadius: 8, padding: 16, alignItems: 'center', marginBottom: 24 },
  disabledButton: { backgroundColor: '#ccc' },
  loginButtonText: { color: '#fff', fontSize: 16, fontWeight: 'bold' },
  registerContainer: { flexDirection: 'row', justifyContent: 'center' },
  registerText: { color: '#666' },
});
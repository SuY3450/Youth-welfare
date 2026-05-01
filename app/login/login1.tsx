import { useRouter } from 'expo-router';
import React, { useState } from 'react';
import {
  Image,
  SafeAreaView,
  StyleSheet,
  Text, TextInput, TouchableOpacity,
  View
} from 'react-native';

export default function LoginScreen() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const isValidEmail = (email: string) => {
    return /^[^\s@]+@[^\s@]+\.(com|net|org|co\.kr|kr)$/.test(email);
  };

  const canLogin = isValidEmail(email) && password.length > 0;

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
        <TextInput
          style={styles.input}
          placeholder="••••••••"
          value={password}
          onChangeText={setPassword}
          secureTextEntry
        />

        <TouchableOpacity onPress={() => router.push('/login/forgot1')}>
          <Text style={styles.forgotPassword}>비밀번호 찾기</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.loginButton, !canLogin && styles.disabledButton]}
          onPress={() => router.push('/input')}
          disabled={!canLogin}
        >
          <Text style={styles.loginButtonText}>로그인</Text>
        </TouchableOpacity>

        <View style={styles.divider}>
          <View style={styles.line} />
          <Text style={styles.dividerText}>또는</Text>
          <View style={styles.line} />
        </View>

        <TouchableOpacity style={styles.googleButton}>
          <Image
            source={require('../../assets/images/google-signin.png')}
            style={styles.googleImage}
            resizeMode="contain"
          />
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
  forgotPassword: { color: '#1DB88E', textAlign: 'right', marginBottom: 24 },
  loginButton: { backgroundColor: '#1DB88E', borderRadius: 8, padding: 16, alignItems: 'center', marginBottom: 24 },
  disabledButton: { backgroundColor: '#ccc' },
  loginButtonText: { color: '#fff', fontSize: 16, fontWeight: 'bold' },
  divider: { flexDirection: 'row', alignItems: 'center', marginBottom: 16 },
  line: { flex: 1, height: 1, backgroundColor: '#ddd' },
  dividerText: { marginHorizontal: 8, color: '#999' },
  googleButton: { alignItems: 'center', marginBottom: 24 },
  googleImage: { width: 200, height: 44 },
  registerContainer: { flexDirection: 'row', justifyContent: 'center' },
  registerText: { color: '#666' },
});
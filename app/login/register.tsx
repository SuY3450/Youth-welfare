import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import React, { useRef, useState } from 'react';
import {
  Keyboard,
  SafeAreaView, ScrollView,
  StyleSheet,
  Text, TextInput, TouchableOpacity,
  TouchableWithoutFeedback,
  View
} from 'react-native';

export default function RegisterScreen() {
  const router = useRouter();
  const [name, setName] = useState('');
  const [year, setYear] = useState('');
  const [month, setMonth] = useState('');
  const [day, setDay] = useState('');
  const [email, setEmail] = useState('');
  const [emailVerified, setEmailVerified] = useState(false);
  const [password, setPassword] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showPasswordConfirm, setShowPasswordConfirm] = useState(false);

  const monthRef = useRef<TextInput>(null);
  const dayRef = useRef<TextInput>(null);

  const isValidName = /^[가-힣]{3,}$/.test(name);

  const isValidEmail = (email: string) => {
    return /^[^\s@]+@[^\s@]+\.(com|net|org|co\.kr|kr)$/.test(email);
  };

  const isPasswordMatch = password.length > 0 && password === passwordConfirm;

  const canNext =
    isValidName &&
    year.length === 4 &&
    month.length === 2 &&
    day.length === 2 &&
    isValidEmail(email) &&
    emailVerified &&
    isPasswordMatch;

  return (
    <TouchableWithoutFeedback onPress={Keyboard.dismiss}>
      <SafeAreaView style={styles.container}>
        <ScrollView contentContainerStyle={styles.content}>
          <View style={styles.header}>
            <Text style={styles.title}>회원가입</Text>
            <Text style={styles.step}>1 / 2</Text>
          </View>
          <Text style={styles.subtitle}>가입 정보를 입력해주세요</Text>
          <View style={styles.progressBar}>
            <View style={styles.progressFill} />
          </View>

          <Text style={styles.label}>이름 <Text style={styles.required}>*</Text></Text>
          <TextInput
            style={styles.input}
            placeholder="홍길동"
            value={name}
            onChangeText={setName}
            maxLength={10}
          />

          <Text style={styles.label}>생년월일 <Text style={styles.required}>*</Text></Text>
          <View style={styles.birthRow}>
            <TextInput
              style={[styles.input, styles.birthInput]}
              placeholder="YYYY"
              value={year}
              onChangeText={(text) => {
                setYear(text);
                if (text.length === 4) monthRef.current?.focus();
              }}
              keyboardType="numeric"
              maxLength={4}
            />
            <TextInput
              ref={monthRef}
              style={[styles.input, styles.birthInput]}
              placeholder="MM"
              value={month}
              onChangeText={(text) => {
                setMonth(text);
                if (text.length === 2) dayRef.current?.focus();
              }}
              keyboardType="numeric"
              maxLength={2}
            />
            <TextInput
              ref={dayRef}
              style={[styles.input, styles.birthInput]}
              placeholder="DD"
              value={day}
              onChangeText={(text) => {
                setDay(text);
                if (text.length === 2) Keyboard.dismiss();
              }}
              keyboardType="numeric"
              maxLength={2}
            />
          </View>

          <Text style={styles.label}>이메일 <Text style={styles.required}>*</Text></Text>
          <View style={styles.emailRow}>
            <TextInput
              style={[styles.input, styles.emailInput]}
              placeholder="example@email.com"
              value={email}
              onChangeText={(text) => { setEmail(text); setEmailVerified(false); }}
              keyboardType="email-address"
            />
            <TouchableOpacity
              style={[styles.verifyButton, !isValidEmail(email) && styles.verifyButtonDisabled]}
              onPress={() => { if (isValidEmail(email)) setEmailVerified(true); }}
              disabled={!isValidEmail(email)}
            >
              <Text style={styles.verifyButtonText}>인증</Text>
            </TouchableOpacity>
          </View>
          {emailVerified && (
            <Text style={styles.verifiedText}>인증이 완료되었습니다</Text>
          )}

          <View style={styles.passwordSection}>
            <Text style={styles.label}>비밀번호 <Text style={styles.required}>*</Text></Text>
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

            <Text style={styles.label}>비밀번호 확인 <Text style={styles.required}>*</Text></Text>
            <View style={[styles.inputRow, isPasswordMatch && styles.inputRowSuccess]}>
              <TextInput
                style={styles.inputWithCheck}
                placeholder="••••••••"
                value={passwordConfirm}
                onChangeText={setPasswordConfirm}
                secureTextEntry={!showPasswordConfirm}
              />
              {isPasswordMatch
                ? <Text style={styles.checkMark}>✓</Text>
                : <TouchableOpacity onPress={() => setShowPasswordConfirm(!showPasswordConfirm)} style={styles.eyeButton}>
                    <Ionicons name={showPasswordConfirm ? 'eye' : 'eye-off'} size={20} color="#999" />
                  </TouchableOpacity>
              }
            </View>
          </View>

          <View style={styles.spacer} />

          <TouchableOpacity
            style={[styles.nextButton, !canNext && styles.disabledButton]}
            onPress={() => router.push({
              pathname: '/login/agree',
              params: { email, password, name }
            })}
            disabled={!canNext}
          >
            <Text style={styles.nextButtonText}>다음 단계</Text>
          </TouchableOpacity>
        </ScrollView>
      </SafeAreaView>
    </TouchableWithoutFeedback>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  content: { flexGrow: 1, paddingHorizontal: 24, paddingTop: 40, paddingBottom: 40 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 },
  title: { fontSize: 30, fontWeight: 'bold' },
  step: { fontSize: 14, color: '#999' },
  subtitle: { fontSize: 13, color: '#999', marginBottom: 8 },
  progressBar: { height: 3, backgroundColor: '#eee', borderRadius: 2, marginBottom: 24 },
  progressFill: { width: '50%', height: 3, backgroundColor: '#1DB88E', borderRadius: 2 },
  label: { fontSize: 15, marginBottom: 8, color: '#222', fontWeight: '700' },
  required: { color: 'red' },
  input: { borderWidth: 1, borderColor: '#ddd', borderRadius: 10, paddingVertical: 16, paddingHorizontal: 14, marginBottom: 18, fontSize: 15 },
  birthRow: { flexDirection: 'row', gap: 8 },
  birthInput: { flex: 1 },
  emailRow: { flexDirection: 'row', gap: 8 },
  emailInput: { flex: 1, marginBottom: 0 },
  verifyButton: { backgroundColor: '#1DB88E', borderRadius: 10, paddingHorizontal: 18, justifyContent: 'center', height: 56 },
  verifyButtonDisabled: { backgroundColor: '#C7C7C7' },
  verifyButtonText: { color: '#fff', fontWeight: 'bold' },
  verifiedText: { fontSize: 12, color: '#333', marginTop: 6, marginBottom: 8 },
  passwordSection: { marginTop: 16 },
  passwordRow: { flexDirection: 'row', alignItems: 'center', borderWidth: 1, borderColor: '#ddd', borderRadius: 10, marginBottom: 18 },
  passwordInput: { flex: 1, paddingVertical: 16, paddingHorizontal: 14, fontSize: 15 },
  eyeButton: { paddingHorizontal: 12 },
  inputRow: { flexDirection: 'row', alignItems: 'center', borderWidth: 1, borderColor: '#ddd', borderRadius: 10, marginBottom: 18 },
  inputRowSuccess: { borderColor: '#1DB88E' },
  inputWithCheck: { flex: 1, paddingVertical: 16, paddingHorizontal: 14, fontSize: 15 },
  checkMark: { color: '#1DB88E', fontSize: 18, paddingRight: 14, fontWeight: 'bold' },
  spacer: { flex: 1, minHeight: 24 },
  nextButton: { backgroundColor: '#1DB88E', borderRadius: 8, padding: 16, alignItems: 'center', marginBottom: 24 },
  disabledButton: { backgroundColor: '#A8E6C9' },
  nextButtonText: { color: '#fff', fontSize: 16, fontWeight: 'bold' },
});
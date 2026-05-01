import { useRouter } from 'expo-router';
import React, { useRef, useState } from 'react';
import {
  Image,
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
              style={styles.verifyButton}
              onPress={() => { if (isValidEmail(email)) setEmailVerified(true); }}
            >
              <Text style={styles.verifyButtonText}>인증</Text>
            </TouchableOpacity>
          </View>
          {emailVerified && (
            <Text style={styles.verifiedText}>인증이 완료되었습니다</Text>
          )}

          <View style={styles.passwordSection}>
            <Text style={styles.label}>비밀번호 <Text style={styles.required}>*</Text></Text>
            <TextInput
              style={styles.input}
              placeholder="••••••••"
              value={password}
              onChangeText={setPassword}
              secureTextEntry
            />

            <Text style={styles.label}>비밀번호 확인 <Text style={styles.required}>*</Text></Text>
            <View style={[styles.inputRow, isPasswordMatch && styles.inputRowSuccess]}>
              <TextInput
                style={styles.inputWithCheck}
                placeholder="••••••••"
                value={passwordConfirm}
                onChangeText={setPasswordConfirm}
                secureTextEntry
              />
              {isPasswordMatch && <Text style={styles.checkMark}>✓</Text>}
            </View>
          </View>

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

          <TouchableOpacity
            style={[styles.nextButton, !canNext && styles.disabledButton]}
            onPress={() => router.push('/login/agree')}
            disabled={!canNext}
          >
            <Text style={styles.nextButtonText}>다음 단계 →</Text>
          </TouchableOpacity>
        </ScrollView>
      </SafeAreaView>
    </TouchableWithoutFeedback>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  content: { paddingHorizontal: 24, paddingTop: 40, paddingBottom: 40 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 },
  title: { fontSize: 22, fontWeight: 'bold' },
  step: { fontSize: 14, color: '#999' },
  subtitle: { fontSize: 13, color: '#999', marginBottom: 8 },
  progressBar: { height: 3, backgroundColor: '#eee', borderRadius: 2, marginBottom: 24 },
  progressFill: { width: '50%', height: 3, backgroundColor: '#1DB88E', borderRadius: 2 },
  label: { fontSize: 14, marginBottom: 6, color: '#333' },
  required: { color: 'red' },
  input: { borderWidth: 1, borderColor: '#ddd', borderRadius: 8, padding: 12, marginBottom: 16, fontSize: 14 },
  birthRow: { flexDirection: 'row', gap: 8 },
  birthInput: { flex: 1 },
  emailRow: { flexDirection: 'row', gap: 8 },
  emailInput: { flex: 1, marginBottom: 0 },
  verifyButton: { backgroundColor: '#1DB88E', borderRadius: 8, paddingHorizontal: 16, justifyContent: 'center', height: 48 },
  verifyButtonText: { color: '#fff', fontWeight: 'bold' },
  verifiedText: { fontSize: 12, color: '#333', marginTop: 6, marginBottom: 8 },
  passwordSection: { marginTop: 16 },
  inputRow: { flexDirection: 'row', alignItems: 'center', borderWidth: 1, borderColor: '#ddd', borderRadius: 8, marginBottom: 16 },
  inputRowSuccess: { borderColor: '#1DB88E' },
  inputWithCheck: { flex: 1, padding: 12, fontSize: 14 },
  checkMark: { color: '#1DB88E', fontSize: 18, paddingRight: 12, fontWeight: 'bold' },
  divider: { flexDirection: 'row', alignItems: 'center', marginBottom: 16 },
  line: { flex: 1, height: 1, backgroundColor: '#ddd' },
  dividerText: { marginHorizontal: 8, color: '#999' },
  googleButton: { alignItems: 'center', marginBottom: 24 },
  googleImage: { width: 200, height: 44 },
  nextButton: { backgroundColor: '#1DB88E', borderRadius: 8, padding: 16, alignItems: 'center' },
  disabledButton: { backgroundColor: '#ccc' },
  nextButtonText: { color: '#fff', fontSize: 16, fontWeight: 'bold' },
});
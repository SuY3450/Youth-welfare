import { useLocalSearchParams, useRouter } from 'expo-router';
import React, { useState } from 'react';
import {
  Alert,
  SafeAreaView, ScrollView,
  StyleSheet,
  Text, TouchableOpacity,
  View
} from 'react-native';
import { supabase } from '../../constants/supabase';

export default function TermsScreen() {
  const router = useRouter();
  const { email, password } = useLocalSearchParams();
  const [allChecked, setAllChecked] = useState(false);
  const [terms1, setTerms1] = useState(false);
  const [terms2, setTerms2] = useState(false);
  const [terms3, setTerms3] = useState(false);
  const [marketing, setMarketing] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleAllCheck = () => {
    const newValue = !allChecked;
    setAllChecked(newValue);
    setTerms1(newValue);
    setTerms2(newValue);
    setTerms3(newValue);
    setMarketing(newValue);
  };

  const canComplete = terms1 && terms2 && terms3;

  const handleSignUp = async () => {
    setLoading(true);
    const { error } = await supabase.auth.signUp({
      email: email as string,
      password: password as string,
    });
    setLoading(false);
    if (error) {
      Alert.alert('회원가입 실패', error.message);
    } else {
      router.push('/login/login1');
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.header}>
          <Text style={styles.title}>약관 동의</Text>
          <Text style={styles.step}>2 / 2</Text>
        </View>
        <Text style={styles.subtitle}>서비스 이용을 위해 아래 약관에 동의해주세요</Text>
        <View style={styles.progressBar}>
          <View style={styles.progressFill} />
        </View>

        <TouchableOpacity style={styles.allCheckBox} onPress={handleAllCheck}>
          <Text style={styles.checkbox}>{allChecked ? '☑' : '☐'}</Text>
          <Text style={styles.allCheckText}>전체 동의하기</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.checkRow} onPress={() => setTerms1(!terms1)}>
          <Text style={styles.checkbox}>{terms1 ? '☑' : '☐'}</Text>
          <Text style={styles.checkText}>[필수] 서비스 이용약관 보기</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.checkRow} onPress={() => setTerms2(!terms2)}>
          <Text style={styles.checkbox}>{terms2 ? '☑' : '☐'}</Text>
          <Text style={styles.checkText}>[필수] 개인정보 수집 및 이용 동의 보기</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.checkRow} onPress={() => setTerms3(!terms3)}>
          <Text style={styles.checkbox}>{terms3 ? '☑' : '☐'}</Text>
          <Text style={styles.checkText}>[필수] 만 19세 이상 (만 19-34세) 확인</Text>
        </TouchableOpacity>

        <View style={styles.infoBox}>
          <Text style={styles.infoText}>본 서비스는 만 19~34세 청년 대상이며, 허위 정보 입력 시 이용이 제한될 수 있습니다.</Text>
        </View>

        <TouchableOpacity style={styles.checkRow} onPress={() => setMarketing(!marketing)}>
          <Text style={styles.checkbox}>{marketing ? '☑' : '☐'}</Text>
          <Text style={styles.checkText}>[선택] 마케팅 정보 수신 동의{'\n'}새로운 청년 지원사업 알림을 받아보세요</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.completeButton, (!canComplete || loading) && styles.disabledButton]}
          onPress={handleSignUp}
          disabled={!canComplete || loading}
        >
          <Text style={styles.completeButtonText}>{loading ? '처리 중...' : '가입 완료'}</Text>
        </TouchableOpacity>

        <View style={styles.loginRow}>
          <Text style={styles.loginText}>이미 계정이 있나요? </Text>
          <TouchableOpacity onPress={() => router.push('/login/login1')}>
            <Text style={styles.loginLink}>로그인</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </SafeAreaView>
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
  progressFill: { width: '100%', height: 3, backgroundColor: '#1DB88E', borderRadius: 2 },
  allCheckBox: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#F0FBF7', padding: 16, borderRadius: 8, marginBottom: 16 },
  allCheckText: { fontSize: 16, fontWeight: 'bold', marginLeft: 8 },
  checkRow: { flexDirection: 'row', alignItems: 'flex-start', marginBottom: 16 },
  checkbox: { fontSize: 18, color: '#1DB88E', marginRight: 8 },
  checkText: { fontSize: 14, color: '#333', flex: 1 },
  infoBox: { backgroundColor: '#F0FBF7', padding: 12, borderRadius: 8, marginBottom: 16 },
  infoText: { fontSize: 12, color: '#666' },
  completeButton: { backgroundColor: '#1DB88E', borderRadius: 8, padding: 16, alignItems: 'center', marginBottom: 16 },
  disabledButton: { backgroundColor: '#ccc' },
  completeButtonText: { color: '#fff', fontSize: 16, fontWeight: 'bold' },
  loginRow: { flexDirection: 'row', justifyContent: 'center' },
  loginText: { color: '#666' },
  loginLink: { color: '#1DB88E', fontWeight: 'bold' },
});
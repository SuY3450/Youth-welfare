import { Ionicons } from '@expo/vector-icons';
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

  const Checkbox = ({ checked }: { checked: boolean }) => (
    <Ionicons
      name={checked ? 'checkbox' : 'square-outline'}
      size={26}
      color={checked ? '#1DB88E' : '#C7C7C7'}
      style={{ marginRight: 10 }}
    />
  );

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

        <View style={styles.agreementCard}>
          <TouchableOpacity style={styles.allCheckRow} onPress={handleAllCheck}>
            <Checkbox checked={allChecked} />
            <Text style={styles.allCheckText}>전체 동의하기</Text>
          </TouchableOpacity>

          <View style={styles.divider} />

          <TouchableOpacity style={styles.checkRow} onPress={() => setTerms1(!terms1)}>
            <Checkbox checked={terms1} />
            <Text style={styles.checkText}>[필수] 서비스 이용약관 보기</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.checkRow} onPress={() => setTerms2(!terms2)}>
            <Checkbox checked={terms2} />
            <Text style={styles.checkText}>[필수] 개인정보 수집 및 이용 동의 보기</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.checkRow} onPress={() => setTerms3(!terms3)}>
            <Checkbox checked={terms3} />
            <Text style={styles.checkText}>[필수] 만 19세 이상 (만 19-34세) 확인</Text>
          </TouchableOpacity>

          <View style={styles.infoBox}>
            <Text style={styles.infoText}>본 서비스는 만 19~34세 청년 대상이며, 허위 정보 입력 시 이용이 제한될 수 있습니다.</Text>
          </View>

          <TouchableOpacity style={styles.checkRow} onPress={() => setMarketing(!marketing)}>
            <Checkbox checked={marketing} />
            <View style={{ flex: 1 }}>
              <Text style={styles.checkText}>[선택] 마케팅 정보 수신 동의</Text>
              <Text style={styles.checkSubText}>새로운 청년 지원사업 알림을 받아보세요</Text>
            </View>
          </TouchableOpacity>
        </View>

        <View style={styles.spacer} />

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
  content: { flexGrow: 1, paddingHorizontal: 24, paddingTop: 40, paddingBottom: 24 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 },
  title: { fontSize: 24, fontWeight: 'bold', color: '#111' },
  step: { fontSize: 14, color: '#999' },
  subtitle: { fontSize: 13, color: '#888', marginBottom: 12 },
  progressBar: { height: 3, backgroundColor: '#eee', borderRadius: 2, marginBottom: 24 },
  progressFill: { width: '100%', height: 3, backgroundColor: '#1DB88E', borderRadius: 2 },

  agreementCard: { backgroundColor: '#EDFAF8', borderRadius: 14, padding: 18 },
  allCheckRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 4 },
  allCheckText: { fontSize: 16, fontWeight: 'bold', color: '#111' },
  divider: { height: 1, backgroundColor: '#E0E5E2', marginVertical: 14 },

  checkRow: { flexDirection: 'row', alignItems: 'flex-start', marginBottom: 14 },
  checkText: { fontSize: 14, color: '#333', flex: 1, lineHeight: 22 },
  checkSubText: { fontSize: 12, color: '#888', marginTop: 2 },

  infoBox: { backgroundColor: '#FFF8E1', padding: 10, borderRadius: 7, marginBottom: 14, marginLeft: 36 },
  infoText: { fontSize: 12, color: '#8A6D3B', lineHeight: 18 },

  spacer: { flex: 1, minHeight: 20 },
  completeButton: { backgroundColor: '#1DB88E', borderRadius: 10, paddingVertical: 18, alignItems: 'center', marginBottom: 12 },
  disabledButton: { backgroundColor: '#A8E6C9' },
  completeButtonText: { color: '#fff', fontSize: 16, fontWeight: 'bold' },
  loginRow: { flexDirection: 'row', justifyContent: 'center', marginBottom: 12 },
  loginText: { color: '#888' },
  loginLink: { color: '#1DB88E', fontWeight: 'bold' },
});

import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import React, { useState } from 'react';
import { Alert, FlatList, Modal, SafeAreaView, ScrollView, StyleSheet, Text, TextInput, TouchableOpacity, View } from 'react-native';
import { API_URL } from '../constants/api';
import { supabase } from '../constants/supabase';

const cityList = [
  '서울특별시', '경기도', '인천광역시', '부산광역시', '대구광역시',
  '광주광역시', '대전광역시', '울산광역시', '세종특별자치시',
  '강원도', '충청북도', '충청남도', '전라북도', '전라남도',
  '경상북도', '경상남도', '제주특별자치도'
];

const districts: { [key: string]: string[] } = {
  '서울특별시': ['종로구', '중구', '용산구', '성동구', '광진구', '동대문구', '중랑구', '성북구', '강북구', '도봉구', '노원구', '은평구', '서대문구', '마포구', '양천구', '강서구', '구로구', '금천구', '영등포구', '동작구', '관악구', '서초구', '강남구', '송파구', '강동구'],
  '경기도': ['수원시', '고양시', '용인시', '성남시', '부천시', '화성시', '안산시', '남양주시', '안양시', '평택시', '시흥시', '파주시', '의정부시', '김포시', '광주시', '광명시', '군포시', '하남시', '오산시', '양주시', '이천시', '구리시', '의왕시', '포천시', '양평군', '여주시', '동두천시', '가평군', '과천시', '연천군'],
  '인천광역시': ['중구', '동구', '미추홀구', '연수구', '남동구', '부평구', '계양구', '서구', '강화군', '옹진군'],
  '부산광역시': ['중구', '서구', '동구', '영도구', '부산진구', '동래구', '남구', '북구', '해운대구', '사하구', '금정구', '강서구', '연제구', '수영구', '사상구', '기장군'],
  '대구광역시': ['중구', '동구', '서구', '남구', '북구', '수성구', '달서구', '달성군'],
  '광주광역시': ['동구', '서구', '남구', '북구', '광산구'],
  '대전광역시': ['동구', '중구', '서구', '유성구', '대덕구'],
  '울산광역시': ['중구', '남구', '동구', '북구', '울주군'],
  '세종특별자치시': ['세종시'],
  '강원도': ['춘천시', '원주시', '강릉시', '동해시', '태백시', '속초시', '삼척시', '홍천군', '횡성군', '영월군', '평창군', '정선군', '철원군', '화천군', '양구군', '인제군', '고성군', '양양군'],
  '충청북도': ['청주시', '충주시', '제천시', '보은군', '옥천군', '영동군', '증평군', '진천군', '괴산군', '음성군', '단양군'],
  '충청남도': ['천안시', '공주시', '보령시', '아산시', '서산시', '논산시', '계룡시', '당진시', '금산군', '부여군', '서천군', '청양군', '홍성군', '예산군', '태안군'],
  '전라북도': ['전주시', '군산시', '익산시', '정읍시', '남원시', '김제시', '완주군', '진안군', '무주군', '장수군', '임실군', '순창군', '고창군', '부안군'],
  '전라남도': ['목포시', '여수시', '순천시', '나주시', '광양시', '담양군', '곡성군', '구례군', '고흥군', '보성군', '화순군', '장흥군', '강진군', '해남군', '영암군', '무안군', '함평군', '영광군', '장성군', '완도군', '진도군', '신안군'],
  '경상북도': ['포항시', '경주시', '김천시', '안동시', '구미시', '영주시', '영천시', '상주시', '문경시', '경산시', '군위군', '의성군', '청송군', '영양군', '영덕군', '청도군', '고령군', '성주군', '칠곡군', '예천군', '봉화군', '울진군', '울릉군'],
  '경상남도': ['창원시', '진주시', '통영시', '사천시', '김해시', '밀양시', '거제시', '양산시', '의령군', '함안군', '창녕군', '고성군', '남해군', '하동군', '산청군', '함양군', '거창군', '합천군'],
  '제주특별자치도': ['제주시', '서귀포시'],
};

const educationList = ['제한 없음', '고졸 미만', '고교 재학', '고졸 예정', '고교 졸업', '대학 재학', '대졸 예정', '대학 졸업', '석·박사', '기타'];

interface SelectorProps {
  visible: boolean;
  title: string;
  data: string[];
  onSelect: (val: string) => void;
  onClose: () => void;
}

const SelectorModal = ({ visible, title, data, onSelect, onClose }: SelectorProps) => (
  <Modal visible={visible} animationType="fade" transparent={true}>
    <TouchableOpacity style={styles.modalOverlay} activeOpacity={1} onPress={onClose}>
      <View style={styles.modalContent}>
        <Text style={styles.modalTitle}>{title}</Text>
        <FlatList
          data={data}
          keyExtractor={(item) => item}
          renderItem={({ item }) => (
            <TouchableOpacity style={styles.modalItem} onPress={() => onSelect(item)}>
              <Text style={styles.modalItemText}>{item}</Text>
            </TouchableOpacity>
          )}
          style={{ maxHeight: 350 }}
        />
      </View>
    </TouchableOpacity>
  </Modal>
);

export default function InputScreen() {
  const router = useRouter();
  const [age, setAge] = useState('');
  const [selectedCity, setSelectedCity] = useState('');
  const [selectedDistrict, setSelectedDistrict] = useState('');
  const [income, setIncome] = useState('');
  const [jobStatus, setJobStatus] = useState('');
  const [education, setEducation] = useState('');
  const [modalType, setModalType] = useState<string | null>(null);

  const canSubmit = age.trim() !== '' && selectedCity !== '' && selectedDistrict !== '' && income !== '' && jobStatus !== '' && education !== '';

  const handleNextStep = async () => {
    const { data: { session }, error: sessionError } = await supabase.auth.getSession();
    if (sessionError || !session) {
      Alert.alert('로그인 필요', '다시 로그인해주세요.');
      router.replace('/login/login1');
      return;
    }

    try {
      const response = await fetch(`${API_URL}/input`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({
          user_id: session.user.id,
          age: parseInt(age),
          city: selectedCity,
          district: selectedDistrict,
          income: income,
          jobStatus: jobStatus,
          education: education,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        Alert.alert('저장 실패', errorData.detail || '서버 오류가 발생했습니다.');
        return;
      }

      const data = await response.json();
      router.push({ pathname: '/InternetScreen', params: { profile_id: data.profile_id } });
    } catch (error) {
      console.error('오류:', error);
      Alert.alert('네트워크 오류', '백엔드 서버에 연결할 수 없습니다.');
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.header}>
          <Text style={styles.headerTitle}>내 정보 입력</Text>
          <Text style={styles.stepText}>1 / 2</Text>
        </View>
        <View style={styles.progressBarBg}><View style={styles.progressBarFill} /></View>

        <View style={styles.inputGroup}>
          <Text style={styles.label}>나이</Text>
          <View style={styles.inlineInput}>
            <TextInput style={styles.textInput} value={age} onChangeText={setAge} keyboardType="number-pad" placeholder="나이 입력" placeholderTextColor="#BBB" />
            <Text style={styles.unitText}>(만) 세</Text>
          </View>
        </View>

        <View style={styles.inputGroup}>
          <Text style={styles.label}>거주 지역</Text>
          <View style={styles.row}>
            <TouchableOpacity style={[styles.dropdown, { flex: 1, marginRight: 10 }]} onPress={() => setModalType('city')}>
              <Text style={[styles.dropdownText, !selectedCity && styles.placeholderText]}>{selectedCity || '시/도 선택'}</Text>
              <Ionicons name="chevron-down" size={16} color="#333" />
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.dropdown, { flex: 1 }]}
              onPress={() => {
                if (!selectedCity) {
                  Alert.alert('알림', '시/도를 먼저 선택해주세요.');
                  return;
                }
                setModalType('district');
              }}
            >
              <Text style={[styles.dropdownText, !selectedDistrict && styles.placeholderText]}>{selectedDistrict || '시/군/구 선택'}</Text>
              <Ionicons name="chevron-down" size={16} color="#333" />
            </TouchableOpacity>
          </View>
        </View>

        <View style={styles.inputGroup}>
          <Text style={styles.label}>소득 구간</Text>
          <View style={styles.grid}>
            {['50% 이하', '50~100% 이하', '100~150%', '150% 초과'].map((item) => (
              <TouchableOpacity key={item} style={[styles.choiceBtn, income === item && styles.activeBtn]} onPress={() => setIncome(item)}>
                <Text style={income === item ? styles.activeText : styles.choiceText}>{item}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        <View style={styles.inputGroup}>
          <Text style={styles.label}>취업 상태</Text>
          <View style={styles.row}>
            {['재직', '구직', '프리랜서'].map((status) => (
              <TouchableOpacity key={status} style={[styles.statusBtn, jobStatus === status && styles.activeBtn]} onPress={() => setJobStatus(status)}>
                <Text style={jobStatus === status ? styles.activeText : styles.choiceText}>{status}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        <View style={styles.inputGroup}>
          <Text style={styles.label}>학력</Text>
          <TouchableOpacity style={styles.dropdown} onPress={() => setModalType('education')}>
            <Text style={[styles.dropdownText, !education && styles.placeholderText]}>{education || '선택'}</Text>
            <Ionicons name="chevron-down" size={20} color="#333" />
          </TouchableOpacity>
        </View>

        <TouchableOpacity
          style={[styles.nextButton, !canSubmit && styles.nextButtonDisabled]}
          onPress={handleNextStep}
          disabled={!canSubmit}
        >
          <Text style={styles.nextButtonText}>다음 단계</Text>
        </TouchableOpacity>
      </ScrollView>

      <SelectorModal visible={modalType === 'city'} title="시/도 선택" data={cityList} onSelect={(val) => { setSelectedCity(val); setSelectedDistrict(''); setModalType(null); }} onClose={() => setModalType(null)} />
      <SelectorModal
        visible={modalType === 'district'}
        title="시/군/구 선택"
        data={selectedCity ? ['전체', ...districts[selectedCity]] : []}
        onSelect={(val) => { setSelectedDistrict(val); setModalType(null); }}
        onClose={() => setModalType(null)}
      />
      <SelectorModal visible={modalType === 'education'} title="학력 선택" data={educationList} onSelect={(val) => { setEducation(val); setModalType(null); }} onClose={() => setModalType(null)} />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F7FDFB' },
  scrollContent: { padding: 25, paddingTop: 40 },
  header: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 10 },
  headerTitle: { fontSize: 26, fontWeight: '800' },
  stepText: { fontSize: 16, color: '#999' },
  progressBarBg: { height: 5, backgroundColor: '#E0E0E0', borderRadius: 10, marginBottom: 35 },
  progressBarFill: { width: '50%', height: '100%', backgroundColor: '#00B894', borderRadius: 10 },
  inputGroup: { marginBottom: 25 },
  label: { fontSize: 15, fontWeight: '700', color: '#444', marginBottom: 12 },
  inlineInput: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#FFF', borderRadius: 14, borderWidth: 1, borderColor: '#EEE', paddingHorizontal: 12 },
  textInput: { flex: 1, paddingVertical: 15, fontSize: 16 },
  unitText: { fontSize: 14, color: '#666' },
  dropdown: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', backgroundColor: '#FFF', padding: 15, borderRadius: 14, borderWidth: 1, borderColor: '#EEE' },
  dropdownText: { fontSize: 16, fontWeight: '600' },
  placeholderText: { color: '#BBB', fontWeight: '400' },
  row: { flexDirection: 'row', justifyContent: 'space-between' },
  grid: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between' },
  choiceBtn: { width: '48%', backgroundColor: '#FFF', padding: 18, borderRadius: 14, borderWidth: 1, borderColor: '#EEE', alignItems: 'center', marginBottom: 12 },
  statusBtn: { flex: 1, backgroundColor: '#FFF', padding: 18, borderRadius: 14, borderWidth: 1, borderColor: '#EEE', alignItems: 'center', marginHorizontal: 4 },
  activeBtn: { backgroundColor: '#00B894', borderColor: '#00B894' },
  activeText: { color: '#FFF', fontWeight: '800' },
  choiceText: { color: '#333', fontWeight: '600' },
  nextButton: { backgroundColor: '#00B894', padding: 20, borderRadius: 30, alignItems: 'center', marginTop: 20, marginBottom: 40 },
  nextButtonDisabled: { backgroundColor: '#A8E6C9' },
  nextButtonText: { color: '#FFF', fontSize: 18, fontWeight: 'bold' },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'center', alignItems: 'center' },
  modalContent: { width: '80%', backgroundColor: '#FFF', borderRadius: 25, padding: 20 },
  modalTitle: { fontSize: 18, fontWeight: '800', marginBottom: 15, textAlign: 'center' },
  modalItem: { paddingVertical: 15, borderBottomWidth: 1, borderBottomColor: '#F0F0F0' },
  modalItemText: { fontSize: 16, textAlign: 'center' },
});
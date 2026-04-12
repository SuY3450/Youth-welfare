import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import React, { useState } from 'react';
import { FlatList, Modal, SafeAreaView, ScrollView, StyleSheet, Text, TextInput, TouchableOpacity, View } from 'react-native';

const cityList = ['서울특별시', '경기도'];
const districts: { [key: string]: string[] } = {
  '서울특별시': ['종로구', '중구', '용산구', '성동구', '광진구', '동대문구', '중랑구', '성북구', '강북구', '도봉구', '노원구', '은평구', '서대문구', '마포구', '양천구', '강서구', '구로구', '금천구', '영등포구', '동작구', '관악구', '서초구', '강남구', '송파구', '강동구'],
  '경기도': ['수원시', '고양시', '용인시', '성남시', '부천시', '화성시', '안산시', '남양주시', '안양시', '평택시', '시흥시', '파주시', '의정부시', '김포시', '광주시', '광명시', '군포시', '하남시', '오산시', '양주시', '이천시', '구리시', '의왕시', '포천시', '양평군', '여주시', '동두천시', '가평군', '과천시', '연천군']
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
  const [age, setAge] = useState('27');
  const [selectedCity, setSelectedCity] = useState('서울특별시');
  const [selectedDistrict, setSelectedDistrict] = useState('마포구');
  const [income, setIncome] = useState('50~100% 이하');
  const [jobStatus, setJobStatus] = useState('구직');
  const [education, setEducation] = useState('대학 졸업');
  const [modalType, setModalType] = useState<string | null>(null);

  const handleNextStep = () => {
    router.push('/InternetScreen');
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
            <TextInput style={styles.textInput} value={age} onChangeText={setAge} keyboardType="number-pad" />
            <Text style={styles.unitText}>(만) 세</Text>
          </View>
        </View>

        <View style={styles.inputGroup}>
          <Text style={styles.label}>거주 지역</Text>
          <View style={styles.row}>
            <TouchableOpacity style={[styles.dropdown, { flex: 1, marginRight: 10 }]} onPress={() => setModalType('city')}>
              <Text style={styles.dropdownText}>{selectedCity}</Text>
              <Ionicons name="chevron-down" size={16} color="#333" />
            </TouchableOpacity>
            <TouchableOpacity style={[styles.dropdown, { flex: 1 }]} onPress={() => setModalType('district')}>
              <Text style={styles.dropdownText}>{selectedDistrict}</Text>
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
            <Text style={styles.dropdownText}>{education}</Text>
            <Ionicons name="chevron-down" size={20} color="#333" />
          </TouchableOpacity>
        </View>

        <TouchableOpacity style={styles.nextButton} onPress={handleNextStep}>
          <Text style={styles.nextButtonText}>다음 단계 →</Text>
        </TouchableOpacity>
      </ScrollView>

      <SelectorModal visible={modalType === 'city'} title="시/도 선택" data={cityList} onSelect={(val) => { setSelectedCity(val); setSelectedDistrict(districts[val][0]); setModalType(null); }} onClose={() => setModalType(null)} />
      <SelectorModal visible={modalType === 'district'} title="구/시 선택" data={districts[selectedCity]} onSelect={(val) => { setSelectedDistrict(val); setModalType(null); }} onClose={() => setModalType(null)} />
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
  progressBarFill: { width: '50%', height: '100%', backgroundColor: '#67B292', borderRadius: 10 },
  inputGroup: { marginBottom: 25 },
  label: { fontSize: 15, fontWeight: '700', color: '#444', marginBottom: 12 },
  inlineInput: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#FFF', borderRadius: 14, borderWidth: 1, borderColor: '#EEE', paddingHorizontal: 12 },
  textInput: { flex: 1, paddingVertical: 15, fontSize: 16 },
  unitText: { fontSize: 14, color: '#666' },
  dropdown: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', backgroundColor: '#FFF', padding: 15, borderRadius: 14, borderWidth: 1, borderColor: '#EEE' },
  dropdownText: { fontSize: 16, fontWeight: '600' },
  row: { flexDirection: 'row', justifyContent: 'space-between' },
  grid: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between' },
  choiceBtn: { width: '48%', backgroundColor: '#FFF', padding: 18, borderRadius: 14, borderWidth: 1, borderColor: '#EEE', alignItems: 'center', marginBottom: 12 },
  statusBtn: { flex: 1, backgroundColor: '#FFF', padding: 18, borderRadius: 14, borderWidth: 1, borderColor: '#EEE', alignItems: 'center', marginHorizontal: 4 },
  activeBtn: { backgroundColor: '#67B292', borderColor: '#67B292' },
  activeText: { color: '#FFF', fontWeight: '800' },
  choiceText: { color: '#333', fontWeight: '600' },
  nextButton: { backgroundColor: '#67B292', padding: 20, borderRadius: 30, alignItems: 'center', marginTop: 20, marginBottom: 40 },
  nextButtonText: { color: '#FFF', fontSize: 18, fontWeight: 'bold' },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'center', alignItems: 'center' },
  modalContent: { width: '80%', backgroundColor: '#FFF', borderRadius: 25, padding: 20 },
  modalTitle: { fontSize: 18, fontWeight: '800', marginBottom: 15, textAlign: 'center' },
  modalItem: { paddingVertical: 15, borderBottomWidth: 1, borderBottomColor: '#F0F0F0' },
  modalItemText: { fontSize: 16, textAlign: 'center' },
});
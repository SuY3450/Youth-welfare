import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { SafeAreaView, ScrollView, StyleSheet, Switch, Text, TouchableOpacity, View } from 'react-native';
import { useState } from 'react';

export default function MyPageScreen() {
  const router = useRouter();
  const [alarmEnabled, setAlarmEnabled] = useState(true);

  return (
    <SafeAreaView style={styles.wrap}>
      <ScrollView style={styles.container} showsVerticalScrollIndicator={false}>

        {/* 제목 */}
        <Text style={styles.pageTitle}>마이페이지</Text>

        {/* 프로필 카드 */}
        <View style={styles.profileCard}>
          {/* 프로필 정보 */}
          <View style={styles.profileTop}>
            <View style={styles.avatar}>
              <Ionicons name="person" size={36} color="#fff" />
            </View>
            <View style={styles.profileInfo}>
              <Text style={styles.profileName}>홍길동</Text>
              <Text style={styles.profileSub}>27세 (1998년생) · 서울특별시 마포구</Text>
            </View>
          </View>

          {/* 태그 */}
          <View style={styles.tagRow}>
            <View style={styles.tag}><Text style={styles.tagText}>소득 50~100%</Text></View>
            <View style={styles.tag}><Text style={styles.tagText}>구직</Text></View>
            <View style={styles.tag}><Text style={styles.tagText}>대학교 졸업</Text></View>
          </View>

          {/* 프로필 수정 버튼 */}
          <TouchableOpacity style={styles.editButton}>
            <Text style={styles.editButtonText}>프로필 수정하기</Text>
          </TouchableOpacity>
        </View>

        {/* 통계 카드 */}
        <View style={styles.statsCard}>
          <View style={styles.statItem}>
            <Text style={styles.statNumber}>12</Text>
            <Text style={styles.statLabel}>매칭 정책</Text>
          </View>
          <View style={styles.statDivider} />
          <View style={styles.statItem}>
            <Text style={[styles.statNumber, { color: '#00C49A' }]}>3</Text>
            <Text style={styles.statLabel}>신청 가능</Text>
          </View>
          <View style={styles.statDivider} />
          <View style={styles.statItem}>
            <Text style={[styles.statNumber, { color: '#FF8C00' }]}>780만</Text>
            <Text style={styles.statLabel}>예상 수혜</Text>
          </View>
        </View>

        {/* 관심 분야 */}
        <View style={styles.sectionCard}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>관심 분야</Text>
            <TouchableOpacity>
              <Text style={styles.sectionEdit}>편집</Text>
            </TouchableOpacity>
          </View>
          <View style={styles.interestRow}>
            <View style={styles.interestTag}><Text style={styles.interestText}>🏠 주거</Text></View>
            <View style={styles.interestTag}><Text style={styles.interestText}>💼 취업</Text></View>
            <View style={styles.interestTag}><Text style={styles.interestText}>💰 금융</Text></View>
          </View>
        </View>

        {/* 설정 카드 */}
        <View style={styles.sectionCard}>
          {/* 알림 설정 */}
          <View style={styles.settingItem}>
            <View style={styles.settingLeft}>
              <Text style={styles.settingIcon}>🔔</Text>
              <View>
                <Text style={styles.settingTitle}>알림 설정</Text>
                <Text style={styles.settingDesc}>마감 알림, 새 정책 알림</Text>
              </View>
            </View>
            <Switch
              value={alarmEnabled}
              onValueChange={setAlarmEnabled}
              trackColor={{ false: '#ddd', true: '#00C49A' }}
              thumbColor={'#fff'}
            />
          </View>

          <View style={styles.divider} />

          {/* 내 서류 보관함 */}
          <TouchableOpacity style={styles.settingItem}>
            <View style={styles.settingLeft}>
              <Text style={styles.settingIcon}>📄</Text>
              <View>
                <Text style={styles.settingTitle}>내 서류 보관함</Text>
                <Text style={styles.settingDesc}>업로드한 서류 관리</Text>
              </View>
            </View>
            <Ionicons name="chevron-forward" size={18} color="#aaa" />
          </TouchableOpacity>
        </View>

        {/* 로그아웃 버튼 */}
        <TouchableOpacity style={styles.logoutButton}>
          <Text style={styles.logoutText}>로그아웃</Text>
        </TouchableOpacity>

        <View style={{ height: 20 }} />
      </ScrollView>

      {/* 하단 탭바 */}
      <View style={styles.bottomTab}>
        <TouchableOpacity style={styles.tabItem} onPress={() => router.push('/')}>
          <Ionicons name="home-outline" size={24} color="#999" />
          <Text style={styles.tabText}>홈</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.tabItem}>
          <Ionicons name="grid-outline" size={24} color="#999" />
          <Text style={styles.tabText}>일정</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.tabItem}>
          <Ionicons name="person-circle" size={24} color="#67B292" />
          <Text style={[styles.tabText, { color: '#67B292' }]}>마이</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: '#F7FDFB' },
  container: { flex: 1, paddingHorizontal: 20 },

  // 제목
  pageTitle: { fontSize: 26, fontWeight: '800', color: '#111', marginTop: 16, marginBottom: 16 },

  // 프로필 카드
  profileCard: { backgroundColor: '#00C49A', borderRadius: 20, padding: 20, marginBottom: 16 },
  profileTop: { flexDirection: 'row', alignItems: 'center', marginBottom: 14 },
  avatar: { width: 56, height: 56, borderRadius: 28, backgroundColor: 'rgba(255,255,255,0.3)', justifyContent: 'center', alignItems: 'center', marginRight: 14 },
  profileInfo: {},
  profileName: { color: '#fff', fontSize: 20, fontWeight: 'bold', marginBottom: 4 },
  profileSub: { color: 'rgba(255,255,255,0.85)', fontSize: 12 },
  tagRow: { flexDirection: 'row', gap: 8, marginBottom: 16 },
  tag: { backgroundColor: 'rgba(255,255,255,0.25)', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 20 },
  tagText: { color: '#fff', fontSize: 12, fontWeight: '600' },
  editButton: { backgroundColor: '#fff', borderRadius: 12, paddingVertical: 14, alignItems: 'center' },
  editButtonText: { color: '#00C49A', fontWeight: 'bold', fontSize: 15 },

  // 통계 카드
  statsCard: { backgroundColor: '#fff', borderRadius: 16, padding: 20, marginBottom: 16, flexDirection: 'row', alignItems: 'center', shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 8, elevation: 2 },
  statItem: { flex: 1, alignItems: 'center' },
  statNumber: { fontSize: 24, fontWeight: '800', color: '#111', marginBottom: 4 },
  statLabel: { fontSize: 12, color: '#888' },
  statDivider: { width: 1, height: 40, backgroundColor: '#eee' },

  // 섹션 카드
  sectionCard: { backgroundColor: '#fff', borderRadius: 16, padding: 18, marginBottom: 16, shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 8, elevation: 2 },
  sectionHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 },
  sectionTitle: { fontSize: 16, fontWeight: 'bold', color: '#111' },
  sectionEdit: { color: '#00C49A', fontSize: 14 },
  interestRow: { flexDirection: 'row', gap: 8 },
  interestTag: { backgroundColor: '#f0faf5', paddingHorizontal: 14, paddingVertical: 8, borderRadius: 20 },
  interestText: { color: '#333', fontSize: 14 },

  // 설정 아이템
  settingItem: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 6 },
  settingLeft: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  settingIcon: { fontSize: 24 },
  settingTitle: { fontSize: 15, fontWeight: '600', color: '#111', marginBottom: 2 },
  settingDesc: { fontSize: 12, color: '#888' },
  divider: { height: 1, backgroundColor: '#f0f0f0', marginVertical: 12 },

  // 로그아웃
  logoutButton: { backgroundColor: '#fff', borderRadius: 16, paddingVertical: 18, alignItems: 'center', shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 8, elevation: 2 },
  logoutText: { color: '#FF4444', fontSize: 16, fontWeight: 'bold' },

  // 하단 탭바
  bottomTab: { flexDirection: 'row', height: 80, backgroundColor: '#FFF', borderTopWidth: 1, borderTopColor: '#EEE', paddingBottom: 20 },
  tabItem: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  tabText: { fontSize: 12, marginTop: 4, color: '#999', fontWeight: '600' },
});

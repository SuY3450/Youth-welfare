import { Ionicons } from '@expo/vector-icons';
import { usePathname, useRouter } from 'expo-router';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';

export default function BottomTabBar() {
  const router = useRouter();
  const pathname = usePathname();

  const tabs = [
    { name: '홈', icon: 'home-outline', activeIcon: 'home', path: '/' },
    { name: '복지봇', icon: 'chatbubble-outline', activeIcon: 'chatbubble', path: '/(tabs)/chat' },
    { name: '마이', icon: 'person-outline', activeIcon: 'person', path: '/mypage' },
  ];

  return (
    <View style={styles.container}>
      {tabs.map((tab) => {
        const isActive = pathname === tab.path || 
          (tab.path === '/' && pathname === '/index');
        return (
          <TouchableOpacity
            key={tab.name}
            style={styles.tab}
            onPress={() => router.push(tab.path as any)}
          >
            <Ionicons
              name={isActive ? tab.activeIcon as any : tab.icon as any}
              size={24}
              color={isActive ? '#00C49A' : '#999'}
            />
            <Text style={[styles.tabText, isActive && styles.tabTextActive]}>
              {tab.name}
            </Text>
          </TouchableOpacity>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    height: 80,
    backgroundColor: '#FFF',
    borderTopWidth: 1,
    borderTopColor: '#EEE',
    paddingBottom: 20,
  },
  tab: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  tabText: { fontSize: 12, marginTop: 4, color: '#999', fontWeight: '600' },
  tabTextActive: { color: '#00C49A' },
});
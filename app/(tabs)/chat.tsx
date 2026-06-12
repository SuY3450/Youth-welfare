import { Ionicons } from '@expo/vector-icons';
import * as DocumentPicker from 'expo-document-picker';
import { useRouter } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  SafeAreaView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { API_URL } from '../../constants/api';
import { supabase } from '../../constants/supabase';

interface Message {
  id: string;
  role: 'user' | 'ai';
  text: string;
  time: string;
  isPdf?: boolean;
}

const SUGGESTIONS = [
  '취업 관련 정책 알려줘',
  '소득 기준이 어떻게 돼?',
  '신청 방법 알려줘',
];

const getTime = () => {
  const now = new Date();
  const h = now.getHours();
  const m = now.getMinutes().toString().padStart(2, '0');
  const ampm = h >= 12 ? '오후' : '오전';
  return `${ampm} ${h > 12 ? h - 12 : h}:${m}`;
};

export default function ChatScreen() {
  const router = useRouter();
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'ai',
      text: '안녕하세요! 저는 복지봇이에요 🤖\n청년 복지 혜택에 대해 무엇이든 물어보세요!\n\nPDF 파일을 업로드하면 내용을 분석해드려요 📄',
      time: getTime(),
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [pdfText, setPdfText] = useState('');
  const [isLoggedIn, setIsLoggedIn] = useState<boolean | null>(null);
  const flatListRef = useRef<FlatList>(null);

  // 로그인 상태 확인
  useEffect(() => {
    const checkLogin = async () => {
      const { data: { user } } = await supabase.auth.getUser();
      setIsLoggedIn(!!user);
    };
    checkLogin();
  }, []);

  const sendMessage = async (text?: string) => {
    const messageText = text || input.trim();
    if (!messageText || loading) return;

    // 로그인 체크
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) {
      Alert.alert(
        '로그인 필요',
        '로그인 후 이용해주세요.',
        [
          { text: '취소', style: 'cancel' },
          { text: '로그인', onPress: () => router.push('/login/login1') },
        ]
      );
      return;
    }

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      text: messageText,
      time: getTime(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await fetch(`${API_URL}/welfare/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: messageText,
          user_id: user?.id || '',
          pdf_context: pdfText || '',
        }),
      });
      console.log('챗봇 응답 상태:', response.status);
      const data = await response.json();
      console.log('챗봇 응답:', JSON.stringify(data));
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'ai',
        text: data.reply || '죄송해요, 답변을 가져오지 못했어요.',
        time: getTime(),
      };
      setMessages(prev => [...prev, aiMessage]);
    } catch (e) {
      console.log('챗봇 에러:', e);
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'ai',
        text: '네트워크 오류가 발생했어요. 다시 시도해주세요.',
        time: getTime(),
      };
      setMessages(prev => [...prev, aiMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handlePdfUpload = async () => {
    // 로그인 체크
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) {
      Alert.alert(
        '로그인 필요',
        '로그인 후 이용해주세요.',
        [
          { text: '취소', style: 'cancel' },
          { text: '로그인', onPress: () => router.push('/login/login1') },
        ]
      );
      return;
    }

    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: 'application/pdf',
        copyToCacheDirectory: true,
      });

      if (result.canceled) return;

      const file = result.assets[0];

      const userMessage: Message = {
        id: Date.now().toString(),
        role: 'user',
        text: `📄 ${file.name}`,
        time: getTime(),
        isPdf: true,
      };
      setMessages(prev => [...prev, userMessage]);
      setLoading(true);

      const formData = new FormData();
      formData.append('file', {
        uri: file.uri,
        name: file.name,
        type: 'application/pdf',
      } as any);
      formData.append('user_id', user?.id || '');

      const response = await fetch(`${API_URL}/welfare/chat/pdf`, {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();

      if (data.pdf_text) {
        setPdfText(data.pdf_text);
      }

      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'ai',
        text: data.reply || 'PDF를 분석했어요!',
        time: getTime(),
      };
      setMessages(prev => [...prev, aiMessage]);

      const guideMessage: Message = {
        id: (Date.now() + 2).toString(),
        role: 'ai',
        text: '📎 PDF 내용을 기반으로 추가 질문도 가능해요!\n예: "신청 자격이 뭐야?" "필요 서류 알려줘" "마감일이 언제야?"',
        time: getTime(),
      };
      setMessages(prev => [...prev, guideMessage]);

    } catch (e) {
      Alert.alert('오류', 'PDF 업로드 중 오류가 발생했어요.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setTimeout(() => flatListRef.current?.scrollToEnd({ animated: true }), 100);
  }, [messages]);

  // 로그인 안 된 화면
  if (isLoggedIn === false) {
    return (
      <SafeAreaView style={styles.wrap}>
        <View style={styles.header}>
          <View style={styles.headerAvatar}>
            <Text style={styles.headerAvatarText}>🤖</Text>
          </View>
          <View style={{ flex: 1 }}>
            <Text style={styles.headerTitle}>복지봇</Text>
          </View>
        </View>
        <View style={styles.loginRequired}>
          <Text style={styles.loginRequiredIcon}>🔒</Text>
          <Text style={styles.loginRequiredTitle}>로그인이 필요해요</Text>
          <Text style={styles.loginRequiredSub}>복지봇을 이용하려면 로그인해주세요</Text>
          <TouchableOpacity
            style={styles.loginBtn}
            onPress={() => router.push('/login/login1')}
          >
            <Text style={styles.loginBtnText}>로그인하러 가기</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  const renderMessage = ({ item }: { item: Message }) => (
    <View style={[styles.msgRow, item.role === 'user' && styles.msgRowUser]}>
      {item.role === 'ai' && (
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>🤖</Text>
        </View>
      )}
      <View style={[
        styles.bubble,
        item.role === 'user' ? styles.bubbleUser : styles.bubbleAi,
        item.isPdf && styles.bubblePdf,
      ]}>
        {item.isPdf && (
          <View style={styles.pdfBadge}>
            <Ionicons name="document-text" size={12} color="#00A582" />
            <Text style={styles.pdfBadgeText}>PDF</Text>
          </View>
        )}
        <Text style={item.role === 'user' ? styles.bubbleTextUser : styles.bubbleTextAi}>
          {item.text}
        </Text>
        <Text style={[styles.timeText, item.role === 'user' && { color: 'rgba(255,255,255,0.7)' }]}>
          {item.time}
        </Text>
      </View>
    </View>
  );

  return (
    <SafeAreaView style={styles.wrap}>
      {/* 헤더 */}
      <View style={styles.header}>
        <View style={styles.headerAvatar}>
          <Text style={styles.headerAvatarText}>🤖</Text>
        </View>
        <View style={{ flex: 1 }}>
          <Text style={styles.headerTitle}>복지봇</Text>
          <View style={styles.onlineRow}>
            <View style={styles.onlineDot} />
            <Text style={styles.onlineText}>온라인</Text>
          </View>
        </View>
        {pdfText ? (
          <View style={styles.pdfActiveBadge}>
            <Ionicons name="document-text" size={12} color="#00A582" />
            <Text style={styles.pdfActiveText}>PDF 분석 중</Text>
          </View>
        ) : null}
      </View>

      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        keyboardVerticalOffset={90}
      >
        <FlatList
          ref={flatListRef}
          data={messages}
          keyExtractor={(item) => item.id}
          renderItem={renderMessage}
          contentContainerStyle={styles.messageList}
          showsVerticalScrollIndicator={false}
          ListFooterComponent={
            loading ? (
              <View style={styles.msgRow}>
                <View style={styles.avatar}>
                  <Text style={styles.avatarText}>🤖</Text>
                </View>
                <View style={styles.typingBubble}>
                  <ActivityIndicator size="small" color="#00C49A" />
                  <Text style={styles.typingText}>답변 중...</Text>
                </View>
              </View>
            ) : null
          }
        />

        {messages.length <= 1 && (
          <View style={styles.suggestions}>
            {SUGGESTIONS.map((s, i) => (
              <TouchableOpacity key={i} style={styles.sugBtn} onPress={() => sendMessage(s)}>
                <Text style={styles.sugText}>{s}</Text>
              </TouchableOpacity>
            ))}
          </View>
        )}

        <View style={styles.inputArea}>
          <TouchableOpacity style={styles.pdfBtn} onPress={handlePdfUpload}>
            <Ionicons name="document-attach" size={22} color="#00C49A" />
          </TouchableOpacity>
          <TextInput
            style={styles.input}
            placeholder="복지봇에게 물어보세요"
            placeholderTextColor="#BBB"
            value={input}
            onChangeText={setInput}
            multiline
            maxLength={200}
          />
          <TouchableOpacity
            style={[styles.sendBtn, (!input.trim() || loading) && styles.sendBtnDisabled]}
            onPress={() => sendMessage()}
            disabled={!input.trim() || loading}
          >
            <Ionicons name="send" size={18} color="#fff" />
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: '#F7FDFB' },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: '#fff',
    borderBottomWidth: 0.5,
    borderBottomColor: '#EEF2F0',
  },
  headerAvatar: {
    width: 40, height: 40, borderRadius: 20,
    backgroundColor: '#E6F9F4',
    justifyContent: 'center', alignItems: 'center',
  },
  headerAvatarText: { fontSize: 20 },
  headerTitle: { fontSize: 16, fontWeight: '700', color: '#111' },
  onlineRow: { flexDirection: 'row', alignItems: 'center', gap: 4, marginTop: 2 },
  onlineDot: { width: 6, height: 6, borderRadius: 3, backgroundColor: '#00C49A' },
  onlineText: { fontSize: 11, color: '#00C49A', fontWeight: '600' },
  pdfActiveBadge: {
    flexDirection: 'row', alignItems: 'center', gap: 4,
    backgroundColor: '#E6F9F4', paddingHorizontal: 10, paddingVertical: 5,
    borderRadius: 12, borderWidth: 0.5, borderColor: '#C8EDE3',
  },
  pdfActiveText: { fontSize: 11, color: '#00A582', fontWeight: '600' },
  messageList: { padding: 16, gap: 12 },
  msgRow: { flexDirection: 'row', alignItems: 'flex-end', gap: 8, marginBottom: 12 },
  msgRowUser: { flexDirection: 'row-reverse' },
  avatar: {
    width: 32, height: 32, borderRadius: 16,
    backgroundColor: '#E6F9F4',
    justifyContent: 'center', alignItems: 'center', flexShrink: 0,
  },
  avatarText: { fontSize: 16 },
  bubble: { maxWidth: '72%', padding: 10, borderRadius: 16 },
  bubbleAi: {
    backgroundColor: '#F0FBF7',
    borderBottomLeftRadius: 4,
    borderWidth: 0.5, borderColor: '#C8EDE3',
  },
  bubbleUser: { backgroundColor: '#00C49A', borderBottomRightRadius: 4 },
  bubblePdf: {
    backgroundColor: '#E6F9F4',
    borderWidth: 1, borderColor: '#00C49A',
  },
  pdfBadge: {
    flexDirection: 'row', alignItems: 'center', gap: 3,
    marginBottom: 4,
  },
  pdfBadgeText: { fontSize: 10, color: '#00A582', fontWeight: '700' },
  bubbleTextAi: { fontSize: 14, color: '#222', lineHeight: 20 },
  bubbleTextUser: { fontSize: 14, color: '#fff', lineHeight: 20 },
  timeText: { fontSize: 10, color: '#999', marginTop: 4, textAlign: 'right' },
  typingBubble: {
    flexDirection: 'row', alignItems: 'center', gap: 8,
    backgroundColor: '#F0FBF7', borderRadius: 16, borderBottomLeftRadius: 4,
    padding: 10, borderWidth: 0.5, borderColor: '#C8EDE3',
  },
  typingText: { fontSize: 13, color: '#00C49A' },
  suggestions: { paddingHorizontal: 16, paddingBottom: 8, gap: 8 },
  sugBtn: {
    backgroundColor: '#F0FBF7', borderWidth: 0.5, borderColor: '#C8EDE3',
    borderRadius: 20, paddingHorizontal: 14, paddingVertical: 8, alignSelf: 'flex-start',
  },
  sugText: { fontSize: 13, color: '#00A582', fontWeight: '600' },
  inputArea: {
    flexDirection: 'row', alignItems: 'center', gap: 8,
    paddingHorizontal: 16, paddingVertical: 10,
    backgroundColor: '#fff', borderTopWidth: 0.5, borderTopColor: '#EEF2F0',
  },
  pdfBtn: {
    width: 40, height: 40, borderRadius: 20,
    backgroundColor: '#E6F9F4',
    justifyContent: 'center', alignItems: 'center',
  },
  input: {
    flex: 1, backgroundColor: '#F7FDFB',
    borderWidth: 0.5, borderColor: '#C8EDE3',
    borderRadius: 20, paddingHorizontal: 16, paddingVertical: 10,
    fontSize: 14, color: '#111', maxHeight: 100,
  },
  sendBtn: {
    width: 40, height: 40, borderRadius: 20,
    backgroundColor: '#00C49A',
    justifyContent: 'center', alignItems: 'center',
  },
  sendBtnDisabled: { backgroundColor: '#A8E6C9' },

  // 로그인 필요 화면
  loginRequired: {
    flex: 1, justifyContent: 'center', alignItems: 'center', paddingHorizontal: 40,
  },
  loginRequiredIcon: { fontSize: 60, marginBottom: 20 },
  loginRequiredTitle: { fontSize: 20, fontWeight: '800', color: '#111', marginBottom: 8 },
  loginRequiredSub: { fontSize: 14, color: '#888', marginBottom: 32, textAlign: 'center' },
  loginBtn: {
    backgroundColor: '#00C49A', paddingVertical: 14, paddingHorizontal: 40,
    borderRadius: 30, shadowColor: '#00C49A', shadowOpacity: 0.3, shadowRadius: 10, elevation: 4,
  },
  loginBtnText: { color: '#fff', fontSize: 16, fontWeight: '800' },
});
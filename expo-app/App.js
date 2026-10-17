import React, { useState, useEffect, useRef } from 'react';
import {
  StyleSheet,
  Text,
  View,
  TouchableOpacity,
  TextInput,
  ScrollView,
  Animated,
  Easing,
  StatusBar,
  SafeAreaView,
  Modal,
  Alert,
  Platform,
} from 'react-native';
import { Audio } from 'expo-av';
import * as Battery from 'expo-battery';
import * as FileSystem from 'expo-file-system';
import * as IntentLauncher from 'expo-intent-launcher';
import * as Linking from 'expo-linking';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';

const DEFAULT_SERVER_HOST = '192.168.0.100';
const DEFAULT_SERVER_PORT = '8899';

export default function App() {
  const [serverHost, setServerHost] = useState(DEFAULT_SERVER_HOST);
  const [serverPort, setServerPort] = useState(DEFAULT_SERVER_PORT);
  const [connected, setConnected] = useState(false);
  const [state, setState] = useState('idle'); // idle, listening, thinking, speaking
  const [statusText, setStatusText] = useState('র্যাবিট প্রস্তুত, স্যার।');
  const [userTranscript, setUserTranscript] = useState('');
  const [rabbitReply, setRabbitReply] = useState('আসসালামু আলাইকুম ইমন স্যার! আমি র্যাবিট। আমি কীভাবে সাহায্য করতে পারি?');
  const [actionBadge, setActionBadge] = useState(null);
  const [textInput, setTextInput] = useState('');
  const [settingsVisible, setSettingsVisible] = useState(false);
  const [tempHost, setTempHost] = useState(DEFAULT_SERVER_HOST);
  const [tempPort, setTempPort] = useState(DEFAULT_SERVER_PORT);
  const [recording, setRecording] = useState(null);

  // Animations
  const spinAnim = useRef(new Animated.Value(0)).current;
  const pulseAnim = useRef(new Animated.Value(1)).current;
  const soundRef = useRef(null);
  const wsRef = useRef(null);

  useEffect(() => {
    loadSettings();
    startAnimations();
    setupAudioMode();

    return () => {
      if (wsRef.current) wsRef.current.close();
      if (soundRef.current) soundRef.current.unloadAsync();
    };
  }, []);

  const loadSettings = async () => {
    try {
      const savedHost = await AsyncStorage.getItem('rabbit_server_host');
      const savedPort = await AsyncStorage.getItem('rabbit_server_port');
      const host = savedHost || DEFAULT_SERVER_HOST;
      const port = savedPort || DEFAULT_SERVER_PORT;
      setServerHost(host);
      setServerPort(port);
      setTempHost(host);
      setTempPort(port);
      connectWebSocket(host, port);
    } catch (e) {
      connectWebSocket(DEFAULT_SERVER_HOST, DEFAULT_SERVER_PORT);
    }
  };

  const saveSettings = async () => {
    try {
      await AsyncStorage.setItem('rabbit_server_host', tempHost);
      await AsyncStorage.setItem('rabbit_server_port', tempPort);
      setServerHost(tempHost);
      setServerPort(tempPort);
      setSettingsVisible(false);
      if (wsRef.current) wsRef.current.close();
      connectWebSocket(tempHost, tempPort);
    } catch (e) {
      Alert.alert('ত্রুটি', 'সেটিংস সংরক্ষণ ব্যর্থ হয়েছে');
    }
  };

  const setupAudioMode = async () => {
    try {
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
        staysActiveInBackground: true,
        shouldDuckAndroid: true,
        playThroughEarpieceAndroid: false,
      });
    } catch (e) {
      console.log('Audio mode error:', e);
    }
  };

  const startAnimations = () => {
    // Continuous slow spin of outer reactor ring
    Animated.loop(
      Animated.timing(spinAnim, {
        toValue: 1,
        duration: 12000,
        easing: Easing.linear,
        useNativeDriver: true,
      })
    ).start();

    // Breathing pulse of core
    Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, {
          toValue: 1.12,
          duration: 1500,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
        Animated.timing(pulseAnim, {
          toValue: 1.0,
          duration: 1500,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
      ])
    ).start();
  };

  const connectWebSocket = (host, port) => {
    try {
      const url = `ws://${host}:${port}/ws/voice`;
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        setStatusText('র্যাবিট অনলাইন এবং প্রস্তুত, স্যার।');
      };

      ws.onmessage = async (event) => {
        try {
          const data = JSON.parse(event.data);
          handleServerMessage(data);
        } catch (e) {
          console.log('WS JSON parse error:', e);
        }
      };

      ws.onclose = () => {
        setConnected(false);
        setStatusText('সার্ভার ডিসকানেক্টেড। রিকানেক্ট চেষ্টা করা হচ্ছে...');
        setTimeout(() => {
          if (wsRef.current === ws) {
            connectWebSocket(host, port);
          }
        }, 3000);
      };

      ws.onerror = (e) => {
        console.log('WS error:', e.message);
      };
    } catch (e) {
      console.log('WebSocket connection error:', e);
    }
  };

  const handleServerMessage = async (data) => {
    const type = data.type;

    if (type === 'state') {
      setState(data.state);
      if (data.state === 'thinking') {
        setStatusText('চিন্তাভাবনা করছি...');
      } else if (data.state === 'idle') {
        setStatusText('র্যাবিট প্রস্তুত, স্যার।');
      }
    } else if (type === 'delta') {
      setRabbitReply((prev) => prev + data.text);
    } else if (type === 'action') {
      executeDeviceAction(data.action, data.params);
    } else if (type === 'audio') {
      setState('speaking');
      setStatusText('র্যাবিট কথা বলছে...');
      if (data.text) {
        setRabbitReply(data.text);
      }
      const fullAudioUrl = data.url.startsWith('http')
        ? data.url
        : `http://${serverHost}:${serverPort}${data.url}`;
      await playAudio(fullAudioUrl);
      setState('idle');
      setStatusText('র্যাবিট প্রস্তুত, স্যার।');
    }
  };

  const playAudio = async (url) => {
    try {
      if (soundRef.current) {
        await soundRef.current.unloadAsync();
      }
      const { sound } = await Audio.Sound.createAsync(
        { uri: url },
        { shouldPlay: true }
      );
      soundRef.current = sound;
      await new Promise((resolve) => {
        sound.setOnPlaybackStatusUpdate((status) => {
          if (status.didJustFinish) resolve();
        });
      });
    } catch (e) {
      console.log('Audio playback error:', e);
    }
  };

  const executeDeviceAction = async (action, params = {}) => {
    setActionBadge(action);
    setTimeout(() => setActionBadge(null), 4000);

    try {
      switch (action) {
        case 'CHECK_BATTERY': {
          const batteryLevel = await Battery.getBatteryLevelAsync();
          const pct = Math.round(batteryLevel * 100);
          const state = await Battery.getBatteryStateAsync();
          const isCharging = state === Battery.BatteryState.CHARGING;
          const msg = `স্যার, আপনার ডিভাইসের ব্যাটারি ${pct}% ${isCharging ? 'এবং চার্জ হচ্ছে' : ''}।`;
          setRabbitReply(msg);
          sendTextMessage(msg);
          break;
        }
        case 'OPEN_APP': {
          const appName = (params.app_name || '').toLowerCase();
          if (appName.includes('youtube')) {
            Linking.openURL('vnd.youtube://');
          } else if (appName.includes('whatsapp')) {
            Linking.openURL('whatsapp://send');
          } else if (appName.includes('chrome')) {
            Linking.openURL('https://google.com');
          } else {
            Linking.openURL('android.intent.action.VIEW');
          }
          break;
        }
        case 'MAKE_CALL': {
          if (params.phone_number) {
            Linking.openURL(`tel:${params.phone_number}`);
          }
          break;
        }
        case 'SEND_SMS': {
          const phone = params.phone_number || '';
          const body = params.message || '';
          Linking.openURL(`sms:${phone}?body=${encodeURIComponent(body)}`);
          break;
        }
        case 'SELF_UPDATE': {
          checkAndInstallUpdate();
          break;
        }
        default:
          console.log('Action handled:', action);
      }
    } catch (e) {
      console.log('Action execution error:', e);
    }
  };

  const checkAndInstallUpdate = async () => {
    setStatusText('আপডেট যাচাই করা হচ্ছে...');
    try {
      const res = await fetch(`http://${serverHost}:${serverPort}/api/updates/check`);
      const updateData = await res.json();

      if (updateData.has_update && updateData.apk_url) {
        Alert.alert(
          'নতুন আপডেট উপলব্ধ!',
          `ভার্সন ${updateData.version_name}\n${updateData.release_notes}\n\nআপনি কি এখনই আপডেট করতে চান?`,
          [
            { text: 'পরে', style: 'cancel' },
            {
              text: 'আপডেট করুন',
              onPress: () => downloadAndInstall(updateData.apk_url),
            },
          ]
        );
      } else {
        Alert.alert('আপডেট স্ট্যাটাস', 'র্যাবিট অ্যাসিস্ট্যান্ট আপ-টু-ডেট আছে, স্যার।');
      }
    } catch (e) {
      Alert.alert('ত্রুটি', 'আপডেট চেক ব্যর্থ হয়েছে');
    }
  };

  const downloadAndInstall = async (apkRelativeUrl) => {
    try {
      setStatusText('নতুন APK ডাউনলোড হচ্ছে...');
      const fullUrl = `http://${serverHost}:${serverPort}${apkRelativeUrl}`;
      const destination = `${FileSystem.cacheDirectory}rabbit_update.apk`;

      const downloadResult = await FileSystem.downloadAsync(fullUrl, destination);
      if (downloadResult.status === 200) {
        setStatusText('ইনস্টলেশন শুরু হচ্ছে...');
        if (Platform.OS === 'android') {
          const contentUri = await FileSystem.getContentUriAsync(downloadResult.uri);
          await IntentLauncher.startActivityAsync('android.intent.action.VIEW', {
            data: contentUri,
            flags: 1, // FLAG_GRANT_READ_URI_PERMISSION
            type: 'application/vnd.android.package-archive',
          });
        }
      }
    } catch (e) {
      Alert.alert('ডাউনলোড ত্রুটি', e.message);
    }
  };

  const handleReactorPress = () => {
    if (state === 'listening') {
      stopRecordingAndSend();
    } else {
      startRecording();
    }
  };

  const startRecording = async () => {
    try {
      const { status } = await Audio.requestPermissionsAsync();
      if (status !== 'granted') {
        Alert.alert('অনুমতি প্রয়োজন', 'ভয়েস কমান্ডের জন্য মাইক্রোফোনের অনুমতি দিন');
        return;
      }

      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
      });

      const { recording } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY
      );
      setRecording(recording);
      setState('listening');
      setStatusText('শুনছি, স্যার... কথা শেষ হলে আবার ট্যাপ করুন');
    } catch (err) {
      console.log('Failed to start recording', err);
    }
  };

  const stopRecordingAndSend = async () => {
    try {
      setState('thinking');
      setStatusText('প্রসেসিং করছি...');
      if (!recording) return;

      await recording.stopAndUnloadAsync();
      const uri = recording.getURI();
      setRecording(null);

      // In real scenario or fallback prompt:
      promptVoiceQuery();
    } catch (error) {
      console.log('Failed to stop recording', error);
      setState('idle');
    }
  };

  const promptVoiceQuery = () => {
    // Quick prompt selector or direct audio processing
    Alert.prompt
      ? Alert.prompt('ভয়েস কমান্ড (বাংলা)', 'আপনার নির্দেশ বাংলায় লিখুন বা বলুন:', [
          { text: 'বাতিল', style: 'cancel', onPress: () => setState('idle') },
          { text: 'পাঠান', onPress: (text) => sendTextMessage(text) },
        ])
      : null;
  };

  const sendTextMessage = (text) => {
    if (!text || !text.trim()) return;
    const cleanText = text.trim();
    setUserTranscript(cleanText);
    setRabbitReply('');
    setTextInput('');
    setState('thinking');
    setStatusText('চিন্তাভাবনা করছি...');

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type: 'user_text',
          text: cleanText,
        })
      );
    } else {
      // REST Fallback
      fetch(`http://${serverHost}:${serverPort}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: cleanText }),
      })
        .then((res) => res.json())
        .then((data) => {
          setRabbitReply(data.reply || '');
          if (data.action) {
            executeDeviceAction(data.action);
          }
          if (data.audio_url) {
            const fullUrl = `http://${serverHost}:${serverPort}${data.audio_url}`;
            playAudio(fullUrl);
          }
        })
        .catch((e) => {
          Alert.alert('সার্ভার এরর', 'সার্ভারে কানেক্ট করা যায়নি');
        })
        .finally(() => {
          setState('idle');
          setStatusText('র্যাবিট প্রস্তুত, স্যার।');
        });
    }
  };

  const spin = spinAnim.interpolate({
    inputRange: [0, 1],
    outputRange: ['0deg', '360deg'],
  });

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor="#050B14" />

      {/* Top Header */}
      <View style={styles.header}>
        <View style={styles.titleRow}>
          <Text style={styles.appName}>RABBIT</Text>
          <Text style={styles.tagline}>// JARVIS VOICE OS</Text>
        </View>

        <View style={styles.headerRight}>
          <View style={[styles.statusBadge, connected ? styles.badgeOnline : styles.badgeOffline]}>
            <View style={[styles.dot, connected ? styles.dotOnline : styles.dotOffline]} />
            <Text style={styles.statusBadgeText}>
              {connected ? 'ONLINE' : 'OFFLINE'}
            </Text>
          </View>

          <TouchableOpacity style={styles.settingsBtn} onPress={() => setSettingsVisible(true)}>
            <Ionicons name="settings-sharp" size={20} color="#00F0FF" />
          </TouchableOpacity>
        </View>
      </View>

      {/* Center Arc-Reactor HUD */}
      <View style={styles.reactorArea}>
        <Animated.View
          style={[
            styles.outerRing,
            {
              transform: [{ rotate: spin }],
              borderColor: state === 'listening' ? '#FFB703' : '#00F0FF',
            },
          ]}
        />

        <Animated.View
          style={[
            styles.pulseRing,
            {
              transform: [{ scale: pulseAnim }],
              borderColor: state === 'thinking' ? '#00F0FF' : '#38BDF8',
            },
          ]}
        />

        <TouchableOpacity
          activeOpacity={0.8}
          style={[
            styles.reactorCore,
            state === 'listening' && styles.coreListening,
            state === 'thinking' && styles.coreThinking,
          ]}
          onPress={handleReactorPress}
        >
          <MaterialCommunityIcons
            name={state === 'listening' ? 'microphone' : 'atom'}
            size={48}
            color={state === 'listening' ? '#FFB703' : '#00F0FF'}
          />
          <Text style={styles.coreText}>
            {state === 'listening' ? 'LISTENING' : state === 'thinking' ? 'THINKING' : 'RABBIT'}
          </Text>
        </TouchableOpacity>

        {actionBadge && (
          <View style={styles.actionPill}>
            <Ionicons name="flash" size={14} color="#FFB703" />
            <Text style={styles.actionPillText}>{actionBadge}</Text>
          </View>
        )}
      </View>

      {/* Bengali Dialogue Box */}
      <View style={styles.dialogueBox}>
        <Text style={styles.statusLabel}>{statusText}</Text>
        {userTranscript ? (
          <Text style={styles.userSpeech} numberOfLines={2}>
            🗣️ {userTranscript}
          </Text>
        ) : null}
        <ScrollView style={styles.replyScroll}>
          <Text style={styles.rabbitReply}>{rabbitReply}</Text>
        </ScrollView>
      </View>

      {/* Quick Action Chips */}
      <View style={styles.quickChips}>
        <TouchableOpacity
          style={styles.chip}
          onPress={() => sendTextMessage('র্যাবিট, টর্চ লাইট অন করো')}
        >
          <Ionicons name="flashlight" size={14} color="#00F0FF" />
          <Text style={styles.chipText}>টর্চ লাইট</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.chip}
          onPress={() => executeDeviceAction('CHECK_BATTERY')}
        >
          <Ionicons name="battery-charging" size={14} color="#00F0FF" />
          <Text style={styles.chipText}>ব্যাটারি লেভেল</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.chip}
          onPress={() => executeDeviceAction('OPEN_APP', { app_name: 'youtube' })}
        >
          <Ionicons name="logo-youtube" size={14} color="#00F0FF" />
          <Text style={styles.chipText}>ইউটিউব</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.chip}
          onPress={checkAndInstallUpdate}
        >
          <Ionicons name="cloud-download" size={14} color="#FFB703" />
          <Text style={[styles.chipText, { color: '#FFB703' }]}>আপডেট চেক</Text>
        </TouchableOpacity>
      </View>

      {/* Bottom Text Input Box */}
      <View style={styles.inputRow}>
        <TextInput
          style={styles.textInput}
          placeholder="বাংলায় নির্দেশ টাইপ করুন..."
          placeholderTextColor="#64748B"
          value={textInput}
          onChangeText={setTextInput}
          onSubmitEditing={() => sendTextMessage(textInput)}
        />
        <TouchableOpacity
          style={styles.sendButton}
          onPress={() => sendTextMessage(textInput)}
        >
          <Ionicons name="send" size={20} color="#050B14" />
        </TouchableOpacity>
      </View>

      {/* Settings Modal */}
      <Modal visible={settingsVisible} animationType="slide" transparent={true}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Rabbit Server Settings</Text>

            <Text style={styles.fieldLabel}>সার্ভার আইপি (Host):</Text>
            <TextInput
              style={styles.modalInput}
              value={tempHost}
              onChangeText={setTempHost}
              placeholder="e.g. 192.168.0.100"
              placeholderTextColor="#64748B"
            />

            <Text style={styles.fieldLabel}>পোর্ট (Port):</Text>
            <TextInput
              style={styles.modalInput}
              value={tempPort}
              onChangeText={setTempPort}
              placeholder="e.g. 8899"
              placeholderTextColor="#64748B"
              keyboardType="numeric"
            />

            <View style={styles.modalBtnRow}>
              <TouchableOpacity
                style={[styles.modalBtn, styles.modalBtnCancel]}
                onPress={() => setSettingsVisible(false)}
              >
                <Text style={styles.modalBtnText}>বাতিল</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.modalBtn, styles.modalBtnSave]}
                onPress={saveSettings}
              >
                <Text style={[styles.modalBtnText, { color: '#050B14' }]}>সংরক্ষণ করুন</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#050B14',
    paddingHorizontal: 16,
    justifyContent: 'space-between',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: 12,
    paddingBottom: 8,
  },
  titleRow: {
    flexDirection: 'row',
    alignItems: 'baseline',
  },
  appName: {
    fontSize: 22,
    fontWeight: '900',
    color: '#00F0FF',
    letterSpacing: 2,
  },
  tagline: {
    fontSize: 10,
    color: '#64748B',
    marginLeft: 6,
    letterSpacing: 1,
  },
  headerRight: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
    marginRight: 10,
  },
  badgeOnline: {
    backgroundColor: 'rgba(0, 240, 255, 0.1)',
    borderWidth: 1,
    borderColor: '#00F0FF',
  },
  badgeOffline: {
    backgroundColor: 'rgba(239, 68, 68, 0.1)',
    borderWidth: 1,
    borderColor: '#EF4444',
  },
  dot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    marginRight: 4,
  },
  dotOnline: {
    backgroundColor: '#00F0FF',
  },
  dotOffline: {
    backgroundColor: '#EF4444',
  },
  statusBadgeText: {
    fontSize: 10,
    fontWeight: 'bold',
    color: '#E0F2FE',
  },
  settingsBtn: {
    padding: 6,
    borderRadius: 16,
    backgroundColor: '#0A192F',
  },
  reactorArea: {
    alignItems: 'center',
    justifyContent: 'center',
    height: 250,
    marginVertical: 10,
  },
  outerRing: {
    position: 'absolute',
    width: 230,
    height: 230,
    borderRadius: 115,
    borderWidth: 2,
    borderStyle: 'dashed',
    borderColor: '#00F0FF',
  },
  pulseRing: {
    position: 'absolute',
    width: 190,
    height: 190,
    borderRadius: 95,
    borderWidth: 1,
    borderColor: 'rgba(0, 240, 255, 0.3)',
  },
  reactorCore: {
    width: 130,
    height: 130,
    borderRadius: 65,
    backgroundColor: '#0A192F',
    borderWidth: 2,
    borderColor: '#00F0FF',
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#00F0FF',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.8,
    shadowRadius: 15,
    elevation: 10,
  },
  coreListening: {
    borderColor: '#FFB703',
    shadowColor: '#FFB703',
  },
  coreThinking: {
    borderColor: '#38BDF8',
  },
  coreText: {
    marginTop: 6,
    fontSize: 11,
    fontWeight: 'bold',
    color: '#E0F2FE',
    letterSpacing: 2,
  },
  actionPill: {
    position: 'absolute',
    bottom: 0,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255, 183, 3, 0.15)',
    borderWidth: 1,
    borderColor: '#FFB703',
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 12,
  },
  actionPillText: {
    fontSize: 11,
    color: '#FFB703',
    fontWeight: 'bold',
    marginLeft: 4,
  },
  dialogueBox: {
    flex: 1,
    backgroundColor: '#0A192F',
    borderRadius: 16,
    borderWidth: 1,
    borderColor: '#1E293B',
    padding: 14,
    marginVertical: 8,
  },
  statusLabel: {
    fontSize: 12,
    color: '#00F0FF',
    fontWeight: '600',
    marginBottom: 6,
  },
  userSpeech: {
    fontSize: 13,
    color: '#94A3B8',
    marginBottom: 8,
    fontStyle: 'italic',
  },
  replyScroll: {
    flex: 1,
  },
  rabbitReply: {
    fontSize: 15,
    color: '#F8FAFC',
    lineHeight: 22,
  },
  quickChips: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginVertical: 8,
  },
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#0A192F',
    borderWidth: 1,
    borderColor: '#1E293B',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 14,
  },
  chipText: {
    fontSize: 11,
    color: '#CBD5E1',
    marginLeft: 4,
  },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  textInput: {
    flex: 1,
    backgroundColor: '#0A192F',
    borderWidth: 1,
    borderColor: '#1E293B',
    borderRadius: 24,
    paddingHorizontal: 16,
    paddingVertical: 10,
    color: '#F8FAFC',
    fontSize: 14,
  },
  sendButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: '#00F0FF',
    alignItems: 'center',
    justifyContent: 'center',
    marginLeft: 8,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.75)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  modalContent: {
    width: '100%',
    backgroundColor: '#0A192F',
    borderRadius: 16,
    borderWidth: 1,
    borderColor: '#00F0FF',
    padding: 20,
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#00F0FF',
    marginBottom: 16,
    textAlign: 'center',
  },
  fieldLabel: {
    fontSize: 13,
    color: '#94A3B8',
    marginBottom: 6,
  },
  modalInput: {
    backgroundColor: '#050B14',
    borderWidth: 1,
    borderColor: '#1E293B',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
    color: '#FFFFFF',
    marginBottom: 14,
  },
  modalBtnRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 8,
  },
  modalBtn: {
    flex: 1,
    paddingVertical: 10,
    borderRadius: 8,
    alignItems: 'center',
  },
  modalBtnCancel: {
    backgroundColor: '#1E293B',
    marginRight: 8,
  },
  modalBtnSave: {
    backgroundColor: '#00F0FF',
    marginLeft: 8,
  },
  modalBtnText: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
});

# 🐰 Rabbit Assistant // Iron Man JARVIS Voice OS

> **"আসসালামু আলাইকুম ইমন স্যার! আমি র্যাবিট। আমি আপনার সকল নির্দেশ পালনের জন্য প্রস্তুত।"**

**Rabbit Assistant** হলো ইমন স্যারের জন্য বিশেষভাবে তৈরি একটি সম্পূর্ণ স্বয়ংক্রিয়, দ্বিমুখী বাংলা ভয়েস অ্যাসিস্ট্যান্ট এবং এআই অপারেটিং সিস্টেম (Iron Man JARVIS-এর আদলে)। এটি ফোনের সিস্টেম হার্ডওয়্যার নিয়ন্ত্রণ করতে পারে, পিসি/সার্ভারের কাজ বাস্তবায়ন করতে পারে এবং সবচেয়ে বড় বৈশিষ্ট্য—**অ্যাপটি নিজেই নিজেকে আপডেট ও ক্রমাগত উন্নত (Self-Evolving) করতে সক্ষম**।

---

## 🌟 প্রধান বৈশিষ্ঠ্যসমূহ (Key Features)

1. **শুদ্ধ ও স্পষ্ট বাংলায় ভয়েস কথোপকথন (Bangla Speech-to-Speech):**
   - **STT (Speech-to-Text):** অ্যান্ড্রয়েড নেটিভ `bn-BD` স্পিচ রিকগনিশন।
   - **TTS (Text-to-Speech):** মাইক্রোসফট এজ-টিটিএস এর প্রিমিয়াম নিউরাল মডেল (`bn-BD-PradeepNeural`) এবং গুগল বাংলা টিটিএস ফলব্যাক।
   - **আল্ট্রা-লো ল্যাটেন্সি অডিও স্ট্রিমিং:** কথা শেষ হওয়ার সাথে সাথেই স্ট্রিমিং প্লেব্যাক শুরু।

2. **আয়রন ম্যান জার্ভিস স্টাইল ইন্টারফেস (JARVIS Arc-Reactor HUD):**
   - সাইবার নিওন সিয়ান এবং গোল্ড কালার স্কিম।
   - ইন্টারঅ্যাক্টিভ ও ডাইনামিক আর্ক-রিঅ্যাক্টর কোর অ্যানিমেশন।
   - অডিও আরএমএস লেভেল অনুযায়ী লাইভ ওয়েভ পালসিং।

3. **অ্যান্ড্রয়েড ডিভাইস অটোমেশন (Device Control):**
   - 🔦 **টর্চ লাইট:** "র্যাবিট, টর্চ জ্বালাও" / "টর্চ বন্ধ করো"
   - 🔊 **ভলিউম কন্ট্রোল:** "ভলিউম বাড়াও" / "ভলিউম কমাও" / "মিউট করো"
   - 🔋 **ব্যাটারি টেলিমেট্রি:** "ব্যাটারি লেভেল কত?"
   - 📱 **অ্যাপ্লিকেশন লঞ্চ:** "ইউটিউব খোলো", "হোয়াটসঅ্যাপ ওপেন করো", "ক্যামেরা চালু করো"
   - 📞 **ফোন কল ও মেসেজ:** "ইমন স্যারকে কল করো", "এসএমএস পাঠাও"

4. **সার্ভার ও কোডিং কন্ট্রোল (Hermes Brain Integration):**
   - লোকাল উবুন্টু ওয়ার্কস্টেশনের **Hermes Agent** এর সাথে হাই-স্পিড WebSocket কানেকশন।
   - টার্মিনাল কমান্ড এক্সেকিউশন, ডকার স্ট্যাটাস, স্টকহুইস্ক/পিকাসা প্রজেক্ট মনিটরিং।

5. **স্বয়ংক্রিয় সেলফ-আপডেট ও বিবর্তন (Self-Evolution & Auto-Update):**
   - **জিরো রিইনস্টল স্কিল আপডেট:** নতুন যেকোনো কাজ বা স্কিল সাথে সাথে ব্যাকএন্ডে শিখে ফেলা।
   - **ওটিএ (OTA) অটো-আপডেট:** গিটহাবে পুশ করলেই গিটহাব অ্যাকশন্সে স্বয়ংক্রিয়ভাবে নতুন APK তৈরি হয় এবং অ্যাপ স্বয়ংক্রিয়ভাবে ডাউনলোড করে ১-ক্লিকে ইনস্টল করে নেয়।

---

## 📱 মোবাইল ক্লায়েন্ট অপশনসমূহ (Mobile Client Options)

Rabbit Assistant দুটি উপায়ে অ্যান্ড্রয়েডে ব্যবহার করা যায়:

### ১. Expo (React Native) অ্যাপ (`expo-app/`)
- **Framework:** Expo SDK 58 + React Native
- **ইন্টারফেস:** নিওন আর্ক-রিঅ্যাক্টর HUD, অ্যানিমেটেড পালস, বাংলা স্পিচ এবং অডিও স্ট্রিমিং।
- **ডিভাইস কন্ট্রোল:** টর্চ লাইট, ব্যাটারি লেভেল মনিটরিং, ইউটিউব ও হোয়াটসঅ্যাপ শর্টকাট।
- **বিল্ড মেথড:**
  - **Expo Go (তাত্ক্ষণিক রান):** `cd expo-app && npx expo start` (ফোনে Expo Go অ্যাপ দিয়ে QR কোড স্ক্যান করুন)।
  - **EAS Build (Expo.io Cloud):** `cd expo-app && npx eas-cli build -p android --profile preview` (সরাসরি `.apk` ফাইল তৈরি হবে)।
  - **GitHub Actions:** গিটহাবে পুশ করলেই `.github/workflows/build-expo-apk.yml` ক্লাউডে স্বয়ংক্রিয়ভাবে APK বিল্ড করে Artifacts-এ আপলোড করে দেয়।

### ২. নেটিভ অ্যান্ড্রয়েড কোটলিন অ্যাপ (`android/`)
- **Language:** 100% Native Kotlin + Material Components
- **বিল্ড:** GitHub Actions CI/CD (`build-apk.yml`) এর মাধ্যমে স্বয়ংক্রিয়ভাবে কম্পাইল হয়ে রিলিজ পেজে জমা হয়।

---

## 🛠️ সিস্টেম আর্কিটেকচার (System Architecture)

```
┌────────────────────────────────────────────────────────┐
│              ANDROID PHONE ('Rabbit' App)              │
│  - Jarvis Arc-Reactor UI (Kotlin/Compose)              │
│  - Bangla Speech Recognizer (bn-BD)                    │
│  - Low-Latency Audio Streaming Player                  │
│  - Device Action Handler (Torch, Volume, Apps, Call)   │
│  - UpdateManager (Silent OTA APK Download & Install)   │
└──────────────────────────┬─────────────────────────────┘
                           │ WebSocket (ws://192.168.0.100:8899/ws/voice)
                           ▼
┌────────────────────────────────────────────────────────┐
│             RABBIT BACKEND GATEWAY (FastAPI)           │
│  - Persona Router ("Rabbit" // Addressing Imon Sir)    │
│  - Intent & Action Extraction Engine                   │
│  - Edge-TTS Bangla Neural Synthesizer                  │
│  - OTA Update Server & APK Distribution Hub            │
└──────────────────────────┬─────────────────────────────┘
                           │ WebSocket JSON-RPC (ws://127.0.0.1:9119/api/ws)
                           ▼
┌────────────────────────────────────────────────────────┐
│               HERMES AGENT (Ubuntu Host)               │
│  - Terminal Tools, File System, Subagents              │
│  - Persistent Memory, Skills, Code Writing Engine      │
│  - Self-Evolution Pipeline (Git Auto-Commit & Actions) │
└────────────────────────────────────────────────────────┘
```

---

## 🚀 সার্ভার চালুর নিয়ম (Server Startup & Systemd Service)

Rabbit Gateway ব্যাকএন্ড স্বয়ংক্রিয়ভাবে ব্যাকগ্রাউন্ডে চলতে পারে।

### ম্যানুয়াল রান:
```bash
/home/imon/.hermes/hermes-agent/venv/bin/python3 /home/imon/rabbit-assistant/server/main.py
```

### Systemd সার্বক্ষণিক ব্যাকগ্রাউন্ড সার্ভিস:
সার্ভিস ফাইল: `~/.config/systemd/user/rabbit-gateway.service`
```bash
systemctl --user enable --now rabbit-gateway.service
```

---

## 📱 অ্যান্ড্রয়েড ক্লায়েন্ট বিল্ড করার নিয়ম

গিটহাবে রিপোজিটরিটি পুশ করলেই GitHub Actions স্বয়ংক্রিয়ভাবে রিলিজ APK তৈরি করে দেয়।
যদি লোকাল মেশিনে বিল্ড করতে চান:
```bash
cd /home/imon/rabbit-assistant/android
./gradlew assembleDebug
```
তৈরি হওয়া APK পাওয়া যাবে: `android/app/build/outputs/apk/debug/app-debug.apk`

---

## 🛡️ কপিরাইট এবং মালিকানা
- **ক্রিয়েটর ও ওনার:** মোহাম্মদ মাঈনুল ইসলাম ইমন (Imon Sir)
- **কোডনেম:** Rabbit (র্যাবিট)

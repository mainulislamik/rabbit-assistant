# Proguard rules for Rabbit Assistant
-keep class com.rabbit.assistant.** { *; }
-keepclassmembers class * {
    @android.webkit.JavascriptInterface <methods>;
}
-dontwarn okhttp3.**
-dontwarn okio.**

package com.rabbit.assistant.voice

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.util.Log

class SpeechRecognizerManager(
    private val context: Context,
    private val listener: SpeechCallback
) {
    private val tag = "SpeechRecognizer"
    private var speechRecognizer: SpeechRecognizer? = null
    private var isListening = false
    private var continuousMode = false

    interface SpeechCallback {
        fun onSpeechReady()
        fun onSpeechRmsChanged(rmsdB: Float)
        fun onSpeechPartialResult(partialText: String)
        fun onSpeechResult(finalText: String)
        fun onSpeechError(errorCode: Int, errorMessage: String)
        fun onSpeechEnded()
    }

    init {
        initRecognizer()
    }

    private fun initRecognizer() {
        try {
            if (!SpeechRecognizer.isRecognitionAvailable(context)) {
                Log.e(tag, "Speech recognition is not available on this device")
                listener.onSpeechError(-1, "স্পিচ রিকগনিশন ডিভাইসটিতে সমর্থিত নয়।")
                return
            }

            speechRecognizer = SpeechRecognizer.createSpeechRecognizer(context).apply {
                setRecognitionListener(object : RecognitionListener {
                    override fun onReadyForSpeech(params: Bundle?) {
                        isListening = true
                        listener.onSpeechReady()
                    }

                    override fun onBeginningOfSpeech() {
                        Log.d(tag, "User began speaking")
                    }

                    override fun onRmsChanged(rmsdB: Float) {
                        listener.onSpeechRmsChanged(rmsdB)
                    }

                    override fun onBufferReceived(buffer: ByteArray?) {}

                    override fun onEndOfSpeech() {
                        isListening = false
                        listener.onSpeechEnded()
                    }

                    override fun onError(error: Int) {
                        isListening = false
                        val errorMsg = when (error) {
                            SpeechRecognizer.ERROR_NO_MATCH -> "কথা স্পষ্ট শোনা যায়নি।"
                            SpeechRecognizer.ERROR_SPEECH_TIMEOUT -> "কোনো কথা শনাক্ত হয়নি।"
                            SpeechRecognizer.ERROR_NETWORK -> "নেটওয়ার্ক সমস্যা।"
                            SpeechRecognizer.ERROR_AUDIO -> "মাইক্রোফোন অডিও সমস্যা।"
                            else -> "স্পিচ এরর: $error"
                        }
                        Log.w(tag, "SpeechRecognizer error: $errorMsg ($error)")
                        listener.onSpeechError(error, errorMsg)

                        if (continuousMode && error == SpeechRecognizer.ERROR_NO_MATCH) {
                            startListening(true)
                        }
                    }

                    override fun onResults(results: Bundle?) {
                        isListening = false
                        val matches = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                        if (!matches.isNullOrEmpty()) {
                            val spokenText = matches[0]
                            Log.d(tag, "Recognized Bengali Speech: $spokenText")
                            listener.onSpeechResult(spokenText)
                        } else {
                            listener.onSpeechError(SpeechRecognizer.ERROR_NO_MATCH, "কোনো কথা শনাক্ত করা যায়নি।")
                        }
                    }

                    override fun onPartialResults(partialResults: Bundle?) {
                        val partialMatches = partialResults?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                        if (!partialMatches.isNullOrEmpty()) {
                            listener.onSpeechPartialResult(partialMatches[0])
                        }
                    }

                    override fun onEvent(eventType: Int, params: Bundle?) {}
                })
            }
        } catch (e: Exception) {
            Log.e(tag, "Exception during SpeechRecognizer initialization", e)
            listener.onSpeechError(-2, "স্পিচ রিকগনিশন শুরু করতে সমস্যা হয়েছে।")
        }
    }

    fun startListening(continuous: Boolean = false) {
        this.continuousMode = continuous
        if (isListening) {
            stopListening()
        }

        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, "bn-BD")
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_PREFERENCE, "bn-BD")
            putExtra("android.speech.extra.EXTRA_ADDITIONAL_LANGUAGES", arrayOf("bn-BD", "bn-IN", "en-US"))
            putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
            putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 3)
        }

        try {
            speechRecognizer?.startListening(intent)
            isListening = true
        } catch (e: Exception) {
            Log.e(tag, "Failed to start listening", e)
            listener.onSpeechError(-1, e.message ?: "Failed to start speech")
        }
    }

    fun stopListening() {
        try {
            speechRecognizer?.stopListening()
        } catch (e: Exception) {
            Log.e(tag, "Error stopping recognizer", e)
        }
        isListening = false
    }

    fun destroy() {
        stopListening()
        speechRecognizer?.destroy()
        speechRecognizer = null
    }

    fun isCurrentlyListening(): Boolean = isListening
}

package com.rabbit.assistant

import android.Manifest
import android.animation.ObjectAnimator
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.view.View
import android.view.animation.LinearInterpolator
import android.widget.*
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import com.google.gson.JsonObject
import com.rabbit.assistant.device.DeviceActionHandler
import com.rabbit.assistant.network.RabbitWebSocketClient
import com.rabbit.assistant.service.RabbitBackgroundService
import com.rabbit.assistant.update.UpdateManager
import com.rabbit.assistant.voice.AudioStreamPlayer
import com.rabbit.assistant.voice.SpeechRecognizerManager
import java.io.File
import android.util.Log

class MainActivity : AppCompatActivity(),

    RabbitWebSocketClient.SocketEventListener,
    SpeechRecognizerManager.SpeechCallback,
    AudioStreamPlayer.PlaybackCallback,
    DeviceActionHandler.ActionExecutionCallback,
    UpdateManager.UpdateCallback {

    private lateinit var tvConnectionStatus: TextView
    private lateinit var tvStateLabel: TextView
    private lateinit var tvDialogueText: TextView
    private lateinit var tvActionBadge: TextView
    private lateinit var btnArcReactor: FrameLayout
    private lateinit var tvCoreText: TextView
    private lateinit var viewOuterRing: View
    private lateinit var viewMiddleRing: View
    private lateinit var etUserMessage: EditText
    private lateinit var btnSendText: ImageButton
    private lateinit var btnSettings: ImageButton

    private lateinit var chipTorch: Button
    private lateinit var chipBattery: Button
    private lateinit var chipUpdate: Button
    private lateinit var chipServer: Button

    private lateinit var wsClient: RabbitWebSocketClient
    private lateinit var speechManager: SpeechRecognizerManager
    private lateinit var audioPlayer: AudioStreamPlayer
    private lateinit var actionHandler: DeviceActionHandler
    private lateinit var updateManager: UpdateManager
    private var isManualUpdateCheck: Boolean = false


    private var outerRingAnimator: ObjectAnimator? = null
    private var middleRingAnimator: ObjectAnimator? = null

    private val prefName = "rabbit_prefs"
    private val keyHost = "server_host"
    private val keyPort = "server_port"

    private val permissionReqCode = 2026
    private val tag = "MainActivity"

    override fun onCreate(savedInstanceState: Bundle?) {

        super.onCreate(savedInstanceState)
        try {
            setContentView(R.layout.activity_main)

            initViews()
            initServices()
            initAnimations()
            checkPermissions()
            startBackgroundService()
        } catch (t: Throwable) {
            Log.e(tag, "Fatal error in onCreate", t)
        }
    }

    private fun initViews() {
        tvConnectionStatus = findViewById(R.id.tvConnectionStatus)
        tvStateLabel = findViewById(R.id.tvStateLabel)
        tvDialogueText = findViewById(R.id.tvDialogueText)
        tvActionBadge = findViewById(R.id.tvActionBadge)
        btnArcReactor = findViewById(R.id.btnArcReactor)
        tvCoreText = findViewById(R.id.tvCoreText)
        viewOuterRing = findViewById(R.id.viewOuterRing)
        viewMiddleRing = findViewById(R.id.viewMiddleRing)
        etUserMessage = findViewById(R.id.etUserMessage)
        btnSendText = findViewById(R.id.btnSendText)
        btnSettings = findViewById(R.id.btnSettings)

        chipTorch = findViewById(R.id.chipTorch)
        chipBattery = findViewById(R.id.chipBattery)
        chipUpdate = findViewById(R.id.chipUpdate)
        chipServer = findViewById(R.id.chipServer)

        btnArcReactor.setOnClickListener {
            handleCoreTapped()
        }

        btnSendText.setOnClickListener {
            val text = etUserMessage.text.toString().trim()
            if (text.isNotEmpty()) {
                sendUserMessage(text)
                etUserMessage.setText("")
            }
        }

        btnSettings.setOnClickListener {
            showSettingsDialog()
        }

        chipTorch.setOnClickListener {
            sendUserMessage("টর্চ লাইট টগল করো")
        }

        chipBattery.setOnClickListener {
            actionHandler.handleAction("CHECK_BATTERY", null)
        }

        chipUpdate.setOnClickListener {
            isManualUpdateCheck = true
            triggerSelfUpdateCheck(force = true)
        }


        chipServer.setOnClickListener {
            sendUserMessage("সার্ভার স্ট্যাটাস ও কানেকশন হেলথ কেমন?")
        }
    }

    private fun initServices() {
        val prefs = getSharedPreferences(prefName, Context.MODE_PRIVATE)
        val host = prefs.getString(keyHost, "192.168.0.100") ?: "192.168.0.100"
        val port = prefs.getInt(keyPort, 8899)

        wsClient = RabbitWebSocketClient(host, port, this)
        speechManager = SpeechRecognizerManager(this, this)
        audioPlayer = AudioStreamPlayer(this, this)
        actionHandler = DeviceActionHandler(this, this)
        updateManager = UpdateManager(this, this)

        wsClient.connect()
        isManualUpdateCheck = false
        triggerSelfUpdateCheck(force = false)
    }


    private fun initAnimations() {
        outerRingAnimator = ObjectAnimator.ofFloat(viewOuterRing, "rotation", 0f, 360f).apply {
            duration = 16000
            repeatCount = ObjectAnimator.INFINITE
            interpolator = LinearInterpolator()
            start()
        }

        middleRingAnimator = ObjectAnimator.ofFloat(viewMiddleRing, "rotation", 360f, 0f).apply {
            duration = 8000
            repeatCount = ObjectAnimator.INFINITE
            interpolator = LinearInterpolator()
            start()
        }
    }

    private fun startBackgroundService() {
        try {
            val intent = Intent(this, RabbitBackgroundService::class.java)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                startForegroundService(intent)
            } else {
                startService(intent)
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    private fun checkPermissions() {
        val needed = mutableListOf<String>()
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            needed.add(Manifest.permission.RECORD_AUDIO)
        }
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
            needed.add(Manifest.permission.CAMERA)
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
                needed.add(Manifest.permission.POST_NOTIFICATIONS)
            }
        }
        if (needed.isNotEmpty()) {
            ActivityCompat.requestPermissions(this, needed.toTypedArray(), permissionReqCode)
        }
    }

    private fun handleCoreTapped() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.RECORD_AUDIO), permissionReqCode)
            return
        }

        if (speechManager.isCurrentlyListening()) {
            speechManager.stopListening()
            updateUiState("idle", "লিসেনিং স্থগিত করা হয়েছে।")
        } else if (audioPlayer.isPlayingAudio()) {
            audioPlayer.stop()
            updateUiState("idle", "অডিও থামানো হয়েছে।")
        } else {
            speechManager.startListening(continuous = false)
            updateUiState("listening", "শুনছি, বলুন ইমন স্যার...")
        }
    }

    private fun sendUserMessage(text: String) {
        tvDialogueText.text = "ইমন স্যার: $text"
        updateUiState("thinking", "প্রসেস করছি, স্যার...")
        wsClient.sendUserText(text)
    }

    private fun updateUiState(state: String, label: String) {
        runOnUiThread {
            tvStateLabel.text = label.uppercase()
            when (state) {
                "listening" -> {
                    tvCoreText.text = "LISTEN"
                    btnArcReactor.setBackgroundResource(R.drawable.bg_pill_cyan)
                    middleRingAnimator?.duration = 2000
                }
                "thinking" -> {
                    tvCoreText.text = "THINK"
                    btnArcReactor.setBackgroundResource(R.drawable.bg_pill_gold)
                    middleRingAnimator?.duration = 1000
                }
                "speaking" -> {
                    tvCoreText.text = "VOICE"
                    btnArcReactor.setBackgroundResource(R.drawable.bg_reactor_core)
                    middleRingAnimator?.duration = 4000
                }
                else -> {
                    tvCoreText.text = "RABBIT"
                    btnArcReactor.setBackgroundResource(R.drawable.bg_reactor_core)
                    middleRingAnimator?.duration = 8000
                }
            }
        }
    }

    private fun showSettingsDialog() {
        val prefs = getSharedPreferences(prefName, Context.MODE_PRIVATE)
        val currentHost = prefs.getString(keyHost, "192.168.0.100") ?: "192.168.0.100"
        val currentPort = prefs.getInt(keyPort, 8899)

        val layout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(50, 40, 50, 20)
        }

        val etHost = EditText(this).apply {
            hint = "Rabbit Server IP / Domain"
            setText(currentHost)
        }
        val etPort = EditText(this).apply {
            hint = "Rabbit Server Port"
            setText(currentPort.toString())
        }

        layout.addView(etHost)
        layout.addView(etPort)

        AlertDialog.Builder(this)
            .setTitle("Rabbit Core Connection")
            .setView(layout)
            .setPositiveButton("Save & Connect") { _, _ ->
                val newHost = etHost.text.toString().trim()
                val newPort = etPort.text.toString().trim().toIntOrNull() ?: 8899

                prefs.edit().putString(keyHost, newHost).putInt(keyPort, newPort).apply()
                wsClient.updateServerConfig(newHost, newPort)
                Toast.makeText(this, "সার্ভার কনফিগ আপডেট করা হয়েছে।", Toast.LENGTH_SHORT).show()
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun triggerSelfUpdateCheck(force: Boolean) {
        val prefs = getSharedPreferences(prefName, Context.MODE_PRIVATE)
        val host = prefs.getString(keyHost, "192.168.0.100") ?: "192.168.0.100"
        val port = prefs.getInt(keyPort, 8899)
        updateManager.checkForUpdates(host, port, force)
    }

    // --- WebSocket Events ---
    override fun onConnected() {
        runOnUiThread {
            tvConnectionStatus.text = "ONLINE"
            tvConnectionStatus.setBackgroundResource(R.drawable.bg_pill_cyan)
            tvConnectionStatus.setTextColor(ContextCompat.getColor(this, R.color.cyan_primary))
            
            // Auto check for latest server release on connect (OTA update)
            isManualUpdateCheck = false
            triggerSelfUpdateCheck(force = false)
        }
    }


    override fun onDisconnected() {
        runOnUiThread {
            tvConnectionStatus.text = "OFFLINE"
            tvConnectionStatus.setBackgroundResource(R.drawable.bg_pill_gold)
            tvConnectionStatus.setTextColor(ContextCompat.getColor(this, R.color.gold_accent))
        }
    }

    override fun onStateChange(state: String) {
        val label = when (state) {
            "listening" -> "লিসেনিং..."
            "thinking" -> "র্যাবিট চিন্তা করছে..."
            "speaking" -> "কথা বলছে..."
            else -> "র্যাবিট সক্রিয় এবং প্রস্তুত"
        }
        updateUiState(state, label)
    }

    override fun onTextReceived(text: String, isDelta: Boolean) {
        runOnUiThread {
            if (isDelta) {
                tvDialogueText.append(text)
            } else {
                val current = tvDialogueText.text.toString().trim()
                if (text.startsWith("ইমন স্যার:")) {
                    tvDialogueText.text = text
                } else if (current.startsWith("ইমন স্যার:") && !current.contains("র্যাবিট:")) {
                    tvDialogueText.text = "$current\n\nর্যাবিট: $text"
                } else {
                    tvDialogueText.text = if (text.startsWith("র্যাবিট:")) text else "র্যাবিট: $text"
                }
            }
        }
    }

    override fun onAudioReceived(audioUrl: String, text: String?) {
        runOnUiThread {
            if (!text.isNullOrBlank()) {
                val current = tvDialogueText.text.toString().trim()
                if (current.startsWith("ইমন স্যার:") && !current.contains("র্যাবিট:")) {
                    tvDialogueText.text = "$current\n\nর্যাবিট: $text"
                } else {
                    tvDialogueText.text = if (text.startsWith("র্যাবিট:")) text else "র্যাবিট: $text"
                }
            }
            audioPlayer.playAudioUrl(audioUrl)
        }
    }


    override fun onActionReceived(action: String, params: JsonObject?) {
        runOnUiThread {
            tvActionBadge.visibility = View.VISIBLE
            tvActionBadge.text = "ACTION: $action"
            actionHandler.handleAction(action, params)
        }
    }

    override fun onError(message: String) {
        runOnUiThread {
            Toast.makeText(this, message, Toast.LENGTH_SHORT).show()
        }
    }

    // --- SpeechRecognizer Events ---
    override fun onSpeechReady() {
        updateUiState("listening", "শুনছি, বলুন ইমন স্যার...")
    }

    override fun onSpeechRmsChanged(rmsdB: Float) {
        runOnUiThread {
            val scale = 1.0f + (rmsdB.coerceAtLeast(0f) / 40f)
            viewMiddleRing.scaleX = scale
            viewMiddleRing.scaleY = scale
        }
    }

    override fun onSpeechPartialResult(partialText: String) {
        runOnUiThread {
            tvDialogueText.text = "ইমন স্যার: $partialText..."
        }
    }

    override fun onSpeechResult(finalText: String) {
        runOnUiThread {
            sendUserMessage(finalText)
        }
    }

    override fun onSpeechError(errorCode: Int, errorMessage: String) {
        updateUiState("idle", errorMessage)
    }

    override fun onSpeechEnded() {
        updateUiState("thinking", "ভয়েস প্রসেস হচ্ছে...")
    }

    // --- AudioStreamPlayer Events ---
    override fun onPlaybackStarted() {
        updateUiState("speaking", "র্যাবিট উত্তর দিচ্ছে...")
    }

    override fun onPlaybackCompleted() {
        updateUiState("idle", "র্যাবিট সক্রিয় এবং প্রস্তুত")
    }

    override fun onPlaybackError(message: String) {
        updateUiState("idle", "অডিও প্লেব্যাকে সমস্যা হয়েছে")
    }

    // --- ActionExecutionCallback ---
    override fun onActionExecuted(actionName: String, summaryBangla: String) {
        runOnUiThread {
            tvDialogueText.text = summaryBangla
            Toast.makeText(this, summaryBangla, Toast.LENGTH_LONG).show()
        }
    }

    override fun onTriggerSelfUpdate() {
        triggerSelfUpdateCheck(force = true)
    }

    // --- UpdateCallback ---
    override fun onUpdateCheckStarted() {
        Toast.makeText(this, "নতুন আপডেট খোঁজা হচ্ছে...", Toast.LENGTH_SHORT).show()
    }

    override fun onUpdateAvailable(versionName: String, releaseNotes: String) {
        tvDialogueText.text = "র্যাবিট সংস্করণ $versionName আপডেট পাওয়া গেছে। ডাউনলোড শুরু হচ্ছে..."
    }

    override fun onNoUpdateAvailable() {
        if (isManualUpdateCheck) {
            Toast.makeText(this, "আপনার র্যাবিট অ্যাপটি সম্পূর্ণ আপ-টু-ডেট আছে, স্যার।", Toast.LENGTH_SHORT).show()
        }
    }

    override fun onDownloadProgress(percent: Int) {
        tvDialogueText.text = "আপডেট ডাউনলোড হচ্ছে: $percent%"
    }

    override fun onDownloadCompleted(apkFile: File) {
        tvDialogueText.text = "ডাউনলোড সম্পন্ন! নতুন সংস্করণ ইনস্টল করা হচ্ছে..."
    }

    override fun onUpdateError(message: String) {
        if (isManualUpdateCheck) {
            Toast.makeText(this, message, Toast.LENGTH_LONG).show()
        }
    }


    override fun onDestroy() {
        super.onDestroy()
        speechManager.destroy()
        audioPlayer.stop()
        wsClient.disconnect()
        outerRingAnimator?.cancel()
        middleRingAnimator?.cancel()
    }
}

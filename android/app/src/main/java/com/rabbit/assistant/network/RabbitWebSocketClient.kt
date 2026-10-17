package com.rabbit.assistant.network

import android.os.Handler
import android.os.Looper
import android.util.Log
import com.google.gson.Gson
import com.google.gson.JsonObject
import com.google.gson.JsonParser
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.IOException
import java.util.concurrent.TimeUnit

class RabbitWebSocketClient(
    private var serverHost: String = "192.168.0.100",
    private var serverPort: Int = 8899,
    private val listener: SocketEventListener
) {
    private val tag = "RabbitWS"
    private val gson = Gson()
    private val mainHandler = Handler(Looper.getMainLooper())
    private var client: OkHttpClient? = null
    private var webSocket: WebSocket? = null
    private var isConnected = false
    private var shouldReconnect = true
    private val reconnectDelayMs = 3000L

    interface SocketEventListener {
        fun onConnected()
        fun onDisconnected()
        fun onStateChange(state: String) // "idle", "listening", "thinking", "speaking"
        fun onTextReceived(text: String, isDelta: Boolean)
        fun onAudioReceived(audioUrl: String, text: String?)
        fun onActionReceived(action: String, params: JsonObject?)
        fun onError(message: String)
    }

    fun updateConfig(host: String, port: Int) {
        this.serverHost = host
        this.serverPort = port
        disconnect()
        connect()
    }

    fun updateServerConfig(host: String, port: Int) = updateConfig(host, port)


    fun connect() {
        shouldReconnect = true
        if (isConnected && webSocket != null) return

        if (client == null) {
            client = OkHttpClient.Builder()
                .readTimeout(0, TimeUnit.MILLISECONDS)
                .pingInterval(10, TimeUnit.SECONDS)
                .connectTimeout(5, TimeUnit.SECONDS)
                .build()
        }

        val wsUrl = "ws://$serverHost:$serverPort/ws/voice"
        Log.i(tag, "Connecting to WebSocket: $wsUrl")

        val request = Request.Builder().url(wsUrl).build()

        client?.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(ws: WebSocket, response: Response) {
                Log.d(tag, "Connected to Rabbit WebSocket")
                isConnected = true
                webSocket = ws
                mainHandler.post { listener.onConnected() }
            }

            override fun onMessage(ws: WebSocket, text: String) {
                handleIncomingMessage(text)
            }

            override fun onClosing(ws: WebSocket, code: Int, reason: String) {
                Log.d(tag, "WebSocket closing: $reason ($code)")
                ws.close(1000, null)
            }

            override fun onClosed(ws: WebSocket, code: Int, reason: String) {
                Log.d(tag, "WebSocket closed: $reason ($code)")
                isConnected = false
                webSocket = null
                mainHandler.post { listener.onDisconnected() }
                scheduleReconnect()
            }

            override fun onFailure(ws: WebSocket, t: Throwable, response: Response?) {
                Log.w(tag, "WebSocket connection failed: ${t.message}")
                isConnected = false
                webSocket = null
                mainHandler.post { 
                    listener.onDisconnected()
                }
                scheduleReconnect()
            }
        })
    }

    private fun handleIncomingMessage(rawJson: String) {
        try {
            val json = JsonParser.parseString(rawJson).asJsonObject
            val type = json.get("type")?.asString ?: return

            when (type) {
                "connected", "ready" -> {
                    val msg = json.get("message")?.asString ?: "র্যাবিট অনলাইন"
                    isConnected = true
                    mainHandler.post { 
                        listener.onConnected()
                        listener.onTextReceived(msg, false) 
                    }
                }
                "user_text" -> {
                    val sender = json.get("sender")?.asString ?: "ইমন স্যার"
                    val text = json.get("text")?.asString ?: ""
                    mainHandler.post { listener.onTextReceived("$sender: $text", false) }
                }
                "state" -> {

                    val state = json.get("state")?.asString ?: "idle"
                    mainHandler.post { listener.onStateChange(state) }
                }
                "delta" -> {
                    val deltaText = json.get("text")?.asString ?: ""
                    mainHandler.post { listener.onTextReceived(deltaText, true) }
                }
                "audio", "speech_response" -> {
                    val audioUrl = (json.get("url") ?: json.get("audio_url"))?.asString ?: ""
                    val fullUrl = if (audioUrl.startsWith("http")) audioUrl else "http://$serverHost:$serverPort$audioUrl"
                    val text = json.get("text")?.asString
                    if (audioUrl.isNotBlank()) {
                        mainHandler.post { listener.onAudioReceived(fullUrl, text) }
                    } else if (text != null) {
                        mainHandler.post { listener.onTextReceived(text, false) }
                    }
                }
                "action" -> {
                    val actionName = json.get("action")?.asString ?: ""
                    val params = json.get("params")?.asJsonObject
                    mainHandler.post { listener.onActionReceived(actionName, params) }
                }
                "error" -> {
                    val err = json.get("error")?.asString ?: "অজানা ত্রুটি"
                    mainHandler.post { listener.onError(err) }
                }
            }
        } catch (e: Exception) {
            Log.e(tag, "Error parsing message: $rawJson", e)
        }
    }

    fun sendUserText(banglaText: String) {
        if (isConnected && webSocket != null) {
            val payload = JsonObject().apply {
                addProperty("type", "user_text")
                addProperty("text", banglaText)
            }
            webSocket?.send(gson.toJson(payload))
            return
        }

        // Reconnect socket in background if disconnected
        connect()

        // Instant HTTP API Fallback so no user message is ever blocked
        val httpUrl = "http://$serverHost:$serverPort/api/chat"
        val payload = JsonObject().apply {
            addProperty("prompt", banglaText)
        }
        val mediaType = "application/json; charset=utf-8".toMediaType()
        val request = Request.Builder()
            .url(httpUrl)
            .post(payload.toString().toRequestBody(mediaType))
            .build()

        client?.newCall(request)?.enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                mainHandler.post {
                    listener.onError("র্যাবিট কোরের সাথে সংযোগ নেই: ${e.message}")
                }
            }

            override fun onResponse(call: Call, response: Response) {
                response.use { resp ->
                    if (!resp.isSuccessful) {
                        mainHandler.post {
                            listener.onError("সার্ভার প্রতিক্রিয়া: ${resp.code}")
                        }
                        return
                    }
                    val bodyStr = resp.body?.string() ?: return
                    try {
                        val replyObj = JsonParser.parseString(bodyStr).asJsonObject
                        val replyText = replyObj.get("reply")?.asString ?: ""
                        val audioUrl = replyObj.get("audio_url")?.asString
                        mainHandler.post {
                            if (!audioUrl.isNullOrBlank()) {
                                val fullUrl = if (audioUrl.startsWith("http")) audioUrl else "http://$serverHost:$serverPort$audioUrl"
                                listener.onAudioReceived(fullUrl, replyText)
                            } else {
                                listener.onTextReceived(replyText, false)
                            }
                        }
                    } catch (ex: Exception) {
                        Log.e(tag, "HTTP Fallback parse error", ex)
                    }
                }
            }
        })
    }

    fun disconnect() {
        shouldReconnect = false
        webSocket?.close(1000, "Normal Closure")
        isConnected = false
        webSocket = null
    }

    private fun scheduleReconnect() {
        if (!shouldReconnect) return
        mainHandler.postDelayed({
            if (shouldReconnect && !isConnected) {
                connect()
            }
        }, reconnectDelayMs)
    }

    fun isSocketConnected(): Boolean = isConnected
    fun getFullHttpUrl(path: String): String = "http://$serverHost:$serverPort$path"
}

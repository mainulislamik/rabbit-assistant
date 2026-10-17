package com.rabbit.assistant.network

import android.os.Handler
import android.os.Looper
import android.util.Log
import com.google.gson.Gson
import com.google.gson.JsonObject
import com.google.gson.JsonParser
import okhttp3.*
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

    init {
        buildClient()
    }

    private fun buildClient() {
        client = OkHttpClient.Builder()
            .readTimeout(0, TimeUnit.MILLISECONDS)
            .pingInterval(15, TimeUnit.SECONDS)
            .retryOnConnectionFailure(true)
            .build()
    }

    fun updateServerConfig(host: String, port: Int) {
        val changed = (host != serverHost || port != serverPort)
        serverHost = host
        serverPort = port
        if (changed && isConnected) {
            disconnect()
            connect()
        }
    }

    fun connect() {
        shouldReconnect = true
        if (isConnected) return

        val wsUrl = "ws://$serverHost:$serverPort/ws/voice"
        Log.d(tag, "Connecting to Rabbit Core at $wsUrl")

        val request = Request.Builder()
            .url(wsUrl)
            .build()

        webSocket = client?.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                Log.d(tag, "Connected to Rabbit WebSocket")
                isConnected = true
                mainHandler.post { listener.onConnected() }
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                handleIncomingMessage(text)
            }

            override fun onClosing(webSocket: WebSocket, code: Int, reason: String) {
                Log.d(tag, "Closing: $code / $reason")
                webSocket.close(1000, null)
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                Log.d(tag, "Closed: $code / $reason")
                isConnected = false
                mainHandler.post { listener.onDisconnected() }
                scheduleReconnect()
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                Log.e(tag, "Failure: ${t.message}")
                isConnected = false
                mainHandler.post {
                    listener.onDisconnected()
                    listener.onError(t.localizedMessage ?: "Connection failure")
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
                "connected" -> {
                    val msg = json.get("message")?.asString ?: "র্যাবিট অনলাইন"
                    mainHandler.post { listener.onTextReceived(msg, false) }
                }
                "state" -> {
                    val state = json.get("state")?.asString ?: "idle"
                    mainHandler.post { listener.onStateChange(state) }
                }
                "delta" -> {
                    val deltaText = json.get("text")?.asString ?: ""
                    mainHandler.post { listener.onTextReceived(deltaText, true) }
                }
                "audio" -> {
                    val audioUrl = json.get("url")?.asString ?: ""
                    val fullUrl = if (audioUrl.startsWith("http")) audioUrl else "http://$serverHost:$serverPort$audioUrl"
                    val text = json.get("text")?.asString
                    mainHandler.post { listener.onAudioReceived(fullUrl, text) }
                }
                "action" -> {
                    val actionName = json.get("action")?.asString ?: ""
                    val params = json.get("params")?.asJsonObject
                    mainHandler.post { listener.onActionReceived(actionName, params) }
                }
                "error" -> {
                    val err = json.get("error")?.asString ?: "Unknown error"
                    mainHandler.post { listener.onError(err) }
                }
            }
        } catch (e: Exception) {
            Log.e(tag, "Error parsing message: $rawJson", e)
        }
    }

    fun sendUserText(banglaText: String) {
        if (!isConnected || webSocket == null) {
            listener.onError("র্যাবিট কোরের সাথে সংযোগ নেই।")
            return
        }
        val payload = JsonObject().apply {
            addProperty("type", "user_text")
            addProperty("text", banglaText)
        }
        webSocket?.send(gson.toJson(payload))
    }

    fun disconnect() {
        shouldReconnect = false
        webSocket?.close(1000, "Normal Closure")
        isConnected = false
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

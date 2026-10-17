package com.rabbit.assistant.voice

import android.content.Context
import android.media.AudioAttributes
import android.media.MediaPlayer
import android.net.Uri
import android.util.Log

class AudioStreamPlayer(
    private val context: Context,
    private val listener: PlaybackCallback
) {
    private val tag = "RabbitAudio"
    private var mediaPlayer: MediaPlayer? = null
    private var isPlaying = false

    interface PlaybackCallback {
        fun onPlaybackStarted()
        fun onPlaybackCompleted()
        fun onPlaybackError(message: String)
    }

    fun playAudioUrl(audioUrl: String) {
        stop()

        try {
            Log.d(tag, "Streaming audio from: $audioUrl")
            mediaPlayer = MediaPlayer().apply {
                setAudioAttributes(
                    AudioAttributes.Builder()
                        .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                        .setUsage(AudioAttributes.USAGE_ASSISTANT)
                        .build()
                )
                setDataSource(context, Uri.parse(audioUrl))
                setOnPreparedListener { mp ->
                    isPlaying = true
                    mp.start()
                    listener.onPlaybackStarted()
                }
                setOnCompletionListener {
                    isPlaying = false
                    listener.onPlaybackCompleted()
                    releasePlayer()
                }
                setOnErrorListener { _, what, extra ->
                    isPlaying = false
                    val err = "Playback error: what=$what extra=$extra"
                    Log.e(tag, err)
                    listener.onPlaybackError(err)
                    releasePlayer()
                    true
                }
                prepareAsync()
            }
        } catch (e: Exception) {
            isPlaying = false
            Log.e(tag, "Failed to initialize playback for $audioUrl", e)
            listener.onPlaybackError(e.localizedMessage ?: "Playback initialization failed")
        }
    }

    fun stop() {
        if (isPlaying) {
            try {
                mediaPlayer?.stop()
            } catch (e: Exception) {
                Log.e(tag, "Error stopping mediaPlayer", e)
            }
        }
        releasePlayer()
        isPlaying = false
    }

    private fun releasePlayer() {
        try {
            mediaPlayer?.release()
        } catch (e: Exception) {
            Log.e(tag, "Error releasing mediaPlayer", e)
        }
        mediaPlayer = null
    }

    fun isPlayingAudio(): Boolean = isPlaying
}

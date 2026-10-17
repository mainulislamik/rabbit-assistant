package com.rabbit.assistant

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.os.Build

class RabbitApp : Application() {

    companion object {
        const val CHANNEL_ID = "rabbit_voice_channel"
        const val UPDATE_CHANNEL_ID = "rabbit_update_channel"
        lateinit var instance: RabbitApp
            private set
    }

    override fun onCreate() {
        super.onCreate()
        instance = this
        createNotificationChannels()
    }

    private fun createNotificationChannels() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Rabbit Voice Protocol",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Background Voice Service for Rabbit Assistant"
            }

            val updateChannel = NotificationChannel(
                UPDATE_CHANNEL_ID,
                "Rabbit System Updates",
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "Self-update notifications for Rabbit Assistant"
            }

            val manager = getSystemService(NotificationManager::class.java)
            manager?.createNotificationChannel(channel)
            manager?.createNotificationChannel(updateChannel)
        }
    }
}

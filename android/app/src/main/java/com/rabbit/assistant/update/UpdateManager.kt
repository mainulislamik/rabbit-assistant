package com.rabbit.assistant.update

import android.app.NotificationManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.provider.Settings
import android.os.Handler

import android.os.Looper
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.core.content.FileProvider
import com.google.gson.JsonParser
import com.rabbit.assistant.RabbitApp
import okhttp3.*
import java.io.File
import java.io.FileOutputStream
import java.io.IOException

class UpdateManager(
    private val context: Context,
    private val listener: UpdateCallback
) {
    private val tag = "RabbitUpdate"
    private val client = OkHttpClient()
    private val mainHandler = Handler(Looper.getMainLooper())

    interface UpdateCallback {
        fun onUpdateCheckStarted()
        fun onUpdateAvailable(versionName: String, releaseNotes: String)
        fun onNoUpdateAvailable()
        fun onDownloadProgress(percent: Int)
        fun onDownloadCompleted(apkFile: File)
        fun onUpdateError(message: String)
    }

    fun checkForUpdates(serverHost: String, serverPort: Int, force: Boolean = false) {
        listener.onUpdateCheckStarted()
        val checkUrl = "http://$serverHost:$serverPort/api/updates/check"
        Log.d(tag, "Checking update at $checkUrl")

        val request = Request.Builder().url(checkUrl).build()
        client.newCall(request).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                Log.e(tag, "Update check failed", e)
                mainHandler.post {
                    listener.onUpdateError("আপডেট সার্ভারের সাথে সংযোগ করা সম্ভব হয়নি।")
                }
            }

            override fun onResponse(call: Call, response: Response) {
                response.use {
                    if (!response.isSuccessful) {
                        mainHandler.post { listener.onUpdateError("আপডেট সার্ভার এরর: ${response.code}") }
                        return
                    }
                    val body = response.body?.string() ?: ""
                    try {
                        val json = JsonParser.parseString(body).asJsonObject
                        val serverVersionCode = json.get("version_code")?.asInt ?: 1
                        val serverVersionName = json.get("version_name")?.asString ?: "1.0.0"
                        val releaseNotes = json.get("release_notes")?.asString ?: "Bug fixes and improvements"
                        val downloadUrl = json.get("apk_url")?.asString ?: "/api/updates/download/latest"

                        val currentVersionCode = try {
                            val pInfo = context.packageManager.getPackageInfo(context.packageName, 0)
                            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                                pInfo.longVersionCode.toInt()
                            } else {
                                @Suppress("DEPRECATION")
                                pInfo.versionCode
                            }
                        } catch (e: Exception) {
                            1
                        }

                        if (serverVersionCode > currentVersionCode || force) {
                            val fullDownloadUrl = if (downloadUrl.startsWith("http")) downloadUrl else "http://$serverHost:$serverPort$downloadUrl"
                            mainHandler.post {
                                listener.onUpdateAvailable(serverVersionName, releaseNotes)
                                startDownload(fullDownloadUrl, serverVersionName)
                            }
                        } else {
                            mainHandler.post { listener.onNoUpdateAvailable() }
                        }
                    } catch (e: Exception) {
                        Log.e(tag, "Failed to parse update manifest", e)
                        mainHandler.post { listener.onUpdateError("আপডেট ডাটা প্রসেস করতে ব্যর্থ হয়েছে।") }
                    }
                }
            }
        })
    }

    fun startDownload(downloadUrl: String, versionName: String) {
        val request = Request.Builder().url(downloadUrl).build()

        val notificationManager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val notifBuilder = NotificationCompat.Builder(context, RabbitApp.UPDATE_CHANNEL_ID)
            .setSmallIcon(android.R.drawable.stat_sys_download)
            .setContentTitle("Rabbit OS আপডেট ডাউনলোড হচ্ছে")
            .setContentText("সংস্করণ $versionName")
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setOngoing(true)
            .setProgress(100, 0, false)

        notificationManager.notify(101, notifBuilder.build())

        client.newCall(request).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                notificationManager.cancel(101)
                mainHandler.post { listener.onUpdateError("APK ডাউনলোড ব্যর্থ হয়েছে: ${e.message}") }
            }

            override fun onResponse(call: Call, response: Response) {
                response.use {
                    if (!response.isSuccessful) {
                        notificationManager.cancel(101)
                        mainHandler.post { listener.onUpdateError("ডাউনলোড রেসপন্স এরর: ${response.code}") }
                        return
                    }

                    val body = response.body ?: return
                    val contentLength = body.contentLength()
                    val updatesDir = File(context.getExternalFilesDir(null), "updates")
                    if (!updatesDir.exists()) updatesDir.mkdirs()
                    val apkFile = File(updatesDir, "rabbit_update_$versionName.apk")

                    try {
                        body.byteStream().use { input ->
                            FileOutputStream(apkFile).use { output ->
                                val buffer = ByteArray(8 * 1024)
                                var totalBytesRead = 0L
                                var bytesRead: Int
                                var lastProgress = 0

                                while (input.read(buffer).also { bytesRead = it } != -1) {
                                    output.write(buffer, 0, bytesRead)
                                    totalBytesRead += bytesRead
                                    if (contentLength > 0) {
                                        val progress = ((totalBytesRead * 100) / contentLength).toInt()
                                        if (progress > lastProgress) {
                                            lastProgress = progress
                                            notifBuilder.setProgress(100, progress, false)
                                            notificationManager.notify(101, notifBuilder.build())
                                            mainHandler.post { listener.onDownloadProgress(progress) }
                                        }
                                    }
                                }
                                output.flush()
                            }
                        }

                        notificationManager.cancel(101)
                        mainHandler.post {
                            listener.onDownloadCompleted(apkFile)
                            installApk(apkFile)
                        }
                    } catch (e: Exception) {
                        notificationManager.cancel(101)
                        Log.e(tag, "Error saving APK", e)
                        mainHandler.post { listener.onUpdateError("APK সংরক্ষণ করতে ব্যর্থ হয়েছে।") }
                    }
                }
            }
        })
    }

    fun installApk(apkFile: File) {
        if (!apkFile.exists()) {
            listener.onUpdateError("ইনস্টলার ফাইল পাওয়া যায়নি।")
            return
        }

        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                if (!context.packageManager.canRequestPackageInstalls()) {
                    val manageIntent = Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES).apply {
                        data = Uri.parse("package:${context.packageName}")
                        addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                    }
                    context.startActivity(manageIntent)
                    listener.onUpdateError("স্বয়ংক্রিয় আপডেটের জন্য 'Install unknown apps' পারমিশন অন করুন।")
                    return
                }
            }

            val apkUri: Uri = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {

                FileProvider.getUriForFile(
                    context,
                    "${context.packageName}.provider",
                    apkFile
                )
            } else {
                Uri.fromFile(apkFile)
            }

            val installIntent = Intent(Intent.ACTION_VIEW).apply {
                setDataAndType(apkUri, "application/vnd.android.package-archive")
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }

            context.startActivity(installIntent)
        } catch (e: Exception) {
            Log.e(tag, "Failed to launch package installer", e)
            listener.onUpdateError("প্যাকেজ ইনস্টলার চালু করতে ব্যর্থ: ${e.message}")
        }
    }
}

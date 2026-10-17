package com.rabbit.assistant.device

import android.content.Context
import android.content.Intent
import android.hardware.camera2.CameraAccessException
import android.hardware.camera2.CameraCharacteristics
import android.hardware.camera2.CameraManager
import android.media.AudioManager
import android.net.Uri
import android.os.BatteryManager
import android.os.Build
import android.provider.MediaStore
import android.provider.Settings
import android.util.Log
import android.widget.Toast
import com.google.gson.JsonObject

class DeviceActionHandler(
    private val context: Context,
    private val actionCallback: ActionExecutionCallback
) {
    private val tag = "RabbitAction"
    private val cameraManager = context.getSystemService(Context.CAMERA_SERVICE) as? CameraManager
    private val audioManager = context.getSystemService(Context.AUDIO_SERVICE) as? AudioManager
    private var isTorchOn = false

    interface ActionExecutionCallback {
        fun onActionExecuted(actionName: String, summaryBangla: String)
        fun onTriggerSelfUpdate()
    }

    fun handleAction(action: String, params: JsonObject?): Boolean {
        Log.d(tag, "Executing device action: $action with params: $params")
        return when (action.uppercase()) {
            "FLASHLIGHT_ON" -> setFlashlight(true)
            "FLASHLIGHT_OFF" -> setFlashlight(false)
            "VOLUME_UP" -> adjustVolume(AudioManager.ADJUST_RAISE)
            "VOLUME_DOWN" -> adjustVolume(AudioManager.ADJUST_LOWER)
            "VOLUME_MUTE" -> muteVolume()
            "CHECK_BATTERY" -> checkBatteryLevel()
            "OPEN_APP" -> openApp(params?.get("app_name")?.asString ?: "")
            "MAKE_CALL" -> makePhoneCall(params?.get("phone_number")?.asString ?: "")
            "SEND_SMS" -> sendSms(
                params?.get("phone_number")?.asString ?: "",
                params?.get("message")?.asString ?: ""
            )
            "SELF_UPDATE" -> {
                actionCallback.onTriggerSelfUpdate()
                true
            }
            else -> {
                Log.w(tag, "Unknown or unsupported action: $action")
                false
            }
        }
    }

    private fun setFlashlight(enable: Boolean): Boolean {
        val cm = cameraManager ?: return false
        try {
            val cameraId = cm.cameraIdList.firstOrNull { id ->
                cm.getCameraCharacteristics(id)
                    .get(CameraCharacteristics.FLASH_INFO_AVAILABLE) == true
            }

            if (cameraId != null) {
                cm.setTorchMode(cameraId, enable)
                isTorchOn = enable
                val msg = if (enable) "টর্চ লাইট জ্বালানো হয়েছে, স্যার।" else "টর্চ লাইট বন্ধ করা হয়েছে, স্যার।"
                actionCallback.onActionExecuted(if (enable) "FLASHLIGHT_ON" else "FLASHLIGHT_OFF", msg)
                return true
            }
        } catch (e: Exception) {
            Log.e(tag, "Failed to toggle flashlight", e)
        }
        return false
    }

    private fun adjustVolume(direction: Int): Boolean {
        try {
            audioManager?.adjustStreamVolume(
                AudioManager.STREAM_MUSIC,
                direction,
                AudioManager.FLAG_SHOW_UI
            )
            val msg = if (direction == AudioManager.ADJUST_RAISE) "ভলিউম বাড়ানো হয়েছে।" else "ভলিউম কমানো হয়েছে।"
            actionCallback.onActionExecuted("VOLUME_CHANGE", msg)
            return true
        } catch (e: Exception) {
            Log.e(tag, "Volume adjustment failed", e)
        }
        return false
    }

    private fun muteVolume(): Boolean {
        try {
            audioManager?.adjustStreamVolume(
                AudioManager.STREAM_MUSIC,
                AudioManager.ADJUST_MUTE,
                AudioManager.FLAG_SHOW_UI
            )
            actionCallback.onActionExecuted("VOLUME_MUTE", "ভলিউম মিউট করা হয়েছে।")
            return true
        } catch (e: Exception) {
            Log.e(tag, "Volume mute failed", e)
        }
        return false
    }

    private fun checkBatteryLevel(): Boolean {
        val batteryManager = context.getSystemService(Context.BATTERY_SERVICE) as? BatteryManager
        val batteryLevel = batteryManager?.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY) ?: -1
        val isCharging = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            batteryManager?.isCharging == true
        } else false

        val chargingText = if (isCharging) "এবং ফোনটি চার্জ হচ্ছে" else "এবং ব্যাটারিতে চলছে"
        val msg = "স্যার, আপনার ফোনের ব্যাটারি বর্তমানে $batteryLevel% $chargingText।"
        actionCallback.onActionExecuted("CHECK_BATTERY", msg)
        return true
    }

    private fun openApp(appName: String): Boolean {
        val cleanName = appName.trim().lowercase()
        val packageName = when {
            cleanName.contains("youtube") || cleanName.contains("ইউটিউব") -> "com.google.android.youtube"
            cleanName.contains("whatsapp") || cleanName.contains("হোয়াটসঅ্যাপ") -> "com.whatsapp"
            cleanName.contains("chrome") || cleanName.contains("ক্রোম") -> "com.android.chrome"
            cleanName.contains("camera") || cleanName.contains("ক্যামেরা") -> {
                val intent = Intent(MediaStore.ACTION_IMAGE_CAPTURE).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                context.startActivity(intent)
                actionCallback.onActionExecuted("OPEN_APP", "ক্যামেরা চালু করা হচ্ছে, স্যার।")
                return true
            }
            cleanName.contains("settings") || cleanName.contains("সেটিংস") -> {
                val intent = Intent(Settings.ACTION_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                context.startActivity(intent)
                actionCallback.onActionExecuted("OPEN_APP", "ফোন সেটিংস খোলা হচ্ছে, স্যার।")
                return true
            }
            else -> null
        }

        if (packageName != null) {
            val launchIntent = context.packageManager.getLaunchIntentForPackage(packageName)
            if (launchIntent != null) {
                launchIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                context.startActivity(launchIntent)
                actionCallback.onActionExecuted("OPEN_APP", "$appName অ্যাপ্লিকেশন খোলা হচ্ছে, স্যার।")
                return true
            }
        }

        // Generic launch by installed apps
        val pm = context.packageManager
        val apps = pm.getInstalledApplications(0)
        for (app in apps) {
            val label = pm.getApplicationLabel(app).toString().lowercase()
            if (label.contains(cleanName)) {
                val launchIntent = pm.getLaunchIntentForPackage(app.packageName)
                if (launchIntent != null) {
                    launchIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                    context.startActivity(launchIntent)
                    actionCallback.onActionExecuted("OPEN_APP", "$label অ্যাপ্লিকেশন খোলা হচ্ছে, স্যার।")
                    return true
                }
            }
        }

        actionCallback.onActionExecuted("OPEN_APP_FAILED", "$appName অ্যাপ্লিকেশনটি ফোনে খুঁজে পাওয়া যায়নি।")
        return false
    }

    private fun makePhoneCall(number: String): Boolean {
        if (number.isBlank()) return false
        try {
            val dialIntent = Intent(Intent.ACTION_DIAL, Uri.parse("tel:${Uri.encode(number)}")).apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            context.startActivity(dialIntent)
            actionCallback.onActionExecuted("MAKE_CALL", "$number নম্বরে কল ডায়াল করা হচ্ছে, স্যার।")
            return true
        } catch (e: Exception) {
            Log.e(tag, "Call dial failed", e)
        }
        return false
    }

    private fun sendSms(number: String, message: String): Boolean {
        try {
            val smsIntent = Intent(Intent.ACTION_SENDTO, Uri.parse("smsto:${Uri.encode(number)}")).apply {
                putExtra("sms_body", message)
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            context.startActivity(smsIntent)
            actionCallback.onActionExecuted("SEND_SMS", "$number নম্বরে এসএমএস প্রেরণের স্ক্রিন খোলা হয়েছে, স্যার।")
            return true
        } catch (e: Exception) {
            Log.e(tag, "SMS launch failed", e)
        }
        return false
    }
}

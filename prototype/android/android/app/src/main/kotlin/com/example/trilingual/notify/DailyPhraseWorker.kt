package com.example.trilingual.notify

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import androidx.core.app.NotificationCompat
import androidx.work.*
import com.example.trilingual.MainActivity
import com.example.trilingual.R
import java.util.Calendar
import java.util.concurrent.TimeUnit

/**
 * Daily 8 AM reminder. The notification just nudges the parent — the actual
 * `DailyPhrase` is generated when they open the app (the model isn't loaded
 * in this background worker).
 */
class DailyPhraseWorker(ctx: Context, params: WorkerParameters) : Worker(ctx, params) {

    override fun doWork(): Result {
        ensureChannel(applicationContext)
        val openApp = PendingIntent.getActivity(
            applicationContext, 0,
            Intent(applicationContext, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
        )
        val n = NotificationCompat.Builder(applicationContext, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle("Today's family phrase 🌅")
            .setContentText("Open Trilingual Family for your KO/RU/EN phrase of the day.")
            .setContentIntent(openApp)
            .setAutoCancel(true)
            .build()
        val nm = applicationContext.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        nm.notify(NOTIF_ID, n)
        return Result.success()
    }

    companion object {
        const val CHANNEL_ID = "daily_phrase"
        const val NOTIF_ID = 4242
        const val WORK_NAME = "daily_phrase_8am"

        fun ensureChannel(ctx: Context) {
            val nm = ctx.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            if (nm.getNotificationChannel(CHANNEL_ID) == null) {
                nm.createNotificationChannel(
                    NotificationChannel(CHANNEL_ID, "Daily phrase", NotificationManager.IMPORTANCE_DEFAULT)
                )
            }
        }

        fun schedule(ctx: Context) {
            val now = Calendar.getInstance()
            val target = Calendar.getInstance().apply {
                set(Calendar.HOUR_OF_DAY, 8)
                set(Calendar.MINUTE, 0); set(Calendar.SECOND, 0); set(Calendar.MILLISECOND, 0)
                if (timeInMillis <= now.timeInMillis) add(Calendar.DAY_OF_MONTH, 1)
            }
            val initialDelay = target.timeInMillis - now.timeInMillis
            val req = PeriodicWorkRequestBuilder<DailyPhraseWorker>(1, TimeUnit.DAYS)
                .setInitialDelay(initialDelay, TimeUnit.MILLISECONDS)
                .build()
            WorkManager.getInstance(ctx).enqueueUniquePeriodicWork(
                WORK_NAME, ExistingPeriodicWorkPolicy.KEEP, req,
            )
        }
    }
}

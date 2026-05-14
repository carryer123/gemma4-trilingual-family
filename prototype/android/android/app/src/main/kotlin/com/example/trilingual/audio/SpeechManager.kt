package com.example.trilingual.audio

import android.content.Context
import android.content.Intent
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import kotlinx.coroutines.suspendCancellableCoroutine
import java.util.Locale
import kotlin.coroutines.resume

/**
 * Single-shot on-device speech-to-text. Returns the top final hypothesis or
 * null on error/timeout. Pick locale by which language the child is trying.
 */
class SpeechManager(private val ctx: Context) {

    suspend fun listenOnce(locale: Locale = Locale.KOREAN, timeoutMs: Long = 6_000): String? =
        suspendCancellableCoroutine { cont ->
            val sr = SpeechRecognizer.createSpeechRecognizer(ctx)
            val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                putExtra(RecognizerIntent.EXTRA_LANGUAGE, locale.toLanguageTag())
                putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, false)
                putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE, true)
                putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS, 1500L)
            }
            sr.setRecognitionListener(object : RecognitionListener {
                override fun onReadyForSpeech(p0: android.os.Bundle?) {}
                override fun onBeginningOfSpeech() {}
                override fun onRmsChanged(p0: Float) {}
                override fun onBufferReceived(p0: ByteArray?) {}
                override fun onEndOfSpeech() {}
                override fun onError(err: Int) { sr.destroy(); if (cont.isActive) cont.resume(null) }
                override fun onResults(b: android.os.Bundle?) {
                    val list = b?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                    sr.destroy()
                    if (cont.isActive) cont.resume(list?.firstOrNull())
                }
                override fun onPartialResults(p0: android.os.Bundle?) {}
                override fun onEvent(p0: Int, p1: android.os.Bundle?) {}
            })
            sr.startListening(intent)
            cont.invokeOnCancellation { runCatching { sr.destroy() } }
        }
}

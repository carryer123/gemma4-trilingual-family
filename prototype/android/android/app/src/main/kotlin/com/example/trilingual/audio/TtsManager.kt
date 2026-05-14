package com.example.trilingual.audio

import android.content.Context
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.suspendCancellableCoroutine
import java.util.Locale
import java.util.UUID
import kotlin.coroutines.resume

/**
 * 3-language TTS queue. Plays KO → RU → EN sequentially with per-utterance
 * locale switch. Suspends until all items in a batch finish.
 *
 * Used by:
 *   - bedtime story (3 paras × 3 langs = 9 utterances)
 *   - object card (3 utterances)
 *   - daily phrase (3 utterances)
 *   - mealtime narration (3 utterances per detected object)
 */
class TtsManager(ctx: Context) {

    sealed class Item { data class Speak(val text: String, val locale: Locale) : Item() }

    private val ready = Channel<Boolean>(Channel.CONFLATED)
    private val tts = TextToSpeech(ctx) { status ->
        ready.trySend(status == TextToSpeech.SUCCESS)
    }

    init {
        tts.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
            override fun onStart(id: String?) {}
            override fun onDone(id: String?) { id?.let { doneSignal[it]?.invoke() } }
            override fun onError(id: String?) { id?.let { doneSignal[it]?.invoke() } }
        })
    }

    private val doneSignal = mutableMapOf<String, () -> Unit>()

    private suspend fun awaitInit() {
        ready.receive()
    }

    suspend fun speakOne(text: String, locale: Locale) {
        awaitInit()
        tts.language = locale
        val id = UUID.randomUUID().toString()
        suspendCancellableCoroutine<Unit> { cont ->
            doneSignal[id] = { doneSignal.remove(id); cont.resume(Unit) }
            tts.speak(text, TextToSpeech.QUEUE_ADD, null, id)
            cont.invokeOnCancellation { doneSignal.remove(id); tts.stop() }
        }
    }

    suspend fun speakSequence(items: List<Item.Speak>) {
        items.forEach { speakOne(it.text, it.locale) }
    }

    fun shutdown() { tts.stop(); tts.shutdown() }

    companion object {
        val KO: Locale = Locale.KOREAN
        val RU: Locale = Locale("ru", "RU")
        val EN: Locale = Locale.US
        val FR: Locale = Locale.FRANCE
        fun forCode(code: String): Locale = when (code) {
            "ko" -> KO; "ru" -> RU; "fr" -> FR; else -> EN
        }
    }
}

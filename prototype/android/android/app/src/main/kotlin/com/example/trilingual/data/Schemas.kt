package com.example.trilingual.data

import kotlinx.serialization.Serializable
import kotlinx.serialization.SerialName
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.Json

/**
 * Family setup, persisted across sessions (DataStore).
 *
 * `householdLanguages` is a length-3 list of ISO codes from the demo set
 * {ko, ru, en, fr}. The 4L LoRA can route any 3-of-4 combination per session
 * (Household A = [ko,ru,en], Household B = [ko,fr,en], etc.).
 */
@Serializable
data class FamilySetup(
    val childName: String = "the child",
    val ageBand: String = "0-2",                 // 0-2 | 3-5 | 6-8
    val mode: String = "baby_0_2",               // baby_0_2 | child_3_6 | parent_bridge
    val bridge: String = "en",                   // narration / explanation lang for the parent
    val householdLanguages: List<String> = listOf("ko", "ru", "en"),  // any 3 of {ko,ru,en,fr}
)

/** Custom family vocab — F3. Stored in {ko,ru,en,fr} where applicable. */
@Serializable
data class FamilyWord(
    val ko: String = "",
    val ru: String = "",
    val en: String = "",
    val fr: String = "",
    val emoji: String = "",
    val note: String = "",
) {
    fun toPromptLine(active: List<String>): String {
        val parts = active.mapNotNull { l ->
            when (l) {
                "ko" -> ko.takeIf { it.isNotBlank() }
                "ru" -> ru.takeIf { it.isNotBlank() }
                "en" -> en.takeIf { it.isNotBlank() }
                "fr" -> fr.takeIf { it.isNotBlank() }
                else -> null
            }
        }
        val head = if (emoji.isNotBlank()) "$emoji " else ""
        val tail = if (note.isNotBlank()) " — $note" else ""
        return "- $head${parts.joinToString(" / ")}$tail"
    }
}

/* ---------- 4L canonical schemas (matches probes_v4_4l_audit.jsonl + LoRA training target) ---------- */

@Serializable
data class FamilyCard(
    val mode: String = "",                       // baby_0_2 | child_3_6 | parent_bridge
    @SerialName("age_band") val ageBand: String = "",
    @SerialName("active_languages") val activeLanguages: List<String> = emptyList(),
    val card: JsonElement? = null,               // free-form per mode (rendered raw on UI for now)
    @SerialName("next_action") val nextAction: String = "",
    val safety: Safety = Safety(),
)

@Serializable
data class Safety(
    @SerialName("child_safe") val childSafe: Boolean = true,
    @SerialName("no_private_data") val noPrivateData: Boolean = true,
)

/** F1 — bedtime story (one paragraph per active language). */
@Serializable
data class BedtimeStory(
    val theme: String = "",
    @SerialName("paragraphs_by_lang") val paragraphsByLang: Map<String, List<String>> = emptyMap(),
    @SerialName("age_band") val ageBand: String = "",
    @SerialName("child_name") val childName: String = "",
    val safety: Safety = Safety(),
)

/** F2 — daily family phrase. */
@Serializable
data class DailyPhrase(
    val date: String = "",
    @SerialName("phrase_by_lang") val phraseByLang: Map<String, String> = emptyMap(),
    val situation: String = "",
    @SerialName("pronunciation_hints_by_lang") val pronunciationHintsByLang: Map<String, String> = emptyMap(),
    val mission: String = "",
    val safety: Safety = Safety(),
)

/** F4 — pronunciation verdict. */
@Serializable
data class PronunciationVerdict(
    val target: String = "",
    @SerialName("heard_text") val heardText: String = "",
    @SerialName("score_0_3") val score: Int = 0,
    @SerialName("encouragement_in_bridge") val encouragement: String = "",
    @SerialName("retry_hint") val retryHint: String = "",
)

/** F5 — mealtime narration. */
@Serializable
data class MealtimeNarration(
    @SerialName("detected_object") val detectedObject: String = "",
    @SerialName("one_liner_by_lang") val oneLinerByLang: Map<String, String> = emptyMap(),
    @SerialName("child_question_in_bridge") val childQuestion: String = "",
)

object Schemas {
    val json = Json { ignoreUnknownKeys = true; isLenient = true; coerceInputValues = true }

    inline fun <reified T> parseOrNull(raw: String): T? {
        val s = raw.indexOf('{').takeIf { it >= 0 } ?: return null
        val e = raw.lastIndexOf('}').takeIf { it > s } ?: return null
        return runCatching { json.decodeFromString<T>(raw.substring(s, e + 1)) }.getOrNull()
    }
}

/** Display labels for the four supported demo languages. */
object Lang {
    val all = listOf("ko", "ru", "en", "fr")
    val labels = mapOf("ko" to "한국어", "ru" to "Русский", "en" to "English", "fr" to "Français")
    val ttsTag = mapOf("ko" to "ko-KR", "ru" to "ru-RU", "en" to "en-US", "fr" to "fr-FR")
    fun label(code: String): String = labels[code] ?: code.uppercase()
}

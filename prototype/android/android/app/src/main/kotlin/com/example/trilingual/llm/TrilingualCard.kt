package com.example.trilingual.llm

import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json

@Serializable
data class TrilingualCard(
    val `object`: String = "",
    val korean: String = "",
    val russian: String = "",
    val english: String = "",
    val l1Note: String = "",
    val pronunciationAid: String = "",
    val ageBand: String = "",
    val safetyFlag: String = "review",
) {
    val obj: String get() = `object`

    companion object {
        private val json = Json { ignoreUnknownKeys = true; isLenient = true }

        fun parseOrNull(raw: String): TrilingualCard? {
            val trimmed = extractJson(raw) ?: return null
            return runCatching {
                // tolerate snake_case from the model
                val normalized = trimmed
                    .replace("\"l1_note\"", "\"l1Note\"")
                    .replace("\"pronunciation_aid\"", "\"pronunciationAid\"")
                    .replace("\"age_band\"", "\"ageBand\"")
                    .replace("\"safety_flag\"", "\"safetyFlag\"")
                json.decodeFromString(serializer(), normalized)
            }.getOrNull()
        }

        private fun extractJson(raw: String): String? {
            val start = raw.indexOf('{')
            val end = raw.lastIndexOf('}')
            return if (start in 0 until end) raw.substring(start, end + 1) else null
        }
    }
}

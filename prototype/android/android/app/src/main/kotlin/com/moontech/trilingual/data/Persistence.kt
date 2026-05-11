package com.moontech.trilingual.data

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.firstOrNull
import kotlinx.coroutines.flow.map
import kotlinx.serialization.builtins.ListSerializer
import kotlinx.serialization.encodeToString

private val Context.dataStore by preferencesDataStore(name = "trilingual_family")
private val FAMILY_KEY = stringPreferencesKey("family_setup")
private val VOCAB_KEY  = stringPreferencesKey("family_vocab")
private val RECENT_KEY = stringPreferencesKey("recent_korean_phrases")

class Persistence(private val ctx: Context) {

    val familyFlow: Flow<FamilySetup> =
        ctx.dataStore.data.map { prefs ->
            prefs[FAMILY_KEY]?.let {
                runCatching { Schemas.json.decodeFromString<FamilySetup>(it) }.getOrNull()
            } ?: FamilySetup()
        }

    val vocabFlow: Flow<List<FamilyWord>> =
        ctx.dataStore.data.map { prefs ->
            prefs[VOCAB_KEY]?.let {
                runCatching { Schemas.json.decodeFromString(ListSerializer(FamilyWord.serializer()), it) }.getOrNull()
            } ?: emptyList()
        }

    val recentFlow: Flow<List<String>> =
        ctx.dataStore.data.map { prefs ->
            prefs[RECENT_KEY]?.let {
                runCatching { Schemas.json.decodeFromString(ListSerializer(kotlinx.serialization.builtins.serializer<String>()), it) }.getOrNull()
            } ?: emptyList()
        }

    suspend fun saveFamily(s: FamilySetup) {
        ctx.dataStore.edit { it[FAMILY_KEY] = Schemas.json.encodeToString(s) }
    }

    suspend fun saveVocab(v: List<FamilyWord>) {
        ctx.dataStore.edit {
            it[VOCAB_KEY] = Schemas.json.encodeToString(ListSerializer(FamilyWord.serializer()), v)
        }
    }

    suspend fun saveRecent(r: List<String>) {
        ctx.dataStore.edit {
            it[RECENT_KEY] = Schemas.json.encodeToString(ListSerializer(kotlinx.serialization.builtins.serializer<String>()), r.take(7))
        }
    }

    suspend fun loadFamilyOnce(): FamilySetup = familyFlow.firstOrNull() ?: FamilySetup()
}

package com.moontech.trilingual.ui.screens

import android.Manifest
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.google.accompanist.permissions.ExperimentalPermissionsApi
import com.google.accompanist.permissions.rememberPermissionState
import com.moontech.trilingual.audio.SpeechManager
import com.moontech.trilingual.audio.TtsManager
import com.moontech.trilingual.camera.CameraPreview
import com.moontech.trilingual.data.*
import com.moontech.trilingual.llm.LlmBackend
import com.moontech.trilingual.llm.PromptLibrary
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.contentOrNull
import kotlinx.coroutines.launch
import java.time.LocalDate
import java.util.Locale

/* ---------- shared state (DataStore-backed via AppState) ---------- */

object AppState {
    var family by mutableStateOf(FamilySetup())
    val vocab = mutableStateListOf<FamilyWord>()
    val recentDailyKorean = mutableStateListOf<String>()
    var persistence: Persistence? = null
    var tts: TtsManager? = null
    var speech: SpeechManager? = null

    fun saveFamilyAsync(scope: kotlinx.coroutines.CoroutineScope) {
        persistence?.let { p -> scope.launch { p.saveFamily(family) } }
    }
    fun saveVocabAsync(scope: kotlinx.coroutines.CoroutineScope) {
        persistence?.let { p -> scope.launch { p.saveVocab(vocab.toList()) } }
    }
    fun saveRecentAsync(scope: kotlinx.coroutines.CoroutineScope) {
        persistence?.let { p -> scope.launch { p.saveRecent(recentDailyKorean.toList()) } }
    }
}

@Composable private fun ScreenScaffold(title: String, body: @Composable ColumnScope.() -> Unit) {
    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text(title, style = MaterialTheme.typography.headlineSmall)
        body()
    }
}

private fun speakActive(c: kotlinx.coroutines.CoroutineScope, byLang: Map<String, String>, active: List<String>) {
    val tts = AppState.tts ?: return
    c.launch {
        active.mapNotNull { code ->
            byLang[code]?.takeIf { it.isNotBlank() }?.let { TtsManager.Item.Speak(it, TtsManager.forCode(code)) }
        }.let { tts.speakSequence(it) }
    }
}

/* ---------- Family setup onboarding ---------- */

@Composable
fun FamilySetupScreen(onDone: () -> Unit) {
    var name by remember { mutableStateOf(AppState.family.childName.takeIf { it != "the child" } ?: "") }
    var age by remember { mutableStateOf(AppState.family.ageBand) }
    var bridge by remember { mutableStateOf(AppState.family.bridge) }
    var langs by remember { mutableStateOf(AppState.family.householdLanguages.toMutableList()) }
    val scope = rememberCoroutineScope()
    ScreenScaffold("👋 Welcome — tell me about your family") {
        Text("Stays on this phone. Nothing leaves the device.", style = MaterialTheme.typography.bodySmall)
        OutlinedTextField(name, { name = it }, label = { Text("child's name (or nickname)") }, modifier = Modifier.fillMaxWidth())

        Text("Child age band")
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            listOf("0-2", "3-5", "6-8").forEach { a ->
                FilterChip(selected = age == a, onClick = { age = a }, label = { Text(a) })
            }
        }

        Text("Languages at home (pick exactly 3)")
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Lang.all.forEach { code ->
                val on = code in langs
                FilterChip(
                    selected = on,
                    onClick = {
                        langs = langs.toMutableList().apply {
                            if (on) remove(code) else if (size < 3) add(code)
                        }
                    },
                    label = { Text(Lang.label(code)) },
                )
            }
        }

        Text("Bridge language (parent narration)")
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            langs.forEach { code ->
                FilterChip(selected = bridge == code, onClick = { bridge = code }, label = { Text(Lang.label(code)) })
            }
        }

        Button(
            onClick = {
                if (langs.size != 3) return@Button
                val mode = when (age) {
                    "0-2" -> "baby_0_2"; "3-5" -> "child_3_6"; else -> "parent_bridge"
                }
                val effectiveBridge = if (bridge in langs) bridge else langs.first()
                AppState.family = AppState.family.copy(
                    childName = name.ifBlank { "the child" },
                    ageBand = age, mode = mode, bridge = effectiveBridge,
                    householdLanguages = langs.toList(),
                )
                AppState.saveFamilyAsync(scope)
                onDone()
            },
            enabled = langs.size == 3 && bridge in langs,
            modifier = Modifier.fillMaxWidth(),
        ) { Text("start") }
    }
}

/* ---------- shared card-rendering helpers ---------- */

@Composable private fun JsonValueText(label: String, v: JsonElement?) {
    v ?: return
    val text = when (v) {
        is JsonPrimitive -> v.contentOrNull ?: v.toString()
        is JsonObject -> v.entries.joinToString("\n") { (k, vv) ->
            "  $k: ${(vv as? JsonPrimitive)?.contentOrNull ?: vv.toString()}"
        }
        else -> v.toString()
    }
    Text("$label\n$text")
}

/* ---------- Core: object → multilingual family card ---------- */

@OptIn(ExperimentalPermissionsApi::class, androidx.camera.core.ExperimentalGetImage::class)
@Composable fun ObjectCardScreen(llm: LlmBackend) {
    var input by remember { mutableStateOf("apple") }
    var card by remember { mutableStateOf<FamilyCard?>(null) }
    var busy by remember { mutableStateOf(false) }
    var cameraOn by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()
    val cameraPerm = rememberPermissionState(Manifest.permission.CAMERA)

    ScreenScaffold("📷 Object → family card") {
        Text("Languages: " + AppState.family.householdLanguages.joinToString(" · ") { Lang.label(it) },
             style = MaterialTheme.typography.bodySmall)
        OutlinedTextField(input, { input = it }, label = { Text("object (or use camera)") }, modifier = Modifier.fillMaxWidth())
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(
                onClick = {
                    if (!cameraPerm.status.isGranted) cameraPerm.launchPermissionRequest()
                    else cameraOn = !cameraOn
                },
                modifier = Modifier.weight(1f),
            ) { Text(if (cameraOn) "stop camera" else "use camera") }
            Button(
                onClick = {
                    busy = true
                    scope.launch {
                        val raw = llm.generate(PromptLibrary.objectCard(input, AppState.family, AppState.vocab.toList()))
                        card = Schemas.parseOrNull<FamilyCard>(raw); busy = false
                    }
                },
                enabled = !busy,
                modifier = Modifier.weight(1f),
            ) { Text(if (busy) "thinking…" else "generate card") }
        }
        if (cameraOn && cameraPerm.status.isGranted) {
            Box(Modifier.fillMaxWidth().height(280.dp)) {
                CameraPreview(onLabel = { lbl -> input = lbl })
            }
            Text("Live label → \"$input\"", style = MaterialTheme.typography.bodySmall)
        }
        card?.let { c ->
            ElevatedCard {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text("mode: ${c.mode} · age: ${c.ageBand}")
                    Text("active: ${c.activeLanguages.joinToString(" / ")}")
                    HorizontalDivider()
                    JsonValueText("card:", c.card)
                    Text("next: ${c.nextAction}")
                    Text("safe: ${c.safety.childSafe} · privacy: ${c.safety.noPrivateData}",
                         style = MaterialTheme.typography.bodySmall)
                    val phrasesByLang: Map<String, String> = (c.card as? JsonObject)?.let { obj ->
                        c.activeLanguages.mapNotNull { code ->
                            (obj[code] as? JsonPrimitive)?.contentOrNull?.let { code to it }
                        }.toMap()
                    } ?: emptyMap()
                    if (phrasesByLang.isNotEmpty()) {
                        Button(
                            onClick = { speakActive(scope, phrasesByLang, c.activeLanguages) },
                            modifier = Modifier.fillMaxWidth(),
                        ) { Text("🔊 read aloud (${c.activeLanguages.joinToString(" → ")})") }
                    }
                }
            }
        }
    }
}

/* ---------- F1 bedtime story ---------- */
@Composable fun BedtimeStoryScreen(llm: LlmBackend) {
    var keyword by remember { mutableStateOf("the moon") }
    var story by remember { mutableStateOf<BedtimeStory?>(null) }
    var busy by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()
    ScreenScaffold("🌙 Multilingual bedtime story") {
        OutlinedTextField(keyword, { keyword = it }, label = { Text("topic / object") }, modifier = Modifier.fillMaxWidth())
        Button(
            onClick = {
                busy = true
                scope.launch {
                    val raw = llm.generate(PromptLibrary.bedtimeStory(keyword, AppState.family, AppState.vocab.toList()))
                    story = Schemas.parseOrNull<BedtimeStory>(raw); busy = false
                }
            },
            enabled = !busy,
            modifier = Modifier.fillMaxWidth(),
        ) { Text(if (busy) "weaving…" else "make a 60-second story") }
        story?.let { s ->
            AppState.family.householdLanguages.forEach { code ->
                paragraphCard(Lang.label(code), s.paragraphsByLang[code] ?: emptyList())
            }
            Button(
                onClick = {
                    val items = AppState.family.householdLanguages.flatMap { code ->
                        (s.paragraphsByLang[code] ?: emptyList()).map { TtsManager.Item.Speak(it, TtsManager.forCode(code)) }
                    }
                    scope.launch { AppState.tts?.speakSequence(items) }
                },
                modifier = Modifier.fillMaxWidth(),
            ) { Text("🔊 read aloud (${AppState.family.householdLanguages.joinToString(" → ")})") }
        }
    }
}

@Composable private fun paragraphCard(lang: String, paras: List<String>) {
    if (paras.isEmpty()) return
    ElevatedCard(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(lang, style = MaterialTheme.typography.titleMedium)
            paras.forEach { Text(it) }
        }
    }
}

/* ---------- F2 daily phrase ---------- */
@Composable fun DailyPhraseScreen(llm: LlmBackend) {
    var phrase by remember { mutableStateOf<DailyPhrase?>(null) }
    var busy by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()
    ScreenScaffold("📱 Today's family phrase") {
        Button(
            onClick = {
                busy = true
                scope.launch {
                    val raw = llm.generate(PromptLibrary.dailyPhrase(
                        date = LocalDate.now().toString(),
                        family = AppState.family,
                        recent = AppState.recentDailyKorean.toList(),
                        vocab = AppState.vocab.toList(),
                    ))
                    val p = Schemas.parseOrNull<DailyPhrase>(raw)
                    phrase = p
                    val firstActive = AppState.family.householdLanguages.firstOrNull() ?: "ko"
                    val rec = p?.phraseByLang?.get(firstActive)
                    if (!rec.isNullOrBlank()) {
                        AppState.recentDailyKorean.add(0, rec)
                        while (AppState.recentDailyKorean.size > 7) AppState.recentDailyKorean.removeLast()
                        AppState.saveRecentAsync(scope)
                    }
                    busy = false
                }
            },
            enabled = !busy,
            modifier = Modifier.fillMaxWidth(),
        ) { Text(if (busy) "picking…" else "today's phrase") }
        phrase?.let { p ->
            ElevatedCard {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    AppState.family.householdLanguages.forEach { code ->
                        Text("${Lang.label(code)}  ${p.phraseByLang[code].orEmpty()}")
                    }
                    HorizontalDivider()
                    Text("Situation: ${p.situation}")
                    Text("Mission: ${p.mission}", style = MaterialTheme.typography.titleSmall)
                    val hints = AppState.family.householdLanguages.joinToString(" · ") { code ->
                        "${code.uppercase()} ${p.pronunciationHintsByLang[code].orEmpty()}"
                    }
                    Text("Pronounce: $hints", style = MaterialTheme.typography.bodySmall)
                    Button(
                        onClick = { speakActive(scope, p.phraseByLang, AppState.family.householdLanguages) },
                        modifier = Modifier.fillMaxWidth(),
                    ) { Text("🔊 read aloud") }
                }
            }
        }
    }
}

/* ---------- F3 family word list (persisted, 4L) ---------- */
@Composable fun FamilyWordScreen(llm: LlmBackend) {
    var ko by remember { mutableStateOf("") }
    var ru by remember { mutableStateOf("") }
    var en by remember { mutableStateOf("") }
    var fr by remember { mutableStateOf("") }
    var note by remember { mutableStateOf("") }
    val scope = rememberCoroutineScope()
    val active = AppState.family.householdLanguages
    ScreenScaffold("👤 Our family's words") {
        Text("Saved on this phone only. Used in every prompt.", style = MaterialTheme.typography.bodyMedium)
        AppState.vocab.forEach { w ->
            ElevatedCard(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(12.dp)) {
                    Text(w.toPromptLine(active), style = MaterialTheme.typography.titleMedium)
                    if (w.note.isNotBlank()) Text(w.note, style = MaterialTheme.typography.bodySmall)
                }
            }
        }
        HorizontalDivider()
        if ("ko" in active) OutlinedTextField(ko, { ko = it }, label = { Text("KO") }, modifier = Modifier.fillMaxWidth())
        if ("ru" in active) OutlinedTextField(ru, { ru = it }, label = { Text("RU") }, modifier = Modifier.fillMaxWidth())
        if ("en" in active) OutlinedTextField(en, { en = it }, label = { Text("EN") }, modifier = Modifier.fillMaxWidth())
        if ("fr" in active) OutlinedTextField(fr, { fr = it }, label = { Text("FR") }, modifier = Modifier.fillMaxWidth())
        OutlinedTextField(note, { note = it }, label = { Text("note (optional)") }, modifier = Modifier.fillMaxWidth())
        Button(
            onClick = {
                val anyFilled = listOf(ko, ru, en, fr).any { it.isNotBlank() }
                if (anyFilled) {
                    AppState.vocab.add(FamilyWord(ko = ko.trim(), ru = ru.trim(), en = en.trim(), fr = fr.trim(), note = note.trim()))
                    AppState.saveVocabAsync(scope)
                    ko = ""; ru = ""; en = ""; fr = ""; note = ""
                }
            },
            modifier = Modifier.fillMaxWidth(),
        ) { Text("save to family vocab") }
    }
}

/* ---------- F4 pronunciation game ---------- */
@OptIn(ExperimentalPermissionsApi::class)
@Composable fun PronunciationGameScreen(llm: LlmBackend) {
    var target by remember { mutableStateOf("사과") }
    var heard by remember { mutableStateOf("") }
    var verdict by remember { mutableStateOf<PronunciationVerdict?>(null) }
    var busy by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()
    val ctx = LocalContext.current
    val micPerm = rememberPermissionState(Manifest.permission.RECORD_AUDIO)

    fun localeFor(t: String): Locale = when {
        t.any { it in 'ㄱ'..'힯' } -> TtsManager.KO
        t.any { it in 'Ѐ'..'ӿ' } -> TtsManager.RU
        // simple French-ness heuristic: Latin diacritics
        t.any { it in "àâäçéèêëîïôöùûüÿœæ" } -> TtsManager.FR
        else -> TtsManager.EN
    }

    ScreenScaffold("🎤 Pronunciation game") {
        OutlinedTextField(target, { target = it }, label = { Text("target word") }, modifier = Modifier.fillMaxWidth())
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(
                onClick = {
                    if (!micPerm.status.isGranted) { micPerm.launchPermissionRequest(); return@Button }
                    scope.launch {
                        heard = AppState.speech?.listenOnce(localeFor(target)) ?: ""
                    }
                },
                modifier = Modifier.weight(1f),
            ) { Text("🎙 listen") }
            Button(
                onClick = {
                    busy = true
                    scope.launch {
                        val raw = llm.generate(PromptLibrary.pronunciation(target, heard, AppState.family))
                        verdict = Schemas.parseOrNull<PronunciationVerdict>(raw); busy = false
                    }
                },
                enabled = !busy && heard.isNotBlank(),
                modifier = Modifier.weight(1f),
            ) { Text(if (busy) "judging…" else "score") }
        }
        if (heard.isNotBlank()) Text("heard: \"$heard\"", style = MaterialTheme.typography.bodySmall)
        verdict?.let { v ->
            ElevatedCard {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text("★".repeat(v.score) + "☆".repeat((3 - v.score).coerceAtLeast(0)),
                         style = MaterialTheme.typography.headlineSmall)
                    Text(v.encouragement); Text(v.retryHint, style = MaterialTheme.typography.bodySmall)
                }
            }
        }
    }
}

/* ---------- F5 mealtime mode ---------- */
@OptIn(ExperimentalPermissionsApi::class, androidx.camera.core.ExperimentalGetImage::class)
@Composable fun MealtimeScreen(llm: LlmBackend) {
    var running by remember { mutableStateOf(false) }
    var lastObject by remember { mutableStateOf<String?>(null) }
    var lastNar by remember { mutableStateOf<MealtimeNarration?>(null) }
    val scope = rememberCoroutineScope()
    val cameraPerm = rememberPermissionState(Manifest.permission.CAMERA)
    var startedAt by remember { mutableLongStateOf(0L) }
    val nowMs = remember { mutableLongStateOf(System.currentTimeMillis()) }

    LaunchedEffect(running) {
        if (running) {
            startedAt = System.currentTimeMillis()
            while (running && System.currentTimeMillis() - startedAt < 5 * 60_000) {
                nowMs.longValue = System.currentTimeMillis()
                kotlinx.coroutines.delay(1000)
            }
            running = false
        }
    }

    ScreenScaffold("🍎 Mealtime mode (5 min auto)") {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(
                onClick = {
                    if (!cameraPerm.status.isGranted) cameraPerm.launchPermissionRequest()
                    else running = !running
                },
                modifier = Modifier.weight(1f),
            ) { Text(if (running) "stop" else "start 5-min meal") }
            if (running) {
                val remaining = 5 * 60 - ((nowMs.longValue - startedAt) / 1000).toInt()
                Text("${remaining / 60}:${"%02d".format(remaining % 60)}", style = MaterialTheme.typography.titleMedium)
            }
        }
        if (running && cameraPerm.status.isGranted) {
            Box(Modifier.fillMaxWidth().height(260.dp)) {
                CameraPreview(onLabel = { lbl ->
                    if (lbl == lastObject) return@CameraPreview
                    lastObject = lbl
                    scope.launch {
                        val raw = llm.generate(PromptLibrary.mealtimeNarration(lbl, AppState.family, AppState.vocab.toList()))
                        val n = Schemas.parseOrNull<MealtimeNarration>(raw)
                        lastNar = n
                        if (n != null) speakActive(this, n.oneLinerByLang, AppState.family.householdLanguages)
                    }
                })
            }
        }
        lastObject?.let { Text("now seeing: $it", style = MaterialTheme.typography.bodySmall) }
        lastNar?.let { n ->
            ElevatedCard {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    AppState.family.householdLanguages.forEach { code ->
                        Text("${Lang.label(code)} ${n.oneLinerByLang[code].orEmpty()}")
                    }
                    HorizontalDivider(); Text("👶 ${n.childQuestion}")
                }
            }
        }
    }
}

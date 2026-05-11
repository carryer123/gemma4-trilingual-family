package com.moontech.trilingual

import android.Manifest
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.lifecycle.lifecycleScope
import com.moontech.trilingual.audio.SpeechManager
import com.moontech.trilingual.audio.TtsManager
import com.moontech.trilingual.data.Persistence
import com.moontech.trilingual.llm.LlmBackend
import com.moontech.trilingual.llm.LiteRtLmBackend
import com.moontech.trilingual.notify.DailyPhraseWorker
import com.moontech.trilingual.ui.TrilingualApp
import com.moontech.trilingual.ui.screens.AppState
import com.moontech.trilingual.ui.screens.FamilySetupScreen
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {
    private lateinit var llm: LlmBackend

    private val notifPermLauncher = registerForActivityResult(ActivityResultContracts.RequestPermission()) { /* ignore result */ }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        llm = LiteRtLmBackend(applicationContext)
        AppState.persistence = Persistence(applicationContext)
        AppState.tts = TtsManager(applicationContext)
        AppState.speech = SpeechManager(applicationContext)

        // Hydrate persisted state
        lifecycleScope.launch {
            AppState.persistence?.familyFlow?.collectLatest { AppState.family = it }
        }
        lifecycleScope.launch {
            AppState.persistence?.vocabFlow?.collectLatest { v ->
                AppState.vocab.clear(); AppState.vocab.addAll(v)
            }
        }
        lifecycleScope.launch {
            AppState.persistence?.recentFlow?.collectLatest { r ->
                AppState.recentDailyKorean.clear(); AppState.recentDailyKorean.addAll(r)
            }
        }

        // Daily reminder + notification permission (Android 13+)
        DailyPhraseWorker.schedule(applicationContext)
        if (Build.VERSION.SDK_INT >= 33) notifPermLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)

        setContent {
            MaterialTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    var loaded by remember { mutableStateOf(false) }
                    var err by remember { mutableStateOf<String?>(null) }
                    var setupDone by remember { mutableStateOf(AppState.family.childName != "the child") }
                    LaunchedEffect(Unit) {
                        runCatching { llm.initialize() }
                            .onSuccess { loaded = true }
                            .onFailure { err = it.message }
                    }
                    when {
                        !loaded -> Column(Modifier.fillMaxSize().padding(24.dp), verticalArrangement = Arrangement.Center) {
                            Text(err ?: "Loading on-device Gemma 4 E2B…", style = MaterialTheme.typography.titleMedium)
                            if (err == null) LinearProgressIndicator(Modifier.fillMaxWidth().padding(top = 12.dp))
                        }
                        !setupDone -> FamilySetupScreen(onDone = { setupDone = true })
                        else -> TrilingualApp(llm)
                    }
                }
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        AppState.tts?.shutdown()
        llm.close()
    }
}

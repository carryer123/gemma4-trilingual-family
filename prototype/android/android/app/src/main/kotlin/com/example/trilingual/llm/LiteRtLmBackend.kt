package com.example.trilingual.llm

import android.content.Context
import com.google.ai.edge.litertlm.Backend
import com.google.ai.edge.litertlm.Engine
import com.google.ai.edge.litertlm.EngineConfig
import com.google.ai.edge.litertlm.Session
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.toList
import kotlinx.coroutines.withContext
import java.io.File

/**
 * On-device Gemma 4 E2B + LoRA-v2 (merged) via LiteRT-LM.
 *
 * The .litertlm produced by `litert-torch export_hf` ships in the APK assets
 * and is copied to filesDir on first launch so LiteRT-LM can mmap it.
 *
 * NOTE: We use the raw `Session` API rather than `Engine.createConversation()`.
 * The high-level Conversation template layer is currently broken for Gemma 4
 * E2B exported via litert-torch (upstream issue google-ai-edge/LiteRT-LM#2078),
 * so we apply the Gemma 4 chat template ourselves.
 */
class LiteRtLmBackend(private val ctx: Context) : LlmBackend {

    private var engine: Engine? = null

    override suspend fun initialize() = withContext(Dispatchers.IO) {
        val target = File(ctx.filesDir, "models/gemma-4-E2B-it-merged.litertlm")
        if (!target.exists()) {
            target.parentFile?.mkdirs()
            ctx.assets.open("gemma-4-E2B-it-merged.litertlm").use { input ->
                target.outputStream().use { input.copyTo(it) }
            }
        }
        engine = Engine(
            EngineConfig(modelPath = target.absolutePath, backend = Backend.GPU())
        ).apply { initialize() }
    }

    override suspend fun generate(prompt: String, maxTokens: Int, temperature: Float): String =
        withContext(Dispatchers.Default) {
            val e = requireNotNull(engine) { "engine not initialized" }
            val templated = wrapGemma4Chat(prompt)
            val out = StringBuilder()
            // Raw Session bypasses the Conversation API so the model template
            // layer doesn't interfere. We feed the fully-formed prompt string.
            e.createSession().use { session: Session ->
                session.sendMessageAsync(templated).toList().forEach { out.append(it) }
            }
            out.toString().trim()
        }

    override fun close() {
        engine?.close(); engine = null
    }

    /** Apply Gemma 4 chat template by hand (matches HF chat_template.jinja). */
    private fun wrapGemma4Chat(userMsg: String): String =
        "<start_of_turn>user\n$userMsg<end_of_turn>\n<start_of_turn>model\n"
}

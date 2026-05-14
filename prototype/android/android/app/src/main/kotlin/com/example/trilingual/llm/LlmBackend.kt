package com.example.trilingual.llm

interface LlmBackend {
    suspend fun initialize()
    suspend fun generate(prompt: String, maxTokens: Int = 512, temperature: Float = 0.3f): String
    fun close()
}

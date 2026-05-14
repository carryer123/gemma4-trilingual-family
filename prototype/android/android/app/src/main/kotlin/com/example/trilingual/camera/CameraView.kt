package com.example.trilingual.camera

import android.content.Context
import androidx.camera.core.*
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.foundation.layout.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.label.ImageLabeling
import com.google.mlkit.vision.label.defaults.ImageLabelerOptions
import java.util.concurrent.Executors

/**
 * Compose camera preview that streams labels.
 * `onLabel` fires every ~1.5 s with the top label (>=0.5 confidence).
 * Pass `paused=true` when the screen wants to stop labeling.
 */
@androidx.camera.core.ExperimentalGetImage
@Composable
fun CameraPreview(
    onLabel: (String) -> Unit,
    modifier: Modifier = Modifier,
    paused: Boolean = false,
) {
    val ctx = LocalContext.current
    val owner = LocalLifecycleOwner.current
    var lastLabel by remember { mutableStateOf<String?>(null) }
    var lastEmit by remember { mutableLongStateOf(0L) }

    AndroidView(
        modifier = modifier.fillMaxSize(),
        factory = { c ->
            val previewView = PreviewView(c).apply {
                scaleType = PreviewView.ScaleType.FILL_CENTER
            }
            val executor = Executors.newSingleThreadExecutor()
            val labeler = ImageLabeling.getClient(ImageLabelerOptions.DEFAULT_OPTIONS)
            val future = ProcessCameraProvider.getInstance(c)
            future.addListener({
                val provider = future.get()
                val preview = Preview.Builder().build().also {
                    it.setSurfaceProvider(previewView.surfaceProvider)
                }
                val analysis = ImageAnalysis.Builder()
                    .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                    .build().also { a ->
                        a.setAnalyzer(executor) { img ->
                            if (paused) { img.close(); return@setAnalyzer }
                            val now = System.currentTimeMillis()
                            if (now - lastEmit < 1500) { img.close(); return@setAnalyzer }
                            val media = img.image ?: run { img.close(); return@setAnalyzer }
                            val input = InputImage.fromMediaImage(media, img.imageInfo.rotationDegrees)
                            labeler.process(input)
                                .addOnSuccessListener { labels ->
                                    val top = labels.firstOrNull { it.confidence >= 0.5f }?.text
                                    if (top != null && top != lastLabel) {
                                        lastLabel = top
                                        lastEmit = now
                                        onLabel(top)
                                    }
                                }
                                .addOnCompleteListener { img.close() }
                        }
                    }
                runCatching {
                    provider.unbindAll()
                    provider.bindToLifecycle(owner, CameraSelector.DEFAULT_BACK_CAMERA, preview, analysis)
                }
            }, ContextCompat.getMainExecutor(c))
            previewView
        },
    )
}

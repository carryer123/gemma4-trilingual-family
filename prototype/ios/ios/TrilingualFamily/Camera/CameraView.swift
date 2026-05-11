import SwiftUI
import AVFoundation
import Vision

/// Live camera preview that emits a top label every ~1.5 s via Vision.
/// Mirrors Android CameraPreview. Pure SwiftUI wrapper around a UIKit preview layer.
struct CameraPreviewView: UIViewRepresentable {
    let onLabel: (String) -> Void
    let isPaused: Bool

    func makeCoordinator() -> Coordinator { Coordinator(onLabel: onLabel) }
    func updateUIView(_ uiView: PreviewUIView, context: Context) {
        context.coordinator.paused = isPaused
    }

    func makeUIView(context: Context) -> PreviewUIView {
        let v = PreviewUIView()
        let coord = context.coordinator
        let session = AVCaptureSession()
        session.sessionPreset = .vga640x480

        guard let device = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: .back),
              let input = try? AVCaptureDeviceInput(device: device),
              session.canAddInput(input) else { return v }
        session.addInput(input)

        let output = AVCaptureVideoDataOutput()
        output.alwaysDiscardsLateVideoFrames = true
        output.setSampleBufferDelegate(coord, queue: DispatchQueue(label: "trilingual.video"))
        if session.canAddOutput(output) { session.addOutput(output) }

        let layer = AVCaptureVideoPreviewLayer(session: session)
        layer.videoGravity = .resizeAspectFill
        v.previewLayer = layer

        DispatchQueue.global(qos: .userInitiated).async { session.startRunning() }
        coord.session = session
        return v
    }

    final class PreviewUIView: UIView {
        var previewLayer: AVCaptureVideoPreviewLayer? {
            didSet {
                if let old = oldValue { old.removeFromSuperlayer() }
                if let l = previewLayer { layer.addSublayer(l) }
            }
        }
        override func layoutSubviews() {
            super.layoutSubviews()
            previewLayer?.frame = bounds
        }
    }

    final class Coordinator: NSObject, AVCaptureVideoDataOutputSampleBufferDelegate {
        let onLabel: (String) -> Void
        var paused: Bool = false
        var session: AVCaptureSession?
        private var lastEmit: TimeInterval = 0
        private var lastLabel: String?
        private let request: VNClassifyImageRequest = {
            let r = VNClassifyImageRequest()
            return r
        }()
        init(onLabel: @escaping (String) -> Void) { self.onLabel = onLabel }

        func captureOutput(_ output: AVCaptureOutput, didOutput sampleBuffer: CMSampleBuffer, from connection: AVCaptureConnection) {
            guard !paused else { return }
            let now = Date().timeIntervalSince1970
            guard now - lastEmit > 1.5 else { return }
            guard let pixel = CMSampleBufferGetImageBuffer(sampleBuffer) else { return }
            let handler = VNImageRequestHandler(cvPixelBuffer: pixel, orientation: .right, options: [:])
            do {
                try handler.perform([request])
                let top = (request.results ?? [])
                    .compactMap { $0 as? VNClassificationObservation }
                    .first(where: { $0.confidence >= 0.5 })?.identifier
                if let t = top, t != lastLabel {
                    lastLabel = t
                    lastEmit = now
                    DispatchQueue.main.async { self.onLabel(t) }
                }
            } catch {
                // ignore one-frame failure
            }
        }
    }
}

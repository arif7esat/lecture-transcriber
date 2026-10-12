// meeting-recorder — records system audio (ScreenCaptureKit) and the microphone
// (AVAudioEngine) into two separate CAF files. No virtual audio driver, no change
// to the output device: speakers, headphones and volume keys keep working.
//
// Usage: meeting-recorder <system.caf> <microphone.caf>
// Stop:  press q (or Ctrl+C)
//
// Both sources are timestamped on the host clock. Each file is written aligned to
// the moment recording started; if a source goes quiet (e.g. nothing is playing,
// so ScreenCaptureKit sends no buffers) the gap is filled with silence, so the two
// files stay in sync and can be mixed afterwards without any real-time resampling.
// See docs/MEETING_RECORDER.md for why it is built this way.

import AVFoundation
import CoreMedia
import Foundation
import ScreenCaptureKit

final class TrackWriter {
    private let url: URL
    private let startTime: Double
    private var file: AVAudioFile?
    private var framesWritten: AVAudioFramePosition = 0
    /// Loudest sample so far; stays 0 if the source only delivers digital silence.
    private(set) var peak: Float = 0
    private(set) var receivedBuffers = 0
    /// Gaps filled with silence after the first buffer — a high count means choppy input.
    private(set) var gapCount = 0
    private(set) var gapSeconds = 0.0
    private let lock = NSLock()

    init(url: URL, startTime: Double) {
        self.url = url
        self.startTime = startTime
    }

    func write(_ buffer: AVAudioPCMBuffer, at time: Double) {
        lock.lock()
        defer { lock.unlock() }
        let format = buffer.format
        if file == nil {
            // Files are always written interleaved; leaving this key in makes AVAudioFile log a warning.
            var settings = format.settings
            settings.removeValue(forKey: AVLinearPCMIsNonInterleaved)
            do {
                file = try AVAudioFile(forWriting: url, settings: settings,
                                       commonFormat: format.commonFormat,
                                       interleaved: format.isInterleaved)
            } catch {
                fputs("❌ Could not create \(url.lastPathComponent): \(error)\n", stderr)
                return
            }
        }
        guard let file else { return }

        // Where this buffer belongs relative to the start of the recording.
        // Fill anything missing by more than 20 ms with silence.
        let expected = AVAudioFramePosition(max(0, time - startTime) * format.sampleRate)
        let gap = expected - framesWritten
        if gap > AVAudioFramePosition(format.sampleRate * 0.02) {
            if framesWritten > 0 { // the device's start-up delay is not a gap
                gapCount += 1
                gapSeconds += Double(gap) / format.sampleRate
            }
            writeSilence(frames: gap, format: format, to: file)
        }
        receivedBuffers += 1
        if let channels = buffer.floatChannelData {
            for ch in 0..<Int(format.channelCount) {
                for i in 0..<Int(buffer.frameLength) { peak = max(peak, abs(channels[ch][i])) }
            }
        }
        do {
            try file.write(from: buffer)
            framesWritten += AVAudioFramePosition(buffer.frameLength)
        } catch {
            fputs("⚠️  Could not write \(url.lastPathComponent): \(error)\n", stderr)
        }
    }

    private func writeSilence(frames: AVAudioFramePosition, format: AVAudioFormat, to file: AVAudioFile) {
        var remaining = frames
        let chunk = AVAudioFrameCount(format.sampleRate) // 1-second blocks
        guard let silence = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: chunk) else { return }
        while remaining > 0 {
            let n = AVAudioFrameCount(min(AVAudioFramePosition(chunk), remaining))
            silence.frameLength = n
            for b in UnsafeMutableAudioBufferListPointer(silence.mutableAudioBufferList) {
                if let data = b.mData { memset(data, 0, Int(b.mDataByteSize)) }
            }
            try? file.write(from: silence)
            framesWritten += AVAudioFramePosition(n)
            remaining -= AVAudioFramePosition(n)
        }
    }

    func close() {
        lock.lock()
        file = nil // AVAudioFile closes the file when released
        lock.unlock()
    }
}

final class Recorder: NSObject, SCStreamOutput, SCStreamDelegate {
    private let systemWriter: TrackWriter
    private let micWriter: TrackWriter
    private var stream: SCStream?
    private let engine = AVAudioEngine()
    private let audioQueue = DispatchQueue(label: "system-audio")
    private let videoQueue = DispatchQueue(label: "ignored-video")

    init(systemURL: URL, micURL: URL) {
        let now = CMClockGetTime(CMClockGetHostTimeClock()).seconds
        systemWriter = TrackWriter(url: systemURL, startTime: now)
        micWriter = TrackWriter(url: micURL, startTime: now)
    }

    func start() async throws {
        guard await AVCaptureDevice.requestAccess(for: .audio) else {
            throw Self.error(1, "No microphone permission. Allow Terminal in System Settings → Privacy & Security → Microphone.")
        }

        // System audio. ScreenCaptureKit needs a display filter; the video is captured
        // at 2×2 px, once per second, and thrown away.
        let content: SCShareableContent
        do {
            content = try await SCShareableContent.excludingDesktopWindows(false, onScreenWindowsOnly: true)
        } catch {
            throw Self.error(2, "No screen recording permission. Allow Terminal in System Settings → Privacy & Security → Screen & System Audio Recording, then quit and reopen Terminal.")
        }
        guard let display = content.displays.first else {
            throw Self.error(3, "No display found.")
        }
        let filter = SCContentFilter(display: display, excludingApplications: [], exceptingWindows: [])
        let config = SCStreamConfiguration()
        config.capturesAudio = true
        config.excludesCurrentProcessAudio = true
        config.sampleRate = 48000
        config.channelCount = 2
        config.width = 2
        config.height = 2
        config.minimumFrameInterval = CMTime(value: 1, timescale: 1)
        let stream = SCStream(filter: filter, configuration: config, delegate: self)
        try stream.addStreamOutput(self, type: .audio, sampleHandlerQueue: audioQueue)
        try stream.addStreamOutput(self, type: .screen, sampleHandlerQueue: videoQueue)
        self.stream = stream

        // Microphone (the default input device).
        let input = engine.inputNode
        let micFormat = input.outputFormat(forBus: 0)
        input.installTap(onBus: 0, bufferSize: 4096, format: micFormat) { [micWriter] buffer, when in
            micWriter.write(buffer, at: AVAudioTime.seconds(forHostTime: when.hostTime))
        }

        try engine.start()
        try await stream.startCapture()
    }

    /// A few seconds in, check that the microphone is really delivering sound.
    /// Without permission macOS sends silence instead of an error.
    func checkMicrophone() {
        if micWriter.receivedBuffers == 0 {
            print("\n⚠️  No audio from the microphone. Is Terminal allowed in System Settings → Privacy & Security → Microphone?")
        } else if micWriter.peak == 0 {
            print("\n⚠️  The microphone is completely silent (permission missing?). Allow Terminal in System Settings → Privacy & Security → Microphone, then restart Terminal.")
        } else {
            print("\n🎙  Microphone OK.")
        }
    }

    func stop() async {
        try? await stream?.stopCapture()
        engine.inputNode.removeTap(onBus: 0)
        engine.stop()
        systemWriter.close()
        micWriter.close()
        for (name, w) in [("System audio", systemWriter), ("Microphone", micWriter)] {
            print(String(format: "   %@: %d gaps filled (%.2f s total)", name, w.gapCount, w.gapSeconds))
        }
    }

    func stream(_ stream: SCStream, didOutputSampleBuffer sampleBuffer: CMSampleBuffer, of type: SCStreamOutputType) {
        guard type == .audio, sampleBuffer.isValid,
              let buffer = Self.pcmBuffer(from: sampleBuffer) else { return }
        systemWriter.write(buffer, at: sampleBuffer.presentationTimeStamp.seconds)
    }

    func stream(_ stream: SCStream, didStopWithError error: Error) {
        fputs("\n❌ System audio capture stopped: \(error.localizedDescription)\n", stderr)
    }

    private static func pcmBuffer(from sampleBuffer: CMSampleBuffer) -> AVAudioPCMBuffer? {
        guard let desc = sampleBuffer.formatDescription,
              let asbd = desc.audioStreamBasicDescription else { return nil }
        var streamDesc = asbd
        guard let format = AVAudioFormat(streamDescription: &streamDesc) else { return nil }
        let frames = AVAudioFrameCount(sampleBuffer.numSamples)
        guard let buffer = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: frames) else { return nil }
        buffer.frameLength = frames
        let status = CMSampleBufferCopyPCMDataIntoAudioBufferList(
            sampleBuffer, at: 0, frameCount: Int32(frames), into: buffer.mutableAudioBufferList)
        return status == noErr ? buffer : nil
    }

    private static func error(_ code: Int, _ message: String) -> NSError {
        NSError(domain: "meeting-recorder", code: code, userInfo: [NSLocalizedDescriptionKey: message])
    }
}

/// Puts the terminal in single-keypress mode (no Enter needed); restores it on exit.
final class RawTerminal {
    private var original = termios()
    private let active: Bool

    init() {
        active = isatty(STDIN_FILENO) != 0 && tcgetattr(STDIN_FILENO, &original) == 0
        guard active else { return }
        var raw = original
        raw.c_lflag &= ~tcflag_t(ICANON | ECHO)
        tcsetattr(STDIN_FILENO, TCSANOW, &raw)
    }

    func restore() {
        if active { tcsetattr(STDIN_FILENO, TCSANOW, &original) }
    }
}

@main
struct Main {
    static func main() async {
        let args = CommandLine.arguments
        guard args.count == 3 else {
            fputs("Usage: meeting-recorder <system.caf> <microphone.caf>\n", stderr)
            exit(64)
        }
        let recorder = Recorder(systemURL: URL(fileURLWithPath: args[1]),
                                micURL: URL(fileURLWithPath: args[2]))
        do {
            try await recorder.start()
        } catch {
            fputs("❌ \(error.localizedDescription)\n", stderr)
            exit(1)
        }

        DispatchQueue.main.asyncAfter(deadline: .now() + 3) { recorder.checkMicrophone() }

        let terminal = RawTerminal()
        let started = Date()
        print("🔴 Recording. Press 'q' to stop.")

        // q / Ctrl+C / end of input -> stop.
        let stopSignal = AsyncStream<Void> { continuation in
            signal(SIGINT, SIG_IGN)
            let sigint = DispatchSource.makeSignalSource(signal: SIGINT)
            sigint.setEventHandler { continuation.yield() }
            sigint.resume()
            Thread.detachNewThread {
                var c: UInt8 = 0
                while read(STDIN_FILENO, &c, 1) == 1 {
                    if c == UInt8(ascii: "q") || c == UInt8(ascii: "Q") { break }
                }
                continuation.yield()
            }
            let timer = DispatchSource.makeTimerSource()
            timer.schedule(deadline: .now() + 1, repeating: 1)
            timer.setEventHandler {
                let s = Int(Date().timeIntervalSince(started))
                print(String(format: "\r⏱  %02d:%02d:%02d", s / 3600, s / 60 % 60, s % 60), terminator: "")
                fflush(stdout)
            }
            timer.resume()
            continuation.onTermination = { _ in sigint.cancel(); timer.cancel() }
        }
        for await _ in stopSignal { break }

        terminal.restore()
        print("\n⏹  Stopping...")
        await recorder.stop()
        exit(0)
    }
}

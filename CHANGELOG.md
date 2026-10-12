# Changelog

## 1.1.0 — 2026-10

- **Meeting recorder for macOS** (`Record Meeting.command`, `recorder/`): records system audio via ScreenCaptureKit and
  the microphone via AVAudioEngine into separate, timestamp-aligned tracks, then levels (`dynaudnorm`), mixes and
  limits them into one mono `.m4a` ready for the notebook. No BlackHole / Multi-Output Device needed; the output
  device and volume keys are left alone. Built automatically on first run.
- Health checks: warns within 3 seconds if the microphone delivers only silence (missing permission), and reports
  peak levels and filled gaps per track after each recording.
- New guide: [docs/MEETING_RECORDER.md](docs/MEETING_RECORDER.md), including how to verify a pre-built ffmpeg when
  Homebrew cannot install one.

## 1.0.0 — 2026-10

First public release.

- One-cell Colab pipeline: Google Drive folder → faster-whisper large-v3 transcripts → overlapping, sentence-aligned chunks → back to Drive.
- Google Drive API access (no `drive.mount()`, no public sharing); each recording is saved as soon as it is finished.
- Resumable runs: finished recordings are skipped; an invisible Drive file property marks completion, so interrupted uploads are repaired without re-transcribing.
- Works on Colab's CUDA 13 runtime: CUDA 12 cuBLAS is installed and preloaded for CTranslate2 (fixes `libcublas.so.12 is not found`), plus a 1-second GPU smoke test.
- Per-course `HOTWORDS` (applied to every 30-second window, unlike `initial_prompt`), accent/case-insensitive matching.
- Hallucination filter (phantom phrases + consecutive duplicates), VAD, `condition_on_previous_text=False`.
- Audio decoded with the ffmpeg CLI (immune to PyAV API changes).
- Pinned `faster-whisper`, `ctranslate2`, `nvidia-cublas-cu12`.
- `python transcribe.py split ...` — the chunker as a local, stdlib-only CLI.

<div align="center">

# 🎙️ Lecture Transcriber

**Drop your recordings in a Google Drive folder → get clean transcripts and LLM-ready chunks back in the same folder.**
Free, on a Colab GPU, with Whisper large-v3. No API keys, no installs, no audio leaving your Google account.

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/arif7esat/lecture-transcriber/blob/main/notebooks/lecture_transcriber.ipynb)
![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![Model: Whisper large-v3](https://img.shields.io/badge/model-Whisper%20large--v3-orange.svg)

</div>

---

## Why this exists

You record every lecture, meeting or interview. Then the recordings sit there, because transcribing
them is slow, paid, or both — and even with a transcript, a 90-minute wall of text is too long to paste
into ChatGPT or Claude in one go.

This notebook fixes the whole chain with **one click**:

```
Google Drive folder                         Same folder, after one run
├── Recordings/                             ├── Recordings/ (untouched)
│   ├── Algorithms/                         └── transcripts/
│   │   ├── Week 1.m4a          ──────▶         ├── Week 1/
│   │   └── Week 2.m4a                          │   ├── Week 1.txt          ← full transcript
│   └── Databases/                              │   ├── Week 1_part_1.txt   ← ~1800 words
│       └── Lecture 3.mp3                       │   └── Week 1_part_2.txt   ← + overlap
                                                ├── Week 2/ ...
                                                └── Lecture 3/ ...
```

## Features

- **🆓 Free & private** — runs on Google Colab's free T4 GPU. Your audio goes from *your* Drive to *your* Colab machine and back. No third-party transcription API.
- **🎯 Best open model** — Whisper **large-v3** through [faster-whisper](https://github.com/SYSTRAN/faster-whisper): same accuracy as OpenAI's Whisper, several times faster.
- **🔁 Re-run safe** — finished recordings are skipped. Add new files to the folder, run again, only the new ones are processed.
- **🩹 Self-healing** — if Colab disconnects or an upload breaks halfway, the next run repairs it **without re-transcribing**.
- **🧠 LLM-ready chunks** — transcripts are split at sentence boundaries into ~1800-word parts with a small overlap, each with a header that tells the LLM what is context and what is new.
- **🔤 Domain hotwords** — give each course its own term list (e.g. *"Fourier transform, Laplace, convolution"*); it is applied to the *whole* recording, not just the first 30 seconds.
- **🧹 Hallucination filter** — drops Whisper's classic phantom lines ("Thanks for watching!") and repeated-sentence loops.
- **📁 Any structure** — sub-folders, shortcuts, shared drives, `.mp3 .m4a .wav .mp4 .mov .mkv …` (video works too).
- **🎧 Meeting recorder for macOS** — double-click to record any call (Meet, Zoom, Teams, WhatsApp …): what you hear + your mic, one file, ready to transcribe. [More ↓](#record-your-meetings-macos)
- **🛠️ Works on today's Colab** — includes the fix for Colab's 2026 move to CUDA 13 (`libcublas.so.12 is not found`).

## Quick start (5 minutes)

> New to Colab or Drive? Follow the **[step-by-step beginner guide](docs/GETTING_STARTED.md)** — it assumes nothing.

1. Put your recordings in a Google Drive folder and copy the folder's link.
2. Click **Open in Colab** above.
3. **Runtime → Change runtime type → T4 GPU → Save.**
4. Click 🔑 **Secrets** in the left sidebar → *Add new secret* → name `DRIVE_FOLDER_LINK`, value = your link → turn on *Notebook access*.
   It is stored in your Google account, not in the notebook, and reused next time. (Or paste the link into `DRIVE_FOLDER_LINK` in the cell.) Optionally set `LANGUAGE = "en"`.
5. **Runtime → Run all.** Sign in when asked and tick **all** permission boxes.

That's it. Transcripts appear in a `transcripts/` folder inside your Drive folder, one recording at a time.

## How long does it take?

Two parts: a **one-time setup per Colab session**, then roughly **a tenth of the recording length** per file.

| | Time on a free Colab T4 |
|---|---|
| Session setup (packages, CUDA fix, 3 GB model download) | ~3–5 min, once per session |
| 30 min recording | ~3–5 min |
| 45 min recording | ~5–7 min |
| 1 h recording | ~6–9 min |
| 1.5 h recording | ~9–14 min |
| 3 h recording | ~18–27 min |
| Splitting + uploading | a few seconds per recording |

**Example:** a week with three 45-minute lectures ≈ 4 min setup + 3 × 6 min ≈ **20–25 minutes**, hands-off.

These are estimates: faster-whisper's own benchmark transcribes 13 min of audio in ~1 min on an RTX 3070 Ti
(large model, fp16, beam 5), and a T4 is roughly half as fast. Silence is skipped (VAD), so quiet recordings go
faster. The script prints the real speed for every file — e.g. `45 min audio → 5.8 min (×8 real time)` —
**please share yours in an issue so we can replace these estimates with measurements.**

> Free Colab GPU time is limited and varies. If you hit the limit mid-batch, nothing is lost: run again later and it continues where it stopped.

## What the output looks like

Each part starts with a header, then the overlap from the previous part, clearly marked:

```markdown
# Week 1 | Part 2/4 | Words 1803–3610 of 7412

## Context from the previous part (~118 words, already covered — do not repeat)

...the last few sentences of part 1...

## This part

...new content...
```

That layout lets you feed parts one by one to ChatGPT, Claude, Gemini, Copilot or a local model without losing
the thread between them — and without the model summarizing the same sentences twice.
A ready-to-use prompt for study notes is in **[prompts/study_notes.md](prompts/study_notes.md)**.

## Split transcripts you already have (no GPU)

The chunker also runs locally on any `.txt`, using only the Python standard library:

```bash
python transcribe.py split "Lecture 01.txt" "Lecture 02.txt" --words 1800 --overlap 120
```

## Record your meetings (macOS)

Transcribing meetings, not lectures? The repository includes a small recorder that captures **everyone else**
(the Mac's audio output) and **you** (the microphone) into one `.m4a`:

1. Double-click **`Record Meeting.command`**, type a name, allow Microphone and Screen & System Audio Recording the first time.
2. Join your call in any app. Press **q** when it ends.
3. Drop `~/Meetings/<date>_<name>.m4a` into your Drive folder and run the notebook.

No virtual audio driver and no audio settings to change — your speakers and volume keys keep working. Needs macOS 13+,
Apple's Command Line Tools and ffmpeg. Full guide: **[docs/MEETING_RECORDER.md](docs/MEETING_RECORDER.md)**.

## Documentation

| | |
|---|---|
| 🚀 [Getting started](docs/GETTING_STARTED.md) | From zero: Drive folder, Colab, GPU, first run, results |
| ⚙️ [Configuration](docs/CONFIGURATION.md) | Every setting: language, model, hotwords, chunk size, … |
| 🔬 [How it works](docs/HOW_IT_WORKS.md) | The pipeline and the reasoning behind each design decision |
| 🧯 [Troubleshooting](docs/TROUBLESHOOTING.md) | Every error and warning you might see, and what to do |
| 🎧 [Meeting recorder](docs/MEETING_RECORDER.md) | Record calls on macOS (system audio + mic), then transcribe them |
| 🧠 [Study-notes prompt](prompts/study_notes.md) | Turn the chunks into structured notes with any LLM |

## FAQ

**Is it really free?** Yes. It uses Colab's free GPU tier and open-source models. Colab Pro only makes it faster/longer.

**Why does it ask for Google permissions every time?** Google requires your consent once per Colab session before
code can access your Drive; it cannot be turned off from the notebook. Re-running in the same session does not ask again.
Tick **all** boxes — a missing one makes the sign-in fail and the window come back.

**Who can see my recordings?** Only your Google account. The notebook reads your folder through Google's official Drive API with *your* sign-in; you don't need to share the folder publicly. The model is downloaded from Hugging Face; no audio is sent anywhere.

**Which languages?** All ~100 languages Whisper supports. Set `LANGUAGE` for best results, or leave it as `None` to auto-detect.

**Can I redo a recording?** Delete its folder inside `transcripts/` and run again.

**Does it work without a GPU?** Transcription with large-v3 on CPU is impractically slow, so the notebook stops and tells you. Use `MODEL_NAME = "small"` if you must.

## Contributing

Issues and pull requests are welcome — especially **timing reports**, **hallucination phrases** for your language,
and **hotword lists** for common courses. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Acknowledgements

Built on [OpenAI Whisper](https://github.com/openai/whisper), [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
and [CTranslate2](https://github.com/OpenNMT/CTranslate2).

## License

[MIT](LICENSE)

---

<div align="center">If this saved you a few hours, a ⭐ helps others find it.</div>

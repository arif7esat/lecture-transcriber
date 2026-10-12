# Meeting recorder (macOS) — record any call, then transcribe it

You join meetings on your Mac — Google Meet, Zoom, Teams, WhatsApp, a browser tab — and want a transcript afterwards.
The meeting recorder captures **what you hear** (everyone else) and **what you say** (your microphone) into one
`.m4a` file. Drop that file into your Drive folder and the [notebook](GETTING_STARTED.md) transcribes it like any
lecture.

```
Double-click "Record Meeting.command"  →  talk  →  press q  →  ~/Meetings/2026-10-12_14-30_weekly-sync.m4a
                                                                        │
                                              drop into your Drive folder, run the notebook
                                                                        ▼
                                                    transcripts/weekly-sync/weekly-sync.txt
```

- **Works with every meeting app** — it records the Mac's audio output, not a specific app.
- **No audio settings to change** — no virtual audio driver, no Multi-Output Device. Speakers, headphones and the volume
  keys keep working normally while you record.
- **Nothing leaves your Mac** — recording and mixing happen locally.
- **Balanced levels** — a quiet participant or a low call volume is brought up to speech level automatically.

> **Record responsibly.** Tell participants you are recording. In many countries (and under GDPR/KVKK) recording a
> conversation without consent is illegal.

---

## Requirements

| | |
|---|---|
| **macOS 13 (Ventura) or newer** | System-audio capture uses Apple's ScreenCaptureKit. |
| **Command Line Tools** | Provides the Swift compiler. Install once: `xcode-select --install` |
| **ffmpeg** | Mixes the two tracks at the end. `brew install ffmpeg` — or see [No Homebrew?](#no-homebrew-or-brew-install-ffmpeg-fails) |

Apple Silicon and Intel Macs are both supported. The recorder is compiled automatically on first run (a few seconds).

## Step 1 — First recording

1. In Finder, open the `lecture-transcriber` folder and **double-click `Record Meeting.command`**.
   - If macOS says it *"cannot be opened because it is from an unidentified developer"*: **right-click → Open → Open**.
     You only need to do this once.
2. Type a name for the meeting (or just press Enter). Spaces become dashes.
3. macOS asks for two permissions the first time — allow both:
   - **Microphone** for Terminal.
   - **Screen & System Audio Recording** for Terminal (called *Screen Recording* on older macOS). This is how Apple
     gates system-audio capture; the recorder does not keep any video — it grabs a 2×2-pixel frame once per second
     and throws it away.
4. **After granting Screen Recording, quit Terminal (⌘Q) and run `Record Meeting.command` again.** macOS only applies
   that permission to a freshly started Terminal.

## Step 2 — Record

```
=== Meeting recorder ===
Meeting name (optional): weekly sync
🔴 Recording. Press 'q' to stop.
🎙  Microphone OK.
⏱  00:42:17
```

- Wait for **`🎙 Microphone OK.`** (about 3 seconds in). If you see a ⚠️ warning instead, fix it now —
  see [Troubleshooting](#troubleshooting) — rather than finding out after the meeting.
- Use the meeting app as usual. Use **headphones** if you can: on speakers your microphone also picks up the other
  participants, which makes their voices sound slightly echoey in the recording.
- When the meeting ends, click the Terminal window and press **q**.

## Step 3 — The result

```
⏹  Stopping...
   System audio: 0 gaps filled (0.00 s total)
   Microphone: 0 gaps filled (0.00 s total)
🎚  Mixing...
   System audio: peak -2 dB
   Microphone: peak -5 dB
✅ Saved: /Users/you/Meetings/2026-10-12_14-30_weekly-sync.m4a
```

How to read it:

| Line | Healthy | If not |
|---|---|---|
| `gaps filled` | `0`, or a handful | Hundreds → the audio arrived choppy; please open an issue with the numbers. |
| `System audio: peak` | Between about -20 and 0 dB if anyone else spoke | `nothing recorded!` → Screen Recording permission (see below). |
| `Microphone: peak` | Between about -25 and 0 dB if you spoke | Below -40 dB → your voice barely reached the mic; raise the input level. |

The file is a mono, 48 kHz AAC `.m4a`: about **45 MB per hour**. Put it in your Drive recordings folder and run
the notebook — `.m4a` is supported out of the box. Set `LANGUAGE` in the notebook if your meetings are not in English.

## Options

| | |
|---|---|
| **Save somewhere else** | `MEETINGS_DIR=~/Documents/Calls ./recorder/record-meeting.sh` (default: `~/Meetings`) |
| **Start from a terminal** | `./recorder/record-meeting.sh weekly-sync` — the same as double-clicking, with the name as argument |
| **Stop** | `q`, or `Ctrl+C` |

The **microphone** is your Mac's current default input (System Settings → Sound → Input). Switch it there before
recording if you use a headset or an external mic.

---

## Troubleshooting

### `❌ No screen recording permission`
System Settings → Privacy & Security → **Screen & System Audio Recording** → turn on **Terminal**
(use **+** to add it from Applications → Utilities if it is missing). Then **quit Terminal (⌘Q)** and start again.

### `⚠️ The microphone is completely silent` / `⚠️ No audio from the microphone`
macOS gives an app without microphone permission silence instead of an error. System Settings → Privacy & Security →
**Microphone** → turn on **Terminal**, quit Terminal, start again.

### My voice is very quiet / `Microphone: peak` is below -40 dB
Raise the input level: System Settings → Sound → Input → your microphone → **Input level** to about 75 %.
Check you are recording from the mic you think you are (see *Options*).

### The other participants sound robotic or metallic
Check whether they sounded the same **live**. If yes, that is the meeting app concealing network packet loss (common on
weak Wi-Fi, on either side) and it is already in the audio the app plays — it cannot be fixed afterwards. If the
recording sounds worse than the live call, open an issue with the `gaps filled` numbers.

### `❌ Swift compiler not found`
Run `xcode-select --install` once and follow the dialog.

### No Homebrew, or `brew install ffmpeg` fails
On an older macOS, Homebrew may have no ready-made package and try to compile ffmpeg and dozens of dependencies from
source — this can take an hour and fail (e.g. *x265* with an old Command Line Tools). A pre-built, signed ffmpeg is
quicker:

1. Get **FFmpeg (ZIP)** for your Mac from <https://ffmpeg.martin-riedl.de> (*macOS (Apple Silicon/arm64)* for M-series
   Macs, *macOS (Intel/amd64)* for Intel; *Release* build). The site is a well-known build server but not affiliated
   with ffmpeg.org.
2. Verify it before use:
   ```bash
   shasum -a 256 ~/Downloads/ffmpeg.zip    # must match the SHA256 link next to the download
   ```
3. Unzip, then check Apple's signature and notarization:
   ```bash
   codesign -dv ffmpeg 2>&1 | grep Authority                              # Developer ID Application: …
   spctl --assess --type open --context context:primary-signature -v ffmpeg  # accepted, Notarized Developer ID
   ```
4. Move it onto your `PATH`, e.g. `mv ffmpeg /opt/homebrew/bin/` (Apple Silicon) or `/usr/local/bin/` (Intel).

### The recording is empty or shorter than the meeting
The recorder stops when its Terminal window closes. Keep the window open (it can be in the background) until you press **q**.

---

## How it works — and why it is built this way

```
            ┌─ ScreenCaptureKit ── system audio, 48 kHz stereo ─▶  <name>.system.caf ─┐
recording ──┤                                                                         ├─ ffmpeg (after you press q) ─▶ <name>.m4a
            └─ AVAudioEngine ───── default microphone ──────────▶  <name>.mic.caf ────┘   level each track, mix, limit
```

`recorder/main.swift` is a small Swift command-line program; `recorder/record-meeting.sh` builds it, runs it, and mixes
the result. The raw `.caf` tracks are deleted once the `.m4a` is written (and kept if mixing fails).

**Why not BlackHole + a Multi-Output Device?** That is the classic recipe, and the first version used it. In practice:
the volume keys stop working while the Multi-Output Device is selected, MacBook speakers play noticeably quieter through
it, you must remember to switch the output before every meeting (forget it and the other side is not recorded), and the
system-audio level reaching the recorder depended on device volume settings. ScreenCaptureKit (macOS 13+) captures the
system mix directly, leaves the output device alone, and needs no driver.

**Why two separate tracks instead of mixing live?** The microphone and the system audio run on different hardware
clocks (e.g. 44.1 kHz vs 48 kHz). Mixing them in real time with ffmpeg's `aresample=async` inserted micro-gaps — around
45 per minute in testing — heard as crackles on the microphone side. Writing each source to its own file and mixing
once recording has stopped removes the problem entirely.

**How do the tracks stay in sync?** Every buffer from both sources carries a host-clock timestamp. Each track is written
relative to the same start time; if a source pauses (ScreenCaptureKit may send nothing while the Mac is silent), the gap
is filled with silence. The number of filled gaps is printed at the end as a health check.

**Why level each track separately?** In real calls one side is often much quieter (a test WhatsApp call came in at
-34 dB RMS — barely audible). `dynaudnorm` brings each track to speech level on its own before mixing, so neither
side drowns the other, and `alimiter` prevents clipping. Side effect: in long silences, room noise is raised a little.
Whisper does not mind.

**Why mono?** `transcribe.py` decodes everything to 16 kHz mono before transcription, so keeping the two sides on
separate stereo channels would be dropped anyway — and averaging two channels would halve each voice's level.

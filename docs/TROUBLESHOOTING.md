# Troubleshooting

Find the message you see, follow the fix. If it isn't here, [open an issue](../../../issues/new/choose) and paste the
full output of the cell.

**General rule:** running again is always safe. Finished recordings are skipped, half-finished ones are repaired.

---

## Errors

### `❌ No GPU found`
Either the runtime isn't a GPU runtime, or your free GPU time is used up.
- **Runtime → Change runtime type → T4 GPU → Save**, then run again.
- If T4 is unavailable or the error persists, Colab's free GPU quota is exhausted for now. Try again in a few hours
  (the quota is not published and varies), or use Colab Pro.

### `RuntimeError: Library libcublas.so.12 is not found or cannot be loaded`
Colab moved to CUDA 13 in 2026; faster-whisper's engine needs the CUDA 12 version of cuBLAS. **The current notebook fixes
this automatically** (`✅ CUDA 12 cuBLAS loaded` in the log). If you still see it:
- make sure you're running the latest `transcribe.py` from this repository, not an older copy;
- **Runtime → Disconnect and delete runtime**, then **Run all** again (gives you a clean machine).

The full explanation is in [How it works → The CUDA 13 fix](HOW_IT_WORKS.md#7-the-cuda-13-fix).

### `❌ The model does not run on the GPU: ...`
The 1-second GPU smoke test failed, so the run stopped before downloading your recordings. Try
**Runtime → Disconnect and delete runtime → Run all**. If it persists, Colab's environment has probably changed again —
please open an issue with the full message.

### `❌ Could not read the folder`
- The link is wrong or incomplete — copy it again (**Share → Copy link** on the folder, not on a file).
- You signed in with a different Google account than the one that owns (or can see) the folder. Run again and pick the
  right account in the sign-in window.

### `❌ Drive access failed` / sign-in window never appears
- Your browser blocked the pop-up: allow pop-ups for `colab.research.google.com` and run again.
- You didn't tick all the permission checkboxes. Run again and tick them all.

### `❌ No audio/video files found`
The notebook lists the files it saw. Check that the recordings are in the folder (or its sub-folders) and that their
extensions are in `AUDIO_EXTENSIONS` (`.mp3 .m4a .wav .ogg .flac .aac .webm .mp4 .mov .mkv .avi`).
Google Docs, PDFs, etc. are ignored on purpose.

### `⚠ Skipped '...': same name as '...'`
Two recordings have the same file name (in different sub-folders). Both would produce the same transcript, so the second
is skipped. Rename one of them (e.g. add a course prefix) and run again.

### `❌ Error: ffmpeg could not read the file`
The file is damaged, still uploading, or not really audio. Re-upload it. Files from voice-memo apps sometimes need to be
exported again as `.m4a` or `.mp3`.

### `pip could not install ...`
A temporary problem with the package index or Colab's network. Run again. If it keeps happening, open an issue with the
printed pip output.

---

## Warnings (harmless)

### `Warning: You are sending unauthenticated requests to the HF Hub`
The model is downloaded from Hugging Face without an account. It still works. To make the warning go away (and possibly
download faster):
1. Create a free account at [huggingface.co](https://huggingface.co) → **Settings → Access Tokens** → create a **Read** token.
2. In Colab, click 🔑 (Secrets) in the left sidebar → add a secret named **`HF_TOKEN`** with the token as value →
   turn on **Notebook access**.

No code change needed; the Hugging Face library picks it up automatically.

### `httplib2 transport does not support per-request timeout`
An internal notice from Google's client library. Harmless; the notebook silences it.

---

## Quality problems

### A technical term is always transcribed wrong
Add it to `HOTWORDS` for that course — see [Configuration → Hotwords](CONFIGURATION.md#hotwords). Check the log shows
`🔤 hotwords: yes` for those files. Then delete the recording's folder in `transcripts/` and run again to redo it.

### The transcript is in the wrong language / translated
Auto-detection guessed wrong (common when a recording starts with silence, music or a different language).
Set `LANGUAGE` explicitly, delete the recording's folder in `transcripts/`, run again.

### Phantom sentences like "Thanks for watching" or subtitle credits
Add the exact phrase to `HALLUCINATION_PHRASES` (case and punctuation don't matter). Only segments that consist entirely
of a listed phrase are removed, so real speech is safe. PRs adding phrases for your language are welcome.

### The same sentence repeats many times
Already mitigated (`condition_on_previous_text=False` + duplicate filter). If it still happens on a specific recording,
it's usually very noisy audio or long music; trimming the noisy part helps.

### Long stretches are missing
The voice-activity filter may treat very quiet speech as silence (e.g. a lecturer far from the microphone).
Boosting the recording's volume before uploading usually fixes it.

---

## Workflow questions

### How do I redo one recording?
Delete its folder inside `transcripts/` in Drive and run again.

### Colab disconnected in the middle
Run again. Every recording finished before the disconnect is already in Drive and is skipped. A recording whose upload
was interrupted is completed from its transcript without re-transcribing.

### Drive saving failed and I got a zip
Unzip it and move the recording folders into `transcripts/` in your Drive folder. The next run recognises them
(and adds the missing "done" markers in seconds).

### Can I use my own transcripts from another tool?
Yes. Put `Recording name.txt` (same name as the audio file) into `transcripts/`. The next run splits and files it instead
of transcribing the audio again.

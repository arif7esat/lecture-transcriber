# Getting started — from zero to your first transcript

This guide assumes **nothing**: no programming, no Colab experience. You need:

- a Google account (Gmail is fine),
- some audio or video recordings,
- a web browser on a computer (Chrome, Edge, Firefox, Safari). Phones work for uploading, but run the notebook on a computer.

Nothing gets installed on your computer. Total time for the first run: about 10 minutes plus transcription time.

---

## Step 1 — Put your recordings in Google Drive

1. Open [drive.google.com](https://drive.google.com).
2. Click **+ New → New folder** and give it a name, e.g. `My Lectures`.
3. Open the folder and drag your recordings into it (or **+ New → File upload**).

You can organize it however you like — sub-folders are scanned too:

```
My Lectures/
├── Algorithms/
│   ├── Week 1.m4a
│   └── Week 2.m4a
└── Databases/
    └── Lecture 3.mp3
```

**Two tips that save trouble later:**

- **Give every recording a unique name.** Each transcript is named after its recording, so two files
  called `Week 1.m4a` in different sub-folders would collide (the notebook warns you and skips the second).
  A short prefix works well: `ALG Week 1.m4a`, `DB Week 1.m4a`.
- **Wait until uploads finish** (the progress box in the bottom-right of Drive) before running the notebook.

Supported: `.mp3 .m4a .wav .ogg .flac .aac .webm` and video `.mp4 .mov .mkv .avi` (only the audio is used).

## Step 2 — Copy the folder link

1. In Drive, right-click your folder → **Share → Copy link**.
   *(You do **not** need to change who has access. The notebook reads it with your own sign-in.)*
2. Keep that link handy. It looks like `https://drive.google.com/drive/folders/1AbC...xyz`.

Alternatively, open the folder and copy the address from your browser's address bar — same thing.

## Step 3 — Open the notebook

Click the **Open in Colab** badge at the top of the [README](../README.md).

Colab opens the notebook. You'll see some text and one big code cell.

> **Optional:** *File → Save a copy in Drive* keeps your own copy with your settings saved.
> Without it, everything still works, but your edits disappear when you close the tab.

## Step 4 — Turn on the GPU

The transcription model needs a graphics card (GPU). Colab lends you one for free:

1. Menu **Runtime → Change runtime type**.
2. Under *Hardware accelerator*, choose **T4 GPU**.
3. Click **Save**.

If T4 is greyed out or you later see *"No GPU found"*, your free GPU time for today is used up — try again in a few hours.

## Step 5 — Paste your folder link

At the very top of the code cell you'll find the **SETTINGS** section:

```python
DRIVE_FOLDER_LINK = ""
```

Paste your link between the quotes:

```python
DRIVE_FOLDER_LINK = "https://drive.google.com/drive/folders/1AbC...xyz"
```

While you're there, set the language of your recordings — it's more accurate than auto-detection:

```python
LANGUAGE = "en"     # "en" English, "tr" Turkish, "de" German, "es" Spanish, "fr" French, ...
```

That's all you *need* to change. Everything else has sensible defaults
(see [CONFIGURATION.md](CONFIGURATION.md) when you're curious).

> **Don't want the link in the notebook?** Leave `DRIVE_FOLDER_LINK` empty. Either the notebook will ask for it when it
> runs, or you can store it once as a Colab Secret: click the 🔑 icon in the left sidebar → *Add new secret* →
> name `DRIVE_FOLDER_LINK`, value = your link → turn on *Notebook access*.

## Step 6 — Run it

1. Menu **Runtime → Run all** (or press `Ctrl+F9` / `⌘+F9`).
2. Colab may warn *"This notebook was not authored by Google"* → click **Run anyway**.
   (It's this open-source notebook; you can read every line of it in `transcribe.py`.)
3. After a minute, a Google sign-in window opens:
   - choose the account that owns the folder,
   - **tick every checkbox** on the permissions page (Drive access is needed to read the audio and write the transcripts),
   - click **Continue**.

   If no window appears, check whether your browser blocked a pop-up.

## Step 7 — Watch it work

The output area under the cell shows what's happening. A typical first run:

```
📦 Checking packages...
✅ faster-whisper 1.2.1 ready.
✅ ffmpeg ready.
✅ GPU ready.
☁️  Asking for Drive access — if a window opens, tick ALL boxes...
✅ Drive access granted.

📂 Folder: My Lectures
   🎤 3 recording(s)  |  ✅ 0 done  |  ✂️ 0 to split  |  🆕 3 to transcribe
      🆕 Algorithms/Week 1.m4a   🔤 hotwords: none
      ...
📦 Installing CUDA 12 cuBLAS (~600 MB, about a minute; ...)
✅ CUDA 12 cuBLAS loaded.
⏳ Loading 'large-v3' (downloads ~3 GB once per session, 1-2 min)...
✅ Model loaded, GPU test passed.

▶ [1/3] Week 1.m4a
  audio: 100%|██████████| 2712/2712 [05:41<00:00]
  ✅ 45 min audio → 5.7 min (×8 real time, 3 repeated/filler segment(s) dropped)
  ✂️  6930 words, 912 sentences → 4 part(s)
  ☁️  Drive: transcripts/Week 1/ (4 part(s) uploaded, transcript uploaded)
```

Warnings in yellow/red about **HF_TOKEN** are harmless — see [Troubleshooting](TROUBLESHOOTING.md#warning-you-are-sending-unauthenticated-requests-to-the-hf-hub).

**Keep the browser tab open** while it runs. Colab may disconnect a tab that has been idle for a long time.
If that happens, just run again — every finished recording is already saved.

## Step 8 — Get your transcripts

Open your Drive folder. There is a new `transcripts/` folder:

```
My Lectures/
├── Algorithms/ ...                (your recordings, untouched)
└── transcripts/
    ├── Week 1/
    │   ├── Week 1.txt             ← the full transcript
    │   ├── Week 1_part_1.txt      ← chunk 1 (~1800 words)
    │   ├── Week 1_part_2.txt      ← chunk 2, starts with a short recap of chunk 1
    │   └── ...
    └── ...
```

Each recording is saved as soon as it's finished, so you can start reading the first one while the rest are still running.
At the end, Colab also downloads a zip with everything as a backup.

## Step 9 — Next week

Upload the new recordings into the same folder and **Run all** again. Already-finished recordings are skipped
in seconds; only the new ones are transcribed.

## Step 10 — Turn transcripts into notes (optional)

Open [prompts/study_notes.md](../prompts/study_notes.md), paste the prompt into your favourite AI chat,
then paste the parts one by one. The headers inside each part tell the AI which text is already-covered context
and which is new.

---

### Make it more accurate for your subject

If the transcript keeps getting a technical term wrong, add it to `HOTWORDS` with the name of the
folder (or the start of the file names) as the key:

```python
HOTWORDS = {
    "Algorithms": "Dijkstra, dynamic programming, memoization, big-O notation, heap, adjacency list",
    "Databases":  "normalization, foreign key, B-tree, transaction, ACID, SQL join",
}
```

Matching ignores capitals, accents and spaces, so `"Algorithms"` also matches a folder called `algorithms` or files named `Algorithms Week 3.m4a`.
Recordings that were already transcribed are not redone automatically — delete their folder in `transcripts/` to redo them.

Stuck? See **[Troubleshooting](TROUBLESHOOTING.md)**.

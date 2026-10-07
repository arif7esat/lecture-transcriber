# Configuration

All settings live in the **SETTINGS** block at the top of `transcribe.py` (the code cell in the notebook).
Defaults work for most people; the only one you *must* provide is the folder link.

## Essentials

| Setting | Default | What it does |
|---|---|---|
| `DRIVE_FOLDER_LINK` | `""` | Link to your Drive folder. Empty → read from the Colab Secret `DRIVE_FOLDER_LINK`, otherwise asked at run time. A bare folder ID also works. |
| `LANGUAGE` | `None` | Spoken language as an ISO code (`"en"`, `"tr"`, `"de"`, `"es"`, `"fr"`, `"ar"`, `"zh"`, …). `None` auto-detects per recording and prints what it found. **Setting it is recommended** — detection can be fooled by a silent or noisy start. |

## Transcription

| Setting | Default | What it does |
|---|---|---|
| `MODEL_NAME` | `"large-v3"` | Whisper model. `large-v3` is the most accurate. `medium` ≈ 2× faster, `small` ≈ 4× faster, both less accurate (especially for non-English). `distil-large-v3` is fast and good **for English only**. |
| `BEAM_SIZE` | `5` | Decoding search width. `1` is faster, `5` is more accurate. |
| `HOTWORDS` | example | Domain terms per course/topic, see below. |
| `HALLUCINATION_PHRASES` | EN + TR list | Phrases Whisper invents during silence. A segment consisting **only** of one of them is dropped. Matching ignores case, accents and punctuation. Add your language's usual suspects. |

### Hotwords

```python
HOTWORDS = {
    "Signals and Systems": "Fourier transform, Laplace transform, convolution, impulse response, Nyquist",
    "Organic Chemistry":   "nucleophile, electrophile, SN2, carbocation, stereoisomer, chirality",
}
```

- **How a recording gets its list:** the key is compared with the root folder's name, then every sub-folder on the
  file's path, then the start of the file name. The first match wins.
- **Matching is forgiving:** case, accents, spaces and punctuation are ignored, so `"Signals and Systems"` matches a folder
  `signals_and_systems` and a file `SignalsAndSystems Week 4.m4a`.
- **Keep it short.** Whisper can take about 220 tokens of hints; anything beyond is cut **from the end**, so put the most
  important terms first. 15–25 terms is a good size.
- **Hints, not guarantees.** Hotwords nudge the model toward your spelling; they can't fix inaudible audio.
- The run log shows `🔤 hotwords: yes/none` for each new file, so you can see immediately whether a key matched.

## Chunking

| Setting | Default | What it does |
|---|---|---|
| `CHUNK_WORDS` | `1800` | Target words per part. Parts are cut at the **end of a sentence** after reaching this, so they are slightly longer. ~1800 words ≈ 2400 tokens: comfortable for any modern LLM, small enough for detailed notes. |
| `CHUNK_OVERLAP_WORDS` | `120` | Words from the end of the previous part repeated at the start of the next (whole sentences, may grow up to 2×). Keeps the LLM from losing the thread at the cut. `0` disables it. |
| `MIN_LAST_CHUNK_WORDS` | `300` | A last part shorter than this is merged into the one before, so you never get a tiny 40-word tail. |

The splitter understands abbreviations (`Dr.`, `e.g.`, `Prof.`), initials (`J. R. Smith`) and ordinal numbers written
with a period (`2. Week` in Turkish/German style), so it does not cut there. If a transcript has almost no punctuation,
it falls back to fixed-size blocks.

## Output

| Setting | Default | What it does |
|---|---|---|
| `UPLOAD_TO_DRIVE` | `True` | Save each recording to Drive as soon as it's finished. `False` → only the zip download at the end. |
| `OUTPUT_FOLDER_NAME` | `"transcripts"` | Folder created inside your Drive folder. Any folder with this name **anywhere** in the tree counts as output (its `.txt` files are never treated as input). |

> **Changing `OUTPUT_FOLDER_NAME` later** means existing transcripts in the old folder are no longer found, and the
> recordings are transcribed again. Pick a name once.

## Pinned versions

| Setting | Default | Why it's pinned |
|---|---|---|
| `FASTER_WHISPER_VERSION` | `1.2.1` | Installing "latest" every run means a new release can break the notebook overnight. |
| `CTRANSLATE2_VERSION` | `4.8.2` | faster-whisper's GPU engine. This version needs only cuBLAS 12 (no cuDNN). |
| `CUBLAS12_VERSION` | `12.9.2.10` | The CUDA 12 math library installed on top of Colab's CUDA 13 — see [How it works](HOW_IT_WORKS.md#7-the-cuda-13-fix). |

Bump them deliberately, one at a time, and run a short recording to check.

## Advanced (rarely needed)

| Constant | Default | Meaning |
|---|---|---|
| `AUDIO_EXTENSIONS` | common audio + video | Which files count as recordings. |
| `WORK_DIR`, `OUT_DIR` | `/content/...` | Scratch folders on the Colab machine (wiped at the start of each run). |
| `DONE_PROPERTY` | `transcriber_part_count` | Name of the invisible Drive file property that marks a recording as complete. |
| `SENTENCE_MAX_WORDS`, `BLOCK_WORDS`, `PARAGRAPH_WORDS` | `60`, `40`, `120` | Splitter internals: when a "sentence" is treated as unpunctuated, block size for those, paragraph size in the output. |

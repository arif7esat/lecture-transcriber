# -*- coding: utf-8 -*-
"""
Lecture Transcriber — Google Drive audio -> transcripts -> LLM-ready chunks.
Runs on a free Google Colab T4 GPU with faster-whisper (large-v3).

HOW TO USE (Colab)
  1. Runtime > Change runtime type > T4 GPU.
  2. Paste this whole file into ONE cell (or open the notebook in this repo).
  3. Set DRIVE_FOLDER_LINK below (or leave it empty and paste it when asked).
  4. Run. When the Google sign-in window opens, pick your account and tick ALL boxes.

For every recording, one after another:
  download -> transcribe -> split into chunks -> upload to Drive

Output (in Drive, next to your recordings):
  <OUTPUT_FOLDER_NAME>/
    <recording name>/
      <recording name>.txt            <- full transcript
      <recording name>_part_1.txt     <- ~1800-word chunks with ~120 words of overlap
      <recording name>_part_2.txt ...

Re-running is safe: finished recordings are skipped, half-finished uploads are
repaired automatically (without re-transcribing), and only new audio is processed.

LOCAL USE (no GPU, no Colab) — split any existing transcript into chunks:
  python transcribe.py split lecture.txt [more.txt ...] [--words 1800] [--overlap 120]

Full documentation: README.md and docs/ in the repository.
"""

import glob
import logging
import os
import re
import shutil
import subprocess
import sys
import time
import unicodedata

# ============================================================
# SETTINGS — the only part you normally need to edit
# ============================================================

# Link to the Google Drive folder that holds your recordings (sub-folders are
# scanned too). Lookup order:
#   1) this setting (if not empty)
#   2) a Colab Secret named DRIVE_FOLDER_LINK (key icon in the left sidebar)
#   3) you are asked to paste it when the cell runs
DRIVE_FOLDER_LINK = ""

# Spoken language, e.g. "en", "tr", "de", "es". None = auto-detect per recording.
# Setting it is recommended: detection is skipped and mistakes are avoided.
LANGUAGE = None

MODEL_NAME = "large-v3"          # best accuracy; "medium" or "small" are faster
BEAM_SIZE = 5

CHUNK_WORDS = 1800               # target words per chunk (soft limit, cut at sentence end)
CHUNK_OVERLAP_WORDS = 120        # words repeated from the previous chunk for context
MIN_LAST_CHUNK_WORDS = 300       # a shorter last chunk is merged into the previous one

UPLOAD_TO_DRIVE = True           # False = only download a zip at the end
OUTPUT_FOLDER_NAME = "transcripts"

# Domain terms per course / topic. The key is matched against the Drive folder
# names on the file's path, then against the start of the file name.
# Matching ignores case, accents and spaces: "Software Engineering" ==
# "software_engineering" == "SoftwareEngineering".
# Keep each list short (~200 tokens max); put the most important terms first —
# anything past the limit is cut from the END.
HOTWORDS = {
    "Software Engineering": "software engineering, requirements engineering, "
                            "non-functional requirements, waterfall model, incremental "
                            "development, agile, Scrum, UML, architectural design, "
                            "design patterns, test-driven development, software evolution",
    # "Signals and Systems": "Fourier transform, Laplace transform, convolution, ...",
}

# Whisper sometimes "hears" these phrases in silence or music. A segment that
# consists ONLY of one of them is dropped. Matching ignores case and punctuation.
HALLUCINATION_PHRASES = {
    # English
    "thanks for watching", "thank you for watching", "thank you so much for watching",
    "please subscribe", "subtitles by the amara org community",
    # Turkish
    "altyazı mk", "altyazılar mk", "izlediğiniz için teşekkür ederim",
    "izlediğiniz için teşekkürler", "abone olmayı unutmayın",
    "videoyu beğenmeyi unutmayın", "bir sonraki videoda görüşmek üzere",
}

# Pinned versions. "-U" (always latest) can break the notebook overnight when a
# new release does not match Colab's CUDA setup. Bump these deliberately.
FASTER_WHISPER_VERSION = "1.2.1"
CTRANSLATE2_VERSION = "4.8.2"    # needs CUDA 12 cuBLAS (see ensure_cublas12)
CUBLAS12_VERSION = "12.9.2.10"

AUDIO_EXTENSIONS = {".mp3", ".m4a", ".wav", ".ogg", ".flac", ".aac", ".webm",
                    ".mp4", ".mov", ".mkv", ".avi"}
WORK_DIR = "/content/audio_work"
OUT_DIR = "/content/transcripts_out"
SAMPLE_RATE = 16000              # what Whisper expects
DONE_PROPERTY = "transcriber_part_count"   # invisible Drive marker, see mark_done()


# ============================================================
# Text helpers
# ============================================================
def normalize_key(text: str) -> str:
    """'Düzenli İfadeler' -> 'duzenliifadeler', 'Software_Engineering' -> 'softwareengineering'."""
    text = text.replace("ı", "i").replace("İ", "i")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", text.lower())


HOTWORD_TABLE = {normalize_key(k): v for k, v in HOTWORDS.items()}
HALLUCINATION_KEYS = {normalize_key(p) for p in HALLUCINATION_PHRASES}


def is_hallucination(segment_text: str) -> bool:
    return normalize_key(segment_text) in HALLUCINATION_KEYS


# ============================================================
# Chunking: transcript -> overlapping, sentence-aligned parts
# ============================================================
SENTENCE_MAX_WORDS = 60     # longer "sentences" are treated as unpunctuated text
BLOCK_WORDS = 40            # unpunctuated text is cut into blocks of this size
PARAGRAPH_WORDS = 120       # approximate paragraph size in the output
OVERLAP_CAP_RATIO = 2.0     # overlap may grow up to overlap * ratio to keep whole sentences

# Abbreviations followed by a period that do NOT end a sentence (lower case).
ABBREVIATIONS = {
    # English
    "mr", "mrs", "ms", "dr", "prof", "st", "vs", "etc", "e.g", "i.e", "fig", "eq",
    "ref", "vol", "approx", "dept", "jr", "sr",
    # Turkish
    "doç", "doc", "yrd", "arş", "ars", "gör", "gor", "öğr", "ogr", "müh", "muh",
    "av", "sn", "hz", "nr", "mah", "cad", "sok", "apt", "tel", "vb", "vd", "örn",
    "orn", "bkz", "yy", "bl", "böl", "sy", "s", "ör", "or",
}

# Languages such as Turkish and German write ordinals as "2. Week". These words
# after "<number>." mean the period is an ordinal, not a sentence end.
ORDINAL_FOLLOWERS = {
    "hafta", "ders", "bölüm", "bolum", "sınıf", "sinif", "dönem", "donem", "madde",
    "adım", "adim", "sayfa", "ünite", "unite", "konu", "soru", "yüzyıl", "yuzyil",
    "kısım", "kisim", "aşama", "asama", "seviye", "katman", "sıra", "sira",
    "yarıyıl", "yariyil", "vize", "final", "ocak", "şubat", "subat", "mart", "nisan",
    "mayıs", "mayis", "haziran", "temmuz", "ağustos", "agustos", "eylül", "eylul",
    "ekim", "kasım", "kasim", "aralık", "aralik",
    "woche", "kapitel", "teil", "stunde",
}

PART_FILE = re.compile(r"^(.*)_part_\d+$")


def _lower_tr(s: str) -> str:
    """Lower-casing that also handles Turkish dotted/dotless I."""
    return s.replace("I", "ı").replace("İ", "i").lower()


def _period_ends_sentence(word: str, next_word: str) -> bool:
    """`word` ends with '.'. Is that period really the end of a sentence?"""
    body = word.rstrip(".").lstrip("\"'“‘(«[")
    low = _lower_tr(body)
    if low in ABBREVIATIONS or low.replace(".", "") in ABBREVIATIONS:
        return False
    if len(body) == 1 and body.isalpha():          # initials: "J. R. Smith"
        return False
    if body.isdigit():                              # "3. step", "2. Week" vs "... in 1998."
        if not next_word:
            return True
        first = next_word.lstrip("\"'“‘(«[")
        if first[:1].islower():
            return False
        stem = _lower_tr(re.sub(r"[^\w]", "", first))
        if any(stem.startswith(k) for k in ORDINAL_FOLLOWERS):
            return False
    return True


def split_sentences(text: str) -> list:
    words = text.split()
    sentences, current = [], []
    for i, w in enumerate(words):
        current.append(w)
        core = w.rstrip("\"'”’)»]")
        if not core:
            continue
        nxt = words[i + 1] if i + 1 < len(words) else ""
        if core[-1] in "!?…" or (core[-1] == "." and _period_ends_sentence(core, nxt)):
            sentences.append(" ".join(current))
            current = []
    if current:
        sentences.append(" ".join(current))

    result = []
    for s in sentences:                             # cut unpunctuated runs into blocks
        sw = s.split()
        if len(sw) <= SENTENCE_MAX_WORDS:
            result.append(s)
        else:
            result.extend(" ".join(sw[j:j + BLOCK_WORDS]) for j in range(0, len(sw), BLOCK_WORDS))
    return result


def _paragraphs(sentences: list) -> str:
    paras, cur, n = [], [], 0
    for s in sentences:
        cur.append(s)
        n += len(s.split())
        if n >= PARAGRAPH_WORDS:
            paras.append(" ".join(cur))
            cur, n = [], 0
    if cur:
        paras.append(" ".join(cur))
    return "\n\n".join(paras)


def plan_chunks(sentences, target, overlap, min_last):
    """Returns [(overlap_sentence_indexes, new_sentence_indexes), ...]."""
    wc = [len(s.split()) for s in sentences]
    spans, start, n = [], 0, len(sentences)
    while start < n:
        total, end = 0, start
        while end < n:
            total += wc[end]
            end += 1
            if total >= target:
                break
        spans.append([start, end])
        start = end
    if len(spans) >= 2 and sum(wc[spans[-1][0]:spans[-1][1]]) < min_last:
        spans[-2][1] = spans[-1][1]
        spans.pop()

    cap = int(overlap * OVERLAP_CAP_RATIO)
    plan = []
    for idx, (b, e) in enumerate(spans):
        if idx == 0 or overlap <= 0:
            plan.append(([], list(range(b, e))))
            continue
        prev_b, k, k_total = spans[idx - 1][0], b, 0
        while k > prev_b and k_total < overlap:
            cand = wc[k - 1]
            if k_total > 0 and k_total + cand > cap:
                break
            k -= 1
            k_total += cand
        plan.append((list(range(k, b)), list(range(b, e))))
    return plan


def split_file(path, out_dir=None, target=CHUNK_WORDS, overlap=CHUNK_OVERLAP_WORDS,
               min_last=MIN_LAST_CHUNK_WORDS, header=True) -> int:
    """Split a transcript into <name>_part_N.txt files. Returns the number of parts."""
    with open(path, "r", encoding="utf-8-sig") as f:
        text = " ".join(f.read().split())
    if not text:
        print(f"  skipped (empty): {os.path.basename(path)}")
        return 0

    sentences = split_sentences(text)
    plan = plan_chunks(sentences, target, overlap, min_last)
    total_words = len(text.split())
    name = os.path.splitext(os.path.basename(path))[0]
    out_dir = out_dir or os.path.dirname(os.path.abspath(path))
    os.makedirs(out_dir, exist_ok=True)

    wc = [len(s.split()) for s in sentences]
    cum = [0]
    for w in wc:
        cum.append(cum[-1] + w)

    print(f"  ✂️  {total_words} words, {len(sentences)} sentences → {len(plan)} part(s)")
    for no, (ov, new) in enumerate(plan, start=1):
        first, last = cum[new[0]] + 1, cum[new[-1] + 1]
        ov_words = sum(wc[i] for i in ov)
        lines = []
        if header:
            lines += [f"# {name} | Part {no}/{len(plan)} | Words {first}–{last} of {total_words}", ""]
            if ov:
                lines += [f"## Context from the previous part (~{ov_words} words, "
                          f"already covered — do not repeat)", "",
                          _paragraphs([sentences[i] for i in ov]), "",
                          "## This part", ""]
        elif ov:
            lines += [_paragraphs([sentences[i] for i in ov]), ""]
        lines.append(_paragraphs([sentences[i] for i in new]))
        with open(os.path.join(out_dir, f"{name}_part_{no}.txt"), "w", encoding="utf-8") as out:
            out.write("\n".join(lines).rstrip() + "\n")

    for old in glob.glob(os.path.join(glob.escape(out_dir), glob.escape(name) + "_part_*.txt")):
        m = re.search(r"_part_(\d+)\.txt$", old)
        if m and int(m.group(1)) > len(plan):       # leftovers from an earlier, longer split
            os.remove(old)
    return len(plan)


# ============================================================
# Setup: packages, ffmpeg, GPU, CUDA 12 cuBLAS
# ============================================================
def pip_install(*packages):
    r = subprocess.run([sys.executable, "-m", "pip", "install", "-q", *packages],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-2000:])
        print(r.stderr[-2000:])
        raise SystemExit(f"❌ pip could not install: {' '.join(packages)}")


def install_dependencies():
    print("📦 Checking packages...")
    pip_install(f"faster-whisper=={FASTER_WHISPER_VERSION}",
                f"ctranslate2=={CTRANSLATE2_VERSION}")
    print(f"✅ faster-whisper {FASTER_WHISPER_VERSION} ready.")
    if not shutil.which("ffmpeg"):
        print("📦 Installing ffmpeg...")
        subprocess.run(["apt-get", "install", "-y", "-qq", "ffmpeg"], capture_output=True)
        if not shutil.which("ffmpeg"):
            raise SystemExit("❌ ffmpeg could not be installed.")
    print("✅ ffmpeg ready.")


def require_gpu():
    try:
        out = subprocess.run(["nvidia-smi", "-L"], capture_output=True, text=True)
        ok = out.returncode == 0 and "GPU" in out.stdout
    except FileNotFoundError:
        ok = False
    if not ok:
        raise SystemExit(
            "❌ No GPU found. Either the runtime type is not GPU, or your Colab GPU quota is used up.\n"
            "   Runtime > Change runtime type > T4 GPU, then run again. If the quota is used up,\n"
            "   try again in a few hours. (large-v3 on CPU is far too slow, so we stop here.)")
    print("✅ GPU ready.")


def _find_cublas12_dir():
    import site
    places = site.getsitepackages() + [site.getusersitepackages()] + sys.path
    for sp in dict.fromkeys(places):
        if sp and os.path.isdir(sp):
            hits = glob.glob(os.path.join(sp, "nvidia", "*", "lib", "libcublas.so.12"))
            if hits:
                return os.path.dirname(hits[0])
    return None


def ensure_cublas12():
    """
    Colab moved to CUDA 13 in autumn 2026. CUDA 13 only ships cuBLAS 13, but
    every CTranslate2 release (faster-whisper's GPU engine) looks for
    libcublas.so.12 -> "Library libcublas.so.12 is not found or cannot be loaded".

    Fix: install CUDA 12 cuBLAS from pip and load it into the process BEFORE
    CTranslate2 asks for it. The dynamic loader only searches LD_LIBRARY_PATH
    as it was when the process started, so changing that variable now would
    not help — but once a library is loaded, a later request for the same name
    (soname) gets the already-loaded copy. RTLD_LOCAL keeps its symbols private
    so it cannot clash with the CUDA 13 libraries PyTorch uses. The NVIDIA
    driver is backward compatible, so CUDA 12 libraries run fine on it.
    """
    import ctypes
    try:
        ctypes.CDLL("libcublas.so.12")       # already available (CUDA 12 runtime) or preloaded
        return
    except OSError:
        pass
    lib_dir = _find_cublas12_dir()
    if not lib_dir:
        print("📦 Installing CUDA 12 cuBLAS (~600 MB, about a minute; needed since Colab moved to CUDA 13)...")
        pip_install(f"nvidia-cublas-cu12=={CUBLAS12_VERSION}")
        lib_dir = _find_cublas12_dir()
    if not lib_dir:
        raise SystemExit("❌ libcublas.so.12 still not found after installing nvidia-cublas-cu12.")
    for name in ("libcublasLt.so.12", "libcublas.so.12"):   # order matters: cuBLAS depends on cuBLASLt
        ctypes.CDLL(os.path.join(lib_dir, name), mode=os.RTLD_LOCAL)
    print("✅ CUDA 12 cuBLAS loaded.")


def load_audio(path: str):
    """
    Decode any audio/video file to 16 kHz mono float32 with ffmpeg.
    (faster-whisper's own decoder, PyAV, breaks on some PyAV versions with a
    'metadata_errors' error — the ffmpeg command line is version-proof.)
    """
    import numpy as np
    cmd = ["ffmpeg", "-nostdin", "-threads", "0", "-i", path,
           "-f", "f32le", "-ac", "1", "-ar", str(SAMPLE_RATE), "-"]
    out = subprocess.run(cmd, capture_output=True)
    if out.returncode != 0:
        tail = out.stderr.decode("utf-8", errors="ignore").strip().splitlines()[-3:]
        raise RuntimeError("ffmpeg could not read the file: " + " | ".join(tail))
    audio = np.frombuffer(out.stdout, np.float32).copy()
    if audio.size == 0:
        raise RuntimeError("The file is empty or has no audio track.")
    return audio


# ============================================================
# Google Drive (official API — no drive.mount(), no public sharing needed)
# ============================================================
FOLDER_MIME = "application/vnd.google-apps.folder"
SHORTCUT_MIME = "application/vnd.google-apps.shortcut"


class DriveFile:
    def __init__(self, file_id, path, properties=None):
        self.id = file_id
        self.path = path                         # relative to the root folder
        self.properties = properties or {}
        self.local_path = os.path.join(WORK_DIR, *path.split("/"))


def _q(s):
    return s.replace("\\", "\\\\").replace("'", "\\'")


def folder_id_from_link(link: str) -> str:
    link = link.strip()
    if "folders/" in link:
        return link.split("folders/")[1].split("?")[0].split("/")[0]
    if "id=" in link:
        return link.split("id=")[1].split("&")[0]
    return link


def get_folder_link():
    if DRIVE_FOLDER_LINK.strip():
        print("🔗 Using DRIVE_FOLDER_LINK from the settings.")
        return DRIVE_FOLDER_LINK
    try:
        from google.colab import userdata
        value = userdata.get("DRIVE_FOLDER_LINK")
        if value and value.strip():
            print("🔗 Using DRIVE_FOLDER_LINK from Colab Secrets.")
            return value
    except Exception:
        pass
    return input("🔗 Paste your Google Drive folder link: ")


class Drive:
    def __init__(self):
        from google.colab import auth
        from googleapiclient.discovery import build
        auth.authenticate_user()
        self.svc = build("drive", "v3", cache_discovery=False)

    def name(self, file_id):
        return self.svc.files().get(fileId=file_id, fields="name",
                                    supportsAllDrives=True).execute()["name"]

    def list_tree(self, parent_id, prefix=""):
        """All files under a folder, recursively (follows shortcuts, handles paging)."""
        result, page = [], None
        while True:
            resp = self.svc.files().list(
                q=f"'{parent_id}' in parents and trashed = false",
                fields="nextPageToken, files(id, name, mimeType, shortcutDetails, properties)",
                pageSize=1000, pageToken=page,
                supportsAllDrives=True, includeItemsFromAllDrives=True,
            ).execute()
            for f in resp.get("files", []):
                path = prefix + f["name"]
                mime, fid = f["mimeType"], f["id"]
                if mime == SHORTCUT_MIME:
                    det = f.get("shortcutDetails", {})
                    mime, fid = det.get("targetMimeType", ""), det.get("targetId", fid)
                if mime == FOLDER_MIME:
                    result.extend(self.list_tree(fid, path + "/"))
                else:
                    result.append(DriveFile(fid, path, f.get("properties")))
            page = resp.get("nextPageToken")
            if not page:
                return result

    def download(self, file_id, dest):
        from googleapiclient.http import MediaIoBaseDownload
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        req = self.svc.files().get_media(fileId=file_id, supportsAllDrives=True)
        with open(dest, "wb") as fh:
            dl, done = MediaIoBaseDownload(fh, req, chunksize=32 * 1024 * 1024), False
            while not done:
                _, done = dl.next_chunk(num_retries=3)
        return dest

    def subfolder(self, parent_id, name):
        """Find folder `name` inside parent, create it if missing."""
        q = (f"'{parent_id}' in parents and name = '{_q(name)}' and "
             f"mimeType = '{FOLDER_MIME}' and trashed = false")
        found = self.svc.files().list(q=q, fields="files(id)", supportsAllDrives=True,
                                      includeItemsFromAllDrives=True).execute()["files"]
        if found:
            return found[0]["id"]
        return self.svc.files().create(body={"name": name, "mimeType": FOLDER_MIME,
                                             "parents": [parent_id]},
                                       fields="id", supportsAllDrives=True).execute()["id"]

    def upload(self, local, folder_id):
        """Upload a text file, overwriting a file with the same name. Returns its id."""
        from googleapiclient.http import MediaFileUpload
        name = os.path.basename(local)
        q = f"'{folder_id}' in parents and name = '{_q(name)}' and trashed = false"
        existing = self.svc.files().list(q=q, fields="files(id)", supportsAllDrives=True,
                                         includeItemsFromAllDrives=True).execute()["files"]
        media = MediaFileUpload(local, mimetype="text/plain")
        if existing:
            return self.svc.files().update(fileId=existing[0]["id"], media_body=media,
                                           fields="id", supportsAllDrives=True).execute()["id"]
        return self.svc.files().create(body={"name": name, "parents": [folder_id]},
                                       media_body=media, fields="id",
                                       supportsAllDrives=True).execute()["id"]

    def move(self, file_id, folder_id):
        parents = self.svc.files().get(fileId=file_id, fields="parents",
                                       supportsAllDrives=True).execute().get("parents", [])
        if folder_id in parents:
            return
        self.svc.files().update(fileId=file_id, addParents=folder_id,
                                removeParents=",".join(parents), fields="id",
                                supportsAllDrives=True).execute()

    def mark_done(self, file_id, part_count):
        """
        Put an invisible 'finished' marker on the full transcript (a Drive file
        property — no extra file appears). Called only AFTER every part is
        uploaded: if an upload breaks halfway, the marker is missing and the
        next run re-splits and re-uploads that recording (in seconds, no GPU).
        """
        self.svc.files().update(fileId=file_id,
                                body={"properties": {DONE_PROPERTY: str(part_count)}},
                                fields="id", supportsAllDrives=True).execute()


# ============================================================
# Pipeline
# ============================================================
def hotwords_for(f: DriveFile, root_name: str):
    parts = f.path.split("/")
    for folder in [root_name] + parts[:-1]:
        if normalize_key(folder) in HOTWORD_TABLE:
            return HOTWORD_TABLE[normalize_key(folder)]
    file_key = normalize_key(os.path.splitext(parts[-1])[0])
    for key, terms in HOTWORD_TABLE.items():
        if file_key.startswith(key):
            return terms
    return None


def save_to_drive(drive, out_root_id, name, local_dir, existing_transcript_id, stats):
    """Put <OUTPUT>/<name>/ in Drive: transcript (moved or uploaded), parts, then the marker."""
    if not out_root_id:
        return
    try:
        folder_id = drive.subfolder(out_root_id, name)
        parts = sorted(p for p in glob.glob(os.path.join(glob.escape(local_dir), "*.txt"))
                       if PART_FILE.match(os.path.splitext(os.path.basename(p))[0]))
        moved = bool(existing_transcript_id)
        if moved:
            drive.move(existing_transcript_id, folder_id)
            transcript_id = existing_transcript_id
        else:
            transcript_id = drive.upload(os.path.join(local_dir, name + ".txt"), folder_id)
        for p in parts:
            drive.upload(p, folder_id)
        drive.mark_done(transcript_id, len(parts))      # last step on purpose
        print(f"  ☁️  Drive: {OUTPUT_FOLDER_NAME}/{name}/ ({len(parts)} part(s) uploaded, "
              f"transcript {'moved' if moved else 'uploaded'})")
        stats["uploaded"] += 1
    except Exception as e:
        stats["upload_failed"] += 1
        print(f"  ⚠ Could not save to Drive ({e}) — it will be in the zip.")


def main():
    logging.getLogger("google_auth_httplib2").setLevel(logging.ERROR)   # harmless timeout notice
    install_dependencies()
    import numpy as np
    from faster_whisper import WhisperModel
    from tqdm.auto import tqdm
    require_gpu()

    # --- Drive access -------------------------------------------------
    print("\n" + "=" * 60 + "\n📁 GOOGLE DRIVE FOLDER\n" + "=" * 60)
    root_id = folder_id_from_link(get_folder_link())
    if not root_id:
        raise SystemExit("❌ No valid Google Drive folder link was given.")
    print("\n☁️  Asking for Drive access — if a window opens, tick ALL boxes...")
    try:
        drive = Drive()
    except Exception as e:
        raise SystemExit(f"❌ Drive access failed: {e}")
    print("✅ Drive access granted.")

    for d in (WORK_DIR, OUT_DIR):
        shutil.rmtree(d, ignore_errors=True)
        os.makedirs(d)

    print("\n🔍 Listing the folder...")
    try:
        root_name = drive.name(root_id)
        tree = drive.list_tree(root_id)
    except Exception as e:
        raise SystemExit(f"❌ Could not read the folder: {e}\n"
                         "   Check the link and make sure you signed in with the account that owns it.")
    if not tree:
        raise SystemExit("❌ The folder looks empty.")

    # --- What is already done? ------------------------------------------
    out_key = OUTPUT_FOLDER_NAME.upper()
    audio, transcripts, part_counts = [], {}, {}
    for f in tree:
        parts = f.path.split("/")
        stem, ext = os.path.splitext(parts[-1])
        if any(p.upper() == out_key for p in parts[:-1]):
            if ext.lower() == ".txt":
                m = PART_FILE.match(stem)
                if m:
                    part_counts[m.group(1)] = part_counts.get(m.group(1), 0) + 1
                else:
                    transcripts[stem] = f
        elif ext.lower() in AUDIO_EXTENSIONS:
            audio.append(f)

    if not audio:
        print("❌ No audio/video files found in the folder or its sub-folders. Seen files:")
        for f in tree[:30]:
            print(f"   - {f.path}")
        raise SystemExit()

    def is_complete(name):
        expected = transcripts[name].properties.get(DONE_PROPERTY, "")
        return expected.isdigit() and part_counts.get(name, 0) >= int(expected)

    to_transcribe, to_split, done, seen = [], [], 0, {}
    for f in sorted(audio, key=lambda x: x.path):
        name = os.path.splitext(os.path.basename(f.path))[0]
        if name in seen:
            print(f"  ⚠ Skipped '{f.path}': same name as '{seen[name]}' "
                  f"(both would write the same transcript). Rename one of them.")
            continue
        seen[name] = f.path
        if name not in transcripts:
            to_transcribe.append(f)
        elif not is_complete(name):
            to_split.append((name, transcripts[name]))
        else:
            done += 1

    print(f"\n📂 Folder: {root_name}")
    print(f"   🎤 {len(audio)} recording(s)  |  ✅ {done} done  |  ✂️ {len(to_split)} to split  "
          f"|  🆕 {len(to_transcribe)} to transcribe")
    for name, _ in to_split:
        why = "parts incomplete" if part_counts.get(name) else "no parts yet"
        print(f"      ✂️ {name}  (transcript exists, {why} → split without re-transcribing)")
    for f in to_transcribe:
        print(f"      🆕 {f.path}   🔤 {'hotwords: yes' if hotwords_for(f, root_name) else 'hotwords: none'}")
    if not to_transcribe and not to_split:
        raise SystemExit("\n✨ Nothing to do: every recording is transcribed and split.")

    out_root_id = None
    if UPLOAD_TO_DRIVE:
        try:
            out_root_id = drive.subfolder(root_id, OUTPUT_FOLDER_NAME)
            print(f"\n☁️  Each recording is saved to Drive as soon as it is finished "
                  f"({OUTPUT_FOLDER_NAME}/<recording name>/).")
        except Exception as e:
            print(f"\n⚠ Cannot reach the '{OUTPUT_FOLDER_NAME}' folder in Drive ({e}). "
                  "You will get a zip at the end.")

    stats = {"ok": 0, "failed": 0, "uploaded": 0, "upload_failed": 0}
    started = time.time()

    # --- 1) Transcript exists, parts missing: split only (no GPU, seconds) --
    for i, (name, tf) in enumerate(to_split, start=1):
        print(f"\n✂️ [{i}/{len(to_split)}] {name}")
        local_dir = os.path.join(OUT_DIR, name)
        try:
            drive.download(tf.id, os.path.join(local_dir, name + ".txt"))
            split_file(os.path.join(local_dir, name + ".txt"), local_dir)
            stats["ok"] += 1
            save_to_drive(drive, out_root_id, name, local_dir, tf.id, stats)
        except Exception as e:
            print(f"  ❌ Error: {e}")
            stats["failed"] += 1

    # --- 2) New audio: download -> transcribe -> split -> upload ----------
    if to_transcribe:
        ensure_cublas12()
        print(f"\n⏳ Loading '{MODEL_NAME}' (downloads ~3 GB once per session, 1-2 min)...")
        model = WhisperModel(MODEL_NAME, device="cuda", compute_type="float16",
                             download_root="/content/whisper_models")
        try:   # 1-second smoke test: fail fast with a clear message instead of once per file
            segs, _ = model.transcribe(np.zeros(SAMPLE_RATE, np.float32), language=LANGUAGE or "en")
            list(segs)
        except Exception as e:
            raise SystemExit(f"❌ The model does not run on the GPU: {e}\n"
                             "   See docs/TROUBLESHOOTING.md, or open an issue with this output.")
        print("✅ Model loaded, GPU test passed.")

    for i, f in enumerate(to_transcribe, start=1):
        file_name = os.path.basename(f.path)
        name = os.path.splitext(file_name)[0]
        local_dir = os.path.join(OUT_DIR, name)
        transcript = os.path.join(local_dir, name + ".txt")
        tmp = transcript + ".tmp"
        print(f"\n▶ [{i}/{len(to_transcribe)}] {file_name}")
        try:
            drive.download(f.id, f.local_path)
            samples = load_audio(f.local_path)
            t0 = time.time()
            segments, info = model.transcribe(
                samples,
                language=LANGUAGE,
                beam_size=BEAM_SIZE,
                vad_filter=True,                               # skip silence -> fewer hallucinations, faster
                vad_parameters={"min_silence_duration_ms": 500},
                condition_on_previous_text=False,              # stops "same sentence forever" loops
                hotwords=hotwords_for(f, root_name),           # applied to EVERY 30 s window
            )
            if LANGUAGE is None:
                print(f"  🌐 Detected language: {info.language} ({info.language_probability:.0%})")
            lines, prev, dropped = [], None, 0
            with tqdm(total=round(info.duration), unit="s", desc="  audio") as bar:
                for seg in segments:
                    text = seg.text.strip()
                    if not text or text == prev or is_hallucination(text):
                        dropped += 1
                    else:
                        lines.append(text)
                    prev = text
                    bar.update(max(0, round(seg.end) - bar.n))
            del samples

            os.makedirs(local_dir, exist_ok=True)
            with open(tmp, "w", encoding="utf-8") as out:
                out.write("\n".join(lines) + "\n")
            os.replace(tmp, transcript)                        # never leave a half-written file
            took = time.time() - t0
            print(f"  ✅ {info.duration / 60:.0f} min audio → {took / 60:.1f} min "
                  f"(×{info.duration / max(took, 1):.0f} real time, {dropped} repeated/filler segment(s) dropped)")
            split_file(transcript, local_dir)
            stats["ok"] += 1
            save_to_drive(drive, out_root_id, name, local_dir, None, stats)
        except Exception as e:
            print(f"  ❌ Error: {e}")
            stats["failed"] += 1
        finally:
            for leftover in (f.local_path, tmp):               # keep the disk from filling up
                try:
                    if os.path.exists(leftover):
                        os.remove(leftover)
                except OSError:
                    pass

    # --- Summary + zip ----------------------------------------------------
    total = time.time() - started
    print("\n" + "=" * 60)
    print(f"🎉 Finished — ✅ {stats['ok']} ok, ❌ {stats['failed']} failed  "
          f"(total {int(total // 60)} min {int(total % 60)} s)")
    if out_root_id:
        print(f"   ☁️  Drive: {stats['uploaded']} saved"
              + (f", {stats['upload_failed']} failed" if stats["upload_failed"] else ""))
    print("=" * 60)
    if stats["ok"]:
        zip_path = shutil.make_archive(f"/content/transcripts_{time.strftime('%Y%m%d_%H%M')}",
                                       "zip", root_dir=OUT_DIR)
        print(f"\n📦 {os.path.basename(zip_path)}")
        try:
            from google.colab import files
            files.download(zip_path)
            print("⬇️  Download started.")
        except Exception:
            print(f"⬇️  Automatic download failed → get {zip_path} from the 📁 panel on the left.")
        if not out_root_id or stats["upload_failed"]:
            print(f"\n💡 Put the folders from the zip into '{OUTPUT_FOLDER_NAME}' in your Drive folder,")
            print("   and the next run will skip those recordings.")


def split_cli(args):
    import argparse
    p = argparse.ArgumentParser(prog="transcribe.py split",
                                description="Split transcripts into LLM-ready, overlapping chunks.")
    p.add_argument("files", nargs="+", help=".txt transcripts")
    p.add_argument("--words", type=int, default=CHUNK_WORDS, help="target words per part")
    p.add_argument("--overlap", type=int, default=CHUNK_OVERLAP_WORDS, help="overlap words")
    p.add_argument("--min-last", type=int, default=MIN_LAST_CHUNK_WORDS)
    p.add_argument("--out", help="output folder (default: next to each file)")
    p.add_argument("--no-header", action="store_true", help="plain text, no Markdown headers")
    a = p.parse_args(args)
    for path in a.files:
        if not os.path.isfile(path):
            print(f"not found: {path}")
            continue
        print(f"▶ {os.path.basename(path)}")
        split_file(path, a.out, a.words, a.overlap, a.min_last, header=not a.no_header)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "split":
        split_cli(sys.argv[2:])
    else:
        main()

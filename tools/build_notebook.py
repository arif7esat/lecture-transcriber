"""
Regenerate notebooks/lecture_transcriber.ipynb from transcribe.py.

transcribe.py is the single source of truth; the notebook is just a Colab-friendly
wrapper (an intro cell + the script as one code cell, GPU runtime preselected).

    python tools/build_notebook.py
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "transcribe.py")
NOTEBOOK = os.path.join(ROOT, "notebooks", "lecture_transcriber.ipynb")

INTRO = """# 🎙️ Lecture Transcriber

Google Drive recordings → transcripts → LLM-ready chunks, on a free Colab GPU (Whisper large-v3).

**Steps**
1. **Runtime → Change runtime type** → make sure **T4 GPU** is selected → Save.
2. In the code cell below, paste your Drive folder link into `DRIVE_FOLDER_LINK` (and set `LANGUAGE`, e.g. `"en"`).
3. **Runtime → Run all.** When the Google sign-in opens, choose your account and **tick every box**.

Transcripts appear in a `transcripts/` folder inside your Drive folder, one recording at a time.
Running again later only processes new recordings.

📖 [Beginner guide](https://github.com/arif7esat/lecture-transcriber/blob/main/docs/GETTING_STARTED.md) ·
⚙️ [Settings](https://github.com/arif7esat/lecture-transcriber/blob/main/docs/CONFIGURATION.md) ·
🧯 [Troubleshooting](https://github.com/arif7esat/lecture-transcriber/blob/main/docs/TROUBLESHOOTING.md)
"""


def lines(text):
    parts = text.splitlines(keepends=True)
    if parts and parts[-1].endswith("\n"):
        parts[-1] = parts[-1].rstrip("\n")
    return parts


def main():
    with open(SCRIPT, encoding="utf-8") as f:
        code = f.read()
    nb = {
        "nbformat": 4,
        "nbformat_minor": 0,
        "metadata": {
            "accelerator": "GPU",
            "colab": {"provenance": [], "gpuType": "T4"},
            "kernelspec": {"name": "python3", "display_name": "Python 3"},
            "language_info": {"name": "python"},
        },
        "cells": [
            {"cell_type": "markdown", "metadata": {"id": "intro"}, "source": lines(INTRO)},
            {"cell_type": "code", "metadata": {"id": "transcriber"}, "execution_count": None,
             "outputs": [], "source": lines(code)},
        ],
    }
    os.makedirs(os.path.dirname(NOTEBOOK), exist_ok=True)
    with open(NOTEBOOK, "w", encoding="utf-8") as f:
        json.dump(nb, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print(f"wrote {os.path.relpath(NOTEBOOK, ROOT)}")


if __name__ == "__main__":
    main()

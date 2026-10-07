# Contributing

Thanks for helping! The most useful contributions don't even need code:

- **Timing reports** — paste the `✅ NN min audio → N.N min (×N real time)` lines from your run, plus the GPU
  (T4 / L4 / A100) and `MODEL_NAME`. They replace the estimates in the README.
- **Hallucination phrases** for your language — the sentences Whisper invents during silence.
- **Hotword lists** for common courses (keep them ~20 terms, most important first).
- **Colab breakages** — Colab changes its environment without notice. If the notebook breaks, an issue with the full
  output is gold.

## Code changes

- `transcribe.py` is the single source of truth. After editing it, regenerate the notebook:
  ```bash
  python tools/build_notebook.py
  ```
- The chunker must stay **standard-library only**, so `python transcribe.py split` works anywhere.
- Test the chunker locally:
  ```bash
  python transcribe.py split "examples/Intro to Algorithms Week 1/Intro to Algorithms Week 1.txt" --words 120 --overlap 25 --min-last 30
  ```
- Test the full pipeline on Colab with one short recording before opening a PR that touches transcription, Drive or setup code.
- Keep user-facing messages short and actionable: say what happened and what to do.

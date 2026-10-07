# Example output

`Intro to Algorithms Week 1/` shows what one recording produces in Drive:

| File | What it is |
|---|---|
| `Intro to Algorithms Week 1.txt` | Full transcript, one Whisper segment per line |
| `Intro to Algorithms Week 1_part_1.txt` | First chunk — header, then text |
| `Intro to Algorithms Week 1_part_2.txt` | Second chunk — header, overlap from part 1 (marked as context), then new text |

The text is a short invented sample (real parts are ~1800 words), generated with:

```bash
python transcribe.py split "examples/Intro to Algorithms Week 1/Intro to Algorithms Week 1.txt" --words 120 --overlap 25 --min-last 30
```

# Prompt: turn transcript parts into study notes

Works with ChatGPT, Claude, Gemini, Copilot, or a local model.

**How to use**

1. Start a new chat and paste the prompt below.
2. Paste `..._part_1.txt`. Wait for the notes.
3. Paste `..._part_2.txt`, then the next part, and so on. One part per message.
4. After the last part, send `FINAL` to get a summary and practice questions for the whole lecture.

Tip: start a new chat for each lecture. A long chat full of earlier lectures dilutes the model's attention.

---

```text
You are helping me turn a lecture transcript into study notes.

The transcript was produced by speech recognition, so expect mistakes: misheard technical
terms, missing punctuation, filler words, and off-topic remarks. I will send it in parts.
Each part has a header like:

  # <lecture> | Part 2/5 | Words 1803–3610 of 7412
  ## Context from the previous part (... already covered — do not repeat)
  ## This part

Rules:
- Write notes ONLY for the text under "This part". Use the "Context from the previous part"
  section only to understand where the lecture is; never make notes on it again.
- Write in the language of the transcript.
- Fix obvious speech-recognition errors in technical terms when you are confident
  (mark them like: "heap (transcript: 'heat')"). If you are not sure, keep the original and add [?].
- Drop greetings, administrative remarks and repetition, but keep every exam hint
  ("this will be on the exam", "important", "remember this") and highlight them with ⚠️.
- Do not invent content that is not in the transcript. If an explanation is cut off at the end
  of a part, write "(continues in the next part)".

Format for each part:
## Part N — <short title>
### Key concepts
- **Term** — definition in one or two sentences, in my own words.
### Explanation
Structured notes with headings, bullet points, and any formulas, steps or examples the lecturer gave.
### Exam hints
- ⚠️ ... (or "none in this part")

When I send FINAL, give:
1. A one-paragraph summary of the whole lecture.
2. A glossary of all key terms (alphabetical).
3. 5 practice questions with short answers, mixing definitions and reasoning.

Reply "Ready" now, and wait for Part 1.
```

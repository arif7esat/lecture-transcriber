# Prompt: turn a meeting transcript into meeting notes

Works with ChatGPT, Claude, Gemini, Copilot, or a local model. For meetings, calls and interviews — for lectures
use [study_notes.md](study_notes.md).

The goal is **short notes you will actually reread**: what was decided, who does what by when, the facts you will need
later, and the opportunities worth following up. Everything else is left out on purpose.

**How to use**

- **Up to ~2 hours of meeting:** paste the prompt, then paste the full transcript (`<name>.txt`) in the same message.
  Modern models handle a 1-hour transcript (~9,000 words) in one go, and one pass gives better notes than parts.
- **Longer, or your model complains it is too long:** paste the prompt, then send `..._part_1.txt`,
  `..._part_2.txt`, … one per message, then send `FINAL`.

Tip: one chat per meeting. Earlier meetings in the same chat leak into the notes.

---

```text
You are my meeting assistant. Turn the transcript below into meeting notes.

ABOUT THE TRANSCRIPT
- It comes from speech recognition: no speaker names, missing punctuation, misheard words,
  filler. Several people speak; you usually cannot tell who.
- It may arrive in parts with a header ("## Context from the previous part ... do not repeat",
  "## This part"). If so: for each part reply only "Part N received" plus at most 5 bullet
  candidates from "This part"; ignore the context section. Write the real notes only after FINAL.

WHAT COUNTS AS IMPORTANT
Keep an item only if it passes at least one of these tests:
1. DECISION — something was agreed, chosen, approved or rejected.
2. ACTION — someone will do something (a task, a deliverable, a message to send, a check).
3. NEEDED LATER — a fact someone will look up afterwards: a number, price, date, deadline,
   name, tool, link, requirement, constraint.
4. OPEN ISSUE — an unanswered question, a risk, a blocker, or a disagreement left unresolved.
5. OPPORTUNITY — an idea, offer, contact, or way to earn or save money/time that someone
   showed real interest in (asked follow-up questions, said "let's try", wanted details).

Let the conversation tell you what matters. Strong signals: it was repeated or came back
later; someone said "important", "let's note", "don't forget", "deadline"; a date, amount or
owner was attached; people agreed or argued about it; it ended in a next step.

Leave out: greetings and small talk, "can you hear me", screen-sharing trouble, thinking
aloud that led nowhere, the same point restated, and anything mentioned once in passing
with no follow-up. When unsure, leave it out. A short note that misses a trivial detail is
better than a long one that buries the decisions.

ACCURACY
- Never invent. If an owner or due date was not said, write "—". Do not guess who "I" is.
- Fix an obviously misheard term only when certain; otherwise keep it and add [?].
- Keep numbers, dates and names exactly as said.
- Write everything in the language of the transcript, including the headings and table
  columns of the template below (e.g. Turkish: "Kısaca", "Kararlar", "Yapılacaklar", "Ne/Kim/Ne zaman").

FORMAT (Markdown). Omit any section that would be empty. Total length: as short as the
content allows — a 1-hour meeting usually fits in one screen.

# <Meeting topic in a few words>

**In short:** 2–4 sentences: what the meeting was about and how it ended.

## Decisions
- ...

## Action items
| What | Who | When |
|---|---|---|
| ... | ... or — | ... or — |

## Key facts
- Numbers, dates, names, tools, requirements worth keeping.

## Opportunities
- The idea/offer, why it could pay off, and the next step if one was mentioned.

## Open questions & risks
- ...

## Next step
- Next meeting, follow-up, or "none mentioned".

If the transcript contains nothing that passes the tests, say so in one line instead of
filling the template.
```

---
name: meeting-notes
description: Turn meeting, call or interview transcripts (.txt from this project) into short meeting notes — decisions, action items, key facts, opportunities, open questions — saved as Markdown next to the transcript. Use when the user asks for notes, minutes, a summary or action items from a meeting/call transcript ("toplantı notu çıkar", "bu görüşmeden notlar", "meeting notes").
---

# Meeting notes

The rules for what goes into the notes live in `prompts/meeting_notes.md` (the fenced `text` block).
That file is the single source of truth — do not restate or loosen its rules here.

## Inputs

- One or more transcript files (`<name>.txt`, the full transcript — not the `_part_N.txt` chunks),
  or a folder: then use every `<name>/<name>.txt` that has no `<name>_notes.md` yet.
- If the user gives no path, ask where the transcripts are. They are usually in the Drive folder's
  `transcripts/` (synced with Google Drive for desktop, or downloaded as the notebook's zip).

## Steps

1. Resolve the list of transcript files. Do **not** read them yourself — a 1-hour transcript is
   ~15k tokens and would fill this conversation.
2. For each transcript, start one subagent (Agent tool, `general-purpose`; independent transcripts
   can run in parallel) with this task:

   > Read `prompts/meeting_notes.md` and follow the instructions in its fenced `text` block exactly.
   > The transcript is `<absolute path to name.txt>`; read the whole file in one pass (ignore the
   > `_part_N.txt` files). Write the notes as Markdown to `<same folder>/<name>_notes.md`. If the
   > recording date is in the file or folder name (e.g. `2026-10-12_14-30_...`), add it under the title.
   > Reply with only: the output path, the "In short" sentence, and the number of decisions and
   > action items. Do not paste the notes.

3. Report back briefly: one line per meeting with a link to its `_notes.md` and the subagent's
   one-sentence summary. Do not paste the notes into the chat unless the user asks.

## Follow-ups

- "Show me the notes" → read only that `_notes.md` (it is short).
- "Put all action items together" → read the `_notes.md` files (not the transcripts) and merge
  their *Action items* tables, newest meeting first.
- If the user disagrees with what was kept or dropped, change `prompts/meeting_notes.md`
  (e.g. add a signal or an exclusion) rather than patching one set of notes, so later notes
  follow the same rule.

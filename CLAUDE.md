# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project

**Vibe Through Code Archive** — a public MkDocs (Material theme) site of Ankit's engineering learning notes: AI/Backend/System Design, published from `docs/` at `archive.vibethroughcode.com`.

- Content lives under `docs/stage-<n>/<topic-area>/day-<n>-<slug>.md`.
- `mkdocs.yml` uses `awesome-pages`, `admonition`, `tables`, `pymdownx.superfences`, and TOC permalinks.
- The homepage word map is precomputed — see `README.md` for the `tools/generate_word_frequencies.py` regeneration step after content edits (not needed for note content itself, only if it should surface in the homepage bubbles).

## Note-Making Style (docs/stage-*/**)

These are **revision + interview-prep notes** for someone aiming to become a stronger backend/AI engineer and switch jobs — not tutorials for a beginner audience. Every note should build deep understanding while staying crisp enough to re-read fast before an interview. When writing or restructuring a note, follow the pattern below (established in `docs/stage-1/AI Learning/Hybrid Search + Guradrails/*.md` and `docs/stage-1/AI Learning/LCEL/*.md`):

### Framing
- Open with a **Goal blockquote** (`> **Goal of this Chapter**`) when the topic needs upfront framing, e.g. "this is engineering, not syntax" / "this is engineering, not wording tricks." State explicitly what the chapter is *not* about before saying what it is.
- Follow with a **Crisp Definition** section: one bolded, precise definition sentence — not a paragraph of throat-clearing.

### Body — per concept
For each sub-topic, use this recurring shape (not all sections apply every time, use judgment):
1. **Engineering Problem** — the concrete pain the concept solves, often with a small "without this, X breaks" example.
2. **Definition / crisp explanation** of the concept itself.
3. **Why** questions answered directly — never leave a "why" as just a rhetorical heading with no answer under it.
4. **Trade-offs / when-to-use vs when-not**, usually as a two-column table.
5. **Engineering Insight** — one short paragraph tying the concept to a broader software-engineering principle or pattern (SRP, Adapter, Pipeline Pattern, Open/Closed, etc.). This is what makes it "interview relevant" rather than trivia.

### Formatting conventions
- Diagrams: plain ` ```text ` blocks using `│ ▼ ┌─┴─┐` box-drawing / arrows — real aligned ASCII, not one-word-per-line padding (avoid the old style of `Nothing.\n\nis standardized.` — write normal prose instead).
- Tables for any comparison (X vs Y, good-fit vs poor-fit, benefit vs cost).
- Code examples in real, runnable-looking Python (LangChain-style) when the topic is code-adjacent — not pseudocode.
- Section dividers: `------------------------------------------------------------------------` (long dash rule) between major sections.
- Prefer short paragraphs over the older heavily-padded style (one sentence per line for dramatic effect). That old style was explicitly rejected — see day-2-lcel.md history.

### Closing sections (every note ends with these, in order)
1. **Interview Q&A** — real questions *with answers written out*, not just a bare question list. Answers are 1–3 sentences, precise enough to say out loud in an interview.
2. **Common Interview Traps** — ❌ (wrong belief) / ✔ (correction) pairs, separated by the long-dash rule, for the misconceptions most likely to trip someone up.
3. **What You Should Remember Forever** — a short distilled block (often a `text` code block) that survives even if every other detail is forgotten.
4. **Stage N · Week M Checklist** — a `- [x]` list of the questions the reader should now be able to answer without notes, as the final section.

### When editing an existing note
- Don't revert content the user added directly in the editor (e.g. a pasted code example) — clean it up and integrate it in place rather than discarding it.
- Match section placement to where the user put things (e.g. an execution-order explanation goes directly below the code example it explains, not in a separate later section).
- Prefer editing in place to match the existing file's section order over reshuffling structure.

## Working preferences
- No emojis in notes except the ✔/❌ trap markers and the checklist's own conventions.
- Don't create new note files speculatively — only when asked for a specific day/topic.

#!/usr/bin/env python3
"""Generate committed word-frequency data for the homepage bubble map.

Classification pipeline for turning raw nouns into "technical" terms:
  1. Only NOUN/PROPN tokens (via spaCy's POS tagger) are candidates at all.
     This mechanically drops every verb/adverb/adjective/conjunction and
     never needs manual upkeep for those categories.
  2. Common English function words (DEFAULT_BLACKLIST) are dropped.
  3. Already-decided words (tools/word_map_decisions.json) are resolved
     instantly from the growing cache built up over previous runs.
  4. Words that are extremely rare in general English (per the `wordfreq`
     package) are presumed to be technical jargon/product names and are
     auto-recorded as technical - this is what lets brand-new terms like a
     new library name show up with zero manual intervention.
  5. Words that are extremely common in general English are presumed
     generic and auto-recorded as non-technical.
  6. Anything left is genuinely ambiguous (e.g. "model" vs "example" - both
     are everyday English words and general-purpose frequency can't tell
     them apart). When run in a terminal, you're asked once per word and
     the answer is written back into the decisions cache forever; when run
     non-interactively (e.g. a CI/build hook), ambiguous words are skipped
     for that run and reported so you know a future interactive run has
     something to classify.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

import spacy
from wordfreq import zipf_frequency

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
OUTPUT = DOCS / "assets" / "data" / "word-frequencies.json"
DECISIONS_FILE = ROOT / "tools" / "word_map_decisions.json"

WORD_PATTERN = re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)?", re.UNICODE)
FENCED_CODE_PATTERN = re.compile(r"^\s*(`{3,}|~{3,}).*?^\s*\1\s*$", re.MULTILINE | re.DOTALL)
INLINE_CODE_PATTERN = re.compile(r"`[^`]*`")
MARKDOWN_LINK_PATTERN = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
LINK_DEFINITION_PATTERN = re.compile(r"^\s*\[[^\]]+\]:\s*\S+.*$", re.MULTILINE)
HTML_TAG_PATTERN = re.compile(r"<[^>]*>")

KEEP_POS = {"NOUN", "PROPN"}
# Below this Zipf frequency, a word is rare enough in general English to be
# presumed domain-specific jargon (library/product names, technical terms).
AUTO_TECHNICAL_ZIPF = 2.5
# At or above this Zipf frequency, a word is common enough in general
# English to be presumed generic regardless of grammatical category.
AUTO_GENERIC_ZIPF = 5.3
# A handful of spaCy lemmatizer quirks worth normalizing directly.
LEMMA_OVERRIDES = {"datum": "data", "classes": "class", "fais": "faiss"}
# Ambiguous words used fewer times than this are low-impact (the bubble map
# only ever shows the top ~50 words anyway) and are skipped without asking,
# so classifying stays focused on words that actually matter for the map.
MIN_COUNT_FOR_PROMPT = 3

# Language-level noise that is not useful in a technical word map.
DEFAULT_BLACKLIST = set("""
a an and are as at be been being but by can could did do does doing for from had has have having
he her here hers herself him himself his how i if in into is it its itself just me more most my
myself no nor not of off on once only or other our ours ourselves out over own same she should so
some such than that the their theirs them themselves then there these they this those through to too
under until up very was we were what when where which while who whom why will with would you your
yours yourself yourselves
""".split())

_NLP = None


def get_nlp():
    global _NLP
    if _NLP is None:
        _NLP = spacy.load("en_core_web_sm", disable=["parser", "ner"])
    return _NLP


def text_from_markdown(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    text = FENCED_CODE_PATTERN.sub(" ", text)
    text = INLINE_CODE_PATTERN.sub(" ", text)
    text = MARKDOWN_LINK_PATTERN.sub(r"\1", text)
    text = LINK_DEFINITION_PATTERN.sub(" ", text)
    return HTML_TAG_PATTERN.sub(" ", text)


def merge_plural_lemmas(counts: Counter) -> None:
    """Fold spaCy's occasional proper-noun-tagged plurals ("LLMs", "Models")
    into their singular form so bubbles don't split across both."""
    for word in list(counts):
        if word.endswith("s") and len(word) > 3:
            singular = word[:-1]
            if singular in counts and singular != word:
                counts[singular] += counts.pop(word)


def load_decisions() -> dict:
    if not DECISIONS_FILE.exists():
        return {"technical": [], "nonTechnical": []}
    config = json.loads(DECISIONS_FILE.read_text(encoding="utf-8"))
    for key in ("technical", "nonTechnical"):
        words = config.get(key, [])
        if not isinstance(words, list) or not all(isinstance(w, str) for w in words):
            raise ValueError(f"{DECISIONS_FILE} must contain a '{key}' string array.")
    return config


def save_decisions(technical: set[str], non_technical: set[str]) -> None:
    payload = {"technical": sorted(technical), "nonTechnical": sorted(non_technical)}
    DECISIONS_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def classify(lemma_counts: Counter) -> tuple[Counter, int]:
    """Return (technical word counts, count of unresolved ambiguous words)."""
    config = load_decisions()
    technical = {w.lower().strip() for w in config["technical"]}
    non_technical = {w.lower().strip() for w in config["nonTechnical"]}

    ambiguous: list[str] = []
    for word in sorted(lemma_counts, key=lambda w: -lemma_counts[w]):
        if word in DEFAULT_BLACKLIST or word in non_technical:
            continue
        if word in technical:
            continue
        zipf = zipf_frequency(word, "en")
        if zipf > 0 and zipf < AUTO_TECHNICAL_ZIPF:
            technical.add(word)
        elif zipf >= AUTO_GENERIC_ZIPF or lemma_counts[word] < MIN_COUNT_FOR_PROMPT:
            non_technical.add(word)
        else:
            ambiguous.append(word)

    if ambiguous and sys.stdin.isatty():
        print(f"\n{len(ambiguous)} new word(s) need classification (most-used first).")
        print("Answer y/n; your answer is remembered for every future run.\n")
        try:
            for word in ambiguous:
                answer = input(f"  Is '{word}' (used {lemma_counts[word]}x) a CS/technical term? [y/N] ").strip().lower()
                if answer.startswith("y"):
                    technical.add(word)
                else:
                    non_technical.add(word)
                save_decisions(technical, non_technical)
        except (EOFError, KeyboardInterrupt):
            print("\nStopped early - progress so far has been saved.")
        unresolved = [w for w in ambiguous if w not in technical and w not in non_technical]
    else:
        unresolved = ambiguous
        if unresolved:
            print(
                f"{len(unresolved)} word(s) are not yet classified and were skipped this run "
                f"(run interactively in a terminal to classify them): {', '.join(unresolved[:15])}"
                + (", ..." if len(unresolved) > 15 else "")
            )

    save_decisions(technical, non_technical)

    technical_counts: Counter[str] = Counter()
    for word, count in lemma_counts.items():
        if word in technical:
            technical_counts[word] += count
    return technical_counts, len(unresolved)


def main() -> None:
    markdown_files = sorted(DOCS.rglob("*.md"))
    texts = [text_from_markdown(path) for path in markdown_files]

    raw_counts: Counter[str] = Counter()
    lemma_counts: Counter[str] = Counter()

    nlp = get_nlp()
    for text, doc in zip(texts, nlp.pipe(texts)):
        raw_counts.update(word.lower() for word in WORD_PATTERN.findall(text))
        for token in doc:
            if token.pos_ not in KEEP_POS or not token.is_alpha or token.is_stop:
                continue
            lemma = token.lemma_.lower().strip()
            lemma = LEMMA_OVERRIDES.get(lemma, lemma)
            if len(lemma) < 2:
                continue
            lemma_counts[lemma] += 1
    merge_plural_lemmas(lemma_counts)

    technical_counts, unresolved_count = classify(lemma_counts)

    words = [
        {"word": word, "count": count}
        for word, count in sorted(raw_counts.items(), key=lambda item: (-item[1], item[0]))
    ]
    display_words = [
        {"word": word, "count": count}
        for word, count in sorted(technical_counts.items(), key=lambda item: (-item[1], item[0]))
    ]
    payload = {
        "documentCount": len(markdown_files),
        "totalDistinctWords": len(raw_counts),
        "totalWordUses": sum(raw_counts.values()),
        "displayWordCount": len(display_words),
        "displayWordUses": sum(entry["count"] for entry in display_words),
        "words": words,
        "displayWords": display_words,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)} ({len(display_words)} display words from {len(markdown_files)} documents).")
    if unresolved_count:
        print(f"Note: {unresolved_count} word(s) still need classification - see above.")


if __name__ == "__main__":
    main()

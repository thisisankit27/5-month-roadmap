#!/usr/bin/env python3
"""Generate committed word-frequency data for the homepage bubble map."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
OUTPUT = DOCS / "assets" / "data" / "word-frequencies.json"
BLACKLIST_FILE = ROOT / "tools" / "word_map_blacklist.json"
WORD_PATTERN = re.compile(r"[^\W\d_]+(?:['\u2019][^\W\d_]+)?", re.UNICODE)
FENCED_CODE_PATTERN = re.compile(r"^\s*(`{3,}|~{3,}).*?^\s*\1\s*$", re.MULTILINE | re.DOTALL)
INLINE_CODE_PATTERN = re.compile(r"`[^`]*`")
MARKDOWN_LINK_PATTERN = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
LINK_DEFINITION_PATTERN = re.compile(r"^\s*\[[^\]]+\]:\s*\S+.*$", re.MULTILINE)
HTML_TAG_PATTERN = re.compile(r"<[^>]*>")

# Language-level noise that is not useful in a technical word map.
DEFAULT_BLACKLIST = set("""
a an and are as at be been being but by can could did do does doing for from had has have having
he her here hers herself him himself his how i if in into is it its itself just me more most my
myself no nor not of off on once only or other our ours ourselves out over own same she should so
some such than that the their theirs them themselves then there these they this those through to too
under until up very was we were what when where which while who whom why will with would you your
yours yourself yourselves
""".split())


def text_from_markdown(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    text = FENCED_CODE_PATTERN.sub(" ", text)
    text = INLINE_CODE_PATTERN.sub(" ", text)
    text = MARKDOWN_LINK_PATTERN.sub(r"\1", text)
    text = LINK_DEFINITION_PATTERN.sub(" ", text)
    return HTML_TAG_PATTERN.sub(" ", text)


def load_project_blacklist() -> set[str]:
    """Load the small, user-maintained blacklist and reject malformed entries."""
    config = json.loads(BLACKLIST_FILE.read_text(encoding="utf-8"))
    words = config.get("ignoredWords", [])
    if not isinstance(words, list) or not all(isinstance(word, str) for word in words):
        raise ValueError(f"{BLACKLIST_FILE} must contain an 'ignoredWords' string array.")
    return {word.lower().strip() for word in words if word.strip()}


def main() -> None:
    markdown_files = sorted(DOCS.rglob("*.md"))
    counts: Counter[str] = Counter()
    for path in markdown_files:
        counts.update(word.lower() for word in WORD_PATTERN.findall(text_from_markdown(path)))

    words = [
        {"word": word, "count": count}
        for word, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]
    ignored_words = DEFAULT_BLACKLIST | load_project_blacklist()
    display_words = [entry for entry in words if entry["word"] not in ignored_words]
    payload = {
        "documentCount": len(markdown_files),
        "totalDistinctWords": len(counts),
        "totalWordUses": sum(counts.values()),
        "displayWordCount": len(display_words),
        "displayWordUses": sum(entry["count"] for entry in display_words),
        "words": words,
        "displayWords": display_words,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)} ({len(display_words)} display words from {len(markdown_files)} documents).")


if __name__ == "__main__":
    main()

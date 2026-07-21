#!/usr/bin/env python3
"""Generate the committed word-frequency data used by the homepage bubble map."""
from __future__ import annotations
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
OUTPUT = DOCS / "assets" / "data" / "word-frequencies.json"
WORD_PATTERN = re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)?", re.UNICODE)
FENCED_CODE_PATTERN = re.compile(r"^\s*(`{3,}|~{3,}).*?^\s*\1\s*$", re.MULTILINE | re.DOTALL)
INLINE_CODE_PATTERN = re.compile(r"`[^`]*`")
MARKDOWN_LINK_PATTERN = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
LINK_DEFINITION_PATTERN = re.compile(r"^\s*\[[^\]]+\]:\s*\S+.*$", re.MULTILINE)
HTML_TAG_PATTERN = re.compile(r"<[^>]*>")

def text_from_markdown(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    text = FENCED_CODE_PATTERN.sub(" ", text)
    text = INLINE_CODE_PATTERN.sub(" ", text)
    text = MARKDOWN_LINK_PATTERN.sub(r"\1", text)
    text = LINK_DEFINITION_PATTERN.sub(" ", text)
    return HTML_TAG_PATTERN.sub(" ", text)

def main() -> None:
    markdown_files = sorted(DOCS.rglob("*.md"))
    counts: Counter[str] = Counter()
    for path in markdown_files:
        counts.update(word.lower() for word in WORD_PATTERN.findall(text_from_markdown(path)))
    payload = {"documentCount": len(markdown_files), "totalDistinctWords": len(counts), "totalWordUses": sum(counts.values()), "words": [{"word": word, "count": count} for word, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))]}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)} ({len(counts)} distinct words from {len(markdown_files)} documents).")

if __name__ == "__main__":
    main()

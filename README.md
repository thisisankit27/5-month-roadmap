# Vibe Through Code Archive

## Updating the homepage word map

The homepage uses committed, precomputed word-frequency data. After editing Markdown content, run this before committing:

```powershell
python tools/generate_word_frequencies.py
```

Commit the resulting `docs/assets/data/word-frequencies.json` with the content changes. The browser only downloads this JSON file; it never scans the site's documents.

The homepage only displays terms in the `TECHNICAL_TERMS` whitelist in `docs/assets/javascripts/word-bubbles.js`. Add a term there when you want a new technical topic to appear as a bubble.

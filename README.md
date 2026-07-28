# Vibe Through Code Archive

## Updating the homepage word map

The homepage uses committed, precomputed word-frequency data. After editing Markdown content, run this before committing:

```powershell
python tools/generate_word_frequencies.py
```

Commit the resulting `docs/assets/data/word-frequencies.json` with the content changes. The browser only downloads this JSON file; it never scans the site's documents.

One-time setup: `pip install -r requirements.txt && python -m spacy download en_core_web_sm`.

The generator only ever considers nouns (via spaCy's POS tagger) and classifies each one as technical/non-technical using, in order: a growing decision cache (`tools/word_map_decisions.json`), then automatic rules for words that are clearly rare (presumed jargon) or clearly common (presumed generic) in general English. Anything genuinely ambiguous is skipped unless you run the generator from an interactive terminal, in which case it asks you once per new word and remembers the answer forever after — so classifying gets rarer over time instead of requiring an ever-growing manual blacklist. To correct a decision, just move the word between the `technical`/`nonTechnical` arrays in `tools/word_map_decisions.json`.

Markdown documents
  → run `python tools/generate_word_frequencies.py`
  → generator counts every word (raw, for diagnostics) and every noun (for classification)
  → saves all raw counts in `words`
  → classifies nouns as technical/non-technical (decision cache → rarity rules → interactive prompt)
  → saves the technical entries in `displayWords`
  → commits `word-frequencies.json` and the updated `word_map_decisions.json`

Homepage
  → downloads the committed JSON
  → reads `displayWords`
  → takes the 50 most frequent entries
  → creates the kinetic bubbles
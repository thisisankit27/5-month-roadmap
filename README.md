# Vibe Through Code Archive

## Updating the homepage word map

The homepage uses committed, precomputed word-frequency data. After editing Markdown content, run this before committing:

```powershell
python tools/generate_word_frequencies.py
```

Commit the resulting `docs/assets/data/word-frequencies.json` with the content changes. The browser only downloads this JSON file; it never scans the site's documents.

The generator removes common language words automatically and writes a pre-filtered `displayWords` list for the homepage. To hide an extra recurring word, add it to `ignoredWords` in `tools/word_map_blacklist.json`, then run the generator again. New technical vocabulary appears automatically; no whitelist is required.

Markdown documents
  → run `python tools/generate_word_frequencies.py`
  → generator counts every word
  → saves all counts in `words`
  → removes built-in stop words + `tools/word_map_blacklist.json`
  → saves the remaining entries in `displayWords`
  → commits `word-frequencies.json`

Homepage
  → downloads the committed JSON
  → reads `displayWords`
  → takes the 50 most frequent entries
  → creates the kinetic bubbles
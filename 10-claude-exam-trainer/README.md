# Claude Exam Trainer

A static study site for the **Claude Certified Developer Foundations** exam:
25 objectives, each with notes, worked examples, exam tips, key takeaways,
a glossary, flashcards and a quiz. Content was gathered from Anthropic's
official documentation (Claude docs, Claude Code docs, Anthropic
engineering/research posts, and the MCP spec for the MCP objective); every
section links back to its source page.

## Run it

```bash
cd 10-claude-exam-trainer
python3 -m http.server 8765 --directory site
# open http://localhost:8765
```

No build step is needed — `site/data.js` is committed. After editing any
`content/*.json`, regenerate it:

```bash
python3 build.py
```

## Files

| Path | Role |
|------|------|
| `content/<slug>.json` | One file per exam objective (notes, examples, tips, glossary, quiz). Shape documented in `SCHEMA.md`. |
| `build.py` | Validates every content file (quiz answer indexes) and bundles them, in exam order, into `site/data.js`. |
| `site/index.html`, `site/style.css`, `site/app.js` | The app: dashboard, per-objective tabs, quiz, 60-question mock exam, weak-area drill, flashcards. |
| `site/data.js` | Generated bundle (`window.DATA`). |
| `site/favicon.svg` | Claude-style starburst icon (hand-drawn, not the official asset). |

## Features

- Light/dark theme toggle (persisted; defaults to the system setting).
- Collapsible sidebar (persisted on desktop, slide-over on mobile).
- Quiz progress and missed questions are saved in `localStorage`; an
  objective counts as mastered at ≥90%.

## Caveats

Some source pages were truncated when fetched; those gaps and any claim not
verified against an official page are called out in the notes. Docs change
quickly — re-check against the live pages before the exam.

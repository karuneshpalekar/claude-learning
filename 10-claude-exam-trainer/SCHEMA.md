# Content schema (one JSON file per objective: content/<slug>.json)
{
  "slug": "agent-architecture",
  "title": "Agent Architecture",
  "overview": "2-4 sentence plain-English summary of what this objective covers and why the exam tests it",
  "sources": [{"title": "Page title", "url": "https://..."}],
  "sections": [
    {
      "heading": "Topic name",
      "notes": ["short paragraph or bullet strings, each a standalone note, markdown inline allowed (**bold**, `code`)"],
      "example": {"title": "Example title", "language": "python|json|text|bash|typescript", "code": "worked example, ideally adapted from the docs"},
      "examTips": ["traps, distinctions and 'which is correct when' hints"],
      "source": "https://exact-doc-page-for-this-section"
    }
  ],
  "keyTakeaways": ["8-12 one-line must-remember facts"],
  "glossary": [{"term": "", "definition": ""}],
  "quiz": [
    {"q": "scenario-style question", "options": ["A","B","C","D"], "answer": 0, "explanation": "why right, why others wrong", "source": "url"}
  ]
}
Quiz: 12 questions minimum, exam-style (scenario-based, plausible distractors), answer is 0-based index.

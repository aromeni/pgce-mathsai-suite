# PGCE MathsAI Suite

A growing set of tools built while training as a secondary mathematics teacher (PGCE). Each tool lives in its own top-level directory with its own setup instructions and README.

## Projects

### [`mathsai/`](mathsai/) — AI-assisted KS3/KS4 Edexcel lesson & question generator

A teacher-facing web app that automates lesson planning and practice question generation for KS3/KS4 Edexcel mathematics:

- Browse the full Edexcel curriculum via a topic dashboard
- Generate a complete lesson package per topic — notes, worked examples, key vocabulary, common misconceptions
- Generate three tiers of practice questions (Foundation, Developing, Extending) with mark schemes
- Every piece of AI-generated content is cached in SQLite (generated once, never regenerated unnecessarily) and carries a "not yet checked" flag until a teacher reviews it
- Export lessons and questions to print-friendly PDF
- Track which topics have been taught, to which class, and when
- Runs as a single Docker container, deployed privately over Tailscale

Full setup, architecture, and API documentation: **[`mathsai/README.md`](mathsai/README.md)**. Build rationale and the full phase-by-phase specification: **[`CLAUDE.md`](CLAUDE.md)**.

## CI

`.github/workflows/test.yml` runs MathsAI's backend test suite on every push/PR touching `mathsai/backend/`.

# Paperflow AI — Feature & UX Roadmap

Ideas for improving Paperflow AI (a Paperless-ngx fork adding AI: agentic + per-document
chat, "Suggest" metadata, LanceDB embeddings, Mistral OCR, LLM classification).

Status legend: ✅ done · 🏗️ in progress · 💡 proposed

---

## Recently shipped (UX polish)

- ✅ **Config panel shows env-derived values** as "Inherited from environment" placeholders, with the API key masked.
- ✅ **`ai_enabled` / barcode toggles honour an explicit `False`** (fixed the falsy-coalescing bug; a UI override now wins over an enabling env var).
- ✅ **White-label branding** — "Paperflow AI" consistently across navbar, tab title, dashboard, footer.
- ✅ **Document-list empty state** — distinguishes "no matches for your filters" (with Reset) from "no documents yet".
- ✅ **Chat short-term memory** — recent turns threaded into both chat modes.

---

## 🚩 Flagship: wake up the dormant embeddings → semantic + answer-first search

The LanceDB vector store currently powers **only chat**; the search bar is keyword-only
(Tantivy), so "bike order" misses a German "Fahrradbestellung". Two layered wins on
existing infra:

1. ✅ **"Search by meaning"** — the global search now runs an embedding query in parallel
   with keyword search (gated on AI enabled) and shows a separate "By meaning" group.
   Backend: `GET /api/search/semantic/` over the LanceDB index, permission-scoped.
2. 💡 **Answer-first results (Perplexity-style)** — a synthesized, cited answer at the top
   of the results page, document hits below. Brings the chat differentiator to the most-used surface.

_Impact: high · Effort: medium · Reuses: LanceDB index, chat retriever._

---

## Theme 1 — More retrieval value from embeddings (reuse LanceDB)

- 💡 **Near-duplicate detection on ingest.** Cosine-similarity check at consume time →
  "looks like a document you already have" with merge / keep-both. Catches re-scans.
- 💡 **"Organize my library" suggestions.** Cluster the embedding space and propose
  structure: "12 documents look like invoices — create an _Invoice_ type and tag them?"
- 💡 **Find similar documents** rail on the document detail (nearest neighbours).

## Theme 2 — From answering to _acting_

- 💡 **Agentic actions in chat (with confirmation).** Give the agent mutating tools —
  "tag all 2025 Sport Conrad invoices as Sports" → proposes a bulk edit you approve.
- 💡 **Proactive "Needs attention" dashboard widget.** AI-curated action list: untagged
  docs, likely duplicates, invoices due soon.
- 💡 **Chat over a selection.** Multi-select in the list → scoped chat; suggested prompt chips.

## Theme 3 — Document understanding (typed custom fields already support date/monetary/float)

- 💡 **Deadlines & Finance view.** Auto-extract due dates → `date` field and amounts →
  `monetary`, then a calendar of upcoming bills + spend summary.
- 💡 **Inline Q&A in the document viewer.** Select text in the PDF → "explain this clause".
- 💡 **Line-item / table extraction → CSV.** Pull invoice line items into a structured, exportable table.
- 💡 **Per-document summary tab** (TL;DR + extracted key facts).
- 💡 **AI field extraction into custom fields** with confidence.

## Theme 4 — Trust, cost & privacy

- 💡 **AI cost & usage dashboard.** Tokens/calls per feature, estimated spend, model in use.
- 💡 **Per-document / per-tag "exclude from AI" flag.** Sensitive docs never leave for a remote LLM.
- 💡 **Confidence + feedback loop on suggestions.** Show *why*; accept/reject feeds back.
- 💡 **Per-document "AI activity" timeline.** What the AI did (classified, summarized, indexed) and when.

## Theme 5 — Onboarding & search UX

- 💡 **Auto-classify on consume with one-click accept.** Run Suggest at ingest; show
  metadata as "ghost" chips you accept/reject. (Highest-leverage onboarding fix.)
- 💡 **First-run "watch AI classify."** Wizard that ingests a sample and shows Suggest filling
  metadata live.
- 💡 **Natural-language search → filter chips.** "Sport Conrad invoices from 2025" → builds the filters.
- 💡 **Search history & saved questions.**

---

## Sequencing

- **Quick wins (days):** AI activity timeline · cost/usage dashboard · exclude-from-AI flag.
- **High-impact bets (1–2 wks):** semantic/answer-first search (flagship) · proactive
  "Needs attention" widget · deadlines/finance view.

# Knowledge Source Ingestion

PDF is the preferred canonical source because every passage can be checked
against the original scanned page. EPUB remains a fallback for born-digital
sources. AstroSpace preserves text exactly as extracted. The LLM may
choose boundaries and metadata, but it never writes or corrects stored passage
text.

## Flow

1. Upload the original PDF or EPUB to the private `astro-knowledge-sources` bucket.
2. OCR scans page-by-page with Mistral and retains the raw export archive.
3. Ask the analyzer for boundaries, dynamic source domains, optional CE mappings,
   topics, content types, and quality notes.
4. Reassemble each chunk only from the original extracted blocks.
5. Auto-publish passages that pass deterministic fidelity and OCR gates.
6. Send concrete failures and a 2% audit sample to `needs_review`.
7. Embed and store sections and chunks in Supabase.
8. Classify retrieval scope without deleting editorial or navigation evidence.
9. CE retrieves only `published` `core` chunks and keeps citations in
   `source_passages`.

## Domain Layers

`source_domains` are unrestricted concepts discovered from the book, such as
`planetary_strength` or `gulika_calculation`. They are not limited by the product
taxonomy. `domains` contains optional mappings to the stable CE routing domains
used to assemble calculations. A passage may have source domains and no CE
mapping.

## Retrieval Scope

Publication confirms that extracted text is acceptable. It does not by itself
make every page relevant to CE. Each passage also has one retrieval scope:

- `core`: astrology rules, translations, commentary, examples and exceptions;
- `editorial`: prefaces, translator notes and historical introductions;
- `navigation`: contents and indexes;
- `publishing`: title pages, catalogues, advertisements and offers;
- `devotional`: devotional material without an astrology rule;
- `out_of_domain`: source material outside the product's astrology domain.

Only `core` is available to CE. Other scopes remain immutable, inspectable and
reversible in Admin. Curated edition boundaries take precedence over generic
heading heuristics so mixed pages do not silently discard source rules.

Poppler text-layer passages always enter `needs_review`. Structured Mistral OCR
passages can be published automatically when page confidence is at least `0.90`,
there is no corruption signature, Sanskrit uncertainty is not concentrated,
and the analyzer reports no warning.

## Backend Environment

Set `SUPABASE_URL` and either `SUPABASE_SECRET_KEY` or
`SUPABASE_SERVICE_ROLE_KEY`. The secret must only exist in a backend worker or
Cloud Run secret, never in browser or mobile code. `ANTHROPIC_API_KEY` is needed
for structure and classification analysis.

## Mistral Import

Download the standard Mistral OCR playground export. It must contain a
`markdown.md` and `page-metadata.json` for each `pages/page-N` directory.

```bash
SUPABASE_SERVICE_ROLE_KEY=... \
python scripts/ingest_mistral_exports.py
```

The importer uploads both the original PDF and the compressed Mistral export to
the private source bucket. Re-ingestion replaces sections and chunks
idempotently by `source_key`; superseded pilots are archived without changing
append-only audit history.

## PDF Text-Layer Pilot

```bash
python -m astrospace.knowledge.ingestion \
  "Astro Space Knowledge Base/PDFs/Uttara kalamritam..pdf" \
  --storage-path pdfs/uttara-kalamritam.pdf \
  --source-key uttara-kalamritam-pdf \
  --start-section 15 \
  --max-sections 20
```

`start-section` is a zero-based page index for PDFs. Use `--heuristic` only for
pipeline testing. Heuristic chunks always require review. Re-ingestion is
idempotent by `source_key`.

## Release Gate

A chunk is available to CE only when:

- its content hash matches its exact stored text;
- every character came from source extraction;
- the original PDF and raw OCR export hashes are available;
- classification confidence is at least `0.70`;
- reported OCR confidence is at least `0.90`, when available;
- the analyzer reported no quality warning;
- `quality_status` is `published`;
- `retrieval_scope` is `core`.

Sanskrit that is damaged in the PDF text layer must not be reconstructed by the
analyzer. Reviewers compare it with the page scan and may publish a book-provided
English translation independently when its boundaries and citation are clear.

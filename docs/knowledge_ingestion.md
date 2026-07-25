# Knowledge Source Ingestion

AstroSpace preserves book text as extracted from the source EPUB. The LLM may
choose boundaries and metadata, but it never writes or corrects stored passage
text.

## Flow

1. Upload the original file to the private `astro-knowledge-sources` bucket.
2. Extract XHTML blocks in EPUB spine order and hash the source and text.
3. Ask the analyzer for block boundaries, CE domains, topics, and quality notes.
4. Reassemble each chunk only from the original extracted blocks.
5. Quarantine low-confidence, low-OCR-confidence, or warned chunks as
   `needs_review`.
6. Embed and store sections and chunks in Supabase.
7. CE retrieves only `published` chunks and keeps citations in
   `source_passages`.

## Backend Environment

Set `SUPABASE_URL` and either `SUPABASE_SECRET_KEY` or
`SUPABASE_SERVICE_ROLE_KEY`. The secret must only exist in a backend worker or
Cloud Run secret, never in browser or mobile code. `ANTHROPIC_API_KEY` is needed
for structure and classification analysis.

## Pilot Command

```bash
python -m astrospace.knowledge.ingestion \
  "Astro Space Knowledge Base/EPUBS/Uttara kalamritam..epub" \
  --storage-path epubs/uttara-kalamritam.epub \
  --source-key uttara-kalamritam \
  --start-section 15 \
  --max-sections 6
```

Use `--heuristic` only for pipeline testing. Heuristic chunks always require
review. Re-ingestion is idempotent by `source_key`.

## Release Gate

A chunk is available to CE only when:

- its content hash matches its exact stored text;
- every character came from source extraction;
- classification confidence is at least `0.70`;
- reported OCR confidence is at least `0.75`, when available;
- the analyzer reported no quality warning;
- `quality_status` is `published`.

The current Uttara Kalamritam pilot is intentionally `needs_review` because the
analyzer detected OCR corruption in all three chunks.

# Acquisition

Acquisition turns a URL, PDF, video, or local clipping into a durable, traceable Wiki artifact. The normal destination is both an archived source and a distilled query note; raw capture alone is an intermediate result.

## When to use it

Use Acquisition when the material itself is the learning object: an article, paper, talk, interview, or other source. For a system-level study of a repository, software product, developer tool, or platform, use the separate `chart` workflow instead. A single article about such a tool can still go through Acquisition.

The detailed routing and operating contract is in [`SKILL.md`](./SKILL.md). It covers web articles, YouTube/Bilibili/Xiaohongshu/X videos, PDFs, local media, and browser clippings.

## The durable artifact flow

1. **Identify the source.** Check the canonical URL and, where applicable, content hash. Reuse a complete existing source chain instead of creating duplicates.
2. **Capture the source.** Save the durable provenance snapshot below `raw/`: articles in `raw/articles/`, papers in `raw/papers/`, media and transcripts in `raw/assets/` and `raw/transcripts/`, and clippings in `raw/clippings/`.
3. **Distill the evidence.** Read the captured material, preserve claims, numbers, conditions, and uncertainty, then write a dated query under `queries/YYYYMMDD-<english-slug>.md`.
4. **Connect the record.** The query points to the raw artifact in `sources:` and `## 来源`, records the original URL, and links important concepts to Wiki pages. A transcript or other generated source should link back to its query where applicable.
5. **Update discovery surfaces.** Add the completed query to `index.md` and `log.md`, then refresh the Wiki catalog. A catalog failure is reported as a failure of that step; it does not erase already-created raw or query artifacts.

The source chain is therefore:

```text
input URL/file → identity check → raw provenance snapshot → evidence pass → query note → index/log/catalog
```

## Generic example

For a request such as “digest `https://example.invalid/talk` into the Wiki”:

- identify the URL before downloading;
- capture the article or video and retain its raw artifact;
- for video, retain the media/audio/transcript chain when those stages succeed;
- create a query such as `queries/20260922-reliable-video-evaluation.md` with `sources:` pointing only to the final `raw/` files;
- add at least two relevant concept wikilinks, then update `index.md`, `log.md`, and the catalog;
- report each stage and any missing or failed stage explicitly.

The filename and date above are illustrative. Do not claim a result, path, or completion state until the corresponding file and gate have been verified.

## Completion states

- **Discovery only:** a collection or album was enumerated and normalized; no source body, raw archive, or query was produced.
- **Raw archived:** a source was captured and passed the relevant extraction gate. This preserves provenance but is **not** completed ingestion.
- **Raw + query complete:** the raw artifact and evidence-grounded query exist, their source links resolve, and index/log updates were made. Catalog refresh is reported separately.
- **Partial or failed:** one or more gates, fallback paths, transcription steps, query writes, index updates, or catalog refreshes failed. Name the exact artifact and stage; never present a partial chain as complete.

Retrieval success is not ingestion success: a downloaded file, third-party extractor output, transcript, or discovery manifest does not by itself prove that a durable Wiki query was created.

## Boundaries

- Keep raw material under `raw/`; queries are the reader-facing distillation layer. Do not cite temporary downloader output as the Wiki source.
- Preserve provenance and distinguish source claims, source-reported results, local verification, inference, and personal judgment.
- Do not fabricate article text, transcript content, query results, catalog state, or completion claims when access or extraction fails.
- For incomplete collection discovery, stop before batch ingestion. A requested limit is a scope, not evidence that the full collection was discovered.
- Do not delete browser clippings during ingestion; cleanup belongs to a separate closeout decision.
- If an input affects a durable project decision or incident, follow the Canon output boundary in [`canon-output-contract.md`](../../references/canon-output-contract.md).

## Further reading

- [`SKILL.md`](./SKILL.md): complete routing, gates, output schema, and commands.
- [`download-notes.md`](./references/download-notes.md): platform-specific download notes and troubleshooting.

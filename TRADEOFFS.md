# Engineering Decisions and Tradeoffs

Each section documents a decision **as implemented in this repository**, alternatives considered, and a credible production evolution.

---

## Why Next.js 15 (App Router)

**Chosen:** `frontend/` with App Router, React Server Components for layout, client components for forms/chat, BFF routes under `src/app/api/`.

**Why:**

- Screening stack requirement; Vercel deployment is first-class.
- BFF (`API_URL` server-side) avoids exposing backend URL and simplifies SSE same-origin (`/api/runs/[id]/stream`).
- `sessionStorage` / `localStorage` for comparison and chat UI state without extra backend endpoints.

**Alternatives:** Remix, Vite SPA + separate API gateway, pure FastAPI Jinja templates.

**Pros:** SEO-ready marketing page, edge-ready static shell, TypeScript end-to-end.  
**Cons:** SSE proxy must use Node runtime (`export const runtime = "nodejs"`); serverless timeout limits long ingest unless moved async.  
**Future:** Move ingest to job polling from dashboard; keep BFF only for auth cookie forwarding.

---

## Why FastAPI

**Chosen:** `backend/app/main.py`, async SQLAlchemy, Pydantic v2 schemas.

**Why:**

- Native async fits Redis, Qdrant async client, and LangGraph `ainvoke`.
- Automatic OpenAPI at `/docs` for screening reviewers.
- Clear layering: `api/` → `domain/services/` → `integrations/`.

**Alternatives:** Django Ninja, Node/NestJS monolith.

**Pros:** Performance, typing, small services.  
**Cons:** Python GIL for CPU work — mitigated via `asyncio.to_thread` for BGE and yt-dlp.  
**Future:** Split read-only API vs write/ingest workers.

---

## Why LangGraph

**Chosen:** `StateGraph(ChatGraphState)` in `chat_graph.py` with conditional re-retrieval.

**Why:**

- Explicit graph matches screening requirement (retrieve → grade → generate → cite).
- Conditional edge `documents_relevant` mirrors production RAG patterns.
- Easier to explain in interviews than a single 300-line prompt chain.

**Alternatives:** Raw LangChain LCEL, custom state machine, Temporal workflows.

**Pros:** Visualizable, testable nodes, shared state typing.  
**Cons:** `compare_graph` scaffold adds maintenance — not wired to main flow.  
**Future:** Compile separate graphs per product surface; Redis checkpointer (`LANGGRAPH_CHECKPOINT_BACKEND`).

---

## Why Qdrant (not Pinecone / pgvector)

**Chosen:** `QdrantClientWrapper`, collection `content_chunks_bge_large_v1_5`, payload filters on `org_id` + `creator_id`.

**Why:**

- Payload indexes match multi-tenant filter-before-search pattern.
- Self-host or Qdrant Cloud — cost control at vector scale.
- 1024-dim cosine aligns with BGE-large.

**Alternatives:** Pinecone (hosted only), pgvector (join complexity), Weaviate.

**Pros:** Fast filtered ANN, simple Python client.  
**Cons:** Another infra component; ops expertise required.  
**Future:** INT8 quantization; optional sparse vectors for hashtags.

---

## Why Gemini 2.5 Flash (not GPT-4o)

**Chosen:** `ChatGoogleGenerativeAI` with `gemini-2.5-flash` in `integrations/gemini/client.py`.

**Why:**

- Stack requirement; strong cost/latency for grade + generate + rewrite.
- Streaming via `astream` integrated with Redis token events.

**Alternatives:** GPT-4o mini, Claude Haiku, open-weight Llama on GPU.

**Pros:** Low $/1M tokens; fast TTFT for SSE UX.  
**Cons:** Vendor lock-in; grading quality varies vs larger models.  
**Future:** Route "deep analysis" to Pro tier; keep Flash for chat.

---

## Why BGE (`bge-large-en-v1.5`)

**Chosen:** In-process `sentence-transformers` loading `BAAI/bge-large-en-v1.5`, 1024 dimensions, instruction prefixes:

- Query: `Represent this sentence for searching relevant passages: `
- Document: `Represent this document for retrieval: `

**Why:**

- Strong retrieval quality for English short-form transcripts.
- No per-token embedding API cost.
- `QDRANT_VECTOR_SIZE=1024` matches model output.

**Alternatives:** OpenAI `text-embedding-3-large`, Cohere embed, e5-large.

**Pros:** Predictable marginal cost; works offline.  
**Cons:** Heavy cold start; RAM per replica; `EMBEDDING_SERVICE_URL` in settings is **unused** today.  
**Future:** Extract to GPU microservice; version collections on model change.

---

## Why chunk size 400 / overlap 80

**Chosen:** `ChunkingStrategy.TRANSCRIPT_MAX_TOKENS = 400`, `TRANSCRIPT_OVERLAP_TOKENS = 80`, sentence-boundary splits via regex `(?<=[.!?])\s+`.

**Why:**

- Shorts/Reels transcripts are short; 400 tokens ≈ 1–2 paragraphs — fits Gemini context with multiple chunks.
- 80-token overlap reduces boundary cuts mid-thought (common RAG practice).
- tiktoken `cl100k_base` for counting when available.

**Alternatives:** 256/512 windows, semantic chunking via LLM, one-chunk-per-video.

**Pros:** Balanced retrieval granularity for hook vs body questions.  
**Cons:** More vectors per video → higher ingest cost.  
**Future:** Dynamic chunk size by `duration_sec`; cap max 12 chunks/video.

---

## Why additional chunk types (metadata, hook, hashtags)

**Chosen:** `build_all_chunks()` emits `metadata`, `hook`, `hashtag_block`, and `transcript` chunks.

**Why:**

- Compare questions often target hooks and hashtags — dedicated chunks improve recall vs transcript-only.
- Metadata chunk embeds engagement stats for "which performed better" queries.

**Alternatives:** Transcript-only indexing.

**Pros:** Better precision for analytic questions.  
**Cons:** 3–4 extra vectors per video.  
**Future:** Learned chunk type weights in reranker.

---

## Why SSE (not WebSockets)

**Chosen:** `StreamingResponse` with `text/event-stream`; Redis Streams backend; browser `EventSource` in `use-sse.ts`.

**Why:**

- One-way token stream fits LLM generation; simpler than WS for screening scope.
- HTTP/2 friendly; works through Next.js BFF proxy.
- Named events: `status`, `token`, `citation`, `done`, `error`.

**Alternatives:** WebSockets, long-polling, GraphQL subscriptions.

**Pros:** Native browser API; easy FastAPI support.  
**Cons:** No bi-directional cancel; reconnect logic minimal (`Last-Event-ID` header supported server-side, underused client-side).  
**Future:** WS only if we need cancel-in-flight; otherwise SSE + fetch abort.

---

## Why Redis

**Chosen:** Redis DB 0 for streams + memory; DB 1/2 configured for Celery (stub).

**Why:**

- Redis Streams decouple graph worker from SSE HTTP connection (graph publishes, API consumes).
- Low-latency chat memory with TTL (`CHAT_MEMORY_TTL_SECONDS=86400`).

**Alternatives:** Postgres LISTEN/NOTIFY, Kafka, in-memory only.

**Pros:** Simple, fast, dual-purpose.  
**Cons:** Durability vs Kafka; memory cost at huge stream volume.  
**Future:** `MAXLEN` on streams; separate Redis for Celery.

---

## Why PostgreSQL

**Chosen:** SQLAlchemy models for orgs, creators, content, transcripts, chunks, runs, citations, jobs.

**Why:**

- ACID for runs and citations — audit trail for screening demo.
- JSONB for `engagement`, `raw_metadata`, `filters`.
- Alembic migration `20250601_0001_initial_schema.py`.

**Alternatives:** MongoDB only, DynamoDB.

**Pros:** Relational integrity; familiar ops.  
**Cons:** Not ideal for huge transcript blobs at scale.  
**Future:** S3 for transcripts; PG stores pointers.

---

## Metadata design (Qdrant payload)

**Chosen:** `ChunkMetadataPayload` v1.0 denormalized into Qdrant; mirrors fields in `chunks` table via `qdrant_point_id`.

**Why:**

- Retrieval UI and citations need `url`, `platform`, `title` without PG round-trip per hit.
- `schema_version` supports migrations.

**Alternatives:** Store only IDs in Qdrant; hydrate from PG.

**Pros:** Faster search path; simpler graph context building.  
**Cons:** Duplicate data; stale payload if video re-ingested without delete.  
**Future:** Re-ingest deletes old Qdrant points by `content_item_id` filter.

---

## Citation strategy

**Chosen:**

1. **Live:** `cite` node publishes up to 10 citations to SSE.
2. **Durable:** `GraphRunnerService._persist_citations` writes `citations` table.
3. **UI:** `CitationList` shows rank, platform badge, URL, preview.

**Why:**

- Users see sources as they stream — trust signal.
- DB supports later analytics / feedback loops.

**Alternatives:** Inline footnotes only in markdown; no DB persistence.

**Pros:** Transparent RAG; interview-friendly.  
**Cons:** Citations are retrieval-ranked, not claim-verified ( `fact_check` node exists only in unused compare_graph).  
**Future:** NLI model to drop unsupported claims; link citation span to transcript offset.

---

## Engagement rate formula

**Chosen:** `(likes + comments) / views * 100` in `compute_engagement_rate`, 4 decimal places, 0 if views missing.

**Why:**

- Simple, explainable metric for dashboard cards.
- Consistent between extractor and API response.

**Alternatives:** ER by followers, watch-time weighted ER.

**Pros:** Works with yt-dlp fields today.  
**Cons:** Views denominator unreliable on Instagram; likes may be hidden.  
**Future:** Platform-specific formulas with confidence flags in UI.

---

## Auth: `DEV_AUTH_BYPASS`

**Chosen:** `OrgService.get_or_create_default_org()` when `DEV_AUTH_BYPASS=true` (default).

**Why:**

- Unblocks local and screening demo without Clerk/Auth0 integration.
- Production JWT path raises `501 Not Implemented`.

**Pros:** Fast reviewer onboarding.  
**Cons:** Must not ship enabled in production.  
**Future:** JWT validation + row-level `org_id` enforcement on every query.

---

## Synchronous compare on optional query

**Chosen:** If `CompareUrlsRequest.query` is set, `start_compare` runs **full chat graph synchronously** in the ingest request.

**Why:**

- Convenience for single-shot "analyze and answer" demo.

**Pros:** One API call.  
**Cons:** Multiplies timeout risk; blocks worker.  
**Future:** Always return `run_id` and poll/stream.

---

## Summary Table

| Decision | MVP fit | Production gap |
|----------|---------|----------------|
| Next.js + BFF | Excellent | Ingest polling |
| FastAPI async | Excellent | Worker split |
| LangGraph chat | Excellent | Compare graph wire-up |
| Qdrant + BGE | Excellent | GPU embed service |
| Gemini Flash | Excellent | Grade cost control |
| Redis SSE | Good | Stream trimming |
| Celery scaffold | Poor | Implement tasks |
| JWT auth | Poor | Required for prod |

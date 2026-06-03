# Architecture

This document describes the **as-built** architecture of the Shorts × Reels RAG platform. All diagrams reflect code under `backend/` and `frontend/`.

---

## 1. High-Level Architecture

```mermaid
flowchart TB
  subgraph client [Client Tier]
    Browser[Browser]
  end

  subgraph vercel [Vercel - frontend/]
    Next[Next.js 15 App Router]
    BFF[BFF Routes /api/*]
  end

  subgraph railway [Railway - backend/]
    API[FastAPI Uvicorn]
    LG[LangGraph Chat Graph]
    BGE[sentence-transformers BGE]
  end

  subgraph data [Data Tier]
    PG[(PostgreSQL)]
    Redis[(Redis)]
    QD[(Qdrant)]
  end

  subgraph external [External]
    YT[YouTube / yt-dlp]
    IG[Instagram / yt-dlp]
    Gemini[Google Gemini API]
  end

  Browser --> Next
  Next --> BFF
  BFF --> API
  API --> PG
  API --> Redis
  API --> QD
  API --> LG
  LG --> QD
  LG --> Gemini
  LG --> Redis
  API --> BGE
  BGE --> QD
  API --> YT
  API --> IG
```

**Boundary rules:**

- **PostgreSQL** — system of record: creators, content, transcripts, chunks, analysis runs, citations, jobs.
- **Qdrant** — semantic index only; every search filters `org_id` + `creator_id` (`QdrantClientWrapper._build_filter`).
- **Redis** — ephemeral: SSE fan-out (`run:{run_id}` streams) and chat memory (`chat:memory:{session_id}`).
- **LangGraph** — chat orchestration in-process; compare graph exists but is **not** used for `/compare/urls` today.

---

## 2. Component Diagram

```mermaid
flowchart LR
  subgraph frontend_components [frontend/src]
    UrlForm[home/url-form.tsx]
    VideoCard[dashboard/video-card.tsx]
    ChatPanel[chat/chat-panel.tsx]
    UseSSE[hooks/use-sse.ts]
    UseChat[hooks/use-chat.ts]
    ApiClient[lib/api-client.ts]
  end

  subgraph api_layer [backend/app/api/v1]
    CompareR[compare.py]
    ChatR[chat.py]
    RunsR[runs.py]
  end

  subgraph domain [backend/app/domain/services]
    CompareS[CompareService]
    RunS[RunService]
    VideoIngest[VideoIngestService]
    GraphRunner[GraphRunnerService]
  end

  subgraph graph [backend/app/graph]
    ChatGraph[graphs/chat_graph.py]
    RagNodes[nodes/rag.py]
  end

  subgraph integrations [backend/app/integrations]
    Extract[extraction/extractor.py]
    QdrantC[qdrant/client.py]
    RedisC[redis/client.py]
    GeminiC[gemini/client.py]
    EmbedC[embeddings/client.py]
  end

  UrlForm --> ApiClient
  ChatPanel --> UseChat
  UseChat --> UseSSE
  ApiClient --> CompareR
  ApiClient --> ChatR
  CompareR --> CompareS
  ChatR --> RunS
  RunsR --> RunS
  CompareS --> VideoIngest
  RunS --> GraphRunner
  GraphRunner --> ChatGraph
  ChatGraph --> RagNodes
  VideoIngest --> Extract
  VideoIngest --> EmbedC
  VideoIngest --> QdrantC
  RagNodes --> QdrantC
  RagNodes --> GeminiC
  RagNodes --> RedisC
```

---

## 3. Data Flow — URL Ingest (`POST /v1/compare/urls`)

```mermaid
sequenceDiagram
  participant U as User
  participant FE as Next.js BFF
  participant API as FastAPI
  participant CS as CompareService
  participant VI as VideoIngestService
  participant EX as VideoExtractor
  participant PG as PostgreSQL
  participant CH as ChunkingStrategy
  participant EM as EmbeddingClient
  participant QD as Qdrant

  U->>FE: POST /api/compare/urls
  FE->>API: POST /v1/compare/urls
  API->>CS: ingest_urls(org_id, body)
  CS->>VI: create_comparison_creator()
  VI->>PG: INSERT creators

  loop YouTube then Instagram
    CS->>VI: ingest_from_url(url, platform)
    VI->>EX: extract(url) [yt-dlp thread]
    EX-->>VI: VideoExtract
    VI->>PG: UPSERT content_items, transcripts
    VI->>CH: build_all_chunks()
    VI->>EM: embed_texts() [asyncio.to_thread]
    EM-->>VI: vectors[1024]
    VI->>PG: INSERT chunks
    VI->>QD: upsert_points(payload)
  end

  CS-->>API: creator_id, metrics, transcript_preview
  API-->>FE: CompareUrlsResponse
  FE-->>U: Redirect /dashboard + sessionStorage
```

**Deduping:** `content_hash = sha256(platform:id:transcript)` skips re-index when unchanged (`VideoIngestService.ingest_from_url`).

---

## 4. Ingestion Pipeline

```mermaid
flowchart TD
  A[URL] --> B{Platform detect}
  B -->|youtube.com / youtu.be| C[yt-dlp extract_info]
  B -->|instagram.com| C
  C --> D[YouTube: youtube-transcript-api]
  C --> E[Normalize VideoExtract]
  E --> F[compute_engagement_rate]
  F --> G[PostgreSQL content + transcript]
  G --> H[Chunk types]
  H --> H1[metadata]
  H --> H2[hook]
  H --> H3[hashtag_block]
  H --> H4[transcript windows 400/80]
  H1 --> I[BGE embed_texts]
  H2 --> I
  H3 --> I
  H4 --> I
  I --> J[Qdrant upsert + chunk registry]
```

**Extraction implementation:** `backend/app/integrations/extraction/extractor.py`  
**Chunking:** `backend/app/rag/chunking/strategy.py` — `TRANSCRIPT_MAX_TOKENS=400`, `TRANSCRIPT_OVERLAP_TOKENS=80`

---

## 5. Chat Pipeline (LangGraph)

**Compiled graph:** `build_chat_graph()` in `backend/app/graph/graphs/chat_graph.py`

```mermaid
stateDiagram-v2
  [*] --> load_memory
  load_memory --> rewrite_query
  rewrite_query --> retrieve
  retrieve --> grade_documents
  grade_documents --> generate: sufficient
  grade_documents --> retrieve: insufficient AND attempts < 2
  generate --> cite
  cite --> save_memory
  save_memory --> [*]
```

**Routing:** `documents_relevant()` in `app/graph/edges.py` — sufficient if `len(graded_chunks) >= grade_min_chunks` (default 2) OR `retrieval_attempts >= 2`.

| Node | File | Behavior |
|------|------|----------|
| `load_memory` | `nodes/rag.py` | Redis → LangChain messages |
| `rewrite_query` | `nodes/rag.py` | Gemini standalone query from last 6 turns |
| `retrieve` | `nodes/rag.py` | BGE query embed + Qdrant top-K (8 or 16 on retry) |
| `grade_documents` | `nodes/rag.py` | Score ≥ 0.35 + optional Gemini YES/NO |
| `generate` | `nodes/rag.py` | Gemini stream → Redis `token` events |
| `cite` | `nodes/rag.py` | Build citations → Redis `citation` events |
| `save_memory` | `nodes/rag.py` | Append user/assistant to Redis memory |

**Execution:** `RunService.send_chat_message` → `asyncio.create_task(GraphRunnerService.run_chat)`.

---

## 6. Retrieval Pipeline

```mermaid
flowchart LR
  Q[User query] --> RQ[rewrite_query optional]
  RQ --> EQ[embed_query + QUERY_PREFIX]
  EQ --> V[1024-dim vector]
  V --> S[Qdrant search]
  S --> F[Filter org_id + creator_id]
  F --> H[ChunkHit list]
  H --> G[grade_documents]
  G --> C[Context blocks for Gemini]
```

**Retrieval service:** `backend/app/rag/retrieval/service.py`  
**Settings:** `RETRIEVAL_TOP_K=8`, `RETRIEVAL_SCORE_THRESHOLD=0.35`

---

## 7. Streaming Pipeline

```mermaid
sequenceDiagram
  participant G as generate node
  participant R as Redis XADD run:uuid
  participant API as GET /runs/id/stream
  participant BFF as Next /api/runs/id/stream
  participant ES as EventSource

  G->>R: token {delta}
  G->>R: citation {...}
  G->>R: done {run_id, status}
  ES->>BFF: GET stream
  BFF->>API: proxy body
  API->>R: XREAD BLOCK
  R-->>API: payload JSON
  API-->>BFF: SSE event: token
  BFF-->>ES: forward
```

**Stream key:** `{REDIS_STREAM_PREFIX}:{run_id}` (default `run:{uuid}`)  
**Payload shape:** `{"event":"token","delta":"..."}` serialized in field `payload`  
**Client:** `frontend/src/hooks/use-sse.ts` listens for `status|token|citation|done|error`

---

## 8. Memory Flow

```mermaid
flowchart TB
  subgraph server [Server Memory]
    RedisKey["chat:memory:{session_id}"]
    TTL[TTL 86400s max 40 msgs]
  end

  subgraph client [Client Memory]
    LS["localStorage shorts-reels-chat:{creatorId}"]
    SS["sessionStorage shorts-reels-comparison"]
  end

  Load[load_memory node] --> RedisKey
  Save[save_memory node] --> RedisKey
  ChatUI[use-chat hook] --> LS
  Dashboard[dashboard page] --> SS
```

**Session ID:** `AnalysisRun.id` from `POST /chat/sessions` (type `CHAT`, status `COMPLETED`).  
**Message runs:** Each user message creates a new `AnalysisRun` with `run_type=CHAT`, status `QUEUED` → background graph.

---

## 9. Error Handling Flow

```mermaid
flowchart TD
  A[Request] --> B{DomainError?}
  B -->|NotFoundError| C[404]
  B -->|ValidationError| D[422]
  B -->|QuotaExceededError| E[429]
  B -->|IntegrationError| F[400]
  B -->|NotImplementedFeatureError| G[501]
  B -->|other DomainError| H[400]

  I[Graph exception] --> J[run.status = failed]
  J --> K[Redis error event]
  K --> L[SSE client onError]

  M[yt-dlp failure] --> N[IntegrationError qdrant/yt-dlp]
  N --> O[502/400 to client]

  P[Qdrant down on startup] --> Q[lifespan passes silently]
  Q --> R[ready endpoint shows qdrant=false]
```

**Handler:** `app/api/exception_handlers.py` maps `DomainError` subclasses to HTTP status.

---

## 10. Deployment Architecture

```mermaid
flowchart TB
  subgraph vercel [Vercel Edge/Node]
    FE[Next.js]
  end

  subgraph railway [Railway Project]
    API[FastAPI Service]
    PG[(Postgres Plugin)]
    RD[(Redis Plugin)]
  end

  subgraph qdrant_cloud [Qdrant Cloud]
    QC[(Vectors)]
  end

  subgraph google [Google Cloud]
    GM[Gemini API]
  end

  Users --> FE
  FE -->|API_URL server-side| API
  API --> PG
  API --> RD
  API --> QC
  API --> GM
```

**Note:** BGE runs **in the API process** today (`EmbeddingClient` + `asyncio.to_thread`). For production scale, split to a dedicated embedding worker with GPU.

---

## Database Schema (PostgreSQL)

| Table | Role |
|-------|------|
| `organizations` | Tenant |
| `users` | Org members |
| `creators` | Comparison session / channel grouping |
| `content_items` | One Short or Reel per row |
| `transcripts` | Full text + segments JSON |
| `chunks` | Chunk registry + `qdrant_point_id` |
| `analysis_runs` | Compare + chat runs |
| `citations` | Persisted citation rows per run |
| `jobs` | Async job registry (Celery stub) |
| `usage_daily` | Quota counters (read stub) |

Migration: `backend/alembic/versions/20250601_0001_initial_schema.py`

---

## Qdrant Design (As Implemented)

| Property | Value |
|----------|-------|
| Collection | `content_chunks_bge_large_v1_5` |
| Dimensions | 1024 |
| Distance | Cosine |
| Payload indexes | `org_id`, `creator_id`, `platform`, `content_item_id`, `chunk_type` |
| Schema | `ChunkMetadataPayload` v1.0 (`app/rag/metadata/schema.py`) |

---

## Compare Graph (Scaffold)

`backend/app/graph/graphs/compare_graph.py` defines a multi-step compare workflow (`plan_compare_queries`, `parallel_retrieve`, `synthesize_compare`, etc.), but **nodes in `nodes/compare.py` are phase stubs** and **`CompareService.start_compare` invokes `build_chat_graph()`** instead.

Document this accurately in reviews: the **production RAG path is the chat graph**.

---

## Related Documents

- [SYSTEM_DESIGN.md](./SYSTEM_DESIGN.md) — capacity and NFRs  
- [SCALABILITY.md](./SCALABILITY.md) — growth paths  
- [TRADEOFFS.md](./TRADEOFFS.md) — decision log  

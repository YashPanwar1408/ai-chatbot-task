# Scalability

This document analyzes scalability of the **current implementation** and proposes evolution paths. Numbers are planning estimates, not load-test results.

---

## Current Architecture Limits

| Constraint | Cause in code | Symptom |
|------------|---------------|---------|
| **Synchronous ingest** | `CompareService.ingest_urls` runs extraction + BGE + Qdrant in the HTTP request | Timeouts at 30–120s; poor UX on Vercel BFF |
| **In-process BGE** | `EmbeddingClient` loads `BAAI/bge-large-en-v1.5` inside API worker | High RAM (~2GB+); cold start minutes; CPU contention |
| **Single graph worker** | `asyncio.create_task` on API process | Chat + ingest compete for same event loop |
| **No connection pool tuning** | Default SQLAlchemy/asyncpg pool | Postgres connection exhaustion under burst |
| **Redis stream fan-out** | One consumer per SSE connection via `XREAD` | Redis CPU grows with concurrent streams |
| **No embedding cache** | Every query calls `embed_query` | Redundant GPU/CPU on repeated questions |
| **Celery stub** | `tasks_*.py` raise `NotImplementedFeatureError` | No backpressure queue for ingest |

**Per-URL ingest cost (estimated):**

- yt-dlp + transcript: 5–30s (network bound)
- Chunking: <1s
- BGE embed ~5–15 chunks: 2–10s CPU
- Qdrant upsert: <1s  
- **Total:** ~10–45s per video × 2 URLs per comparison

---

## Scale Scenarios

### ~100 users (MVP / demo)

**Profile:** 10–30 comparisons/day, 50–200 chat messages/day.

| Component | Headroom | Action |
|-----------|----------|--------|
| Single API + single Postgres | Sufficient | Keep `DEV_AUTH_BYPASS=false` only in prod |
| Qdrant local/cloud free tier | Sufficient | ~thousands of vectors |
| Redis single instance | Sufficient | |
| BGE in API | Acceptable | One replica; watch RAM |

**Bottleneck:** First-request BGE model download — mitigate with pre-baked Docker image.

---

### ~1,000 users

**Profile:** ~200 comparisons/day, ~3k chat messages/day (~100k vectors/year if 10 chunks/video).

| Component | Pressure | Mitigation |
|-----------|----------|------------|
| API CPU | Ingest blocks workers | **Queue ingest** (Celery/ARQ); return `job_id` immediately |
| Postgres | Write spikes on ingest | PgBouncer; batch commits where safe |
| Qdrant | ~500k–2M vectors | Payload indexes already exist; monitor HNSW RAM |
| Gemini | Grade per chunk + generate | Cache grades; raise `RETRIEVAL_SCORE_THRESHOLD`; cap chunks in context |
| SSE | Concurrent streams | Sticky sessions optional; Redis Cluster if >10k concurrent |

**Target topology:**

```text
2× API (stateless)
1× Worker (ingest + graph)
1× Embedding GPU service
Managed Postgres + Redis + Qdrant Cloud
```

---

### ~10,000 users

**Profile:** ~2k comparisons/day, ~50k chats/day.

| Bottleneck | Breaks first | Solution |
|------------|--------------|----------|
| **Embedding throughput** | In-process BGE | Dedicated autoscaling embedding fleet; batch size 64+ |
| **Ingest latency** | yt-dlp serial in request | Per-org rate limits; priority queues; parallel platform fetch |
| **Qdrant write QPS** | Batch upserts per video | Async indexer; bulk upsert 500 points |
| **Postgres size** | `transcripts.text` growth | Archive raw text to S3; keep chunk previews in PG |
| **LLM cost** | `grade_documents` calls Gemini per chunk | Cross-encoder reranker locally; grade only top-5 |

**Read path scaling:** Horizontally scale API replicas; Qdrant read replicas if search QPS > write QPS.

---

### ~100,000 users

**Profile:** Enterprise / consumer viral — requires full async platform.

| Layer | Strategy |
|-------|----------|
| **Ingest** | Kafka/SQS → worker pool; idempotency keys on `jobs.idempotency_key` |
| **Vectors** | Qdrant sharding by `org_id` hash OR collection per embedding model version |
| **Search** | CDN for static metadata; separate retrieval microservice |
| **LLM** | Request budgeting per org; `usage_daily` enforcement (implement stub) |
| **Multi-region** | Postgres read replicas; Qdrant geo-replication; Redis Global Datastore |

**Storage estimate (order of magnitude):**

- 100k users × 5 comparisons/month × 2 videos × 10 chunks = **10M new chunks/month**
- Vector storage: 10M × 1024 × 4 bytes ≈ **40 GB/month** raw (less with quantization)

---

## Horizontal Scaling

| Service | Stateless? | Scale method |
|---------|------------|--------------|
| FastAPI | Yes (except in-memory BGE) | Railway/K8s replicas behind LB |
| Next.js BFF | Yes | Vercel auto |
| Workers | Yes | Celery concurrency = CPU/GPU |
| Postgres | No | Read replicas for dashboards; primary for writes |
| Redis | No (streams) | Redis Cluster; separate DB index for Celery |
| Qdrant | Partial | Replicas + sharding |

---

## Redis Usage at Scale

**Current uses:**

1. `XADD` / `XREAD` — SSE (`run:{run_id}`)
2. `GET` / `SET` — `chat:memory:{session_id}` JSON list

**At scale:**

- Trim streams with `MAXLEN ~` on `XADD` to prevent unbounded growth
- Move chat memory to dedicated Redis DB
- Consider Pub/Sub for fan-out if multiple API instances consume same run (today each SSE client XREADs)

---

## Qdrant Scaling

**Current:** Single collection `content_chunks_bge_large_v1_5`, tenant filter on every query.

**Phase 2:**

- INT8 scalar quantization (~4× RAM reduction)
- Separate collection per `embedding_model` version for zero-downtime migrations
- Avoid per-creator collections (ops explosion)

**Search latency target:** p95 < 100ms for `top_k=8` with payload index — achievable to ~10M points per collection with tuned HNSW.

---

## Embedding Throughput

**Current:** `asyncio.to_thread` + `SentenceTransformer.encode(batch_size=32)`.

**Rough CPU throughput:** 50–200 chunks/minute per 4 vCPU (model dependent).

**GPU:** 10–50× improvement — deploy `EmbeddingClient` as gRPC/HTTP service.

**Query cache key:** `embed:{model}:{sha256(query)}` in Redis, TTL 24h — not implemented; high ROI.

---

## Queue Systems

**Scaffold present:** `app/workers/celery_app.py`, broker URL in settings.

**Recommended wiring:**

| Task | Queue | Priority |
|------|-------|----------|
| `ingest.sync_creator` | `ingest` | normal |
| `embed.batch_embed_content` | `embed` | high |
| `graph.run_chat` | `interactive` | high |
| `graph.run_compare` | `batch` | low |

---

## Database Scaling

- **Indexes already:** `content_items(creator_id)`, `analysis_runs(creator_id)`, unique content per platform
- **Add:** partial index on `analysis_runs(status)` where `queued|running`
- **Partitioning (future):** `analysis_runs` by `created_at` month for analytics
- **PgBouncer:** transaction mode for API; session mode for Alembic only

---

## Caching Strategy (Recommended)

| Key | TTL | Saves |
|-----|-----|-------|
| `retrieval:{creator}:{query_hash}` | 1h | Qdrant + BGE query |
| `extract:{platform}:{content_id}` | 24h | yt-dlp |
| `run:summary:{run_id}` | 5m | Postgres read on poll |

---

## Capacity Planning Summary

| Metric | 1k users | 10k users | 100k users |
|--------|----------|-----------|------------|
| Comparisons/day | 200 | 2,000 | 20,000 |
| Chat messages/day | 3,000 | 50,000 | 500,000 |
| API replicas | 1–2 | 3–6 | 10–30 |
| Embedding workers | 0 (in API) | 2 GPU | 10+ GPU |
| Qdrant tier | 1 node 8GB | 16–32GB + replica | Cluster |
| Postgres | 10GB | 100GB | 1TB+ (archive) |
| Gemini spend | $ tens/day | $ hundreds/day | $ thousands/day — grade optimization critical |

---

## What Breaks First (Honest Order)

1. **Synchronous URL ingest** under concurrent users  
2. **BGE RAM** on small Railway instances  
3. **Gemini rate limits / cost** from per-chunk grading  
4. **Instagram extraction failures** (yt-dlp without auth)  
5. **Postgres connections** without pooler  

See [TRADEOFFS.md](./TRADEOFFS.md) for why the current shape is acceptable for a screening MVP and how to evolve it.

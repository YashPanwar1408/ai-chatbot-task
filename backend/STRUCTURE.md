# Backend folder structure

```
backend/
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── app/
│   ├── main.py
│   ├── config/
│   │   ├── settings.py
│   │   └── logging.py
│   ├── api/
│   │   ├── deps.py
│   │   ├── exception_handlers.py
│   │   └── v1/
│   │       ├── router.py
│   │       ├── health.py
│   │       ├── creators.py
│   │       ├── content.py
│   │       ├── ingest.py
│   │       ├── compare.py
│   │       ├── chat.py
│   │       ├── jobs.py
│   │       ├── runs.py
│   │       └── usage.py
│   ├── schemas/
│   ├── domain/
│   │   ├── exceptions.py
│   │   └── services/
│   ├── db/
│   │   ├── base.py
│   │   ├── session.py
│   │   ├── enums.py
│   │   └── models/
│   ├── integrations/
│   │   ├── qdrant/
│   │   ├── redis/
│   │   ├── gemini/
│   │   ├── embeddings/
│   │   ├── youtube/
│   │   └── instagram/
│   ├── rag/
│   │   ├── chunking/
│   │   ├── metadata/
│   │   └── retrieval/
│   ├── graph/
│   │   ├── state.py
│   │   ├── edges.py
│   │   ├── nodes/
│   │   ├── graphs/
│   │   └── checkpoints/
│   ├── workers/
│   └── observability/
├── scripts/
├── tests/
├── pyproject.toml
├── alembic.ini
└── .env.example
```

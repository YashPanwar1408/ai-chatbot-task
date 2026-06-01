# Frontend folder structure

```
frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx                    # Homepage (URL inputs)
│   │   ├── globals.css
│   │   ├── dashboard/
│   │   │   └── page.tsx                # Side-by-side cards + chat
│   │   └── api/                        # BFF (proxies to FastAPI)
│   │       ├── compare/urls/route.ts
│   │       ├── chat/sessions/route.ts
│   │       ├── chat/sessions/[sessionId]/messages/route.ts
│   │       └── runs/[runId]/route.ts
│   │       └── runs/[runId]/stream/route.ts
│   ├── components/
│   │   ├── ui/                         # shadcn primitives
│   │   ├── home/url-form.tsx
│   │   ├── dashboard/video-card.tsx
│   │   ├── chat/chat-panel.tsx
│   │   ├── chat/message-list.tsx
│   │   ├── chat/citation-list.tsx
│   │   └── shared/
│   ├── hooks/
│   │   ├── use-sse.ts
│   │   └── use-chat.ts
│   └── lib/
│       ├── api-client.ts
│       ├── server-api.ts
│       ├── types.ts
│       ├── storage.ts
│       └── utils.ts
├── package.json
├── tailwind.config.ts
└── components.json
```

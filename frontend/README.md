# Shorts vs Reels — Frontend

Next.js 15 app for comparing YouTube Shorts and Instagram Reels.

## Stack

- Next.js 15 (App Router)
- TypeScript
- Tailwind CSS
- shadcn/ui components

## Setup

```bash
cd frontend
npm install
cp .env.example .env.local
```

Set `API_URL=http://localhost:8000` (FastAPI backend).

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Pages

| Route | Description |
|-------|-------------|
| `/` | Enter YouTube + Instagram URLs |
| `/dashboard` | Side-by-side video cards + streaming chat |

## Features

- **Homepage**: URL form → `POST /api/compare/urls` (BFF → backend)
- **Dashboard**: views, likes, comments, engagement rate, hashtags
- **Chat**: SSE streaming tokens, live citations, local + server memory

## Folder structure

```
src/
├── app/
│   ├── page.tsx                 # Homepage
│   ├── dashboard/page.tsx       # Dashboard
│   ├── api/                     # BFF routes
│   └── layout.tsx
├── components/
│   ├── ui/                      # shadcn
│   ├── home/url-form.tsx
│   ├── dashboard/video-card.tsx
│   └── chat/
├── hooks/
│   ├── use-sse.ts
│   └── use-chat.ts
└── lib/
    ├── api-client.ts
    ├── types.ts
    └── storage.ts
```

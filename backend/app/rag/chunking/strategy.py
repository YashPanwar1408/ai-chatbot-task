"""Chunking strategy for transcript and metadata."""

from __future__ import annotations

import re
from dataclasses import dataclass

import tiktoken

from app.db.enums import ChunkType


@dataclass
class RawChunk:
    chunk_index: int
    chunk_type: str
    text: str
    token_count: int | None = None
    time_range: dict | None = None


class ChunkingStrategy:
    """Semantic + token-based chunking for Shorts/Reels content."""

    TRANSCRIPT_MAX_TOKENS = 400
    TRANSCRIPT_OVERLAP_TOKENS = 80

    def __init__(self) -> None:
        try:
            self._encoding = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self._encoding = None

    def count_tokens(self, text: str) -> int:
        if self._encoding is None:
            return max(1, len(text.split()))
        return len(self._encoding.encode(text))

    def _split_sentences(self, text: str) -> list[str]:
        parts = re.split(r"(?<=[.!?])\s+", text.strip())
        return [part.strip() for part in parts if part.strip()]

    def chunk_transcript(self, text: str, segments: list[dict] | None = None) -> list[RawChunk]:
        if not text.strip():
            return []

        sentences = self._split_sentences(text)
        if not sentences:
            return []

        chunks: list[RawChunk] = []
        current: list[str] = []
        current_tokens = 0
        chunk_index = 0

        def flush() -> None:
            nonlocal chunk_index, current, current_tokens
            if not current:
                return
            chunk_text = " ".join(current).strip()
            chunks.append(
                RawChunk(
                    chunk_index=chunk_index,
                    chunk_type=ChunkType.TRANSCRIPT.value,
                    text=chunk_text,
                    token_count=self.count_tokens(chunk_text),
                )
            )
            chunk_index += 1
            overlap_sentences: list[str] = []
            overlap_tokens = 0
            for sentence in reversed(current):
                sentence_tokens = self.count_tokens(sentence)
                if overlap_tokens + sentence_tokens > self.TRANSCRIPT_OVERLAP_TOKENS:
                    break
                overlap_sentences.insert(0, sentence)
                overlap_tokens += sentence_tokens
            current = overlap_sentences
            current_tokens = overlap_tokens

        for sentence in sentences:
            sentence_tokens = self.count_tokens(sentence)
            if current and current_tokens + sentence_tokens > self.TRANSCRIPT_MAX_TOKENS:
                flush()
            current.append(sentence)
            current_tokens += sentence_tokens

        flush()
        return chunks

    def chunk_metadata(
        self,
        *,
        title: str | None,
        description: str | None,
        platform: str,
        creator_name: str,
        engagement_rate: float,
        views: int | None,
        upload_date_iso: str | None,
    ) -> RawChunk:
        text = (
            f"[PLATFORM={platform}][CREATOR={creator_name}]\n"
            f"Title: {title or ''}\n"
            f"Description: {(description or '')[:1500]}\n"
            f"Stats: views={views}, engagement_rate={engagement_rate}%, "
            f"published={upload_date_iso or 'unknown'}"
        )
        return RawChunk(
            chunk_index=0,
            chunk_type=ChunkType.METADATA.value,
            text=text.strip(),
            token_count=self.count_tokens(text),
        )

    def chunk_hook(self, transcript_segments: list[dict]) -> RawChunk | None:
        if not transcript_segments:
            return None
        hook_parts: list[str] = []
        for segment in transcript_segments[:3]:
            text = str(segment.get("text", "")).strip()
            if text:
                hook_parts.append(text)
        if not hook_parts:
            return None
        hook_text = " ".join(hook_parts)
        return RawChunk(
            chunk_index=0,
            chunk_type=ChunkType.HOOK.value,
            text=f"[HOOK]\n{hook_text}",
            token_count=self.count_tokens(hook_text),
            time_range={
                "start_sec": transcript_segments[0].get("start", 0),
                "end_sec": transcript_segments[min(2, len(transcript_segments) - 1)].get(
                    "start", 0
                ),
            },
        )

    def chunk_hashtags(self, hashtags: list[str]) -> RawChunk | None:
        if not hashtags:
            return None
        text = "[HASHTAGS]\n" + " ".join(hashtags)
        return RawChunk(
            chunk_index=0,
            chunk_type=ChunkType.HASHTAG_BLOCK.value,
            text=text,
            token_count=self.count_tokens(text),
        )

    def build_all_chunks(
        self,
        *,
        transcript: str,
        segments: list[dict],
        title: str | None,
        description: str | None,
        platform: str,
        creator_name: str,
        engagement_rate: float,
        views: int | None,
        upload_date_iso: str | None,
        hashtags: list[str],
    ) -> list[RawChunk]:
        chunks: list[RawChunk] = []
        metadata = self.chunk_metadata(
            title=title,
            description=description,
            platform=platform,
            creator_name=creator_name,
            engagement_rate=engagement_rate,
            views=views,
            upload_date_iso=upload_date_iso,
        )
        metadata.chunk_index = len(chunks)
        chunks.append(metadata)

        hook = self.chunk_hook(segments)
        if hook:
            hook.chunk_index = len(chunks)
            chunks.append(hook)

        hashtag_chunk = self.chunk_hashtags(hashtags)
        if hashtag_chunk:
            hashtag_chunk.chunk_index = len(chunks)
            chunks.append(hashtag_chunk)

        for transcript_chunk in self.chunk_transcript(transcript, segments):
            transcript_chunk.chunk_index = len(chunks)
            chunks.append(transcript_chunk)

        return chunks

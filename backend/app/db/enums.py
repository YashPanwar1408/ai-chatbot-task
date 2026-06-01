"""Shared database enum types."""

import enum


class PlanTier(str, enum.Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class UserRole(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class IngestStatus(str, enum.Enum):
    IDLE = "idle"
    RUNNING = "running"
    FAILED = "failed"
    READY = "ready"


class Platform(str, enum.Enum):
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"


class ContentType(str, enum.Enum):
    SHORT = "short"
    REEL = "reel"


class ProcessingStatus(str, enum.Enum):
    PENDING = "pending"
    TRANSCRIBED = "transcribed"
    CHUNKED = "chunked"
    INDEXED = "indexed"
    FAILED = "failed"


class TranscriptSource(str, enum.Enum):
    CAPTION = "caption"
    ASR = "asr"
    DESCRIPTION = "description"


class ChunkType(str, enum.Enum):
    TRANSCRIPT = "transcript"
    CAPTION = "caption"
    METADATA = "metadata"
    HASHTAG_BLOCK = "hashtag_block"
    HOOK = "hook"


class RunType(str, enum.Enum):
    COMPARE = "compare"
    CHAT = "chat"


class AnalysisRunStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class JobType(str, enum.Enum):
    SYNC_CREATOR = "sync_creator"
    EMBED_BATCH = "embed_batch"
    REINDEX = "reindex"


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

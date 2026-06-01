from app.rag.chunking.strategy import ChunkingStrategy


def test_chunk_transcript_splits_long_text() -> None:
    chunker = ChunkingStrategy()
    text = " ".join(["This is sentence number %d." % index for index in range(120)])
    chunks = chunker.chunk_transcript(text)
    assert len(chunks) >= 2
    assert all(chunk.token_count for chunk in chunks)

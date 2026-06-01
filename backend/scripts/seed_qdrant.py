"""CLI script to initialize Qdrant collection. Business logic not implemented."""

import asyncio

from app.integrations.qdrant.client import QdrantClientWrapper


async def main() -> None:
    client = QdrantClientWrapper()
    await client.ensure_collection()
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())

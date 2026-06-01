"""Instagram Reels extraction client."""

from app.integrations.extraction.extractor import VideoExtractor
from app.integrations.extraction.models import VideoExtract


class InstagramClient:
    def __init__(self) -> None:
        self._extractor = VideoExtractor()

    async def extract_from_url(self, url: str) -> VideoExtract:
        return await self._extractor.extract_instagram(url)

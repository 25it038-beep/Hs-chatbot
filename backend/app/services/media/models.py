"""Data models and schemas for YouTube video search, playback, and metadata.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class YouTubeVideo(BaseModel):
    video_id: str
    title: str
    channel_title: str = "YouTube Channel"
    channel_id: str = ""
    thumbnail_url: str = ""
    published_at: str = ""
    description: str = ""
    watch_url: str = ""
    embed_url: str = ""
    duration: Optional[str] = None
    view_count: Optional[str] = None
    source: str = "youtube"

    def model_post_init(self, __context: Any) -> None:
        if self.video_id:
            if not self.watch_url:
                self.watch_url = f"https://www.youtube.com/watch?v={self.video_id}"
            if not self.embed_url:
                self.embed_url = f"https://www.youtube.com/embed/{self.video_id}"
            if not self.thumbnail_url:
                self.thumbnail_url = f"https://img.youtube.com/vi/{self.video_id}/hqdefault.jpg"

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class YouTubeSearchResponse(BaseModel):
    type: str = "youtube_search"
    query: str
    total_results: int = 0
    results: List[YouTubeVideo] = Field(default_factory=list)
    featured_video: Optional[YouTubeVideo] = None
    next_page_token: Optional[str] = None
    error: Optional[str] = None

    def model_post_init(self, __context: Any) -> None:
        if self.results and not self.featured_video:
            self.featured_video = self.results[0]
        if self.results:
            self.total_results = len(self.results)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

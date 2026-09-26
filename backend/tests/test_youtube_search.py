"""Tests for Native YouTube Video Search & Playback Engine.
Validates intent detection, query normalization, search execution,
follow-up reference resolution, and router/classifier integration.
"""

import pytest
from app.services.intent import GeneralIntentClassifier
from app.services.intent.models import IntentCategory
from app.services.media.models import YouTubeVideo, YouTubeSearchResponse
from app.services.media.youtube import YouTubeService, youtube_service
from app.services.nvidia.router import ai_router


class TestYouTubeIntentDetection:
    """Tests for detect_video_intent across varied user queries."""

    def test_explicit_video_queries(self):
        queries = [
            "show some videos for tamil songs on youtube",
            "find videos about quantum computing",
            "show me YouTube videos of guitar lessons",
            "search youtube for python tutorials",
            "find trailers for upcoming movies",
            "play some music videos",
            "watch lecture on machine learning",
        ]
        for q in queries:
            assert youtube_service.detect_video_intent(q) is True, f"Failed for query: {q}"

    def test_music_and_song_queries(self):
        queries = [
            "tamil songs",
            "ar rahman songs",
            "latest hindi songs",
            "rock music video",
            "telugu songs",
        ]
        for q in queries:
            assert youtube_service.detect_video_intent(q) is True, f"Failed for query: {q}"

    def test_followup_ordinal_queries(self):
        queries = [
            "play the second one",
            "play the 1st one",
            "watch the third video",
            "play the 2nd song",
            "play the last one",
            "video #2",
        ]
        for q in queries:
            assert youtube_service.detect_video_intent(q) is True, f"Failed for query: {q}"

    def test_non_video_queries(self):
        queries = [
            "what is the capital of France?",
            "write a python script to reverse a string",
            "what time is it in Tokyo?",
            "explain how quantum computing works",
            "who is the prime minister of Canada?",
        ]
        for q in queries:
            assert youtube_service.detect_video_intent(q) is False, f"Unexpected True for query: {q}"


class TestYouTubeQueryExtraction:
    """Tests for query normalization, language/region mapping, and recency."""

    def test_extract_tamil_songs_query(self):
        info = youtube_service.extract_video_query("show some videos for tamil songs on youtube")
        assert "tamil" in info["query"]
        assert "songs" in info["query"]
        assert info["relevance_lang"] == "ta"
        assert info["region_code"] == "IN"

    def test_extract_recency_and_order(self):
        info = youtube_service.extract_video_query("show latest news videos")
        assert info["order"] == "date"
        assert info["is_fresh"] is True

    def test_extract_max_results(self):
        info = youtube_service.extract_video_query("show 8 videos of cat playing piano")
        assert info["max_results"] == 8
        assert "cat playing piano" in info["query"]


class TestYouTubeVideoModels:
    """Tests for YouTubeVideo and YouTubeSearchResponse data models."""

    def test_auto_url_construction(self):
        video = YouTubeVideo(
            video_id="dQw4w9WgXcQ",
            title="Never Gonna Give You Up",
            channel_title="Rick Astley",
        )
        assert video.watch_url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert video.embed_url == "https://www.youtube.com/embed/dQw4w9WgXcQ"
        assert "dQw4w9WgXcQ" in video.thumbnail_url

    def test_search_response_featured_video(self):
        v1 = YouTubeVideo(video_id="vid1", title="Video 1")
        v2 = YouTubeVideo(video_id="vid2", title="Video 2")
        resp = YouTubeSearchResponse(query="test", results=[v1, v2])
        assert resp.total_results == 2
        assert resp.featured_video is not None
        assert resp.featured_video.video_id == "vid1"


class TestYouTubeFollowupResolution:
    """Tests for resolve_followup mapping user commands to prior search results."""

    @pytest.fixture
    def mock_previous_videos(self):
        return [
            {"video_id": "id1", "title": "First Song - Hits", "channel_title": "Music Label"},
            {"video_id": "id2", "title": "Second Melody Song", "channel_title": "Artist Official"},
            {"video_id": "id3", "title": "Third Acoustic Track", "channel_title": "Band"},
        ]

    def test_resolve_ordinal_first(self, mock_previous_videos):
        res = youtube_service.resolve_followup("play the first one", mock_previous_videos)
        assert res is not None
        assert res["index"] == 1
        assert res["video"]["video_id"] == "id1"

    def test_resolve_ordinal_second(self, mock_previous_videos):
        res = youtube_service.resolve_followup("play the second one", mock_previous_videos)
        assert res is not None
        assert res["index"] == 2
        assert res["video"]["video_id"] == "id2"

    def test_resolve_ordinal_3rd(self, mock_previous_videos):
        res = youtube_service.resolve_followup("watch the 3rd video", mock_previous_videos)
        assert res is not None
        assert res["index"] == 3
        assert res["video"]["video_id"] == "id3"

    def test_resolve_last(self, mock_previous_videos):
        res = youtube_service.resolve_followup("play the last one", mock_previous_videos)
        assert res is not None
        assert res["index"] == 3
        assert res["video"]["video_id"] == "id3"

    def test_resolve_fuzzy_title(self, mock_previous_videos):
        res = youtube_service.resolve_followup("play the melody song", mock_previous_videos)
        assert res is not None
        assert res["index"] == 2
        assert res["video"]["video_id"] == "id2"


@pytest.mark.asyncio
class TestYouTubeSearchExecution:
    """Tests executing YouTube search with mock and fallback handling."""

    async def test_search_results_structure(self):
        # Even without an API key, fallback scraping returns valid structure or graceful list
        resp = await youtube_service.search("tamil songs", max_results=3)
        assert isinstance(resp, YouTubeSearchResponse)
        assert resp.query == "tamil songs"
        if resp.results:
            first = resp.results[0]
            assert first.video_id is not None
            assert len(first.video_id) == 11
            assert first.watch_url.startswith("https://www.youtube.com/watch?v=")
            assert first.embed_url.startswith("https://www.youtube.com/embed/")


class TestIntentClassifierAndRouterIntegration:
    """Tests integration with GeneralIntentClassifier and AIRouter."""

    def test_general_intent_classifier_video_search(self):
        res = GeneralIntentClassifier.classify("show some videos for tamil songs on youtube")
        assert res.primary_intent == IntentCategory.VIDEO_SEARCH
        assert res.needs_quiz is False
        assert res.target_workflow == "video_search"

    def test_ai_router_video_search(self):
        decision = ai_router.classify("find tutorials on youtube for react js")
        assert decision["primary_intent"] == "video_search"
        assert decision["requires_videos"] is True
        task = ai_router.detect_task("find tutorials on youtube for react js")
        assert task == "video_search"

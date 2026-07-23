"""Tests for ContextMerger and EvidenceItem.

All tests use in-memory fixtures — no network calls, no database.
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# EvidenceItem
# ---------------------------------------------------------------------------


class TestEvidenceItem:
    def test_minimal_construction(self):
        from src.services.merger.context_merger import EvidenceItem

        item = EvidenceItem(content="Hello world")
        assert item.content == "Hello world"
        assert item.score == 0.0
        assert item.title == ""
        assert item.url == ""
        assert item.source == ""
        assert item.source_type == ""

    def test_full_construction(self):
        from src.services.merger.context_merger import EvidenceItem

        item = EvidenceItem(
            content="Some content",
            score=0.85,
            title="My Title",
            url="https://example.com",
            source="Tavily",
            source_type="web",
            metadata={"chunk_idx": 3},
        )
        assert item.content == "Some content"
        assert item.score == pytest.approx(0.85)
        assert item.title == "My Title"
        assert item.url == "https://example.com"
        assert item.source == "Tavily"
        assert item.source_type == "web"
        assert item.metadata == {"chunk_idx": 3}

    def test_score_clamped(self):
        from src.services.merger.context_merger import EvidenceItem

        # Score below 0
        item = EvidenceItem(content="x", score=-0.5)
        assert item.score == 0.0

        # Score above 1
        item = EvidenceItem(content="x", score=1.5)
        assert item.score == 1.0

        # Score in range unaffected
        item = EvidenceItem(content="x", score=0.75)
        assert item.score == pytest.approx(0.75)

    def test_to_dict(self):
        from src.services.merger.context_merger import EvidenceItem

        item = EvidenceItem(
            content="Hello",
            score=0.9,
            title="Title",
            url="https://example.com",
            source="KB",
            source_type="knowledge_base",
            metadata={"id": 1},
        )
        d = item.to_dict()
        assert d["content"] == "Hello"
        assert d["score"] == pytest.approx(0.9)
        assert d["title"] == "Title"
        assert d["url"] == "https://example.com"
        assert d["source"] == "KB"
        assert d["source_type"] == "knowledge_base"
        assert d["metadata"] == {"id": 1}

    def test_content_preview(self):
        from src.services.merger.context_merger import EvidenceItem

        short = EvidenceItem(content="Hello")
        assert short.content_preview == "Hello"

        long = EvidenceItem(content="A" * 100)
        assert len(long.content_preview) == 83  # 80 chars + "..."

    def test_sort_by_score_descending(self):
        from src.services.merger.context_merger import EvidenceItem

        items = [
            EvidenceItem(content="low", score=0.3),
            EvidenceItem(content="high", score=0.9),
            EvidenceItem(content="mid", score=0.6),
        ]
        # EvidenceItem no longer has order=True — sort explicitly by score
        sorted_items = sorted(items, key=lambda e: e.score, reverse=True)
        assert sorted_items[0].score == pytest.approx(0.9)
        assert sorted_items[1].score == pytest.approx(0.6)
        assert sorted_items[2].score == pytest.approx(0.3)


# ---------------------------------------------------------------------------
# ContextMerger — basic merging
# ---------------------------------------------------------------------------


class TestContextMergerMerge:
    def test_empty_inputs(self):
        from src.services.merger.context_merger import ContextMerger

        merger = ContextMerger()
        result = merger.merge()
        assert result == []

    def test_knowledge_only(self):
        from src.services.merger.context_merger import ContextMerger

        merger = ContextMerger()
        knowledge = [
            {"chunk_content": "KB chunk 1", "similarity": 0.9, "parent_url": "https://kb.example.com/1"},
            {"chunk_content": "KB chunk 2", "similarity": 0.7, "parent_url": "https://kb.example.com/2"},
        ]
        result = merger.merge(knowledge=knowledge)
        assert len(result) == 2
        assert result[0].content == "KB chunk 1"
        assert result[0].score == pytest.approx(0.9)
        assert result[0].source_type == "knowledge_base"
        assert result[0].url == "https://kb.example.com/1"

    def test_web_search_only_with_objects(self):
        from src.services.merger.context_merger import ContextMerger
        from src.services.search.models import SearchResult

        merger = ContextMerger()
        results = [
            SearchResult(title="R1", url="https://example.com/1", snippet="Snippet 1", source="example.com", score=0.8),
            SearchResult(title="R2", url="https://example.com/2", snippet="Snippet 2", source="example.com", score=0.6),
        ]
        result = merger.merge(web_search=results)
        assert len(result) == 2
        assert result[0].content == "Snippet 1"
        assert result[0].score == pytest.approx(0.8)
        assert result[0].source_type == "web"

    def test_web_search_only_with_dicts(self):
        from src.services.merger.context_merger import ContextMerger

        merger = ContextMerger()
        results = [
            {"title": "R1", "url": "https://example.com/1", "snippet": "Snippet 1", "source": "example.com", "score": 0.8},
        ]
        result = merger.merge(web_search=results)
        assert len(result) == 1
        assert result[0].content == "Snippet 1"

    def test_live_pages_only(self):
        from src.services.merger.context_merger import ContextMerger

        merger = ContextMerger()

        class FakeChunk:
            def __init__(self, text, score, source_idx=0, chunk_idx=0):
                self.text = text
                self.score = score
                self.source_idx = source_idx
                self.chunk_idx = chunk_idx

        chunks = [
            FakeChunk("Chunk A", 0.95),
            FakeChunk("Chunk B", 0.5),
        ]
        result = merger.merge(live_pages=chunks)
        assert len(result) == 2
        assert result[0].content == "Chunk A"
        assert result[0].source_type == "live_page"

    def test_live_pages_with_dicts(self):
        from src.services.merger.context_merger import ContextMerger

        merger = ContextMerger()
        chunks = [
            {"text": "Dict chunk 1", "score": 0.88, "source_idx": 0, "chunk_idx": 1},
        ]
        result = merger.merge(live_pages=chunks)
        assert len(result) == 1
        assert result[0].content == "Dict chunk 1"
        assert result[0].metadata["source_idx"] == 0
        assert result[0].metadata["chunk_idx"] == 1

    def test_merge_from_all_sources(self):
        from src.services.merger.context_merger import ContextMerger
        from src.services.search.models import SearchResult

        merger = ContextMerger()
        knowledge = [
            {"chunk_content": "KB content", "similarity": 0.7, "parent_url": "https://kb.example.com"},
        ]
        web = [
            SearchResult(title="Web", url="https://web.example.com", snippet="Web snippet", source="web", score=0.8),
        ]
        class FakeChunk:
            def __init__(self):
                self.text = "Live chunk"
                self.score = 0.9
                self.source_idx = 0
                self.chunk_idx = 0

        result = merger.merge(knowledge=knowledge, web_search=web, live_pages=[FakeChunk()])
        # All sources merged
        assert len(result) >= 3
        # Sorted by score descending: 0.9, 0.8, 0.7
        assert result[0].score == pytest.approx(0.9)
        assert result[1].score == pytest.approx(0.8)
        assert result[2].score == pytest.approx(0.7)

    def test_min_score_filters_low_scoring_items(self):
        from src.services.merger.context_merger import ContextMerger

        merger = ContextMerger(min_score=0.5)
        knowledge = [
            {"chunk_content": "Good", "similarity": 0.9},
            {"chunk_content": "Bad", "similarity": 0.3},
        ]
        result = merger.merge(knowledge=knowledge)
        assert len(result) == 1
        assert result[0].content == "Good"


# ---------------------------------------------------------------------------
# ContextMerger — deduplication
# ---------------------------------------------------------------------------


class TestContextMergerDedup:
    def test_url_dedup_keeps_highest_score(self):
        from src.services.merger.context_merger import ContextMerger
        from src.services.search.models import SearchResult

        merger = ContextMerger()
        web = [
            SearchResult(title="A", url="https://example.com/same", snippet="Low score snippet", source="web", score=0.3),
            SearchResult(title="B", url="https://example.com/same", snippet="High score snippet", source="web", score=0.9),
        ]
        result = merger.merge(web_search=web)
        assert len(result) == 1
        assert result[0].content == "High score snippet"

    def test_url_dedup_keeps_different_urls(self):
        from src.services.merger.context_merger import ContextMerger
        from src.services.search.models import SearchResult

        merger = ContextMerger()
        web = [
            SearchResult(title="A", url="https://example.com/1", snippet="Snippet 1", source="web", score=0.5),
            SearchResult(title="B", url="https://example.com/2", snippet="Snippet 2", source="web", score=0.5),
        ]
        result = merger.merge(web_search=web)
        assert len(result) == 2

    def test_text_dedup_removes_near_duplicates(self):
        from src.services.merger.context_merger import ContextMerger

        merger = ContextMerger(dedup_text=True, ngram_threshold=0.5)
        # Use content long enough to exceed _TEXT_DEDUP_MIN_LENGTH (60 chars)
        knowledge = [
            {"chunk_content": "The quick brown fox jumps over the lazy dog near the riverbank yesterday afternoon", "similarity": 0.9},
            {"chunk_content": "The quick brown fox jumps over the lazy dog near the riverbank yesterday afternoon!", "similarity": 0.8},  # near-identical
            {"chunk_content": "Completely different content about something unrelated to the fox or the dog at all", "similarity": 0.7},
        ]
        result = merger.merge(knowledge=knowledge)
        # The near-duplicate should be removed
        assert len(result) == 2
        assert "quick brown fox" in result[0].content

    def test_dedup_disabled(self):
        from src.services.merger.context_merger import ContextMerger
        from src.services.search.models import SearchResult

        merger = ContextMerger(dedup_url=False, dedup_text=False)
        web = [
            SearchResult(title="A", url="https://example.com/same", snippet="Same snippet", source="web", score=0.5),
            SearchResult(title="B", url="https://example.com/same", snippet="Same snippet", source="web", score=0.5),
        ]
        result = merger.merge(web_search=web)
        # Both should be present since dedup is disabled
        assert len(result) == 2

    def test_max_evidence_cap(self):
        from src.services.merger.context_merger import ContextMerger

        merger = ContextMerger(max_evidence=3)
        knowledge = [
            {"chunk_content": f"Chunk {i}", "similarity": 1.0 - (i * 0.1)}
            for i in range(10)
        ]
        result = merger.merge(knowledge=knowledge)
        assert len(result) == 3


# ---------------------------------------------------------------------------
# ContextMerger — merge_to_text
# ---------------------------------------------------------------------------


class TestContextMergerMergeToText:
    def test_empty(self):
        from src.services.merger.context_merger import ContextMerger

        merger = ContextMerger()
        assert merger.merge_to_text() == ""

    def test_joins_with_separator(self):
        from src.services.merger.context_merger import ContextMerger

        merger = ContextMerger()
        knowledge = [
            {"chunk_content": "First", "similarity": 0.9},
            {"chunk_content": "Second", "similarity": 0.8},
        ]
        text = merger.merge_to_text(knowledge=knowledge, separator="|")
        assert text == "First|Second"

    def test_default_separator(self):
        from src.services.merger.context_merger import ContextMerger

        merger = ContextMerger()
        knowledge = [
            {"chunk_content": "A", "similarity": 0.9},
            {"chunk_content": "B", "similarity": 0.8},
        ]
        text = merger.merge_to_text(knowledge=knowledge)
        # Default separator is \n\n---\n\n
        assert "---" in text


# ---------------------------------------------------------------------------
# ContextMerger — bigram similarity internals
# ---------------------------------------------------------------------------


class TestContextMergerBigram:
    def test_identical_texts(self):
        from src.services.merger.context_merger import ContextMerger

        sim = ContextMerger._bigram_similarity("hello world", "hello world")
        assert sim == pytest.approx(1.0)

    def test_completely_different_texts(self):
        from src.services.merger.context_merger import ContextMerger

        sim = ContextMerger._bigram_similarity("abc", "xyz")
        assert sim == pytest.approx(0.0)

    def test_both_empty(self):
        from src.services.merger.context_merger import ContextMerger

        sim = ContextMerger._bigram_similarity("", "")
        assert sim == pytest.approx(1.0)

    def test_one_empty(self):
        from src.services.merger.context_merger import ContextMerger

        sim = ContextMerger._bigram_similarity("hello", "")
        assert sim == pytest.approx(0.0)

    def test_slightly_different(self):
        from src.services.merger.context_merger import ContextMerger

        # These are similar but not identical
        sim = ContextMerger._bigram_similarity(
            "The quick brown fox",
            "The quick brown fox!",
        )
        assert 0.5 < sim < 1.0

    def test_case_and_whitespace_normalized(self):
        from src.services.merger.context_merger import ContextMerger

        sim = ContextMerger._bigram_similarity(
            "Hello   World",
            "hello world",
        )
        assert sim == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# ContextMerger — converter handling edge cases
# ---------------------------------------------------------------------------


class TestContextMergerEdgeCases:
    def test_empty_content_skipped(self):
        from src.services.merger.context_merger import ContextMerger

        merger = ContextMerger()
        # Knowledge match with empty chunk_content
        knowledge = [
            {"chunk_content": "", "similarity": 0.9},
            {"chunk_content": "  ", "similarity": 0.8},
            {"chunk_content": "Valid", "similarity": 0.7},
        ]
        result = merger.merge(knowledge=knowledge)
        assert len(result) == 1
        assert result[0].content == "Valid"

    def test_missing_keys_in_knowledge(self):
        from src.services.merger.context_merger import ContextMerger

        merger = ContextMerger()
        knowledge = [
            {"chunk_content": "No similarity key"},
            {"similarity": 0.5},  # No content
        ]
        result = merger.merge(knowledge=knowledge)
        assert len(result) == 1
        assert result[0].score == 0.0

    def test_duck_typed_search_result(self):
        from src.services.merger.context_merger import ContextMerger

        merger = ContextMerger()

        class DuckResult:
            snippet = "Duck snippet"
            score = 0.75
            title = "Duck"
            url = "https://duck.example.com"
            source = "DuckEngine"

        result = merger.merge(web_search=[DuckResult()])
        assert len(result) == 1
        assert result[0].content == "Duck snippet"
        assert result[0].score == pytest.approx(0.75)
        assert result[0].source == "DuckEngine"

    def test_mixed_none_inputs(self):
        from src.services.merger.context_merger import ContextMerger

        merger = ContextMerger()
        # All inputs as None should produce empty result
        result = merger.merge(knowledge=None, web_search=None, live_pages=None)
        assert result == []
"""Knowledge management domain models (Phase 27)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def _from_row(cls, row: dict[str, Any]):
    return cls(**{field: row.get(field) for field in cls.__dataclass_fields__})


@dataclass(frozen=True)
class KnowledgeCollection:
    id: str
    workspace_id: str
    name: str
    description: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    archived_at: str | None = None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "KnowledgeCollection":
        return _from_row(cls, row)


@dataclass(frozen=True)
class KnowledgeSource:
    id: str
    workspace_id: str
    source_type: str
    name: str
    status: str
    collection_id: str | None = None
    config: dict[str, Any] | None = None
    product: str | None = None
    schedule: str = "manual"
    last_crawled_at: str | None = None
    last_indexed_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    archived_at: str | None = None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "KnowledgeSource":
        return _from_row(cls, row)


@dataclass(frozen=True)
class KnowledgeDocument:
    id: str
    workspace_id: str
    source_id: str
    status: str
    parent_url: str | None = None
    title: str | None = None
    chunk_count: int = 0
    char_count: int = 0
    error_message: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    archived_at: str | None = None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "KnowledgeDocument":
        return _from_row(cls, row)


@dataclass(frozen=True)
class CrawlJob:
    id: str
    workspace_id: str
    source_id: str
    status: str
    pages_discovered: int = 0
    pages_ingested: int = 0
    started_at: str | None = None
    completed_at: str | None = None
    error_message: str | None = None
    created_at: str | None = None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "CrawlJob":
        return _from_row(cls, row)


@dataclass(frozen=True)
class CrawlLog:
    id: str
    crawl_job_id: str
    url: str
    status: str
    message: str | None = None
    created_at: str | None = None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "CrawlLog":
        return _from_row(cls, row)


@dataclass(frozen=True)
class DocumentVersion:
    id: str
    document_id: str
    version_number: int
    content_hash: str | None = None
    chunk_count: int = 0
    created_at: str | None = None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "DocumentVersion":
        return _from_row(cls, row)


@dataclass(frozen=True)
class EmbeddingJob:
    id: str
    document_id: str
    status: str
    chunks_embedded: int = 0
    error_message: str | None = None
    created_at: str | None = None
    completed_at: str | None = None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "EmbeddingJob":
        return _from_row(cls, row)


@dataclass(frozen=True)
class QualityReport:
    id: str
    workspace_id: str
    generated_at: str | None = None
    duplicate_chunk_count: int = 0
    broken_url_count: int = 0
    empty_document_count: int = 0
    embedding_failure_count: int = 0
    large_chunk_count: int = 0
    missing_metadata_count: int = 0
    details: dict[str, Any] | None = None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "QualityReport":
        return _from_row(cls, row)

"""Pydantic schemas for the /workspaces/{workspace_id}/knowledge/* surface
(Phase 27). Separate file, same rationale as Phase 26's `schemas_admin.py`
— keeps a large, cohesive request/response set out of `schemas.py`.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class KnowledgeCollectionSchema(BaseModel):
    id: str
    workspace_id: str
    name: str
    description: str | None = None
    created_at: str | None = None


class KnowledgeCollectionCreateRequest(BaseModel):
    name: str = Field(..., min_length=1)
    description: str | None = None


class KnowledgeSourceSchema(BaseModel):
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


class KnowledgeSourceCreateRequest(BaseModel):
    source_type: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    collection_id: str | None = None
    config: dict[str, Any] | None = None
    product: str | None = None
    schedule: str = "manual"


class KnowledgeSourceUpdateRequest(BaseModel):
    name: str | None = None
    collection_id: str | None = None
    config: dict[str, Any] | None = None
    product: str | None = None
    schedule: str | None = None


class KnowledgeDocumentSchema(BaseModel):
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


class CrawlJobSchema(BaseModel):
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


class CrawlLogSchema(BaseModel):
    id: str
    url: str
    status: str
    message: str | None = None
    created_at: str | None = None


class FaqCreateRequest(BaseModel):
    question: str = Field(..., min_length=1)
    answer: str = Field(..., min_length=1)
    collection_id: str | None = None
    product: str | None = None
    category: str | None = None


class DocumentPreviewSchema(BaseModel):
    document: KnowledgeDocumentSchema
    chunk_count: int
    chunks: list[dict[str, Any]]
    embedding_status: str
    metadata: dict[str, Any]


class KnowledgeTestRequest(BaseModel):
    question: str = Field(..., min_length=1)
    product_filter: list[str] | None = None


class KnowledgeTestChunkSchema(BaseModel):
    content: str
    similarity: float
    url: str
    product: str | None = None


class KnowledgeTestResultSchema(BaseModel):
    question: str
    chunks: list[KnowledgeTestChunkSchema]
    sources: list[str]
    confidence: float


class QualityReportSchema(BaseModel):
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


class KnowledgeDashboardSchema(BaseModel):
    total_sources: int
    indexed_sources: int
    pending_sources: int
    failed_sources: int
    total_documents: int
    total_chunks: int
    last_crawl: str | None = None
    last_index: str | None = None

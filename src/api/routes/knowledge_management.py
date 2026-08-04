"""Self-service knowledge management routes (Phase 27) —
`/workspaces/{workspace_id}/knowledge/*`. Every route depends on
`require_workspace_admin(workspace_id)`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from ...services.admin.tenant_repository import AdminWorkspaceRepository
from ...services.auth.auth_service import AuthUser
from ...services.knowledge_management.collection_service import CollectionService
from ...services.knowledge_management.crawl_job_repository import CrawlJobRepository
from ...services.knowledge_management.crawl_log_repository import CrawlLogRepository
from ...services.knowledge_management.crawl_service import CrawlService
from ...services.knowledge_management.document_repository import DocumentRepository
from ...services.knowledge_management.faq_service import FaqService
from ...services.knowledge_management.preview_service import PreviewService
from ...services.knowledge_management.quality_service import QualityService
from ...services.knowledge_management.source_service import SourceService
from ...services.knowledge_management.testing_service import TestingService
from ...services.knowledge_management.upload_service import UploadService
from ..deps import require_workspace_admin
from ..schemas_knowledge import (
    CrawlJobSchema,
    CrawlLogSchema,
    DocumentPreviewSchema,
    FaqCreateRequest,
    KnowledgeCollectionCreateRequest,
    KnowledgeCollectionSchema,
    KnowledgeDashboardSchema,
    KnowledgeDocumentSchema,
    KnowledgeSourceCreateRequest,
    KnowledgeSourceSchema,
    KnowledgeSourceUpdateRequest,
    KnowledgeTestRequest,
    KnowledgeTestResultSchema,
    QualityReportSchema,
)

router = APIRouter()

_collection_service = CollectionService()
_source_service = SourceService()
_document_repository = DocumentRepository()
_crawl_service = CrawlService()
_crawl_job_repository = CrawlJobRepository()
_crawl_log_repository = CrawlLogRepository()
_upload_service = UploadService()
_faq_service = FaqService()
_preview_service = PreviewService()
_quality_service = QualityService()
_testing_service = TestingService()
_workspace_repository = AdminWorkspaceRepository()


def _to_source_schema(source) -> KnowledgeSourceSchema:
    return KnowledgeSourceSchema(
        id=source.id, workspace_id=source.workspace_id, source_type=source.source_type, name=source.name,
        status=source.status, collection_id=source.collection_id, config=source.config, product=source.product,
        schedule=source.schedule, last_crawled_at=source.last_crawled_at, last_indexed_at=source.last_indexed_at,
        created_at=source.created_at,
    )


def _to_document_schema(document) -> KnowledgeDocumentSchema:
    return KnowledgeDocumentSchema(
        id=document.id, workspace_id=document.workspace_id, source_id=document.source_id, status=document.status,
        parent_url=document.parent_url, title=document.title, chunk_count=document.chunk_count,
        char_count=document.char_count, error_message=document.error_message, created_at=document.created_at,
    )


def _get_workspace_or_404(workspace_id: str):
    workspace = _workspace_repository.get_by_id(workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace


def _get_source_or_404(source_id: str, workspace_id: str):
    source = _source_service.get(source_id)
    if source is None or source.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Source not found")
    return source


@router.get("/workspaces/{workspace_id}/knowledge/dashboard", response_model=KnowledgeDashboardSchema)
def get_knowledge_dashboard(
    workspace_id: str, user: AuthUser = Depends(require_workspace_admin)
) -> KnowledgeDashboardSchema:
    _get_workspace_or_404(workspace_id)
    sources = _source_service.list_for_workspace(workspace_id)
    documents = _document_repository.list_for_workspace(workspace_id)

    crawl_times = [s.last_crawled_at for s in sources if s.last_crawled_at]
    index_times = [s.last_indexed_at for s in sources if s.last_indexed_at]

    return KnowledgeDashboardSchema(
        total_sources=len(sources),
        indexed_sources=sum(1 for s in sources if s.status == "ready"),
        pending_sources=sum(1 for s in sources if s.status in ("pending", "processing", "embedding")),
        failed_sources=sum(1 for s in sources if s.status == "failed"),
        total_documents=len(documents),
        total_chunks=sum(d.chunk_count for d in documents),
        last_crawl=max(crawl_times) if crawl_times else None,
        last_index=max(index_times) if index_times else None,
    )


@router.get("/workspaces/{workspace_id}/knowledge/collections", response_model=list[KnowledgeCollectionSchema])
def list_collections(
    workspace_id: str, user: AuthUser = Depends(require_workspace_admin)
) -> list[KnowledgeCollectionSchema]:
    return [
        KnowledgeCollectionSchema(id=c.id, workspace_id=c.workspace_id, name=c.name, description=c.description, created_at=c.created_at)
        for c in _collection_service.list_for_workspace(workspace_id)
    ]


@router.post("/workspaces/{workspace_id}/knowledge/collections", response_model=KnowledgeCollectionSchema)
def create_collection(
    workspace_id: str, request: KnowledgeCollectionCreateRequest, user: AuthUser = Depends(require_workspace_admin)
) -> KnowledgeCollectionSchema:
    _get_workspace_or_404(workspace_id)
    collection = _collection_service.create(workspace_id, request.name, request.description)
    return KnowledgeCollectionSchema(
        id=collection.id, workspace_id=collection.workspace_id, name=collection.name,
        description=collection.description, created_at=collection.created_at,
    )


@router.get("/workspaces/{workspace_id}/knowledge/sources", response_model=list[KnowledgeSourceSchema])
def list_sources(workspace_id: str, user: AuthUser = Depends(require_workspace_admin)) -> list[KnowledgeSourceSchema]:
    return [_to_source_schema(s) for s in _source_service.list_for_workspace(workspace_id)]


@router.post("/workspaces/{workspace_id}/knowledge/sources", response_model=KnowledgeSourceSchema)
def create_source(
    workspace_id: str, request: KnowledgeSourceCreateRequest, user: AuthUser = Depends(require_workspace_admin)
) -> KnowledgeSourceSchema:
    _get_workspace_or_404(workspace_id)
    try:
        source = _source_service.create(
            workspace_id, request.source_type, request.name, request.collection_id,
            request.config, request.product, request.schedule,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_source_schema(source)


@router.patch("/workspaces/{workspace_id}/knowledge/sources/{source_id}", response_model=KnowledgeSourceSchema)
def update_source(
    workspace_id: str, source_id: str, request: KnowledgeSourceUpdateRequest,
    user: AuthUser = Depends(require_workspace_admin),
) -> KnowledgeSourceSchema:
    _get_source_or_404(source_id, workspace_id)
    fields = {k: v for k, v in request.model_dump().items() if v is not None}
    return _to_source_schema(_source_service.update(source_id, **fields))


@router.delete("/workspaces/{workspace_id}/knowledge/sources/{source_id}", response_model=KnowledgeSourceSchema)
def delete_source(
    workspace_id: str, source_id: str, user: AuthUser = Depends(require_workspace_admin)
) -> KnowledgeSourceSchema:
    """Archives the source and removes its chunks from search (see the
    plan's locked decision: archiving deletes documentation_chunks rows,
    no retrieval RPC changes needed)."""
    _get_source_or_404(source_id, workspace_id)
    return _to_source_schema(_source_service.archive(source_id))


@router.post("/workspaces/{workspace_id}/knowledge/sources/{source_id}/pause", response_model=KnowledgeSourceSchema)
def pause_source(
    workspace_id: str, source_id: str, user: AuthUser = Depends(require_workspace_admin)
) -> KnowledgeSourceSchema:
    _get_source_or_404(source_id, workspace_id)
    return _to_source_schema(_source_service.pause(source_id))


@router.post("/workspaces/{workspace_id}/knowledge/sources/{source_id}/resume", response_model=KnowledgeSourceSchema)
def resume_source(
    workspace_id: str, source_id: str, user: AuthUser = Depends(require_workspace_admin)
) -> KnowledgeSourceSchema:
    _get_source_or_404(source_id, workspace_id)
    return _to_source_schema(_source_service.resume(source_id))


@router.post("/workspaces/{workspace_id}/knowledge/sources/{source_id}/recrawl", response_model=CrawlJobSchema)
def recrawl_source(
    workspace_id: str, source_id: str, user: AuthUser = Depends(require_workspace_admin)
) -> CrawlJobSchema:
    _get_source_or_404(source_id, workspace_id)
    try:
        job = _crawl_service.start_crawl(source_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return CrawlJobSchema(
        id=job.id, workspace_id=job.workspace_id, source_id=job.source_id, status=job.status,
        pages_discovered=job.pages_discovered, pages_ingested=job.pages_ingested,
        started_at=job.started_at, completed_at=job.completed_at, error_message=job.error_message,
        created_at=job.created_at,
    )


@router.get(
    "/workspaces/{workspace_id}/knowledge/sources/{source_id}/crawl-history", response_model=list[CrawlJobSchema]
)
def get_crawl_history(
    workspace_id: str, source_id: str, user: AuthUser = Depends(require_workspace_admin)
) -> list[CrawlJobSchema]:
    _get_source_or_404(source_id, workspace_id)
    jobs = _crawl_job_repository.list_for_source(source_id)
    return [
        CrawlJobSchema(
            id=j.id, workspace_id=j.workspace_id, source_id=j.source_id, status=j.status,
            pages_discovered=j.pages_discovered, pages_ingested=j.pages_ingested,
            started_at=j.started_at, completed_at=j.completed_at, error_message=j.error_message,
            created_at=j.created_at,
        )
        for j in jobs
    ]


@router.get(
    "/workspaces/{workspace_id}/knowledge/crawl-jobs/{job_id}/logs", response_model=list[CrawlLogSchema]
)
def get_crawl_job_logs(
    workspace_id: str, job_id: str, user: AuthUser = Depends(require_workspace_admin)
) -> list[CrawlLogSchema]:
    job = _crawl_job_repository.get(job_id)
    if job is None or job.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Crawl job not found")
    logs = _crawl_log_repository.list_for_job(job_id)
    return [CrawlLogSchema(id=l.id, url=l.url, status=l.status, message=l.message, created_at=l.created_at) for l in logs]


@router.post("/workspaces/{workspace_id}/knowledge/sources/{source_id}/uploads", response_model=KnowledgeDocumentSchema)
def upload_to_source(
    workspace_id: str, source_id: str, file: UploadFile = File(...),
    user: AuthUser = Depends(require_workspace_admin),
) -> KnowledgeDocumentSchema:
    _get_source_or_404(source_id, workspace_id)
    content = file.file.read()
    try:
        document = _upload_service.ingest_upload(source_id, file.filename or "upload", content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_document_schema(document)


@router.get("/workspaces/{workspace_id}/knowledge/faqs", response_model=list[KnowledgeSourceSchema])
def list_faqs(workspace_id: str, user: AuthUser = Depends(require_workspace_admin)) -> list[KnowledgeSourceSchema]:
    return [
        _to_source_schema(s) for s in _source_service.list_for_workspace(workspace_id) if s.source_type == "faq"
    ]


@router.post("/workspaces/{workspace_id}/knowledge/faqs", response_model=KnowledgeDocumentSchema)
def create_faq(
    workspace_id: str, request: FaqCreateRequest, user: AuthUser = Depends(require_workspace_admin)
) -> KnowledgeDocumentSchema:
    _get_workspace_or_404(workspace_id)
    document = _faq_service.create_faq(
        workspace_id, request.question, request.answer, request.collection_id, request.product, request.category
    )
    return _to_document_schema(document)


@router.get(
    "/workspaces/{workspace_id}/knowledge/documents/{document_id}/preview", response_model=DocumentPreviewSchema
)
def get_document_preview(
    workspace_id: str, document_id: str, user: AuthUser = Depends(require_workspace_admin)
) -> DocumentPreviewSchema:
    document = _document_repository.get(document_id)
    if document is None or document.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Document not found")
    preview = _preview_service.get_document_preview(document_id)
    return DocumentPreviewSchema(
        document=_to_document_schema(preview["document"]),
        chunk_count=preview["chunk_count"],
        chunks=preview["chunks"],
        embedding_status=preview["embedding_status"],
        metadata=preview["metadata"],
    )


@router.post("/workspaces/{workspace_id}/knowledge/test", response_model=KnowledgeTestResultSchema)
def test_knowledge(
    workspace_id: str, request: KnowledgeTestRequest, user: AuthUser = Depends(require_workspace_admin)
) -> KnowledgeTestResultSchema:
    _get_workspace_or_404(workspace_id)
    result = _testing_service.test_question(request.question, workspace_id, request.product_filter)
    return KnowledgeTestResultSchema(**result)


@router.get("/workspaces/{workspace_id}/knowledge/quality", response_model=QualityReportSchema | None)
def get_latest_quality_report(
    workspace_id: str, user: AuthUser = Depends(require_workspace_admin)
) -> QualityReportSchema | None:
    report = _quality_service.latest_report(workspace_id)
    if report is None:
        return None
    return QualityReportSchema(
        id=report.id, workspace_id=report.workspace_id, generated_at=report.generated_at,
        duplicate_chunk_count=report.duplicate_chunk_count, broken_url_count=report.broken_url_count,
        empty_document_count=report.empty_document_count, embedding_failure_count=report.embedding_failure_count,
        large_chunk_count=report.large_chunk_count, missing_metadata_count=report.missing_metadata_count,
        details=report.details,
    )


@router.post("/workspaces/{workspace_id}/knowledge/quality/scan", response_model=QualityReportSchema)
def run_quality_scan(workspace_id: str, user: AuthUser = Depends(require_workspace_admin)) -> QualityReportSchema:
    _get_workspace_or_404(workspace_id)
    report = _quality_service.run_quality_scan(workspace_id)
    return QualityReportSchema(
        id=report.id, workspace_id=report.workspace_id, generated_at=report.generated_at,
        duplicate_chunk_count=report.duplicate_chunk_count, broken_url_count=report.broken_url_count,
        empty_document_count=report.empty_document_count, embedding_failure_count=report.embedding_failure_count,
        large_chunk_count=report.large_chunk_count, missing_metadata_count=report.missing_metadata_count,
        details=report.details,
    )


@router.get("/workspaces/{workspace_id}/knowledge/jobs", response_model=list[CrawlJobSchema])
def list_jobs(workspace_id: str, user: AuthUser = Depends(require_workspace_admin)) -> list[CrawlJobSchema]:
    _get_workspace_or_404(workspace_id)
    jobs = []
    for source in _source_service.list_for_workspace(workspace_id):
        jobs.extend(_crawl_job_repository.list_for_source(source.id))
    jobs.sort(key=lambda j: j.created_at or "", reverse=True)
    return [
        CrawlJobSchema(
            id=j.id, workspace_id=j.workspace_id, source_id=j.source_id, status=j.status,
            pages_discovered=j.pages_discovered, pages_ingested=j.pages_ingested,
            started_at=j.started_at, completed_at=j.completed_at, error_message=j.error_message,
            created_at=j.created_at,
        )
        for j in jobs
    ]

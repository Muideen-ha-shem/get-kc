export type SourceType = 'website' | 'pdf' | 'docx' | 'pptx' | 'markdown' | 'txt' | 'faq';
export type SourceStatus = 'pending' | 'processing' | 'embedding' | 'ready' | 'failed' | 'archived' | 'paused';
export type Schedule = 'manual' | 'daily' | 'weekly' | 'monthly';

export type KnowledgeCollection = {
  id: string;
  workspace_id: string;
  name: string;
  description: string | null;
  created_at: string | null;
};

export type KnowledgeSource = {
  id: string;
  workspace_id: string;
  source_type: SourceType;
  name: string;
  status: SourceStatus;
  collection_id: string | null;
  config: Record<string, unknown> | null;
  product: string | null;
  schedule: Schedule;
  last_crawled_at: string | null;
  last_indexed_at: string | null;
  created_at: string | null;
};

export type KnowledgeDocument = {
  id: string;
  workspace_id: string;
  source_id: string;
  status: SourceStatus;
  parent_url: string | null;
  title: string | null;
  chunk_count: number;
  char_count: number;
  error_message: string | null;
  created_at: string | null;
};

export type CrawlJob = {
  id: string;
  workspace_id: string;
  source_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  pages_discovered: number;
  pages_ingested: number;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  created_at: string | null;
};

export type KnowledgeDashboard = {
  total_sources: number;
  indexed_sources: number;
  pending_sources: number;
  failed_sources: number;
  total_documents: number;
  total_chunks: number;
  last_crawl: string | null;
  last_index: string | null;
};

export type KnowledgeTestChunk = {
  content: string;
  similarity: number;
  url: string;
  product: string | null;
};

export type KnowledgeTestResult = {
  question: string;
  chunks: KnowledgeTestChunk[];
  sources: string[];
  confidence: number;
};

export type QualityReport = {
  id: string;
  workspace_id: string;
  generated_at: string | null;
  duplicate_chunk_count: number;
  broken_url_count: number;
  empty_document_count: number;
  embedding_failure_count: number;
  large_chunk_count: number;
  missing_metadata_count: number;
};

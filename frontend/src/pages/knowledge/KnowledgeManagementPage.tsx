import { FormEvent, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  AlertOctagon,
  CheckCircle2,
  Clock,
  Copy,
  Database,
  FileText,
  FileX,
  Layers,
  Maximize2,
  RefreshCw,
  Search,
  Tag,
  Unlink,
  XCircle,
} from 'lucide-react';
import { apiJson, apiUpload } from '../../lib/apiClient';
import { MetricCard } from '../../components/MetricCard';
import { Select } from '../../components/Select';
import { StatusBadge } from '../../components/StatusBadge';
import { CARD, INPUT_CLASS, PRIMARY_BUTTON, SECONDARY_BUTTON } from '../../lib/uiClassNames';
import type {
  CrawlJob,
  KnowledgeCollection,
  KnowledgeDashboard,
  KnowledgeDocument,
  KnowledgeSource,
  KnowledgeTestResult,
  QualityReport,
  Schedule,
  SourceType,
} from './knowledgeTypes';

type Tab = 'dashboard' | 'sources' | 'uploads' | 'faq' | 'collections' | 'testing' | 'quality' | 'jobs';
const TABS: Tab[] = ['dashboard', 'sources', 'uploads', 'faq', 'collections', 'testing', 'quality', 'jobs'];
const SOURCE_TYPES: SourceType[] = ['website', 'pdf', 'docx', 'pptx', 'markdown', 'txt', 'faq'];
const SCHEDULES: Schedule[] = ['manual', 'daily', 'weekly', 'monthly'];

function DashboardTab({ workspaceId }: { workspaceId: string }) {
  const [stats, setStats] = useState<KnowledgeDashboard | null>(null);

  useEffect(() => {
    apiJson<KnowledgeDashboard>(`/workspaces/${workspaceId}/knowledge/dashboard`).then(setStats).catch(() => {});
  }, [workspaceId]);

  if (!stats) return <p className="text-sm text-ink/40">Loading…</p>;

  return (
    <div className="grid grid-cols-4 gap-4">
      <MetricCard label="Total Sources" value={stats.total_sources} icon={Database} tone="ink" />
      <MetricCard label="Indexed Sources" value={stats.indexed_sources} icon={CheckCircle2} tone="green" />
      <MetricCard label="Pending Sources" value={stats.pending_sources} icon={Clock} tone="gold" />
      <MetricCard label="Failed Sources" value={stats.failed_sources} icon={XCircle} tone="red" />
      <MetricCard label="Total Documents" value={stats.total_documents} icon={FileText} tone="ink" />
      <MetricCard label="Total Chunks" value={stats.total_chunks} icon={Layers} tone="ink" />
      <MetricCard
        label="Last Crawl"
        value={stats.last_crawl?.slice(0, 19).replace('T', ' ') ?? '—'}
        icon={RefreshCw}
        tone="gold"
        small
      />
      <MetricCard
        label="Last Index"
        value={stats.last_index?.slice(0, 19).replace('T', ' ') ?? '—'}
        icon={Search}
        tone="gold"
        small
      />
    </div>
  );
}

function SourcesTab({ workspaceId, collections }: { workspaceId: string; collections: KnowledgeCollection[] }) {
  const [sources, setSources] = useState<KnowledgeSource[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [sourceType, setSourceType] = useState<SourceType>('website');
  const [name, setName] = useState('');
  const [url, setUrl] = useState('');
  const [maxDepth, setMaxDepth] = useState(2);
  const [includePaths, setIncludePaths] = useState('');
  const [excludePaths, setExcludePaths] = useState('');
  const [collectionId, setCollectionId] = useState('');
  const [product, setProduct] = useState('');
  const [schedule, setSchedule] = useState<Schedule>('manual');

  function load() {
    apiJson<KnowledgeSource[]>(`/workspaces/${workspaceId}/knowledge/sources`).then(setSources).catch(() => {});
  }

  useEffect(load, [workspaceId]);

  async function createSource(event: FormEvent) {
    event.preventDefault();
    const config =
      sourceType === 'website'
        ? {
            url,
            max_depth: maxDepth,
            include_paths: includePaths ? includePaths.split(',').map((p) => p.trim()) : undefined,
            exclude_paths: excludePaths ? excludePaths.split(',').map((p) => p.trim()) : undefined,
          }
        : null;
    await apiJson(`/workspaces/${workspaceId}/knowledge/sources`, {
      method: 'POST',
      body: JSON.stringify({
        source_type: sourceType, name, collection_id: collectionId || null,
        config, product: product || null, schedule,
      }),
    });
    setShowCreate(false);
    setName('');
    setUrl('');
    load();
  }

  async function recrawl(sourceId: string) {
    await apiJson(`/workspaces/${workspaceId}/knowledge/sources/${sourceId}/recrawl`, { method: 'POST' });
    load();
  }

  async function pause(sourceId: string) {
    await apiJson(`/workspaces/${workspaceId}/knowledge/sources/${sourceId}/pause`, { method: 'POST' });
    load();
  }

  async function resume(sourceId: string) {
    await apiJson(`/workspaces/${workspaceId}/knowledge/sources/${sourceId}/resume`, { method: 'POST' });
    load();
  }

  async function remove(sourceId: string) {
    if (!confirm('Archive this source? Its chunks will be removed from search.')) return;
    await apiJson(`/workspaces/${workspaceId}/knowledge/sources/${sourceId}`, { method: 'DELETE' });
    load();
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-3">
        <h2 className="text-sm font-semibold text-ink/50 uppercase">Sources</h2>
        <button onClick={() => setShowCreate((v) => !v)} className={PRIMARY_BUTTON}>
          + New Source
        </button>
      </div>

      {showCreate && (
        <form onSubmit={createSource} className={`${CARD} p-4 mb-4 flex flex-col gap-3 max-w-lg`}>
          <label className="text-sm text-ink">
            Type
            <Select value={sourceType} onChange={(e) => setSourceType(e.target.value as SourceType)} className="mt-1">
              {SOURCE_TYPES.filter((t) => t !== 'faq').map((t) => <option key={t} value={t}>{t}</option>)}
            </Select>
          </label>
          <label className="text-sm text-ink">
            Name
            <input value={name} onChange={(e) => setName(e.target.value)} required className={INPUT_CLASS} />
          </label>
          {sourceType === 'website' && (
            <>
              <label className="text-sm text-ink">
                Website URL
                <input value={url} onChange={(e) => setUrl(e.target.value)} required className={INPUT_CLASS} />
              </label>
              <label className="text-sm text-ink">
                Crawl depth
                <input type="number" min={1} max={5} value={maxDepth} onChange={(e) => setMaxDepth(Number(e.target.value))} className={INPUT_CLASS} />
              </label>
              <label className="text-sm text-ink">
                Include paths (comma-separated, optional)
                <input value={includePaths} onChange={(e) => setIncludePaths(e.target.value)} className={INPUT_CLASS} />
              </label>
              <label className="text-sm text-ink">
                Exclude paths (comma-separated, optional)
                <input value={excludePaths} onChange={(e) => setExcludePaths(e.target.value)} className={INPUT_CLASS} />
              </label>
              <label className="text-sm text-ink">
                Schedule
                <Select value={schedule} onChange={(e) => setSchedule(e.target.value as Schedule)} className="mt-1">
                  {SCHEDULES.map((s) => <option key={s} value={s}>{s}</option>)}
                </Select>
              </label>
            </>
          )}
          <label className="text-sm text-ink">
            Collection (optional)
            <Select value={collectionId} onChange={(e) => setCollectionId(e.target.value)} className="mt-1">
              <option value="">None</option>
              {collections.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </Select>
          </label>
          <label className="text-sm text-ink">
            Product tag (optional, e.g. SPIDIFY)
            <input value={product} onChange={(e) => setProduct(e.target.value)} className={INPUT_CLASS} />
          </label>
          <button type="submit" className={`${PRIMARY_BUTTON} self-start`}>Create</button>
        </form>
      )}

      <div className={`${CARD} divide-y divide-ink/10`}>
        {sources.map((s) => (
          <div key={s.id} className="flex items-center justify-between px-4 py-3">
            <div>
              <p className="text-sm font-medium text-ink">{s.name} <span className="text-xs text-ink/40">· {s.source_type} · {s.status}</span></p>
              <p className="text-xs text-ink/50">{s.schedule} {s.last_crawled_at ? `· last crawled ${s.last_crawled_at.slice(0, 19).replace('T', ' ')}` : ''}</p>
            </div>
            <div className="flex gap-2">
              {s.source_type === 'website' && (
                <button onClick={() => recrawl(s.id)} className={SECONDARY_BUTTON}>Recrawl</button>
              )}
              {s.status === 'paused' ? (
                <button onClick={() => resume(s.id)} className="rounded-full bg-green-50 text-green-700 border border-green-200 px-3 py-1 text-xs transition hover:bg-green-100">Resume</button>
              ) : (
                <button onClick={() => pause(s.id)} className={SECONDARY_BUTTON}>Pause</button>
              )}
              <button onClick={() => remove(s.id)} className="rounded-full bg-red-50 text-red-700 border border-red-200 px-3 py-1 text-xs transition hover:bg-red-100">Archive</button>
            </div>
          </div>
        ))}
        {sources.length === 0 && <p className="px-4 py-3 text-sm text-ink/40">No sources yet.</p>}
      </div>
    </div>
  );
}

function UploadsTab({ workspaceId }: { workspaceId: string }) {
  const [sources, setSources] = useState<KnowledgeSource[]>([]);
  const [sourceId, setSourceId] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<KnowledgeDocument | null>(null);

  useEffect(() => {
    apiJson<KnowledgeSource[]>(`/workspaces/${workspaceId}/knowledge/sources`)
      .then((all) => setSources(all.filter((s) => s.source_type !== 'website' && s.source_type !== 'faq')))
      .catch(() => {});
  }, [workspaceId]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!sourceId || !file) return;
    const formData = new FormData();
    formData.append('file', file);
    const document = await apiUpload<KnowledgeDocument>(
      `/workspaces/${workspaceId}/knowledge/sources/${sourceId}/uploads`, formData,
    );
    setResult(document);
  }

  return (
    <div className="max-w-md">
      <p className="text-sm text-ink/60 mb-3">
        Upload a PDF, DOCX, PPTX, Markdown, or TXT file to an existing upload-type source. Only the extracted text
        is kept — the original file is discarded after ingestion.
      </p>
      <form onSubmit={submit} className={`${CARD} p-4 flex flex-col gap-3`}>
        <label className="text-sm text-ink">
          Source
          <Select value={sourceId} onChange={(e) => setSourceId(e.target.value)} required className="mt-1">
            <option value="">Select a source…</option>
            {sources.map((s) => <option key={s.id} value={s.id}>{s.name} ({s.source_type})</option>)}
          </Select>
        </label>
        <input type="file" onChange={(e) => setFile(e.target.files?.[0] ?? null)} required className="text-sm text-ink" />
        <button type="submit" className={`${PRIMARY_BUTTON} self-start`}>Upload</button>
      </form>
      {result && (
        <div className="mt-4 text-sm bg-green-50 border border-green-200 rounded-2xl p-3">
          <p className="font-medium text-ink">{result.title}</p>
          <p className="text-xs text-ink/60">Status: {result.status} · {result.chunk_count} chunks</p>
        </div>
      )}
    </div>
  );
}

function FaqTab({ workspaceId, collections }: { workspaceId: string; collections: KnowledgeCollection[] }) {
  const [faqs, setFaqs] = useState<KnowledgeSource[]>([]);
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');
  const [collectionId, setCollectionId] = useState('');
  const [category, setCategory] = useState('');

  function load() {
    apiJson<KnowledgeSource[]>(`/workspaces/${workspaceId}/knowledge/faqs`).then(setFaqs).catch(() => {});
  }

  useEffect(load, [workspaceId]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    await apiJson(`/workspaces/${workspaceId}/knowledge/faqs`, {
      method: 'POST',
      body: JSON.stringify({ question, answer, collection_id: collectionId || null, category: category || null }),
    });
    setQuestion('');
    setAnswer('');
    load();
  }

  return (
    <div className="max-w-lg">
      <form onSubmit={submit} className={`${CARD} p-4 flex flex-col gap-3 mb-4`}>
        <label className="text-sm text-ink">
          Question
          <input value={question} onChange={(e) => setQuestion(e.target.value)} required className={INPUT_CLASS} />
        </label>
        <label className="text-sm text-ink">
          Answer
          <textarea value={answer} onChange={(e) => setAnswer(e.target.value)} required rows={3} className={INPUT_CLASS} />
        </label>
        <label className="text-sm text-ink">
          Category (optional)
          <input value={category} onChange={(e) => setCategory(e.target.value)} className={INPUT_CLASS} />
        </label>
        <label className="text-sm text-ink">
          Collection (optional)
          <Select value={collectionId} onChange={(e) => setCollectionId(e.target.value)} className="mt-1">
            <option value="">None</option>
            {collections.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </Select>
        </label>
        <button type="submit" className={`${PRIMARY_BUTTON} self-start`}>Add FAQ</button>
      </form>

      <div className={`${CARD} divide-y divide-ink/10`}>
        {faqs.map((f) => (
          <div key={f.id} className="px-4 py-3">
            <p className="text-sm font-medium text-ink">{f.name}</p>
            <p className="text-xs text-ink/50">{f.status}</p>
          </div>
        ))}
        {faqs.length === 0 && <p className="px-4 py-3 text-sm text-ink/40">No FAQs yet.</p>}
      </div>
    </div>
  );
}

function CollectionsTab({
  workspaceId, collections, onChanged,
}: { workspaceId: string; collections: KnowledgeCollection[]; onChanged: () => void }) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');

  async function submit(event: FormEvent) {
    event.preventDefault();
    await apiJson(`/workspaces/${workspaceId}/knowledge/collections`, {
      method: 'POST',
      body: JSON.stringify({ name, description: description || null }),
    });
    setName('');
    setDescription('');
    onChanged();
  }

  return (
    <div className="max-w-md">
      <form onSubmit={submit} className={`${CARD} p-4 flex flex-col gap-3 mb-4`}>
        <label className="text-sm text-ink">
          Name
          <input value={name} onChange={(e) => setName(e.target.value)} required className={INPUT_CLASS} placeholder="Support, Sales, Finance…" />
        </label>
        <label className="text-sm text-ink">
          Description (optional)
          <input value={description} onChange={(e) => setDescription(e.target.value)} className={INPUT_CLASS} />
        </label>
        <button type="submit" className={`${PRIMARY_BUTTON} self-start`}>Create Collection</button>
      </form>
      <div className={`${CARD} divide-y divide-ink/10`}>
        {collections.map((c) => (
          <div key={c.id} className="px-4 py-3">
            <p className="text-sm font-medium text-ink">{c.name}</p>
            {c.description && <p className="text-xs text-ink/50">{c.description}</p>}
          </div>
        ))}
        {collections.length === 0 && <p className="px-4 py-3 text-sm text-ink/40">No collections yet.</p>}
      </div>
    </div>
  );
}

function TestingTab({ workspaceId }: { workspaceId: string }) {
  const [question, setQuestion] = useState('');
  const [result, setResult] = useState<KnowledgeTestResult | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const response = await apiJson<KnowledgeTestResult>(`/workspaces/${workspaceId}/knowledge/test`, {
      method: 'POST',
      body: JSON.stringify({ question }),
    });
    setResult(response);
  }

  return (
    <div className="max-w-2xl">
      <p className="text-sm text-ink/60 mb-3">Reuses the exact retrieval pipeline the AI itself uses — this is what the customer would get back.</p>
      <form onSubmit={submit} className="flex gap-2 mb-4">
        <input value={question} onChange={(e) => setQuestion(e.target.value)} required className="flex-1 border border-ink/10 rounded-xl px-3 py-2 text-sm bg-paper text-ink outline-none focus:border-gold-400" placeholder="Ask a question…" />
        <button type="submit" className={PRIMARY_BUTTON}>Test</button>
      </form>

      {result && (
        <div className={`${CARD} p-4`}>
          <p className="text-sm mb-2 text-ink">Confidence: <strong>{(result.confidence * 100).toFixed(0)}%</strong></p>
          <div className="flex flex-col gap-3">
            {result.chunks.map((chunk, i) => (
              <div key={i} className="border border-ink/10 rounded-xl p-3">
                <p className="text-xs text-ink/50 mb-1">
                  Similarity {(chunk.similarity * 100).toFixed(0)}% {chunk.product ? `· ${chunk.product}` : ''}
                </p>
                <p className="text-sm text-ink">{chunk.content}</p>
                <p className="text-xs text-gold-700 mt-1">{chunk.url}</p>
              </div>
            ))}
            {result.chunks.length === 0 && <p className="text-sm text-ink/40">No chunks retrieved.</p>}
          </div>
        </div>
      )}
    </div>
  );
}

function QualityTab({ workspaceId }: { workspaceId: string }) {
  const [report, setReport] = useState<QualityReport | null>(null);

  function load() {
    apiJson<QualityReport | null>(`/workspaces/${workspaceId}/knowledge/quality`).then(setReport).catch(() => {});
  }

  useEffect(load, [workspaceId]);

  async function runScan() {
    const fresh = await apiJson<QualityReport>(`/workspaces/${workspaceId}/knowledge/quality/scan`, { method: 'POST' });
    setReport(fresh);
  }

  return (
    <div className="max-w-2xl">
      <button onClick={runScan} className={`${PRIMARY_BUTTON} mb-4`}>Run Quality Scan</button>
      {report ? (
        <div className="grid grid-cols-3 gap-4">
          {[
            ['Duplicate Chunks', report.duplicate_chunk_count, Copy] as const,
            ['Broken Sources', report.broken_url_count, Unlink] as const,
            ['Empty Documents', report.empty_document_count, FileX] as const,
            ['Embedding Failures', report.embedding_failure_count, AlertOctagon] as const,
            ['Large Chunks', report.large_chunk_count, Maximize2] as const,
            ['Missing Metadata', report.missing_metadata_count, Tag] as const,
          ].map(([label, value, icon]) => (
            <MetricCard
              key={label}
              label={label}
              value={value}
              icon={icon}
              tone={value > 0 ? 'red' : 'green'}
            />
          ))}
        </div>
      ) : (
        <p className="text-sm text-ink/40">No quality report yet — run a scan.</p>
      )}
    </div>
  );
}

function JobsTab({ workspaceId }: { workspaceId: string }) {
  const [jobs, setJobs] = useState<CrawlJob[]>([]);

  useEffect(() => {
    apiJson<CrawlJob[]>(`/workspaces/${workspaceId}/knowledge/jobs`).then(setJobs).catch(() => {});
  }, [workspaceId]);

  return (
    <table className={`w-full ${CARD} text-sm`}>
      <thead>
        <tr className="text-left text-ink/50 border-b border-ink/10">
          <th className="px-4 py-2 font-medium">Status</th>
          <th className="px-4 py-2 font-medium">Pages discovered</th>
          <th className="px-4 py-2 font-medium">Pages ingested</th>
          <th className="px-4 py-2 font-medium">Started</th>
        </tr>
      </thead>
      <tbody>
        {jobs.map((j) => (
          <tr key={j.id} className="border-b border-ink/10 last:border-0 text-ink">
            <td className="px-4 py-2">{j.status}</td>
            <td className="px-4 py-2">{j.pages_discovered}</td>
            <td className="px-4 py-2">{j.pages_ingested}</td>
            <td className="px-4 py-2 text-ink/50">{j.started_at?.slice(0, 19).replace('T', ' ') ?? '—'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function KnowledgeManagementContent({ workspaceId }: { workspaceId: string }) {
  const [tab, setTab] = useState<Tab>('dashboard');
  const [collections, setCollections] = useState<KnowledgeCollection[]>([]);
  const [forbidden, setForbidden] = useState(false);

  function loadCollections() {
    apiJson<KnowledgeCollection[]>(`/workspaces/${workspaceId}/knowledge/collections`)
      .then(setCollections)
      .catch(() => {});
  }

  useEffect(() => {
    apiJson(`/workspaces/${workspaceId}/knowledge/dashboard`).catch(() => setForbidden(true));
    loadCollections();
  }, [workspaceId]);

  if (forbidden) {
    return (
      <div className="min-h-screen bg-paper p-8 text-center">
        <p className="text-lg font-display text-ink">You don't have admin access to this workspace's knowledge base.</p>
        <Link to="/admin" className="text-gold-700 underline hover:text-gold-600">Back to Admin</Link>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-paper p-6">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-display font-semibold text-ink">Knowledge Management</h1>
        <Link to={`/admin/workspaces/${workspaceId}`} className="text-sm text-gold-700 underline hover:text-gold-600">
          Back to workspace
        </Link>
      </div>

      <div className="flex gap-2 mb-6 border-b border-ink/10 flex-wrap">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-3 py-2 text-sm capitalize transition ${
              tab === t ? 'border-b-2 border-gold-500 text-ink font-medium' : 'text-ink/50 hover:text-ink'
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === 'dashboard' && <DashboardTab workspaceId={workspaceId} />}
      {tab === 'sources' && <SourcesTab workspaceId={workspaceId} collections={collections} />}
      {tab === 'uploads' && <UploadsTab workspaceId={workspaceId} />}
      {tab === 'faq' && <FaqTab workspaceId={workspaceId} collections={collections} />}
      {tab === 'collections' && <CollectionsTab workspaceId={workspaceId} collections={collections} onChanged={loadCollections} />}
      {tab === 'testing' && <TestingTab workspaceId={workspaceId} />}
      {tab === 'quality' && <QualityTab workspaceId={workspaceId} />}
      {tab === 'jobs' && <JobsTab workspaceId={workspaceId} />}
    </div>
  );
}

export function KnowledgeManagementPage() {
  const { workspaceId } = useParams<{ workspaceId: string }>();
  if (!workspaceId) return null;
  return <KnowledgeManagementContent workspaceId={workspaceId} />;
}

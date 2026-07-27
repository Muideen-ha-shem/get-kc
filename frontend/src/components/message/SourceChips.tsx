import { Globe } from 'lucide-react';

type ParsedSource = { url: string; domain: string; title: string };

/** Turns a bare page path into a human page title without any per-product
 * knowledge — "/developers/api" -> "Api", "/" -> "Home Page". Generic for
 * any future Ha-Shem solution site. */
function titleFromPath(pathname: string): string {
  const segments = pathname.split('/').filter(Boolean);
  if (!segments.length) return 'Home Page';
  const last = segments[segments.length - 1].replace(/[-_]/g, ' ').replace(/\.\w+$/, '');
  const words = last.split(' ').filter(Boolean);
  const label = words.map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
  return /page$/i.test(label) ? label : `${label} Page`;
}

function parseSource(raw: string): ParsedSource | null {
  try {
    const url = new URL(raw);
    return { url: raw, domain: url.hostname.replace(/^www\./, ''), title: titleFromPath(url.pathname) };
  } catch {
    return null;
  }
}

export function SourceChips({ sources }: { sources: string[] }) {
  const parsed = sources.map(parseSource).filter((s): s is ParsedSource => s !== null);
  if (!parsed.length) return null;

  return (
    <div className="mt-3 border-t border-ink/10 pt-3">
      <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.24em] text-ink/40">Sources</p>
      <div className="flex flex-wrap gap-2">
        {parsed.map((source) => (
          <a
            key={source.url}
            href={source.url}
            target="_blank"
            rel="noreferrer"
            className="group flex items-center gap-2 rounded-xl border border-ink/10 bg-paper px-2.5 py-1.5 transition hover:border-gold-400 hover:bg-gold-50"
          >
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-white text-ink/50 ring-1 ring-ink/10 transition group-hover:text-gold-600 group-hover:ring-gold-300">
              <Globe size={12} />
            </span>
            <span className="leading-tight">
              <span className="block text-[11px] font-semibold text-ink/80 group-hover:text-gold-800">
                {source.domain}
              </span>
              <span className="block text-[10px] text-ink/45">{source.title}</span>
            </span>
          </a>
        ))}
      </div>
    </div>
  );
}

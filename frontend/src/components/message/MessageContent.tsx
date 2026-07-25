import { motion } from 'framer-motion';
import {
  BadgeCheck,
  Boxes,
  CheckCircle2,
  Cloud,
  Cpu,
  FileCheck2,
  Gauge,
  Headphones,
  MessagesSquare,
  Plug,
  ShieldCheck,
  Sparkles,
  Star,
  Target,
  Zap,
} from 'lucide-react';
import type { ComponentType } from 'react';
import { detectProductHeader } from '../../lib/detectProduct';
import {
  type FeatureItem,
  type MessageBlock,
  type StepItem,
  parseMessageContent,
  tokenizeInline,
} from '../../lib/parseMessage';
import { solutions } from '../../solutions';

// Generic keyword -> icon lookup for feature cards. Purely heuristic on the
// feature title text, so it works for any future solution's feature set
// without hardcoding a product name anywhere.
const FEATURE_ICON_RULES: [RegExp, ComponentType<{ size?: number; className?: string }>][] = [
  [/secur|complian|risk|kyc|verif/i, ShieldCheck],
  [/ai|smart|intelligent|adaptive/i, Sparkles],
  [/interview|chat|convers|message/i, MessagesSquare],
  [/score|rank|gauge|analy/i, Gauge],
  [/integrat|api|sdk|plug/i, Plug],
  [/support|help|sla|service/i, Headphones],
  [/speed|fast|instant|real-time|realtime/i, Zap],
  [/audit|report|document|explain/i, FileCheck2],
  [/cloud|infrastructure|hosting/i, Cloud],
  [/target|match|precision/i, Target],
  [/platform|system|engine/i, Cpu],
  [/catalog|solution|workflow/i, Boxes],
];

function pickFeatureIcon(title: string) {
  const rule = FEATURE_ICON_RULES.find(([regex]) => regex.test(title));
  return rule ? rule[1] : BadgeCheck;
}

function renderInlineText(text: string, keyPrefix: string) {
  return tokenizeInline(text).map((token, index) => {
    const key = `${keyPrefix}-${index}`;
    switch (token.kind) {
      case 'bold':
        return (
          <strong key={key} className="font-semibold text-ink">
            {token.value}
          </strong>
        );
      case 'citation':
        return (
          <sup key={key} className="ml-0.5 text-[10px] font-medium text-gold-600">
            {token.value}
          </sup>
        );
      case 'stat':
        return (
          <span
            key={key}
            className="mx-0.5 inline-flex items-center rounded-md bg-gold-50 px-1.5 py-0.5 text-[0.92em] font-semibold text-gold-700 ring-1 ring-gold-200"
          >
            {token.value}
          </span>
        );
      default:
        return <span key={key}>{token.value}</span>;
    }
  });
}

const BLOCK_ANIMATION = {
  initial: { opacity: 0, y: 10 },
  animate: { opacity: 1, y: 0 },
};

function Heading({ text }: { text: string }) {
  return (
    <h4 className="mb-1.5 mt-4 text-[13px] font-semibold uppercase tracking-[0.14em] text-gold-700 first:mt-0">
      {text}
    </h4>
  );
}

function Paragraph({ text }: { text: string }) {
  return <p className="leading-7 text-ink/85">{renderInlineText(text, 'p')}</p>;
}

function StatsRow({ items }: { items: string[] }) {
  return (
    <div className="flex flex-wrap gap-2 py-1">
      {items.map((item, index) => {
        const match = item.match(/^(\S+)\s*(.*)$/);
        const value = match ? match[1] : item;
        const label = match ? match[2] : '';
        return (
          <div
            key={`${item}-${index}`}
            className="flex flex-col items-center rounded-xl border border-gold-200 bg-gold-50 px-3 py-2 text-center"
          >
            <span className="text-sm font-bold text-gold-700">{value}</span>
            {label ? <span className="text-[10px] font-medium uppercase tracking-wide text-gold-600/80">{label}</span> : null}
          </div>
        );
      })}
    </div>
  );
}

function FeatureCards({ items }: { items: FeatureItem[] }) {
  return (
    <div className="grid gap-2.5 sm:grid-cols-2">
      {items.map((item, index) => {
        const Icon = pickFeatureIcon(item.title);
        return (
          <div key={`${item.title}-${index}`} className="rounded-xl border border-ink/10 bg-white p-3 shadow-sm">
            <div className="flex items-center gap-2">
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-gold-50 text-gold-700">
                <Icon size={14} />
              </span>
              <p className="text-[13px] font-semibold text-ink">{item.title}</p>
            </div>
            {item.body ? <p className="mt-1.5 text-[13px] leading-6 text-ink/65">{renderInlineText(item.body, `fb-${index}`)}</p> : null}
          </div>
        );
      })}
    </div>
  );
}

function Checklist({ items }: { items: string[] }) {
  return (
    <div className="space-y-1.5">
      {items.map((item, index) => (
        <div key={`${item}-${index}`} className="flex items-start gap-2 rounded-lg border border-ink/10 bg-white px-3 py-2">
          <CheckCircle2 size={15} className="mt-0.5 shrink-0 text-emerald-500" />
          <span className="text-[13px] leading-6 text-ink/80">{renderInlineText(item, `cl-${index}`)}</span>
        </div>
      ))}
    </div>
  );
}

function StepsTimeline({ items }: { items: StepItem[] }) {
  return (
    <div className="relative space-y-4 py-1 pl-1">
      {items.map((item, index) => (
        <div key={`${item.title}-${index}`} className="relative flex gap-3">
          <div className="flex flex-col items-center">
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-ink text-[11px] font-bold text-paper">
              {index + 1}
            </span>
            {index < items.length - 1 ? <span className="mt-1 w-px flex-1 bg-ink/15" /> : null}
          </div>
          <div className="pb-2">
            <p className="text-[13px] font-semibold text-ink">{renderInlineText(item.title, `st-${index}`)}</p>
            {item.body ? <p className="mt-0.5 text-[13px] leading-6 text-ink/65">{renderInlineText(item.body, `sb-${index}`)}</p> : null}
          </div>
        </div>
      ))}
    </div>
  );
}

function PricingCards({
  plans,
}: {
  plans: { name: string; price?: string; rows: { label: string; value: string }[] }[];
}) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {plans.map((plan, index) => (
        <div key={`${plan.name}-${index}`} className="flex flex-col rounded-xl border border-ink/10 bg-white p-4 shadow-sm">
          <p className="text-[13px] font-semibold uppercase tracking-wide text-ink/50">{plan.name}</p>
          {plan.price ? <p className="mt-1 text-lg font-bold text-ink">{plan.price}</p> : null}
          <div className="mt-2.5 space-y-1.5">
            {plan.rows.map((row, rowIndex) => (
              <div key={`${row.label}-${rowIndex}`} className="flex items-start gap-1.5 text-[12.5px] text-ink/75">
                <CheckCircle2 size={13} className="mt-0.5 shrink-0 text-emerald-500" />
                <span>
                  {row.value}
                  {row.label ? <span className="text-ink/40"> — {row.label}</span> : null}
                </span>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function DataTable({ headers, rows }: { headers: string[]; rows: string[][] }) {
  return (
    <>
      {/* md+: real table, its own scroll container so the page never scrolls sideways */}
      <div className="hidden overflow-x-auto rounded-xl border border-ink/10 sm:block">
        <table className="w-full border-collapse text-left text-[12.5px]">
          <thead>
            <tr className="bg-paper">
              {headers.map((h, i) => (
                <th key={`${h}-${i}`} className="border-b border-ink/10 px-3 py-2 font-semibold text-ink/70">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, rowIndex) => (
              <tr key={rowIndex} className={rowIndex % 2 ? 'bg-white' : 'bg-paper/40'}>
                {row.map((cell, cellIndex) => (
                  <td key={cellIndex} className="border-b border-ink/5 px-3 py-2 align-top text-ink/75">
                    {renderInlineText(cell, `td-${rowIndex}-${cellIndex}`)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Small screens: collapse to stacked label/value cards. */}
      <div className="space-y-2 sm:hidden">
        {rows.map((row, rowIndex) => (
          <div key={rowIndex} className="rounded-xl border border-ink/10 bg-white p-3">
            {row.map((cell, cellIndex) => (
              <div key={cellIndex} className="flex justify-between gap-3 border-b border-ink/5 py-1 last:border-0 text-[12.5px]">
                <span className="font-medium text-ink/50">{headers[cellIndex]}</span>
                <span className="text-right text-ink/80">{renderInlineText(cell, `mtd-${rowIndex}-${cellIndex}`)}</span>
              </div>
            ))}
          </div>
        ))}
      </div>
    </>
  );
}

function ProductHeaderCard({ name, category, stats }: { name: string; category: string; stats: string[] }) {
  return (
    <div className="mb-3 overflow-hidden rounded-xl border border-ink/10 bg-gradient-to-br from-ink to-ink-soft p-4 text-paper">
      <p className="font-display text-lg font-semibold">{name}</p>
      <p className="text-xs text-paper/60">{category}</p>
      {stats.length ? (
        <div className="mt-2.5 flex flex-wrap gap-2">
          {stats.map((stat) => (
            <span
              key={stat}
              className="inline-flex items-center gap-1 rounded-full border border-gold-400/30 bg-gold-500/15 px-2.5 py-1 text-[11px] font-medium text-gold-200"
            >
              {/^\d\.\d/.test(stat) ? <Star size={10} className="fill-current" /> : null}
              {stat}
            </span>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function renderBlock(block: MessageBlock, key: string) {
  switch (block.type) {
    case 'heading':
      return <Heading key={key} text={block.text} />;
    case 'paragraph':
      return <Paragraph key={key} text={block.text} />;
    case 'stats':
      return <StatsRow key={key} items={block.items} />;
    case 'features':
      return <FeatureCards key={key} items={block.items} />;
    case 'checklist':
      return <Checklist key={key} items={block.items} />;
    case 'steps':
      return <StepsTimeline key={key} items={block.items} />;
    case 'pricing':
      return <PricingCards key={key} plans={block.plans} />;
    case 'table':
      return <DataTable key={key} headers={block.headers} rows={block.rows} />;
    default:
      return null;
  }
}

export function MessageContent({ content }: { content: string }) {
  const blocks = parseMessageContent(content);
  const header = detectProductHeader(content, solutions);

  return (
    <div className="space-y-3">
      {header ? <ProductHeaderCard name={header.solution.name} category={header.solution.category} stats={header.stats} /> : null}
      {blocks.map((block, index) => (
        <motion.div
          key={`block-${index}`}
          initial={BLOCK_ANIMATION.initial}
          animate={BLOCK_ANIMATION.animate}
          transition={{ duration: 0.35, delay: Math.min(index * 0.06, 0.6) }}
        >
          {renderBlock(block, `b-${index}`)}
        </motion.div>
      ))}
    </div>
  );
}

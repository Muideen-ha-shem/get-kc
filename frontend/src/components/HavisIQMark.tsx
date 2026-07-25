type HavisIQMarkProps = {
  size?: number;
  className?: string;
  transparent?: boolean;
};

const INK = '#14171D';
const GLYPH = '#ECEEF2';
const ACCENT = '#C89A3E';

/**
 * The HavisIQ brand mark: an H with its crossbar broken into a single gold
 * node — the two verticals stand for the breadth of the Ha-Shem solution
 * catalog, the node is the advisor connecting a question to the right one.
 *
 * The chip's own ink/pale/gold tones are intentionally fixed regardless of
 * surrounding theme, the way a real app icon doesn't invert with page
 * background. Colors are set inline rather than via Tailwind utility
 * classes on purpose: this is a small, fixed-identity element that must
 * never depend on the Tailwind build picking up a config change (that's
 * exactly what caused it to render as a near-invisible pale "H" on a white
 * chip in practice — the accent dot stayed visible because it's opaque,
 * the chip background silently fell through to transparent).
 */
export function HavisIQMark({ size = 40, className = '', transparent = false }: HavisIQMarkProps) {
  return (
    <div
      className={`flex shrink-0 items-center justify-center rounded-[22%] ${className}`}
      style={{ width: size, height: size, backgroundColor: transparent ? 'transparent' : INK }}
    >
      <svg viewBox="0 0 48 48" width={size * 0.56} height={size * 0.56} fill="none" aria-hidden="true">
        <path d="M14 12 L14 36 M34 12 L34 36" stroke={GLYPH} strokeWidth="4.5" strokeLinecap="round" />
        <path d="M14 24 L20 24 M28 24 L34 24" stroke={GLYPH} strokeWidth="4.5" strokeLinecap="round" />
        <circle cx="24" cy="24" r="4" fill={ACCENT} />
      </svg>
    </div>
  );
}

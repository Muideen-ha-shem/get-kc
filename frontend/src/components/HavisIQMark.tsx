type HavisIQMarkProps = {
  size?: number;
  className?: string;
  transparent?: boolean;
};

const GLYPH = '#ECEEF2';
const ACCENT = '#C89A3E';

// A flat single-tone chip reads dead next to every other icon in the
// product (nav icons, card icons) which all sit on soft gradients or tinted
// pills. This gradient + inset gloss + soft ambient shadow gives the mark
// the same sense of depth/light other icons in the UI already have, instead
// of a flat cut-out square. Colors are set inline (not Tailwind utility
// classes) on purpose: this is a small, fixed-identity element that must
// never depend on the Tailwind build picking up a config change (that's
// exactly what caused it to render as a near-invisible pale "H" on a white
// chip in the past — the accent dot stayed visible because it's opaque, the
// chip background silently fell through to transparent).
const CHIP_BACKGROUND = 'linear-gradient(150deg, #232833 0%, #171B22 48%, #0F1216 100%)';
const CHIP_SHADOW =
  'inset 0 1px 0 rgba(255,255,255,0.09), inset 0 -10px 16px rgba(0,0,0,0.4), 0 6px 16px rgba(15,17,22,0.35), 0 0 0 1px rgba(200,154,62,0.14)';

/**
 * The HavisIQ brand mark: an H with its crossbar broken into a single gold
 * node — the two verticals stand for the breadth of the Ha-Shem solution
 * catalog, the node is the advisor connecting a question to the right one.
 */
export function HavisIQMark({ size = 40, className = '', transparent = false }: HavisIQMarkProps) {
  return (
    <div
      className={`flex shrink-0 items-center justify-center rounded-[22%] ${className}`}
      style={{
        width: size,
        height: size,
        background: transparent ? 'transparent' : CHIP_BACKGROUND,
        boxShadow: transparent ? 'none' : CHIP_SHADOW,
      }}
    >
      <svg viewBox="0 0 48 48" width={size * 0.56} height={size * 0.56} fill="none" aria-hidden="true">
        <path d="M14 12 L14 36 M34 12 L34 36" stroke={GLYPH} strokeWidth="4.5" strokeLinecap="round" />
        <path d="M14 24 L20 24 M28 24 L34 24" stroke={GLYPH} strokeWidth="4.5" strokeLinecap="round" />
        <circle cx="24" cy="24" r="4" fill={ACCENT} />
      </svg>
    </div>
  );
}

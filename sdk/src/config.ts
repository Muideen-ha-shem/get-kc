import type { HavisIQConfig, ResolvedConfig } from './types';

const DEFAULT_API_BASE_URL = 'https://api.havisiq.ai';
const DEFAULT_MODE = 'floating';
const DEFAULT_THEME = 'auto';
const DEFAULT_POSITION = 'bottom-right';

const KNOWN_MODES = new Set(['floating', 'inline', 'popup', 'fullscreen']);

/** Validates and merges defaults into a caller-supplied `HavisIQConfig`.
 * Throws on missing `apiKey` — every other field is optional. */
export function resolveConfig(input: HavisIQConfig): ResolvedConfig {
  if (!input || typeof input.apiKey !== 'string' || input.apiKey.trim() === '') {
    throw new Error('HavisIQ.init: "apiKey" is required');
  }

  const mode = input.mode ?? DEFAULT_MODE;
  if (!KNOWN_MODES.has(mode)) {
    throw new Error(`HavisIQ.init: unknown mode "${mode}"`);
  }

  return {
    apiKey: input.apiKey,
    apiBaseUrl: input.apiBaseUrl ?? DEFAULT_API_BASE_URL,
    mode,
    theme: input.theme ?? DEFAULT_THEME,
    position: input.position ?? DEFAULT_POSITION,
    container: input.container,
    context: input.context ?? {},
    reserveLeft: input.reserveLeft ?? 0,
  };
}

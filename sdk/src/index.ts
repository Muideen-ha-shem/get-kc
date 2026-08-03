import { resolveConfig } from './config';
import { mountWidget } from './widget';
import type { HavisIQConfig } from './types';

/** Vite's IIFE library build (`name: 'HavisIQ'`, see vite.config.ts)
 * assigns this module's named exports directly to `window.HavisIQ`, so a
 * plain `<script src="havisiq-sdk.js">` tag is enough to make
 * `HavisIQ.init({...})` available — no bundler required on the embedding
 * site. */
export function init(config: HavisIQConfig): void {
  const resolved = resolveConfig(config);
  void mountWidget(resolved);
}

declare global {
  interface Window {
    HavisIQ: { init: typeof init };
  }
}

import { resolveConfig } from './config';
import { closePanel, mountWidget, openPanel } from './widget';
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

/** Opens the panel from the host page's own UI — the mechanism a host
 * platform uses to build its own branded entry point (e.g. a sidebar
 * "Intelligence Layer" button) instead of relying only on the SDK's
 * internal floating toggle, which keeps working unchanged either way. */
export const open = openPanel;
export const close = closePanel;

declare global {
  interface Window {
    HavisIQ: { init: typeof init; open: typeof open; close: typeof close };
  }
}

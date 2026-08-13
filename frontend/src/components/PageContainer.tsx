import { ReactNode } from 'react';

/**
 * Constrains and centers page content inside a full-width <main>. Inner
 * sections can still use their own tighter max-w (max-w-2xl/max-w-md) —
 * this just stops the outer column from bleeding edge-to-edge on wide
 * screens.
 */
export function PageContainer({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <div className={`max-w-6xl w-full mx-auto ${className}`}>{children}</div>;
}

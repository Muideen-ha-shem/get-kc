import { SelectHTMLAttributes, forwardRef } from 'react';
import { ChevronDown } from 'lucide-react';

/**
 * Native <select> wrapped with a custom chevron and the shared ink/paper/gold
 * input styling — appearance-none hides the browser's own arrow so ours is
 * the only one shown. Keeps native keyboard/accessibility/mobile behavior.
 */
export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(
  function Select({ className = '', ...props }, ref) {
    return (
      <div className="relative">
        <select
          ref={ref}
          {...props}
          className={`w-full appearance-none border border-ink/10 rounded-xl pl-3 pr-9 py-2 bg-paper text-ink text-sm outline-none transition-colors focus:border-gold-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gold-400/50 focus-visible:ring-offset-2 focus-visible:ring-offset-paper ${className}`}
        />
        <ChevronDown
          size={14}
          className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-ink/40"
        />
      </div>
    );
  },
);

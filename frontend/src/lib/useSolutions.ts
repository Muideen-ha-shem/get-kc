import { useEffect, useState } from 'react';
import { ADVISORY_SERVICES, type Solution } from '../solutions';
import { HIGHLIGHTS_BY_PRODUCT, TYPICAL_USERS_BY_PRODUCT } from '../productCatalogCopy';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '';

type SolutionApiEntry = {
  id: string;
  name: string;
  category: string;
  business_problem: string;
  solution_type: string;
  learn_more_url: string;
};

function toSolution(entry: SolutionApiEntry): Solution {
  return {
    id: entry.id,
    name: entry.name,
    category: entry.category,
    description: entry.business_problem,
    status: 'live',
    highlights: HIGHLIGHTS_BY_PRODUCT[entry.id] ?? [],
    typicalUsers: TYPICAL_USERS_BY_PRODUCT[entry.id] ?? 'Business and operations teams',
    learnMoreUrl: entry.learn_more_url,
  };
}

type UseSolutionsResult = {
  solutions: Solution[];
  isLoading: boolean;
  error: string | null;
};

/**
 * Fetches the live product catalog from `GET /solutions` (backed by
 * PRODUCT_REGISTRY) and merges it with the small static advisory-services
 * list. On fetch failure, falls back to advisory-only so the page still
 * renders something rather than an empty catalog.
 */
export function useSolutions(): UseSolutionsResult {
  const [solutions, setSolutions] = useState<Solution[]>(ADVISORY_SERVICES);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const response = await fetch(`${API_BASE_URL || 'http://localhost:8000'}/solutions`);
        if (!response.ok) throw new Error(`Request failed (${response.status})`);
        const data: SolutionApiEntry[] = await response.json();
        if (cancelled) return;
        setSolutions([...data.map(toSolution), ...ADVISORY_SERVICES]);
        setError(null);
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : 'Failed to load solutions');
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  return { solutions, isLoading, error };
}

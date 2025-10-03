// frontend/src/hooks/useEnrichVulns.ts
import { useCallback, useRef, useState } from 'react';
import { enrichVulns } from '@/api';

export type EnrichedHost = Record<string, any>;

export function useEnrichVulns() {
  const [data, setData] = useState<EnrichedHost[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]   = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const run = useCallback(async (hosts: any[]) => {
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;

    setLoading(true);
    setError(null);

    try {
      const json = await enrichVulns(hosts, ctrl.signal);
      setData(json.hosts ?? null);
      return json.hosts ?? [];
    } catch (e: any) {
      if (e.name !== 'AbortError') setError(e?.message || String(e));
      throw e;
    } finally {
      setLoading(false);
    }
  }, []);

  const cancel = useCallback(() => abortRef.current?.abort(), []);

  return { data, loading, error, run, cancel };
}

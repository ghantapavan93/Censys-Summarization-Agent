// frontend/src/hooks/useExportCsv.ts
import { useCallback, useRef, useState } from 'react';
import { exportCsv } from '@/api';

export function useExportCsv() {
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const run = useCallback(async (rows: any[]) => {
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setError(null);
    setDownloading(true);

    try {
      // Delegate to canonical API which handles dynamic base and filename parsing
      const result = await exportCsv(rows, ctrl.signal);
      if (!result.success) {
        throw new Error('Export failed');
      }
      return { blob: result.blob, filename: result.filename };
    } catch (e: any) {
      if (e.name !== 'AbortError') setError(e?.message || String(e));
      throw e;
    } finally {
      setDownloading(false);
    }
  }, []);

  const cancel = useCallback(() => abortRef.current?.abort(), []);

  return { downloading, error, run, cancel };
}

import { createContext, useCallback, useContext, useMemo, useState } from 'react';

type ToastKind = 'info' | 'success' | 'error';
type ToastItem = { id: number; kind: ToastKind; msg: string };

type ToastCtx = {
  push: (kind: ToastKind, msg: string, opts?: { timeoutMs?: number }) => void;
};

const Ctx = createContext<ToastCtx | null>(null);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const push = useCallback((kind: ToastKind, msg: string, opts?: { timeoutMs?: number }) => {
    const id = Date.now() + Math.random();
    setItems(prev => [...prev, { id, kind, msg }]);
    const t = setTimeout(() => {
      setItems(prev => prev.filter(x => x.id !== id));
    }, opts?.timeoutMs ?? 3500);
    return () => clearTimeout(t);
  }, []);
  const value = useMemo(() => ({ push }), [push]);

  return (
    <Ctx.Provider value={value}>
      {children}
      <div className="toast-viewport">
        {items.map(t => (
          <div
            key={t.id}
            className={`toast ${
              t.kind === 'success' ? 'toast-success' :
              t.kind === 'error'   ? 'toast-error'   : 'toast-info'
            }`}
            role="status"
            aria-live="polite"
          >
            {t.msg}
          </div>
        ))}
      </div>
    </Ctx.Provider>
  );
}

export function useToast() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error('useToast must be used inside <ToastProvider/>');
  return ctx;
}

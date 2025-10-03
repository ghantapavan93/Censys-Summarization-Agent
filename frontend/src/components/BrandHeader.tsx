import { CheckCircle, CircleAlert, Settings as Gear } from 'lucide-react';

export default function BrandHeader({ healthy, onOpenSettings }: { healthy: boolean | null; onOpenSettings: () => void }) {
  return (
    <header className="px-6 py-4 border-b border-border bg-surface/60 backdrop-blur sticky top-0 z-40">
      <div className="mx-auto max-w-7xl flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 rounded-lg bg-accent/15 border border-border flex items-center justify-center">
            <div className="h-3 w-3 rounded-sm bg-accent" />
          </div>
          <h1 className="text-lg font-semibold">Censys Summarization Agent</h1>
        </div>
        <div className="flex items-center gap-2">
          {healthy === true ? (
            <span className="badge badge-ok"><CheckCircle size={16}/> Backend OK</span>
          ) : healthy === false ? (
            <span className="badge"><CircleAlert size={16}/> Backend Unreachable</span>
          ) : null}
          <button className="btn" onClick={onOpenSettings}><Gear size={14}/> Settings</button>
        </div>
      </div>
    </header>
  );
}

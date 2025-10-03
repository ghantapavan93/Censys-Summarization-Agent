import { useEffect, useState } from 'react';
import { X, Save } from 'lucide-react';

export interface Settings {
  backendBase: string; // e.g. /api or http://localhost:8000
  persistInput: boolean;
  autoRunOnUseSample?: boolean; // optional; defaults to true
}

const KEY = 'censys_settings_v2';

export function loadSettings(): Settings {
  try {
    const s = localStorage.getItem(KEY);
    if (s) {
      const parsed = JSON.parse(s);
      return {
        backendBase: parsed.backendBase ?? '/api',
        persistInput: parsed.persistInput ?? true,
        autoRunOnUseSample: parsed.autoRunOnUseSample ?? true,
      };
    }
  } catch {}
  return { backendBase: '/api', persistInput: true, autoRunOnUseSample: true };
}

export function saveSettings(s: Settings) {
  localStorage.setItem(KEY, JSON.stringify(s));
}

export default function SettingsModal({ open, onClose, onSave }: { open: boolean; onClose: () => void; onSave: (s: Settings) => void; }) {
  const [settings, setSettings] = useState<Settings>(loadSettings());

  useEffect(() => {
    if (open) setSettings(loadSettings());
  }, [open]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[95vw] max-w-xl bg-canvas border border-border rounded-2xl p-5">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold">Settings</h3>
          <button className="btn" onClick={onClose}><X size={16}/> Close</button>
        </div>

        <div className="space-y-4">
          <label className="block">
            <div className="text-sm text-neutral-300 mb-1">Backend Base URL</div>
            <input
              className="input w-full"
              placeholder="/api or http://localhost:8000"
              value={settings.backendBase}
              onChange={e => setSettings({ ...settings, backendBase: e.target.value.trim() || '/api' })}
            />
            <div className="text-xs text-neutral-500 mt-1">Used for API requests. In dev, /api proxies to http://localhost:8000 via Vite.</div>
          </label>

          <label className="flex items-center gap-2">
            <input type="checkbox" checked={settings.persistInput} onChange={e => setSettings({ ...settings, persistInput: e.target.checked })} />
            <span className="text-sm">Persist last input in localStorage</span>
          </label>

          <label className="flex items-center gap-2">
            <input type="checkbox" checked={settings.autoRunOnUseSample ?? true} onChange={e => setSettings({ ...settings, autoRunOnUseSample: e.target.checked })} />
            <span className="text-sm">Auto-run on “Use Sample”</span>
          </label>
        </div>

        <div className="flex justify-end mt-5">
          <button className="btn btn-primary" onClick={() => { saveSettings(settings); onSave(settings); }}><Save size={16}/> Save</button>
        </div>
      </div>
    </div>
  );
}

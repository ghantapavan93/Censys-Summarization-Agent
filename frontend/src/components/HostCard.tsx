import { Host } from "../lib/types";
import { RiskChip, KevBadge } from "./RiskChip";

export function HostCard({ h, onClickPort }: { h: Host; onClickPort?: (p: number) => void }) {
  return (
    <div className="rounded-xl border p-3 bg-white shadow-sm hover:shadow-md transition text-sm">
      <div className="flex items-center justify-between">
        <div className="font-mono">{h.ip}</div>
        <div className="flex items-center gap-1.5">
          <RiskChip score={h.risk_score ?? 0} />
          <KevBadge show={!!h.kev_present} />
          {h.cvss_high_present && (
            <span className="ml-2 text-[10px] rounded bg-orange-100 px-1.5 py-0.5 text-orange-700">CVSS≥7</span>
          )}
          <span
            className="ml-1 cursor-help text-neutral-400"
            title={
              `Risk factors:\n` +
              `${h.kev_present ? '• KEV present (+40)\n' : ''}` +
              `${h.cvss_high_present ? '• CVSS≥7 (+25)\n' : ''}` +
              '• HTTP on non-std port (+5) if detected\n' +
              '• WAF reduces score (-5)'
            }
          >ℹ️</span>
        </div>
      </div>
      <div className="text-xs text-slate-600 mt-1">
        {(h.autonomous_system?.name || "—")} · {(h.location?.country_code || "—")}
      </div>
      <div className="mt-2 flex flex-wrap gap-1">
        {(h.services || []).slice(0, 10).map((s, i) => (
          <button
            key={i}
            onClick={() => s.port && onClickPort?.(s.port)}
            className="px-2 py-0.5 text-xs rounded border bg-slate-50 hover:bg-slate-100"
          >
            {s.protocol}/{s.port}
          </button>
        ))}
      </div>
    </div>
  );
}

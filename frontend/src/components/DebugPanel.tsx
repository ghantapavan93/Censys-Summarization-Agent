import React from 'react';
import { enrichVulns, exportCsv } from '../api';

export default function DebugPanel() {
  const [hosts] = React.useState<any[]>([
    { id: 'h1', services: [{ port: 22 }], vulns: [{ cvss: 7.5, kev: true }] },
    { id: 'h2', services: [{ port: 80 }], vulns: [{ cvss_v3: 6.9 }] },
  ]);
  const [enriched, setEnriched] = React.useState<any[] | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [msg, setMsg] = React.useState<string>('');

  const onEnrich = async () => {
    try {
      setBusy(true); setMsg('');
      const { hosts: out } = await enrichVulns(hosts);
      setEnriched(out);
      setMsg(`Enriched ${out.length} hosts. Example risk_score=${out[0]?.risk_score}`);
      console.log('Enriched:', out);
    } catch (e: any) {
      setMsg('Enrich failed: ' + (e?.message || e));
      console.error(e);
    } finally { setBusy(false); }
  };

  const onExport = async () => {
    try {
      setBusy(true); setMsg('');
      const rows = enriched ?? hosts;
      const result = await exportCsv(rows);
      if (!result.success) {
        throw new Error('Export failed');
      }
      const url = URL.createObjectURL(result.blob);
      const a = document.createElement('a');
      a.href = url; a.download = result.filename || 'export.csv';
      a.click();
      URL.revokeObjectURL(url);
      setMsg(`Downloaded ${result.filename || 'export.csv'}`);
    } catch (e: any) {
      setMsg('Export failed: ' + (e?.message || e));
      console.error(e);
    } finally { setBusy(false); }
  };

  return (
    <div style={{padding:12, border:'1px solid #444', borderRadius:8, margin:'12px 0'}}>
      <div style={{fontWeight:600, marginBottom:8}}>Debug Panel</div>
      <button onClick={onEnrich} disabled={busy} style={{marginRight:8}}>
        Enrich Vulns
      </button>
      <button onClick={onExport} disabled={busy || !(enriched ?? hosts)?.length}>
        Export CSV
      </button>
      <div style={{marginTop:8, fontSize:12}}>{busy ? 'Working…' : msg}</div>
    </div>
  );
}

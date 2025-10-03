import { useEnrichVulns } from '../hooks/useEnrichVulns';
import { useExportCsv } from '../hooks/useExportCsv';

export default function DevTools({ hosts }: { hosts: any[] }) {
  const { data: enriched, loading, error, run } = useEnrichVulns();
  const { downloading, error: xerr, run: exportCsv } = useExportCsv();

  return (
    <div style={{padding:12,border:'1px solid #444',borderRadius:8,margin:'12px 0'}}>
      <div style={{fontWeight:600,marginBottom:8}}>Dev Tools</div>
      <button disabled={loading} onClick={() => run(hosts)} style={{marginRight:8}}>
        {loading ? 'Enriching…' : 'Enrich Vulns'}
      </button>
      <button disabled={downloading || !((enriched ?? hosts)?.length)} onClick={async () => {
        const { blob, filename } = await exportCsv(enriched ?? hosts);
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = filename || 'export.csv'; a.click();
        URL.revokeObjectURL(url);
      }}>
        {downloading ? 'Exporting…' : 'Download CSV'}
      </button>
      {(error || xerr) && <div style={{marginTop:8,color:'#f87171',fontSize:12}}>
        {error ? `Enrich error: ${error}` : `Export error: ${xerr}`}
      </div>}
    </div>
  );
}

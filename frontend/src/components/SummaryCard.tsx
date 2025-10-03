import type { RiskItem, CensAIResponse } from '../lib/types';
import { useState } from 'react';
import { FileText, Wand2, ExternalLink, ShieldAlert, Copy } from 'lucide-react';
import { useToast } from './Toast';
import { MuteModal } from './MuteModal';
import { backend } from '../lib/api';
import '../styles/risk-enhancements.css';

interface SummaryCardProps {
  deterministic: string;
  aiRewritten?: string;
  risks: RiskItem[];
  keyFindings: string[];
  nextActions?: string[];
  validJson?: boolean;
  meta?: { generated_at?: string; model?: string; request_id?: string; event_id?: string };
  rawJson?: any;
  rawResponse?: any;
  onRewriteClick: () => void;
  onExportClick: () => void;
  delta?: CensAIResponse['delta'];
  onDeltaFilterToggle?: (which: 'new'|'resolved'|'changed') => void;
}

export default function SummaryCard(props: SummaryCardProps) {
  const { deterministic, aiRewritten, risks, keyFindings, nextActions, validJson, meta, rawJson, rawResponse, onRewriteClick, onExportClick, delta } = props;
  const [tabState, setTabState] = useState<Record<string, string>>({});
  const [deltaOnly, setDeltaOnly] = useState(false);
  const [showMuteModal, setShowMuteModal] = useState(false);
  const [selectedRisk, setSelectedRisk] = useState<RiskItem | null>(null);
  const [mutedRisks, setMutedRisks] = useState<Record<string, any>>({});
  const [creatingTicket, setCreatingTicket] = useState<Record<string, boolean>>({});
  const toast = useToast();

  const visibleRisks = (() => {
    if (!deltaOnly || !delta) return risks;
    const newSet = new Set<string>((delta.new || []) as any);
    const changedSet = new Set<string>((delta.changed || []).map((c: any) => c?.id).filter(Boolean));
    return (risks || []).filter(r => (r.id && (newSet.has(r.id) || changedSet.has(r.id))) );
  })();

  const handleMuteRisk = async (days: number, reason: string) => {
    if (!selectedRisk?.id) return;
    
    try {
      const result = await backend.muteRisk(selectedRisk.id, days, reason);
      setMutedRisks(prev => ({
        ...prev,
        [selectedRisk.id!]: result
      }));
      toast.push('success', `Risk muted for ${days} day${days !== 1 ? 's' : ''}`, { timeoutMs: 3000 });
    } catch (error) {
      toast.push('error', 'Failed to mute risk', { timeoutMs: 3000 });
    }
  };

  const handleCreateTicket = async (type: 'jira' | 'servicenow', risk: RiskItem) => {
    if (!risk.id) return;
    
    const ticketKey = `${risk.id}-${type}`;
    setCreatingTicket(prev => ({ ...prev, [ticketKey]: true }));
    
    try {
      const description = `Security Risk: ${risk.title || 'Unknown'}
      
Severity: ${risk.severity}
CVSS: ${risk.cvss || 'N/A'}
KEV: ${risk.kev ? 'Yes' : 'No'}
${risk.related_cves?.map((cve: string) => `CVE: ${cve}`).join('\n') || ''}

Evidence:
${risk.evidence?.join('\n') || 'No evidence provided'}

Why it matters: ${risk.why_it_matters || 'N/A'}
Recommended fix: ${risk.recommended_fix || 'N/A'}`;
      
      const result = await backend.createTicket(type, risk.id, risk.title || 'Security Risk', description);
      
      // Show the demo message if available, otherwise show the ticket ID
      if (result.demo_message) {
        // Show demo message with special styling and longer timeout
        toast.push('success', result.demo_message, { timeoutMs: 10000 });
      } else {
        // Real integration case
        toast.push('success', `${type.toUpperCase()} ticket created: ${result.id}`, { timeoutMs: 5000 });
        
        // Only open URL if it's not null (real integration)
        if (result.url) {
          window.open(result.url, '_blank');
        }
      }
    } catch (error) {
      toast.push('error', `Failed to create ${type.toUpperCase()} ticket`, { timeoutMs: 3000 });
    } finally {
      setCreatingTicket(prev => ({ ...prev, [ticketKey]: false }));
    }
  };

  function sevClass(s: RiskItem['severity']) {
    switch (s) {
      case 'CRITICAL': return 'inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-gradient-to-r from-red-600 to-red-700 text-white shadow-lg ring-2 ring-red-500/30 animate-pulse';
      case 'HIGH': return 'inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-gradient-to-r from-orange-500 to-orange-600 text-white shadow-lg ring-2 ring-orange-400/30';
      case 'MEDIUM': return 'inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-gradient-to-r from-yellow-500 to-yellow-600 text-white shadow-md ring-2 ring-yellow-400/20';
      case 'LOW': return 'inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-gradient-to-r from-blue-500 to-blue-600 text-white shadow-md ring-2 ring-blue-400/20';
      default: return 'inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-gradient-to-r from-gray-500 to-gray-600 text-white shadow-md';
    }
  }

  function sevIcon(s: RiskItem['severity']) {
    switch (s) {
      case 'CRITICAL': return '🔥';
      case 'HIGH': return '⚠️';
      case 'MEDIUM': return '⚡';
      case 'LOW': return '💡';
      default: return '📋';
    }
  }

  function getRiskCardBorder(s: RiskItem['severity']) {
    const baseClasses = 'border-l-4 shadow-lg transition-all duration-300 hover:shadow-xl hover:scale-[1.02] risk-card';
    switch (s) {
      case 'CRITICAL': return `${baseClasses} border-l-red-500 shadow-red-500/20 bg-gradient-to-r from-red-50/50 to-transparent dark:from-red-950/20 risk-critical`;
      case 'HIGH': return `${baseClasses} border-l-orange-500 shadow-orange-500/20 bg-gradient-to-r from-orange-50/50 to-transparent dark:from-orange-950/20 risk-high`;
      case 'MEDIUM': return `${baseClasses} border-l-yellow-500 shadow-yellow-500/15 bg-gradient-to-r from-yellow-50/50 to-transparent dark:from-yellow-950/20 risk-medium`;
      case 'LOW': return `${baseClasses} border-l-blue-500 shadow-blue-500/15 bg-gradient-to-r from-blue-50/50 to-transparent dark:from-blue-950/20 risk-low`;
      default: return `${baseClasses} border-l-gray-400 shadow-md bg-gradient-to-r from-gray-50/50 to-transparent dark:from-gray-950/20`;
    }
  }

  return (
    <>
      <div className="card space-y-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileText size={18}/>
          <h3 className="text-lg font-semibold">Deterministic Summary</h3>
          {validJson ? (
            <span className="badge badge-ok">Validated JSON</span>
          ) : (
            <span className="badge">Unverified</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button className="btn" onClick={() => navigator.clipboard.writeText(deterministic)}><Copy size={16}/> Copy</button>
          <button className="btn" onClick={onExportClick}><ExternalLink size={16}/> Export</button>
          <button className="btn btn-primary" onClick={onRewriteClick}><Wand2 size={16}/> Rewrite with AI</button>
        </div>
      </div>

      {/* Meta stamp */}
      {(meta?.generated_at || meta?.model) && (
        <div className="text-xs text-neutral-500">
          {(() => {
            const ts = meta?.generated_at;
            let when = '—';
            try { if (ts) when = new Date(ts).toLocaleString(); } catch { when = ts || '—'; }
            return `Generated at ${when}${meta?.model ? ` • model: ${meta.model}` : ''}`;
          })()}
        </div>
      )}

      <p className="leading-relaxed whitespace-pre-wrap">{deterministic}</p>

      {aiRewritten && (
        <div className="bg-[#0b0f14] border border-border rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2"><Wand2 size={16}/><span className="font-medium">Latest AI Rewrite (preview)</span></div>
          <p className="text-neutral-300 whitespace-pre-wrap">{aiRewritten}</p>
        </div>
      )}

      {/* Delta counts widget */}
      {delta?.counts && (
        <div className="flex items-center gap-3 text-sm">
          <button className="rounded-md border border-border px-3 py-1 bg-[#0b0f14] hover:bg-[#0f1520]" title="Show only new risks" onClick={() => setDeltaOnly(true)}>New ({delta.counts.new})</button>
          <div className="rounded-md border border-border px-3 py-1 bg-[#0b0f14]" title="Resolved risks from previous snapshot">Resolved ({delta.counts.resolved})</div>
          <button className="rounded-md border border-border px-3 py-1 bg-[#0b0f14] hover:bg-[#0f1520]" title="Show only changed risks" onClick={() => setDeltaOnly(true)}>Changed ({delta.counts.changed})</button>
          <button className={`btn btn-xs ${deltaOnly ? 'btn-primary' : ''}`} onClick={() => setDeltaOnly(v => !v)}>
            {deltaOnly ? 'Showing: New/Changed' : 'Filter to New/Changed'}
          </button>
        </div>
      )}

      {keyFindings?.length > 0 && (
        <div>
          <h4 className="mb-2 font-medium">Key Findings ({keyFindings.length})</h4>
          <ul className="list-disc ml-6 space-y-1 text-neutral-300">
            {keyFindings.map((k, i) => <li key={i}>{k}</li>)}
          </ul>
        </div>
      )}

      {visibleRisks?.length > 0 && (
        <div>
          <h4 className="mb-4 font-semibold text-lg flex items-center gap-2">
            <ShieldAlert className="text-red-500" size={20}/>
            <span className="bg-gradient-to-r from-red-600 to-orange-600 bg-clip-text text-transparent">Key Security Risks</span>
            <span className="ml-2 px-2 py-1 text-xs bg-gray-100 dark:bg-gray-800 rounded-full text-gray-600 dark:text-gray-400">
              {visibleRisks.length}{deltaOnly ? ` of ${risks.length}` : ''}
            </span>
          </h4>
          <div className="space-y-4">
            {visibleRisks.map((r, i) => (
              <div key={i} className={`relative rounded-xl p-5 transition-all duration-300 hover:shadow-xl hover:scale-[1.02] ${getRiskCardBorder(r.severity)}`}>
                <div className="flex items-start justify-between gap-3 mb-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-3">
                      <span className="text-2xl">{sevIcon(r.severity)}</span>
                      <h5 className="font-semibold text-lg text-gray-900 dark:text-white leading-tight">{r.title}</h5>
                    </div>
                    <div className="flex items-center gap-3 mb-2">
                      <span className={sevClass(r.severity)}>
                        {sevIcon(r.severity)} {r.severity}
                      </span>
                      {r.kev && (
                        <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-gradient-to-r from-purple-600 to-purple-700 text-white shadow-lg ring-2 ring-purple-500/30 animate-bounce">
                          🎯 KEV
                        </span>
                      )}
                      {typeof r.cvss === 'number' && r.cvss >= 7 && (
                        <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-semibold bg-gradient-to-r from-amber-500 to-amber-600 text-white shadow-md">
                          ⚡ CVSS≥7
                        </span>
                      )}
                      {r.cvss && (
                        <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-semibold bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300">
                          CVSS: {r.cvss}
                        </span>
                      )}
                      {typeof r.epss === 'number' && r.epss >= 0.95 && (
                        <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300">
                          📊 EPSS {Math.round((r.epss||0)*100)}%
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                
                {/* Identity chips under title */}
                {(() => {
                  const id = ((r as any).details?.identity) || {};
                  const chips = (
                    [ ['Hostname', id.hostname], ['rDNS', id.rdns], ['Cert CN', id.cn], ['ASN', id.asn], ['Org', id.org] ] as Array<[string, any]>
                  ).filter(([,v]) => !!v);
                  return chips.length ? (
                    <div className="flex flex-wrap gap-2 mb-4">
                      {chips.map(([k,v], idx) => (
                        <span key={idx} className="inline-flex items-center gap-1 rounded-lg bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800 px-3 py-1 text-xs font-medium">
                          <span className="font-semibold">{k}:</span> {String(v)}
                        </span>
                      ))}
                    </div>
                  ) : null;
                })()}
                  <div className="flex gap-2 text-xs">
                    {['Why flagged','Banner/TLS','Fix'].map((t) => (
                      <button key={t} className={`px-2 py-1 rounded ${((tabState[r.id || r.title] || 'Why flagged')===t) ? 'bg-[#10161f] border border-border' : 'text-neutral-400'}`} onClick={() => setTabState((prev: any) => ({ ...prev, [r.id || r.title]: t }))}>{t}</button>
                    ))}
                  </div>
                  <div className="mt-2 text-sm text-neutral-300">
                    {(() => {
                      const active = (tabState[r.id || r.title] || 'Why flagged');
                      if (active === 'Why flagged') {
                        return (
                          <div>
                            {/* Rule ID chip when available (prefix "xyz:") */}
                            {typeof (r as any).id === 'string' && (r as any).id.includes(':') && (
                              <div className="mb-1">
                                <span className="inline-flex items-center gap-1 rounded-full bg-[#0b0f14] text-neutral-300 border border-border px-2 py-0.5 text-[10px]">rule: {(r as any).id.split(':')[1]}</span>
                              </div>
                            )}
                            {Array.isArray(r.related_cves) && r.related_cves.length > 0 ? (() => {
                              const uniq = Array.from(new Set(r.related_cves.filter(Boolean)));
                              const nvd = (cve: string) => `https://nvd.nist.gov/vuln/detail/${cve}`;
                              return (
                                <div className="text-xs text-neutral-400 mb-1 flex flex-wrap gap-2">CVEs:
                                  {uniq.map(c => (
                                    <a key={c} href={nvd(c)} target="_blank" rel="noreferrer" className="underline hover:text-neutral-200">{c}</a>
                                  ))}
                                </div>
                              );
                            })() : null}
                            {r.why_it_matters && r.why_it_matters.trim() !== r.title.trim() && (
                              <div>{r.why_it_matters}</div>
                            )}
                            {Array.isArray(r.evidence) && r.evidence.length > 0 && (
                              <ul className="text-xs text-neutral-400 list-disc ml-5 mt-1">
                                {r.evidence.slice(0,4).map((e, j) => {
                                  let text = String(e || '');
                                  text = text.replace(/\bunknown\s+unknown\b/gi, '');
                                  text = text.replace(/\s+/g, ' ').trim();
                                  return <li key={j}>{text || '—'}</li>;
                                })}
                              </ul>
                            )}
                          </div>
                        );
                      } else if (active === 'Banner/TLS') {
                        const d: any = (r as any).details || {};
                        const tls: any = d.tls || {};
                        const http: any = d.http || {};
                        const fp: any = d.fingerprints || {};
                        const rows = [
                          d.banner ? ['Banner', d.banner] : null,
                          http.title ? ['HTTP Title', http.title] : null,
                          http.server ? ['Server', http.server] : null,
                          http.favicon_hash ? ['Favicon Hash', http.favicon_hash] : null,
                          tls.cn ? ['TLS CN', tls.cn] : null,
                          Array.isArray(tls.san) && tls.san.length ? ['TLS SAN', tls.san.join(', ')] : null,
                          tls.expiry ? ['Expiry', String(tls.expiry)] : null,
                          tls.protocol ? ['Protocol', tls.protocol] : null,
                          tls.cipher ? ['Cipher', tls.cipher] : null,
                          tls.alpn ? ['ALPN', String(tls.alpn)] : null,
                          tls.chain ? ['Chain', String(tls.chain)] : null,
                          fp.ja3 ? ['JA3', String(fp.ja3)] : null,
                          fp.jarm ? ['JARM', String(fp.jarm)] : null,
                        ].filter(Boolean) as Array<[string,string]>;
                        return (
                          <div className="flex gap-4">
                            {d.screenshot ? (
                              <div className="shrink-0">
                                <img src={d.screenshot} width={120} height={90} alt="thumbnail" className="border border-border rounded" />
                              </div>
                            ) : null}
                            {rows.length ? (
                              <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                                {rows.map(([k,v], idx) => (<div key={idx}><span className="text-neutral-400">{k}:</span> {v}</div>))}
                              </div>
                            ) : (<div className="text-xs text-neutral-400">No banner/TLS specifics available.</div>)}
                          </div>
                        );
                      }
                      // Fix
                      return (
                        <div className="flex items-start justify-between gap-2">
                          <div>{r.recommended_fix || <span className="text-xs text-neutral-400">No fix provided.</span>}</div>
                          {r.recommended_fix ? (
                            <button
                              className="btn btn-xs"
                              onClick={async () => { await navigator.clipboard.writeText(r.recommended_fix || ''); toast.push('success', 'Fix copied to clipboard', { timeoutMs: 2000 }); }}
                              title="Copy fix"
                            >
                              <Copy size={14}/>
                            </button>
                          ) : null}
                        </div>
                      );
                    })()}
                  </div>
                
                {/* Ticketing and Mute actions */}
                <div className="mt-4 flex items-center gap-3 text-sm">
                  <button 
                    className={`inline-flex items-center px-4 py-2 rounded-lg font-medium transition-all duration-200 ${
                      creatingTicket[`${r.id}-jira`] 
                        ? 'bg-blue-100 text-blue-600 cursor-not-allowed' 
                        : 'bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white shadow-md hover:shadow-lg hover:scale-105 active:scale-95'
                    }`}
                    onClick={() => handleCreateTicket('jira', r)}
                    disabled={!r.id || creatingTicket[`${r.id}-jira`]}
                  >
                    {creatingTicket[`${r.id}-jira`] ? (
                      <><span className="animate-spin mr-2">⏳</span>Creating...</>
                    ) : (
                      <><span className="mr-2">🎫</span>Create Jira</>
                    )}
                  </button>
                  <button 
                    className={`inline-flex items-center px-4 py-2 rounded-lg font-medium transition-all duration-200 ${
                      creatingTicket[`${r.id}-servicenow`] 
                        ? 'bg-green-100 text-green-600 cursor-not-allowed' 
                        : 'bg-gradient-to-r from-green-600 to-green-700 hover:from-green-700 hover:to-green-800 text-white shadow-md hover:shadow-lg hover:scale-105 active:scale-95'
                    }`}
                    onClick={() => handleCreateTicket('servicenow', r)}
                    disabled={!r.id || creatingTicket[`${r.id}-servicenow`]}
                  >
                    {creatingTicket[`${r.id}-servicenow`] ? (
                      <><span className="animate-spin mr-2">⏳</span>Creating...</>
                    ) : (
                      <><span className="mr-2">📋</span>Create ServiceNow</>
                    )}
                  </button>
                  {(() => {
                    const m: any = mutedRisks[r.id || ''] || (r as any).muted;
                    if (m) {
                      const daysLeft = Math.max(0, Math.ceil(((m.until || 0) * 1000 - Date.now()) / 86400000));
                      return (
                        <span className="inline-flex items-center px-3 py-2 rounded-lg bg-gradient-to-r from-gray-500 to-gray-600 text-white text-sm font-medium shadow-md">
                          <span className="mr-2">😴</span>Snoozed ({daysLeft}d)
                        </span>
                      );
                    }
                    return (
                      <button 
                        className="inline-flex items-center px-4 py-2 rounded-lg font-medium bg-gradient-to-r from-yellow-500 to-yellow-600 hover:from-yellow-600 hover:to-yellow-700 text-white shadow-md hover:shadow-lg transition-all duration-200 hover:scale-105 active:scale-95"
                        onClick={() => {
                          setSelectedRisk(r);
                          setShowMuteModal(true);
                        }}
                        disabled={!r.id}
                      >
                        <span className="mr-2">🔇</span>Mute…
                      </button>
                    );
                  })()}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {nextActions?.length ? (
        <div>
          <h4 className="mb-2 font-medium">Next Actions</h4>
          <ol className="list-decimal ml-6 space-y-1 text-neutral-300">
            {nextActions.map((a, i) => <li key={i}>{a}</li>)}
          </ol>
        </div>
      ) : null}

      {/* Raw JSON accordion (optional) */}
      {rawJson && (
        <details className="rounded-lg border border-border p-3">
          <summary className="cursor-pointer text-sm">Show raw JSON (request){meta?.request_id || meta?.event_id ? ` • ${meta.request_id || meta.event_id}` : ''}</summary>
          <pre className="mt-2 text-xs bg-[#0b0f14] border border-border rounded p-3 overflow-auto">{JSON.stringify(rawJson, null, 2)}</pre>
        </details>
      )}

      {/* Raw response JSON accordion (optional) */}
      {rawResponse && (
        <details className="rounded-lg border border-border p-3">
          <summary className="cursor-pointer text-sm">Show response JSON</summary>
          <pre className="mt-2 text-xs bg-[#0b0f14] border border-border rounded p-3 overflow-auto">{JSON.stringify(rawResponse, null, 2)}</pre>
        </details>
      )}
      </div>

      <MuteModal
        isOpen={showMuteModal}
        onClose={() => setShowMuteModal(false)}
        onConfirm={handleMuteRisk}
        riskTitle={selectedRisk?.title}
      />
    </>
  );
}
import React from 'react';

type Props = {
  rewriteWithAI: boolean;
  setRewriteWithAI: (v: boolean) => void;
  llm: string;
  setLlm: (v: string) => void;
  onRun: () => void;
};

export default function CompactToolbar({ rewriteWithAI, setRewriteWithAI, llm, setLlm, onRun }: Props) {
  const [open, setOpen] = React.useState(true);

  React.useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.altKey && (e.key.toLowerCase() === 'd')) {
        e.preventDefault();
        setOpen(v => !v);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  if (!open) return null;

  return (
    <div style={{
      position: 'fixed', bottom: 12, right: 12,
      background: 'rgba(0,0,0,0.85)', color: 'white',
      borderRadius: 12, padding: 10, display: 'flex', gap: 8,
      alignItems: 'center', zIndex: 9999, boxShadow: '0 6px 18px rgba(0,0,0,0.4)'
    }}>
      <label style={{display:'flex', alignItems:'center', gap:6, fontSize:12}}>
        <input type="checkbox" checked={rewriteWithAI} onChange={e => setRewriteWithAI(e.target.checked)} />
        Rewrite with AI
      </label>

      <select
        value={llm}
        onChange={e => setLlm(e.target.value)}
        style={{ fontSize:12, padding:'4px 6px', borderRadius:8 }}
        title="LLM (Ollama-only wired)"
      >
        <option value="qwen2.5:7b">Ollama • qwen2.5:7b</option>
        <option value="llama3.1:8b">Ollama • llama3.1:8b</option>
      </select>

      <button
        onClick={onRun}
        style={{ fontSize:12, padding:'6px 10px', borderRadius:8, background:'#22c55e', color:'#07130b'}}
        title="Alt+D toggles toolbar"
      >
        Run
      </button>
    </div>
  );
}

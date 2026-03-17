import { useState } from "react";
import { Bot, Database, Globe, CheckCircle2, XCircle, Loader2, Sliders } from "lucide-react";
import { cn } from "@/lib/utils";
import { motion } from "framer-motion";

export default function SettingsPage() {
  const [provider, setProvider] = useState('openai');
  const [model, setModel] = useState('gpt-4o');
  const [temperature, setTemperature] = useState(0.7);
  const [chunkSize, setChunkSize] = useState(500);
  const [chunkOverlap, setChunkOverlap] = useState(50);
  const [topK, setTopK] = useState(5);
  const [dbConnected] = useState(true);
  const [apiUrl, setApiUrl] = useState('http://localhost:5000');
  const [testingConnection, setTestingConnection] = useState(false);

  const models: Record<string, string[]> = {
    openai: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo'],
    anthropic: ['claude-3.5-sonnet', 'claude-3-opus', 'claude-3-haiku'],
    gemini: ['gemini-1.5-pro', 'gemini-1.5-flash'],
  };

  const handleTestConnection = () => {
    setTestingConnection(true);
    setTimeout(() => setTestingConnection(false), 1500);
  };

  const Section = ({ icon: Icon, title, children }: { icon: React.ElementType; title: string; children: React.ReactNode }) => (
    <motion.section
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-panel-hover rounded-2xl p-6 space-y-5"
    >
      <div className="flex items-center gap-2.5">
        <div className="w-8 h-8 rounded-lg bg-primary/8 flex items-center justify-center">
          <Icon className="w-4 h-4 text-primary/70" />
        </div>
        <h3 className="text-sm font-bold text-foreground font-display">{title}</h3>
      </div>
      <div className="space-y-4">{children}</div>
    </motion.section>
  );

  const Label = ({ children }: { children: React.ReactNode }) => (
    <label className="text-[11px] text-muted-foreground/50 mb-1.5 block uppercase tracking-wider font-semibold">{children}</label>
  );

  return (
    <div className="h-full overflow-y-auto scrollbar-thin p-6 space-y-5 max-w-3xl">
      <h2 className="text-xl font-bold text-foreground font-display">Settings</h2>

      <Section icon={Bot} title="AI Model Settings">
        <div>
          <Label>Provider</Label>
          <div className="flex gap-2">
            {['openai', 'anthropic', 'gemini'].map(p => (
              <button
                key={p}
                onClick={() => { setProvider(p); setModel(models[p][0]); }}
                className={cn(
                  "text-xs px-5 py-2.5 rounded-xl border transition-all duration-200 font-semibold",
                  p === provider
                    ? 'bg-primary/10 text-primary border-primary/20 shadow-sm shadow-primary/5'
                    : 'bg-secondary/20 text-muted-foreground border-border/15 hover:text-foreground hover:border-border/30'
                )}
              >
                {p === 'openai' ? 'OpenAI' : p === 'anthropic' ? 'Anthropic' : 'Gemini'}
              </button>
            ))}
          </div>
        </div>
        <div>
          <Label>Model</Label>
          <select value={model} onChange={e => setModel(e.target.value)} className="input-modern font-mono">
            {models[provider].map(m => <option key={m} value={m}>{m}</option>)}
          </select>
        </div>
        <div>
          <Label>Temperature: <span className="text-primary/70">{temperature.toFixed(1)}</span></Label>
          <input type="range" min="0" max="2" step="0.1" value={temperature} onChange={e => setTemperature(parseFloat(e.target.value))} className="w-full accent-primary h-1.5 rounded-full" />
          <div className="flex justify-between text-[9px] text-muted-foreground/35 mt-1 font-mono uppercase tracking-wider">
            <span>Precise</span>
            <span>Creative</span>
          </div>
        </div>
      </Section>

      <Section icon={Sliders} title="RAG Settings">
        <div>
          <Label>Chunk Size: <span className="text-primary/70">{chunkSize}</span> characters</Label>
          <input type="range" min="200" max="2000" step="100" value={chunkSize} onChange={e => setChunkSize(parseInt(e.target.value))} className="w-full accent-primary h-1.5 rounded-full" />
          <div className="flex justify-between text-[9px] text-muted-foreground/35 mt-1 font-mono">
            <span>200</span>
            <span>2000</span>
          </div>
        </div>
        <div>
          <Label>Chunk Overlap: <span className="text-primary/70">{chunkOverlap}</span> characters</Label>
          <input type="range" min="0" max="200" step="10" value={chunkOverlap} onChange={e => setChunkOverlap(parseInt(e.target.value))} className="w-full accent-primary h-1.5 rounded-full" />
        </div>
        <div>
          <Label>Top-K Results: <span className="text-primary/70">{topK}</span></Label>
          <input type="range" min="1" max="20" step="1" value={topK} onChange={e => setTopK(parseInt(e.target.value))} className="w-full accent-primary h-1.5 rounded-full" />
          <div className="flex justify-between text-[9px] text-muted-foreground/35 mt-1 font-mono">
            <span>1</span>
            <span>20</span>
          </div>
        </div>
        <div>
          <Label>Embedding Model</Label>
          <select className="input-modern font-mono">
            <option>text-embedding-3-small</option>
            <option>text-embedding-3-large</option>
            <option>text-embedding-ada-002</option>
          </select>
        </div>
        <div>
          <Label>Minimum Similarity Score</Label>
          <input type="number" defaultValue="0.75" step="0.05" min="0" max="1" className="input-modern font-mono w-32" />
        </div>
      </Section>

      <Section icon={Database} title="Database">
        <div className="flex items-center gap-3">
          <span className="text-[11px] text-muted-foreground/50 uppercase tracking-wider font-semibold">Status:</span>
          {dbConnected ? (
            <span className="flex items-center gap-1.5 text-xs text-success/80 bg-success/8 px-2.5 py-1 rounded-lg border border-success/10 font-medium">
              <CheckCircle2 className="w-3.5 h-3.5" />Connected
            </span>
          ) : (
            <span className="flex items-center gap-1.5 text-xs text-destructive/80 bg-destructive/8 px-2.5 py-1 rounded-lg border border-destructive/10 font-medium">
              <XCircle className="w-3.5 h-3.5" />Error
            </span>
          )}
        </div>
        <div>
          <Label>Vector Database</Label>
          <select className="input-modern font-mono">
            <option>ChromaDB</option>
            <option>Pinecone</option>
            <option>Weaviate</option>
            <option>Qdrant</option>
            <option>FAISS (Local)</option>
          </select>
        </div>
        <button onClick={handleTestConnection} className="flex items-center gap-2 text-xs px-4 py-2.5 rounded-xl bg-primary/8 text-primary hover:bg-primary/12 border border-primary/10 transition-all duration-200 font-semibold">
          {testingConnection ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
          Test Connection
        </button>
      </Section>

      <Section icon={Globe} title="API Settings">
        <div>
          <Label>Backend URL</Label>
          <input value={apiUrl} onChange={e => setApiUrl(e.target.value)} className="input-modern font-mono" />
        </div>
        <div>
          <Label>API Key</Label>
          <input type="password" defaultValue="sk-xxxxxxxxxxxxxxxxxxxxxxxx" className="input-modern font-mono" />
        </div>
        <button onClick={handleTestConnection} className="flex items-center gap-2 text-xs px-4 py-2.5 rounded-xl bg-primary/8 text-primary hover:bg-primary/12 border border-primary/10 transition-all duration-200 font-semibold">
          {testingConnection ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Globe className="w-3.5 h-3.5" />}
          Test Connection
        </button>
      </Section>
    </div>
  );
}

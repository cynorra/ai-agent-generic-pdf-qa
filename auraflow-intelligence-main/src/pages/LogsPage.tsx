import { useState } from "react";
import { logsData } from "@/data/mockData";
import { cn } from "@/lib/utils";
import { Download, ArrowDown, Brain, Wrench, Database, FileSearch, AlertTriangle, Monitor } from "lucide-react";
import type { LogEntry } from "@/data/mockData";
import { motion, AnimatePresence } from "framer-motion";

const filters = ['ALL', 'LLM', 'TOOL', 'DB', 'RAG', 'ERROR'] as const;

const levelColors: Record<string, string> = {
  info: 'bg-info/10 text-info/80 border border-info/10',
  warn: 'bg-warning/10 text-warning/80 border border-warning/10',
  error: 'bg-destructive/10 text-destructive/80 border border-destructive/10',
  debug: 'bg-muted/50 text-muted-foreground/60 border border-border/10',
};

const categoryIcons: Record<string, React.ReactNode> = {
  LLM: <Brain className="w-3.5 h-3.5" />,
  TOOL: <Wrench className="w-3.5 h-3.5" />,
  DB: <Database className="w-3.5 h-3.5" />,
  RAG: <FileSearch className="w-3.5 h-3.5" />,
  ERROR: <AlertTriangle className="w-3.5 h-3.5" />,
  SYSTEM: <Monitor className="w-3.5 h-3.5" />,
};

function LogRow({ log }: { log: LogEntry }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div
      className={cn(
        "border-b border-border/8 hover:bg-secondary/8 transition-all duration-200 cursor-pointer",
        log.level === 'error' && 'bg-destructive/3'
      )}
      onClick={() => setExpanded(!expanded)}
    >
      <div className="flex items-center gap-3 px-5 py-2.5">
        <span className="text-[10px] font-mono text-muted-foreground/35 w-28 shrink-0">{log.timestamp}</span>
        <span className={cn("text-[9px] font-bold uppercase px-2 py-0.5 rounded-md", levelColors[log.level])}>
          {log.level}
        </span>
        <span className="text-muted-foreground/40">{categoryIcons[log.category]}</span>
        <span className="text-sm text-foreground/80 flex-1 truncate">{log.message}</span>
      </div>
      <AnimatePresence>
        {expanded && log.details && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="overflow-hidden"
          >
            <div className="px-5 pb-3 pl-[11.5rem]">
              <pre className="text-[11px] font-mono text-muted-foreground/50 bg-background/30 rounded-xl p-3 overflow-x-auto scrollbar-thin border border-border/10">
                {JSON.stringify(JSON.parse(log.details), null, 2)}
              </pre>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default function LogsPage() {
  const [filter, setFilter] = useState<string>('ALL');
  const [autoScroll, setAutoScroll] = useState(true);

  const filtered = filter === 'ALL' ? logsData : logsData.filter(l => l.category === filter);

  const handleExport = (format: 'json' | 'csv') => {
    const data = format === 'json'
      ? JSON.stringify(filtered, null, 2)
      : ['timestamp,level,category,message', ...filtered.map(l => `${l.timestamp},${l.level},${l.category},"${l.message}"`)].join('\n');
    const blob = new Blob([data], { type: format === 'json' ? 'application/json' : 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `logs.${format}`;
    a.click();
  };

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between px-6 py-4 border-b border-border/20">
        <h2 className="text-xl font-bold text-foreground font-display">System Logs</h2>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setAutoScroll(!autoScroll)}
            className={cn(
              "flex items-center gap-1.5 text-xs px-3.5 py-2 rounded-xl border transition-all duration-200 font-medium",
              autoScroll ? 'bg-primary/8 text-primary border-primary/15' : 'bg-secondary/30 text-muted-foreground border-border/15'
            )}
          >
            <ArrowDown className="w-3.5 h-3.5" />Auto-scroll
          </button>
          <button onClick={() => handleExport('json')} className="flex items-center gap-1.5 text-xs px-3.5 py-2 rounded-xl bg-secondary/30 text-secondary-foreground hover:bg-secondary/50 border border-border/15 transition-all duration-200 font-medium">
            <Download className="w-3.5 h-3.5" />JSON
          </button>
          <button onClick={() => handleExport('csv')} className="flex items-center gap-1.5 text-xs px-3.5 py-2 rounded-xl bg-secondary/30 text-secondary-foreground hover:bg-secondary/50 border border-border/15 transition-all duration-200 font-medium">
            <Download className="w-3.5 h-3.5" />CSV
          </button>
        </div>
      </div>

      <div className="flex items-center gap-1.5 px-6 py-3 border-b border-border/12">
        {filters.map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={cn("tab-pill", f === filter ? "tab-pill-active" : "tab-pill-inactive")}
          >
            {f}
          </button>
        ))}
        <span className="text-[10px] text-muted-foreground/35 ml-auto font-mono">{filtered.length} entries</span>
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-thin">
        {filtered.map(log => (
          <LogRow key={log.id} log={log} />
        ))}
      </div>
    </div>
  );
}

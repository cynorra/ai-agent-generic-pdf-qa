import { useState } from "react";
import { ChevronDown, ChevronRight, CheckCircle2, XCircle, Loader2 } from "lucide-react";
import type { ToolCall } from "@/data/mockData";
import { cn } from "@/lib/utils";
import { motion, AnimatePresence } from "framer-motion";

const statusIcon = {
  success: <CheckCircle2 className="w-3.5 h-3.5 text-success" />,
  error: <XCircle className="w-3.5 h-3.5 text-destructive" />,
  pending: <Loader2 className="w-3.5 h-3.5 text-pending animate-spin" />,
};

const statusDot = {
  success: 'bg-success shadow-sm shadow-success/30',
  error: 'bg-destructive shadow-sm shadow-destructive/30',
  pending: 'bg-pending shadow-sm shadow-pending/30 animate-pulse',
};

export function ToolCallCard({ tool }: { tool: ToolCall }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <motion.div
      initial={{ opacity: 0, x: 16 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.25 }}
      className="rounded-xl border border-border/30 bg-agent-tool/30 overflow-hidden backdrop-blur-sm"
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2.5 px-3.5 py-2.5 text-xs hover:bg-secondary/20 transition-all duration-200"
      >
        <motion.div animate={{ rotate: expanded ? 90 : 0 }} transition={{ duration: 0.15 }}>
          <ChevronRight className="w-3 h-3 text-muted-foreground" />
        </motion.div>
        <div className={cn("w-1.5 h-1.5 rounded-full", statusDot[tool.status])} />
        <span className="font-mono font-medium text-foreground">{tool.name}</span>
        <span className="text-muted-foreground/60 ml-auto font-mono">{tool.duration}</span>
      </button>
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="px-3.5 pb-3 space-y-2 border-t border-border/20">
              {tool.input && (
                <div className="pt-2">
                  <span className="text-[10px] text-muted-foreground/60 uppercase tracking-wider font-semibold">Input</span>
                  <pre className="text-[11px] font-mono text-muted-foreground bg-background/40 rounded-lg p-2.5 overflow-x-auto scrollbar-thin mt-1">{JSON.stringify(JSON.parse(tool.input), null, 2)}</pre>
                </div>
              )}
              {tool.output && (
                <div>
                  <span className="text-[10px] text-muted-foreground/60 uppercase tracking-wider font-semibold">Output</span>
                  <pre className={cn("text-[11px] font-mono rounded-lg p-2.5 overflow-x-auto scrollbar-thin mt-1", tool.status === 'success' ? 'text-success/70 bg-success/5' : 'text-destructive/70 bg-destructive/5')}>{JSON.stringify(JSON.parse(tool.output), null, 2)}</pre>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

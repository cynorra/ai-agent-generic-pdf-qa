import type { ChatMessage } from "@/data/mockData";
import { ToolCallCard } from "./ToolCallCard";
import { Bot, User } from "lucide-react";
import { cn } from "@/lib/utils";
import { useState } from "react";
import { motion } from "framer-motion";
import ReactMarkdown from "react-markdown";

function CitationPill({ source, page, text, score }: { source: string; page: number; text: string; score: number }) {
  const [hovered, setHovered] = useState(false);
  return (
    <span
      className="relative inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-agent-rag/40 text-[10px] font-medium text-success/80 border border-success/15 cursor-default transition-colors hover:border-success/25 hover:bg-agent-rag/60"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      📄 {source} p.{page}
      <span className="text-success/50 font-mono">({(score * 100).toFixed(0)}%)</span>
      {hovered && (
        <div className="absolute bottom-full left-0 mb-2 w-80 p-4 rounded-xl bg-popover/95 backdrop-blur-xl border border-border/50 shadow-2xl z-50 text-xs text-popover-foreground leading-relaxed">
          <div className="absolute bottom-0 left-4 w-2 h-2 bg-popover/95 border-b border-r border-border/50 transform rotate-45 translate-y-1" />
          {text}
        </div>
      )}
    </span>
  );
}

export function ChatBubble({ message, onQuickReply }: { message: ChatMessage; onQuickReply?: (text: string) => void }) {
  const isAssistant = message.role === 'assistant';

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className={cn("flex gap-3", isAssistant ? 'items-start' : 'items-start justify-end')}
    >
      {isAssistant && (
        <div className="w-8 h-8 rounded-xl bg-primary/12 flex items-center justify-center shrink-0 mt-0.5 border border-primary/10">
          <Bot className="w-4 h-4 text-primary" />
        </div>
      )}
      <div className={cn("max-w-[82%] space-y-2.5", isAssistant ? '' : 'order-first')}>
        {/* Tool calls */}
        {message.toolCalls && message.toolCalls.length > 0 && (
          <div className="space-y-1.5">
            {message.toolCalls.map((tc) => (
              <ToolCallCard key={tc.id} tool={tc} />
            ))}
          </div>
        )}

        {/* Message */}
        <div className={cn(
          "rounded-2xl px-4 py-3 text-sm leading-relaxed",
          isAssistant
            ? 'bg-agent-bubble/80 border border-border/20 backdrop-blur-sm'
            : 'bg-agent-user/80 border border-primary/15 backdrop-blur-sm'
        )}>
          <div className="prose prose-sm prose-invert max-w-none prose-p:my-1 prose-ul:my-1 prose-li:my-0.5 prose-strong:text-foreground prose-headings:text-foreground">
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>
          <span className="text-[10px] text-muted-foreground/40 mt-1.5 block font-mono">{message.timestamp}</span>
        </div>

        {/* Citations */}
        {message.citations && message.citations.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {message.citations.map((c, i) => (
              <CitationPill key={i} {...c} />
            ))}
          </div>
        )}

        {/* Quick replies */}
        {message.quickReplies && (
          <div className="flex flex-wrap gap-1.5">
            {message.quickReplies.map((qr, i) => (
              <motion.button
                key={i}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: i * 0.05 }}
                onClick={() => onQuickReply?.(qr)}
                className="text-xs px-3.5 py-1.5 rounded-xl border border-primary/20 text-primary hover:bg-primary/8 hover:border-primary/30 transition-all duration-200"
              >
                {qr}
              </motion.button>
            ))}
          </div>
        )}
      </div>
      {!isAssistant && (
        <div className="w-8 h-8 rounded-xl bg-agent-user/40 flex items-center justify-center shrink-0 mt-0.5 border border-primary/10">
          <User className="w-4 h-4 text-primary/80" />
        </div>
      )}
    </motion.div>
  );
}

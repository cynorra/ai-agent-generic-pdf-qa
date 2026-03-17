import { Bot } from "lucide-react";

export function AgentTypingIndicator() {
  return (
    <div className="flex items-start gap-3 animate-fade-in">
      <div className="w-8 h-8 rounded-xl bg-primary/12 flex items-center justify-center shrink-0 border border-primary/10">
        <Bot className="w-4 h-4 text-primary animate-pulse" />
      </div>
      <div className="bg-agent-bubble/80 border border-border/20 rounded-2xl px-5 py-3.5 flex items-center gap-3 backdrop-blur-sm">
        <div className="flex gap-1.5">
          {[0, 1, 2].map(i => (
            <div
              key={i}
              className="w-1.5 h-1.5 rounded-full bg-primary/50"
              style={{ animation: `typing-dot 1.4s infinite ${i * 0.2}s` }}
            />
          ))}
        </div>
        <span className="text-xs text-muted-foreground/60">Analyzing...</span>
      </div>
    </div>
  );
}

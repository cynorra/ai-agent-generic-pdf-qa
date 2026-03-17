import { useState, useRef, useEffect, useCallback } from "react";
import { Send, Paperclip, Plus, Trash2, Loader2, AlertCircle } from "lucide-react";
import { ChatBubble } from "@/components/chat/ChatBubble";
import { AgentTypingIndicator } from "@/components/chat/AgentTypingIndicator";
import { chatApi, Business } from "@/lib/api";
import type { ChatMessage, Citation, ToolCall } from "@/data/mockData";
import { cn } from "@/lib/utils";
import { motion, AnimatePresence } from "framer-motion";
import { useToast } from "@/hooks/use-toast";

function ActivityPanel({ messages }: { messages: ChatMessage[] }) {
  const allToolCalls = messages.flatMap(m => m.toolCalls || []);
  const allCitations = messages.flatMap(m => m.citations || []);

  return (
    <div className="h-full flex flex-col border-l border-border/20 bg-card/20 backdrop-blur-sm">
      <div className="p-4 border-b border-border/20">
        <h3 className="text-[11px] font-bold text-foreground uppercase tracking-[0.15em] font-display">Agent Activity</h3>
      </div>
      <div className="flex-1 overflow-y-auto scrollbar-thin p-4 space-y-5">
        {allToolCalls.length === 0 && allCitations.length === 0 && (
          <div className="text-center py-8">
            <p className="text-xs text-muted-foreground/40">No activity yet</p>
            <p className="text-[10px] text-muted-foreground/25 mt-1">Tool calls and RAG results will appear here when you ask a question</p>
          </div>
        )}

        {/* Tool Calls */}
        {allToolCalls.length > 0 && (
          <div>
            <h4 className="text-[10px] font-bold text-muted-foreground/70 uppercase tracking-[0.12em] mb-2.5 flex items-center gap-1.5">
              <span className="text-primary">🔧</span> Tool Calls
              <span className="ml-auto text-primary/60 font-mono">{allToolCalls.length}</span>
            </h4>
            <div className="space-y-1">
              {allToolCalls.map(tc => (
                <div key={tc.id} className="flex flex-col gap-1 p-2 rounded-lg bg-secondary/20 border border-border/10 transition-colors hover:bg-secondary/30">
                  <div className="flex items-center gap-2.5 text-[11px]">
                    <span className={cn("w-1.5 h-1.5 rounded-full", tc.status === 'success' ? 'bg-success shadow-sm shadow-success/30' : tc.status === 'error' ? 'bg-destructive' : 'bg-pending animate-pulse')} />
                    <span className="font-mono font-medium text-foreground/90">{tc.name}</span>
                    <span className="text-muted-foreground/50 ml-auto font-mono text-[10px]">{tc.duration}</span>
                  </div>
                  {tc.input && (
                    <div className="text-[9px] font-mono text-muted-foreground/40 mt-1 bg-black/10 p-1.5 rounded overflow-x-auto whitespace-pre">
                      {tc.input}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* RAG Chunks */}
        {allCitations.length > 0 && (
          <div>
            <h4 className="text-[10px] font-bold text-muted-foreground/70 uppercase tracking-[0.12em] mb-2.5 flex items-center gap-1.5">
              <span className="text-success">📄</span> Found Sources
              <span className="ml-auto text-success/60 font-mono">{allCitations.length}</span>
            </h4>
            <div className="space-y-2">
              {allCitations.map((c, i) => (
                <RAGChunkMini key={i} citation={c} />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function RAGChunkMini({ citation }: { citation: Citation }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="rounded-xl bg-agent-rag/20 border border-success/8 p-3">
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-[10px] font-mono text-muted-foreground/70">{citation.source} p.{citation.page}</span>
        <span className="text-[10px] font-mono text-success/80 font-semibold">{(citation.score * 100).toFixed(0)}%</span>
      </div>
      <div className="w-full bg-secondary/30 rounded-full h-1 mb-2 overflow-hidden">
        <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${citation.score * 100}%` }}
            transition={{ duration: 0.6, ease: "easeOut" }}
            className="bg-success/60 h-1 rounded-full"
        />
      </div>
      <button onClick={() => setExpanded(!expanded)} className="text-[10px] text-muted-foreground/50 hover:text-muted-foreground transition-colors">
        {expanded ? 'Hide' : 'Preview'}
      </button>
      <AnimatePresence>
        {expanded && (
          <motion.p
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="text-[10px] text-muted-foreground/60 mt-1.5 leading-relaxed overflow-hidden"
          >
            {citation.text}
          </motion.p>
        )}
      </AnimatePresence>
    </div>
  );
}

export default function ChatPage() {
  const { toast } = useToast();
  const [businesses, setBusinesses] = useState<Business[]>([]);
  const [selectedBusiness, setSelectedBusiness] = useState<string>("");
  const [sessionId, setSessionId] = useState<string | undefined>(undefined);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [loading, setLoading] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const fetchBiz = async () => {
      try {
        setLoading(true);
        const data = await chatApi.listBusinesses();
        setBusinesses(data.businesses);
        if (data.businesses.length > 0) {
          setSelectedBusiness(data.businesses[0].name);
        }
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchBiz();
  }, []);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping, scrollToBottom]);

  const handleSend = async (text?: string) => {
    const content = text || inputValue.trim();
    if (!content || !selectedBusiness) return;

    const userMsg: ChatMessage = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content,
      timestamp: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages(prev => [...prev, userMsg]);
    setInputValue("");
    setIsTyping(true);

    try {
      const response = await chatApi.sendMessage({
        message: content,
        session_id: sessionId,
        business_name: selectedBusiness,
      });

      setSessionId(response.session_id);

      const agentMsg: ChatMessage = {
        id: `msg-${Date.now() + 1}`,
        role: 'assistant',
        content: response.response,
        timestamp: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
        // backend'den tool call ve citation şu an gelmiyor ama audit endpoint'inden çekilebilir
        // Gelecekte backend Response modeline bunlar eklenebilir
      };
      
      setMessages(prev => [...prev, agentMsg]);
    } catch (error: any) {
      console.error("Chat error:", error);
      toast({
        title: "Connection Error",
        description: error.response?.data?.detail || "Could not connect to server. Please ensure backend is running.",
        variant: "destructive",
      });
      // Add error as message
      setMessages(prev => [...prev, {
        id: `err-${Date.now()}`,
        role: 'assistant',
        content: "❌ An error occurred. Please try again.",
        timestamp: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
      }]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleNewChat = () => {
    setMessages([]);
    setSessionId(undefined);
    setIsTyping(false);
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-primary animate-spin" />
      </div>
    );
  }

  return (
    <div className="h-full flex">
      {/* Chat area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-border/20 bg-card/15 backdrop-blur-sm">
          <div className="flex items-center gap-4">
            <div className="flex flex-col">
              <h2 className="text-sm font-bold text-foreground font-display">AuraFlow Chat</h2>
              <span className="text-[10px] text-muted-foreground/40 font-mono">{messages.length} messages</span>
            </div>
            
            <div className="h-4 w-[1px] bg-border/20 mx-1" />
            
            <div className="flex items-center gap-2">
              <span className="text-[10px] uppercase font-bold text-muted-foreground/50">Business:</span>
              <select 
                value={selectedBusiness}
                onChange={e => {
                  setSelectedBusiness(e.target.value);
                  handleNewChat();
                }}
                className="bg-secondary/40 border border-border/10 rounded-lg text-[11px] px-2 py-1 focus:outline-none focus:border-primary/30 transition-colors"
              >
                {businesses.map(b => (
                  <option key={b.id} value={b.name}>{b.name}</option>
                ))}
              </select>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            <button
              onClick={handleNewChat}
              className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-xl bg-primary/8 text-primary hover:bg-primary/12 border border-primary/10 transition-all duration-200 font-medium"
            >
              <Plus className="w-3.5 h-3.5" />
              New Chat
            </button>
            <button
              onClick={() => setMessages([])}
              className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-xl bg-secondary/30 text-muted-foreground hover:text-foreground hover:bg-secondary/50 border border-border/15 transition-all duration-200"
            >
              <Trash2 className="w-3.5 h-3.5" />
              Clear
            </button>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto scrollbar-thin p-5 space-y-5">
          {businesses.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center space-y-4 opacity-60">
              <AlertCircle className="w-12 h-12 text-amber-500/50" />
              <div className="text-center">
                <p className="text-sm font-semibold">No business/PDF found yet.</p>
                <p className="text-xs text-muted-foreground mt-1">Please start by uploading a PDF from "Documents" page.</p>
              </div>
            </div>
          ) : messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center">
              <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                className="text-center space-y-4 max-w-sm"
              >
                <div className="w-16 h-16 bg-gradient-to-tr from-primary/20 to-primary/5 rounded-3xl flex items-center justify-center mx-auto mb-6 shadow-xl shadow-primary/5 border border-primary/10">
                  <span className="text-3xl">✨</span>
                </div>
                <h3 className="text-lg font-bold font-display">Hello! I am AuraFlow.</h3>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  I analyzed documents about **{selectedBusiness}**.
                  You can ask anything about appointments, orders, or document contents.
                </p>
                <div className="pt-4 flex flex-wrap justify-center gap-2">
                  {["What can you do?", "How do I book?", "What products are available?"].map(hint => (
                    <button 
                      key={hint}
                      onClick={() => handleSend(hint)}
                      className="text-[10px] px-3 py-1.5 rounded-full bg-secondary/40 border border-border/15 hover:border-primary/30 transition-colors"
                    >
                      {hint}
                    </button>
                  ))}
                </div>
              </motion.div>
            </div>
          ) : (
            <AnimatePresence mode="popLayout">
              {messages.map(msg => (
                <ChatBubble key={msg.id} message={msg} onQuickReply={(text) => handleSend(text)} />
              ))}
            </AnimatePresence>
          )}
          {isTyping && <AgentTypingIndicator />}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="p-4 border-t border-border/20">
          <div className={cn(
            "flex items-center gap-3 bg-secondary/30 rounded-2xl px-4 py-3 border border-border/20 focus-within:border-primary/30 focus-within:shadow-lg focus-within:shadow-primary/5 transition-all duration-300",
            businesses.length === 0 && "opacity-50 pointer-events-none"
          )}>
            <button className="text-muted-foreground/50 hover:text-muted-foreground transition-colors">
              <Paperclip className="w-4 h-4" />
            </button>
            <input
              value={inputValue}
              onChange={e => setInputValue(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleSend()}
              disabled={businesses.length === 0}
              placeholder={businesses.length === 0 ? "Upload a PDF first..." : `Ask a question about ${selectedBusiness}...`}
              className="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground/40 focus:outline-none"
            />
            <button
              onClick={() => handleSend()}
              disabled={!inputValue.trim() || businesses.length === 0}
              className={cn(
                "w-9 h-9 rounded-xl flex items-center justify-center transition-all duration-200",
                inputValue.trim()
                  ? "bg-gradient-primary text-primary-foreground shadow-md shadow-primary/20 hover:shadow-lg hover:shadow-primary/30"
                  : "bg-secondary/50 text-muted-foreground/30"
              )}
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Activity panel */}
      <div className="w-80 hidden lg:block">
        <ActivityPanel messages={messages} />
      </div>
    </div>
  );
}

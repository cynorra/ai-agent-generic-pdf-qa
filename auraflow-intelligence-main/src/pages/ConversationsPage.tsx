import { conversationsData } from "@/data/mockData";
import { MessageSquare, Clock, Hash, Trash2, Search } from "lucide-react";
import { useState } from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import type { Conversation } from "@/data/mockData";

export default function ConversationsPage() {
  const [conversations, setConversations] = useState<Conversation[]>(conversationsData);
  const [search, setSearch] = useState("");

  const filtered = search
    ? conversations.filter(c => c.title.toLowerCase().includes(search.toLowerCase()) || c.lastMessage.toLowerCase().includes(search.toLowerCase()))
    : conversations;

  const handleDelete = (id: string) => {
    setConversations(prev => prev.filter(c => c.id !== id));
  };

  return (
    <div className="h-full overflow-y-auto scrollbar-thin p-6 space-y-6 max-w-4xl">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-foreground font-display">Conversations</h2>
          <p className="text-[11px] text-muted-foreground/50 font-mono mt-1">{conversations.length} conversations</p>
        </div>
      </div>

      {/* Search */}
      <div className="flex items-center gap-3 bg-secondary/20 rounded-xl px-4 py-2.5 border border-border/15 focus-within:border-primary/25 focus-within:shadow-lg focus-within:shadow-primary/5 transition-all duration-300">
        <Search className="w-4 h-4 text-muted-foreground/40" />
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Search in conversations..."
          className="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground/30 focus:outline-none"
        />
      </div>

      {/* List */}
      <div className="grid gap-3">
        {filtered.map((conv, i) => (
          <motion.div
            key={conv.id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.04 }}
            className="glass-panel-hover rounded-2xl p-5 cursor-pointer group"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-start gap-4 min-w-0 flex-1">
                <div className="w-10 h-10 rounded-xl bg-primary/8 flex items-center justify-center shrink-0 mt-0.5">
                  <MessageSquare className="w-4.5 h-4.5 text-primary/60" />
                </div>
                <div className="min-w-0 flex-1">
                  <h3 className="text-sm font-semibold text-foreground truncate">{conv.title}</h3>
                  <p className="text-xs text-muted-foreground/50 mt-1 truncate">{conv.lastMessage}</p>
                  <div className="flex items-center gap-4 mt-2.5">
                    <span className="flex items-center gap-1.5 text-[10px] text-muted-foreground/35">
                      <Hash className="w-3 h-3" />{conv.messageCount} messages
                    </span>
                    <span className="flex items-center gap-1.5 text-[10px] text-muted-foreground/35">
                      <Clock className="w-3 h-3" />{conv.updatedAt}
                    </span>
                  </div>
                </div>
              </div>
              <button
                onClick={(e) => { e.stopPropagation(); handleDelete(conv.id); }}
                className="p-2 rounded-lg text-muted-foreground/20 hover:text-destructive hover:bg-destructive/8 transition-all opacity-0 group-hover:opacity-100"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </motion.div>
        ))}

        {filtered.length === 0 && (
          <div className="text-center py-12">
            <MessageSquare className="w-8 h-8 text-muted-foreground/20 mx-auto mb-3" />
            <p className="text-sm text-muted-foreground/40">No conversations found</p>
          </div>
        )}
      </div>
    </div>
  );
}

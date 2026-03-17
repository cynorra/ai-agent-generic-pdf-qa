// ── Core Types ──

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  toolCalls?: ToolCall[];
  citations?: Citation[];
  quickReplies?: string[];
}

export interface ToolCall {
  id: string;
  name: string;
  status: 'success' | 'error' | 'pending';
  duration: string;
  input?: string;
  output?: string;
}

export interface Citation {
  source: string;
  page: number;
  text: string;
  score: number;
}

export interface UploadedDocument {
  id: string;
  name: string;
  size: string;
  pages: number;
  chunks: number;
  status: 'uploading' | 'processing' | 'indexed' | 'error';
  uploadedAt: string;
  progress?: number;
}

export interface Conversation {
  id: string;
  title: string;
  lastMessage: string;
  messageCount: number;
  createdAt: string;
  updatedAt: string;
}

export interface LogEntry {
  id: string;
  timestamp: string;
  level: 'info' | 'warn' | 'error' | 'debug';
  category: 'LLM' | 'TOOL' | 'DB' | 'RAG' | 'ERROR' | 'SYSTEM';
  message: string;
  details?: string;
}

export interface RAGChunk {
  id: string;
  text: string;
  page: number;
  score: number;
  source: string;
  embedded: boolean;
}

// ── Documents ──
export const documentsData: UploadedDocument[] = [
  { id: 'd1', name: 'company-handbook.pdf', size: '2.4 MB', pages: 45, chunks: 128, status: 'indexed', uploadedAt: '2 hours ago' },
  { id: 'd2', name: 'product-catalog-2026.pdf', size: '8.1 MB', pages: 92, chunks: 247, status: 'indexed', uploadedAt: '1 day ago' },
  { id: 'd3', name: 'faq-document.pdf', size: '540 KB', pages: 12, chunks: 34, status: 'indexed', uploadedAt: '3 days ago' },
  { id: 'd4', name: 'pricing-guide.pdf', size: '1.2 MB', pages: 18, chunks: 52, status: 'indexed', uploadedAt: '5 days ago' },
];

// ── Conversations ──
export const conversationsData: Conversation[] = [
  { id: 'conv-1', title: 'Product pricing questions', lastMessage: 'The enterprise plan starts at...', messageCount: 8, createdAt: '2026-03-08', updatedAt: '5 min ago' },
  { id: 'conv-2', title: 'Refund policy inquiry', lastMessage: 'According to our handbook...', messageCount: 4, createdAt: '2026-03-08', updatedAt: '1 hour ago' },
  { id: 'conv-3', title: 'Technical specifications', lastMessage: 'The product supports...', messageCount: 12, createdAt: '2026-03-07', updatedAt: '3 hours ago' },
  { id: 'conv-4', title: 'Shipping information', lastMessage: 'We offer free shipping on...', messageCount: 6, createdAt: '2026-03-07', updatedAt: 'Yesterday' },
  { id: 'conv-5', title: 'Account setup help', lastMessage: 'To create your account...', messageCount: 3, createdAt: '2026-03-06', updatedAt: '2 days ago' },
];

// ── RAG Chunks ──
export const ragChunks: RAGChunk[] = [
  { id: 'c1', text: 'Enterprise Plan — Starting at $99/month. Includes unlimited users, priority support, custom integrations, and dedicated account manager. Annual billing available with 20% discount.', page: 8, score: 0.96, source: 'pricing-guide.pdf', embedded: true },
  { id: 'c2', text: 'Refund Policy — Full refund available within 30 days of purchase. Pro-rated refunds for annual plans after the first month. Contact support@company.com to initiate.', page: 3, score: 0.93, source: 'company-handbook.pdf', embedded: true },
  { id: 'c3', text: 'Product dimensions: 12.5" x 8.3" x 0.7". Weight: 2.1 lbs. Available in Silver, Space Gray, and Midnight Blue. Battery life: up to 14 hours.', page: 15, score: 0.91, source: 'product-catalog-2026.pdf', embedded: true },
  { id: 'c4', text: 'Free shipping on orders over $50. Standard delivery: 3-5 business days. Express delivery: 1-2 business days ($12.99). International shipping available to 40+ countries.', page: 6, score: 0.89, source: 'company-handbook.pdf', embedded: true },
  { id: 'c5', text: 'Account Setup — Visit app.company.com/signup. Enter your work email and create a password. Verify your email within 24 hours. Invite team members from Settings > Team.', page: 2, score: 0.87, source: 'faq-document.pdf', embedded: true },
  { id: 'c6', text: 'API Rate Limits — Free tier: 100 requests/hour. Pro: 1,000 requests/hour. Enterprise: 10,000 requests/hour. Custom limits available upon request.', page: 11, score: 0.85, source: 'product-catalog-2026.pdf', embedded: true },
];

// ── Sample Chat ──
export const sampleChat: ChatMessage[] = [
  {
    id: '1',
    role: 'assistant',
    content: "Merhaba! 👋 Ben yapay zeka asistanınızım. Yüklediğiniz dokümanlardaki bilgilere dayanarak sorularınızı yanıtlayabilirim.\n\nŞu anda **4 doküman** indekslenmiş durumda. Size nasıl yardımcı olabilirim?",
    timestamp: '14:20',
    quickReplies: ['Hangi dokümanlar yüklü?', 'Fiyatlandırma hakkında bilgi', 'İade politikası nedir?'],
  },
];

// ── Logs Data ──
export const logsData: LogEntry[] = [
  { id: 'l1', timestamp: '14:15:32.847', level: 'info', category: 'LLM', message: 'LLM response generated', details: '{"tokens_in": 2847, "tokens_out": 312, "latency_ms": 1842, "model": "gpt-4o"}' },
  { id: 'l2', timestamp: '14:15:32.201', level: 'info', category: 'TOOL', message: 'Tool executed: search_knowledge', details: '{"duration_ms": 287, "results": 3}' },
  { id: 'l3', timestamp: '14:15:31.914', level: 'info', category: 'RAG', message: 'Retrieved 3 chunks from pricing-guide.pdf', details: '{"top_score": 0.96, "chunks": 3, "threshold": 0.75}' },
  { id: 'l4', timestamp: '14:15:31.500', level: 'info', category: 'DB', message: 'Conversation history saved', details: '{"conversation_id": "conv-1", "messages": 8}' },
  { id: 'l5', timestamp: '14:15:30.102', level: 'debug', category: 'SYSTEM', message: 'Agent loop iteration completed' },
  { id: 'l6', timestamp: '14:15:29.445', level: 'info', category: 'RAG', message: 'Embedding generated for query', details: '{"model": "text-embedding-3-small", "dimensions": 1536}' },
  { id: 'l7', timestamp: '14:15:28.900', level: 'warn', category: 'RAG', message: 'Low confidence chunk filtered', details: '{"score": 0.42, "threshold": 0.75, "source": "faq-document.pdf", "page": 8}' },
  { id: 'l8', timestamp: '14:15:27.321', level: 'info', category: 'LLM', message: 'Function call: search_knowledge', details: '{"function": "search_knowledge", "args": {"query": "enterprise pricing"}}' },
  { id: 'l9', timestamp: '14:15:26.100', level: 'info', category: 'SYSTEM', message: 'New chat session started', details: '{"session_id": "sess_a8f2k9d1"}' },
  { id: 'l10', timestamp: '14:14:58.700', level: 'error', category: 'ERROR', message: 'PDF parsing failed for corrupted file', details: '{"error": "INVALID_PDF", "file": "broken.pdf"}' },
  { id: 'l11', timestamp: '14:14:45.200', level: 'info', category: 'RAG', message: 'Document indexed: company-handbook.pdf', details: '{"chunks": 128, "pages": 45, "duration_ms": 8400}' },
  { id: 'l12', timestamp: '14:14:44.800', level: 'info', category: 'TOOL', message: 'Embedding batch completed', details: '{"batch_size": 50, "duration_ms": 1200}' },
  { id: 'l13', timestamp: '14:14:22.100', level: 'warn', category: 'LLM', message: 'Token limit approaching', details: '{"used": 3847, "limit": 4096, "percentage": 93.9}' },
  { id: 'l14', timestamp: '14:14:10.500', level: 'info', category: 'RAG', message: 'Knowledge base re-indexed', details: '{"total_chunks": 461, "documents": 4, "duration_ms": 12400}' },
  { id: 'l15', timestamp: '14:13:55.000', level: 'debug', category: 'SYSTEM', message: 'Health check passed', details: '{"db": "connected", "llm": "ready", "uptime_s": 84200}' },
];

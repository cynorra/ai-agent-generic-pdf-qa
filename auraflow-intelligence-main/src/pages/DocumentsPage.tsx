import { useState, useCallback, useEffect } from "react";
import { useDropzone } from "react-dropzone";
import { chatApi, Business } from "@/lib/api";
import { Search, RefreshCw, FileText, CheckCircle2, Upload, Trash2, Loader2, Plus, Info, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { motion, AnimatePresence } from "framer-motion";
import { useToast } from "@/hooks/use-toast";

interface UploadingFile {
  id: string;
  name: string;
  progress: number;
  status: 'uploading' | 'processing' | 'indexed' | 'error';
}

export default function DocumentsPage() {
  const { toast } = useToast();
  const [businesses, setBusinesses] = useState<Business[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [reindexing, setReindexing] = useState(false);
  const [uploadingFiles, setUploadingFiles] = useState<UploadingFile[]>([]);
  
  // New business fields
  const [businessName, setBusinessName] = useState("");
  const [businessType, setBusinessType] = useState("generic");
  const [description, setDescription] = useState("");

  const fetchBusinesses = useCallback(async () => {
    try {
      setLoading(true);
      const data = await chatApi.listBusinesses();
      setBusinesses(data.businesses);
    } catch (error) {
      console.error("Failed to fetch businesses:", error);
      toast({
        title: "Error",
        description: "Failed to load businesses",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  }, [toast]);

  const handleDelete = async (id: string) => {
    if (!confirm("Are you sure you want to delete this business and all related data?")) return;
    
    try {
      await chatApi.deleteBusiness(id);
      toast({
        title: "Success",
        description: "Business deleted successfully",
      });
      fetchBusinesses(); // Refresh list
    } catch (error) {
      console.error("Failed to delete business:", error);
      toast({
        title: "Error",
        description: "An error occurred during deletion",
        variant: "destructive",
      });
    }
  };

  useEffect(() => {
    fetchBusinesses();
  }, [fetchBusinesses]);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (!businessName) {
      toast({
        title: "Missing Information",
        description: "Please enter business name first.",
        variant: "destructive",
      });
      return;
    }

    for (const file of acceptedFiles) {
      const uploadId = `upload-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
      
      const newUpload: UploadingFile = {
        id: uploadId,
        name: file.name,
        progress: 10,
        status: 'uploading',
      };

      setUploadingFiles(prev => [...prev, newUpload]);

      try {
        setUploadingFiles(prev => prev.map(f => f.id === uploadId ? { ...f, progress: 30 } : f));
        
        const result = await chatApi.loadPdf(file, businessName, businessType, description);
        
        setUploadingFiles(prev => prev.map(f => f.id === uploadId ? { ...f, progress: 100, status: 'indexed' } : f));
        
        toast({
          title: "Success",
          description: `'${file.name}' uploaded and indexed for '${businessName}'.`,
        });

        // Refresh list
        fetchBusinesses();
        
        // Remove from uploading list after a short delay
        setTimeout(() => {
          setUploadingFiles(prev => prev.filter(f => f.id !== uploadId));
        }, 2000);

      } catch (error) {
        console.error("Upload failed:", error);
        setUploadingFiles(prev => prev.map(f => f.id === uploadId ? { ...f, status: 'error' } : f));
        toast({
          title: "Upload Error",
          description: `An error occurred while uploading ${file.name}.`,
          variant: "destructive",
        });
      }
    }
  }, [businessName, businessType, description, fetchBusinesses, toast]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxSize: 50 * 1024 * 1024,
  });

  const handleReindex = () => {
    setReindexing(true);
    setTimeout(() => {
      setReindexing(false);
      fetchBusinesses();
    }, 2500);
  };

  const filteredBusinesses = businesses.filter(b => 
    b.name.toLowerCase().includes(search.toLowerCase()) || 
    b.type.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="h-full overflow-y-auto scrollbar-thin p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-foreground font-display">Businesses and Documents</h2>
          <p className="text-[11px] text-muted-foreground/50 font-mono mt-1">
            {businesses.length} registered businesses
          </p>
        </div>
        <button
          onClick={handleReindex}
          disabled={reindexing}
          className={cn(
            "flex items-center gap-2 text-xs px-4 py-2 rounded-xl bg-primary/8 text-primary hover:bg-primary/12 border border-primary/10 transition-all duration-200 font-semibold",
            reindexing && "opacity-50"
          )}
        >
          <RefreshCw className={cn("w-3.5 h-3.5", reindexing && "animate-spin")} />
          {reindexing ? 'Refreshing...' : 'Refresh List'}
        </button>
      </div>

      {/* New Business Form */}
      <div className="glass-panel rounded-2xl p-6 space-y-4">
        <div className="flex items-center gap-2 mb-2">
          <Plus className="w-4 h-4 text-primary" />
          <h3 className="text-sm font-bold text-foreground font-display">New Business Registration & PDF Upload</h3>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <label className="text-[10px] uppercase tracking-wider font-bold text-muted-foreground/70 ml-1">Business Name</label>
            <input 
              value={businessName}
              onChange={e => setBusinessName(e.target.value)}
              placeholder="Ex: My Coffee Shop"
              className="w-full bg-secondary/20 border border-border/10 rounded-xl px-4 py-2 text-sm focus:outline-none focus:border-primary/30 transition-colors"
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-[10px] uppercase tracking-wider font-bold text-muted-foreground/70 ml-1">Business Type</label>
            <select 
              value={businessType}
              onChange={e => setBusinessType(e.target.value)}
              className="w-full bg-secondary/20 border border-border/10 rounded-xl px-4 py-2 text-sm focus:outline-none focus:border-primary/30 transition-colors"
            >
              <option value="generic">General</option>
              <option value="restaurant">Restaurant / Cafe</option>
              <option value="service">Service Industry</option>
              <option value="retail">Retail</option>
              <option value="medical">Health</option>
            </select>
          </div>
        </div>
        
        <div className="space-y-1.5">
          <label className="text-[10px] uppercase tracking-wider font-bold text-muted-foreground/70 ml-1">Description (Optional)</label>
          <textarea 
            value={description}
            onChange={e => setDescription(e.target.value)}
            placeholder="Brief info about business..."
            className="w-full bg-secondary/20 border border-border/10 rounded-xl px-4 py-2 text-sm focus:outline-none focus:border-primary/30 transition-colors min-h-[80px]"
          />
        </div>

        {/* Upload Zone */}
        <div
          {...getRootProps()}
          className={cn(
            "border-2 border-dashed rounded-2xl p-8 flex flex-col items-center gap-3 transition-all duration-300 cursor-pointer group relative overflow-hidden",
            !businessName && "opacity-50 cursor-not-allowed grayscale",
            isDragActive
              ? "border-primary/40 bg-primary/5"
              : "border-border/20 hover:border-primary/20 hover:bg-primary/3"
          )}
        >
          <input {...getInputProps()} disabled={!businessName} />
          <div className={cn(
            "w-12 h-12 rounded-xl flex items-center justify-center transition-all duration-300",
            isDragActive ? "bg-primary/15 scale-110" : "bg-primary/8 group-hover:scale-110 group-hover:bg-primary/12"
          )}>
            <Upload className={cn("w-5 h-5 transition-colors", isDragActive ? "text-primary" : "text-primary/50 group-hover:text-primary/70")} />
          </div>
          <div className="text-center">
            <p className="text-sm text-foreground/70 font-semibold">
              {businessName ? "Drag & drop PDF file here" : "Enter business name first"}
            </p>
            <p className="text-[11px] text-muted-foreground/40 mt-1">Max 50MB</p>
          </div>
        </div>
        
        {!businessName && (
          <div className="flex items-center gap-2 text-[10px] text-amber-500/80 bg-amber-500/5 px-3 py-2 rounded-lg border border-amber-500/10">
            <Info className="w-3 h-3" />
            You must fill in the business name before uploading a PDF.
          </div>
        )}
      </div>

      {/* Uploading Files */}
      <AnimatePresence>
        {uploadingFiles.map(file => (
          <motion.div
            key={file.id}
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="glass-panel rounded-2xl p-4 flex items-center gap-4"
          >
            <div className="w-11 h-11 rounded-xl bg-primary/8 flex items-center justify-center shrink-0">
              {file.status === 'error' ? (
                <X className="w-5 h-5 text-destructive" />
              ) : (
                <Loader2 className="w-5 h-5 text-primary/70 animate-spin" />
              )}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2.5">
                <p className="text-sm font-semibold text-foreground truncate">{file.name}</p>
                <span className={cn(
                  "text-[9px] px-2 py-0.5 rounded-md font-semibold uppercase tracking-wider border",
                  file.status === 'error' ? "bg-destructive/8 text-destructive border-destructive/10" : "bg-pending/8 text-pending/70 border-pending/10"
                )}>
                  {file.status === 'uploading' ? 'Uploading' : file.status === 'error' ? 'Error' : 'Processing'}
                </span>
              </div>
              <div className="w-full bg-secondary/20 rounded-full h-1.5 mt-2 overflow-hidden">
                <motion.div
                  className={cn("h-1.5 rounded-full", file.status === 'error' ? "bg-destructive/50" : "bg-primary/60")}
                  initial={{ width: 0 }}
                  animate={{ width: `${file.progress || 0}%` }}
                  transition={{ duration: 0.3 }}
                />
              </div>
            </div>
            <span className="text-[10px] font-mono text-muted-foreground/40">{file.progress || 0}%</span>
          </motion.div>
        ))}
      </AnimatePresence>

      {/* Business List */}
      <div className="space-y-4">
        <h3 className="text-sm font-bold text-foreground font-display flex items-center gap-2">
          <FileText className="w-4 h-4 text-primary" />
          Registered Businesses ({businesses.length})
        </h3>
        
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 text-primary/30 animate-spin" />
          </div>
        ) : businesses.length === 0 ? (
          <div className="text-center py-12 glass-panel rounded-2xl border-dashed">
            <p className="text-sm text-muted-foreground">No business records found yet.</p>
          </div>
        ) : (
          <div className="grid gap-3">
            {filteredBusinesses.map((biz, i) => (
              <motion.div
                key={biz.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.03 }}
                className="glass-panel-hover rounded-2xl p-4 flex items-center gap-4 group"
              >
                <div className="w-11 h-11 rounded-xl bg-primary/5 flex items-center justify-center shrink-0">
                  <span className="text-lg">🏢</span>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2.5">
                    <p className="text-sm font-semibold text-foreground truncate">{biz.name}</p>
                    <span className="text-[9px] px-2 py-0.5 rounded-md bg-secondary/50 text-muted-foreground font-semibold uppercase tracking-wider">{biz.type}</span>
                  </div>
                  <p className="text-[10px] text-muted-foreground/50 font-mono mt-0.5 truncate">
                    ID: {biz.id} • {biz.description || "No description"}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-muted-foreground/30 invisible group-hover:visible transition-all">Completed</span>
                  <div className="flex items-center gap-2 text-foreground/20 group-hover:text-primary/50 transition-all">
                    <CheckCircle2 className="w-4 h-4" />
                  </div>
                  <button 
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDelete(biz.id);
                    }}
                    className="p-2 rounded-lg hover:bg-destructive/10 hover:text-destructive text-muted-foreground/20 transition-all ml-1"
                    title="Delete"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

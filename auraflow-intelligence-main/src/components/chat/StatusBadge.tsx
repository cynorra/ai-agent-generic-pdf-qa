import { cn } from "@/lib/utils";

type Status = 'pending' | 'confirmed' | 'in_progress' | 'completed' | 'cancelled' | 'booked' | 'success' | 'error';

const statusConfig: Record<Status, { label: string; className: string }> = {
  pending: { label: 'Pending', className: 'bg-pending/10 text-pending/80 border-pending/15' },
  confirmed: { label: 'Confirmed', className: 'bg-success/10 text-success/80 border-success/15' },
  in_progress: { label: 'In Progress', className: 'bg-info/10 text-info/80 border-info/15' },
  completed: { label: 'Completed', className: 'bg-muted/50 text-muted-foreground/60 border-border/15' },
  cancelled: { label: 'Cancelled', className: 'bg-destructive/10 text-destructive/80 border-destructive/15' },
  booked: { label: 'Booked', className: 'bg-info/10 text-info/80 border-info/15' },
  success: { label: 'Success', className: 'bg-success/10 text-success/80 border-success/15' },
  error: { label: 'Error', className: 'bg-destructive/10 text-destructive/80 border-destructive/15' },
};

export function StatusBadge({ status }: { status: Status }) {
  const config = statusConfig[status] || statusConfig.pending;
  return (
    <span className={cn("inline-flex items-center px-2.5 py-1 rounded-lg text-[10px] font-bold uppercase tracking-[0.08em] border", config.className)}>
      {config.label}
    </span>
  );
}

import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { AppSidebar } from "./AppSidebar";
import { Wifi, WifiOff } from "lucide-react";
import { useState } from "react";

export function AppLayout({ children }: { children: React.ReactNode }) {
  const [connected] = useState(true);

  return (
    <SidebarProvider>
      <div className="min-h-screen flex w-full bg-mesh">
        <AppSidebar />
        <div className="flex-1 flex flex-col min-w-0">
          <header className="h-13 flex items-center justify-between border-b border-border/30 px-5 bg-card/40 backdrop-blur-xl shrink-0">
            <div className="flex items-center gap-3">
              <SidebarTrigger className="text-muted-foreground hover:text-foreground transition-colors" />
            </div>
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2.5 text-xs">
                {connected ? (
                  <>
                    <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-success/8 border border-success/15">
                      <Wifi className="w-3 h-3 text-success" />
                      <span className="text-success/80 font-medium">Connected</span>
                    </div>
                    <span className="text-muted-foreground/60 font-mono text-[11px]">localhost:5000</span>
                  </>
                ) : (
                  <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-destructive/8 border border-destructive/15">
                    <WifiOff className="w-3 h-3 text-destructive" />
                    <span className="text-destructive/80 font-medium">Disconnected</span>
                  </div>
                )}
              </div>
            </div>
          </header>
          <main className="flex-1 overflow-hidden">
            {children}
          </main>
        </div>
      </div>
    </SidebarProvider>
  );
}

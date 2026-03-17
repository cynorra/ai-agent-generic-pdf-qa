import { MessageSquare, FileText, History, Terminal, Settings, Sparkles } from "lucide-react";
import { NavLink } from "@/components/NavLink";
import { useLocation } from "react-router-dom";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar";
import { documentsData } from "@/data/mockData";

const navItems = [
  { title: "Chat", url: "/", icon: MessageSquare },
  { title: "Documents", url: "/documents", icon: FileText },
  { title: "Conversations", url: "/conversations", icon: History },
  { title: "Logs", url: "/logs", icon: Terminal },
  { title: "Settings", url: "/settings", icon: Settings },
];

export function AppSidebar() {
  const { state } = useSidebar();
  const collapsed = state === "collapsed";
  const location = useLocation();

  const totalChunks = documentsData.reduce((s, d) => s + d.chunks, 0);

  return (
    <Sidebar collapsible="icon" className="border-r border-border/30">
      <SidebarContent className="pt-5 bg-mesh">
        {/* Brand */}
        <div className={`px-4 mb-8 flex items-center gap-3 ${collapsed ? 'justify-center px-2' : ''}`}>
          <div className="w-9 h-9 rounded-xl bg-gradient-primary flex items-center justify-center shadow-lg shadow-primary/20 shrink-0">
            <Sparkles className="w-4.5 h-4.5 text-primary-foreground" />
          </div>
          {!collapsed && (
            <div>
              <h1 className="text-sm font-bold text-foreground tracking-tight font-display">DocChat AI</h1>
              <p className="text-[10px] text-muted-foreground tracking-wide">PDF Knowledge Bot</p>
            </div>
          )}
        </div>

        {/* Nav */}
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu className="space-y-0.5 px-2">
              {navItems.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild>
                    <NavLink
                      to={item.url}
                      end={item.url === '/'}
                      className="rounded-xl px-3 py-2.5 hover:bg-secondary/60 transition-all duration-200"
                      activeClassName="bg-primary/10 text-primary font-medium shadow-sm shadow-primary/5"
                    >
                      <item.icon className="mr-2.5 h-4 w-4" />
                      {!collapsed && <span className="text-[13px]">{item.title}</span>}
                    </NavLink>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {/* Status */}
        {!collapsed && (
          <div className="mt-auto px-4 pb-5">
            <div className="rounded-xl bg-gradient-subtle p-3.5 border border-border/20">
              <div className="flex items-center gap-2 mb-1.5">
                <div className="w-2 h-2 rounded-full bg-success animate-subtle-pulse" />
                <span className="text-[11px] font-semibold text-foreground">System Active</span>
              </div>
              <p className="text-[10px] text-muted-foreground font-mono">{documentsData.length} documents · {totalChunks} chunks</p>
            </div>
          </div>
        )}
      </SidebarContent>
    </Sidebar>
  );
}

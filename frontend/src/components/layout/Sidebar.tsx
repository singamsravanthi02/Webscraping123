'use client';

import { usePathname } from "next/navigation";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { LayoutDashboard, Briefcase, BookOpen, Target, Settings, LogOut, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/store/authStore";

const navItems = [
  { name: "Overview", href: "/dashboard", icon: LayoutDashboard },
  { name: "Job Discovery", href: "/dashboard/jobs", icon: Briefcase },
  { name: "Mock Interviews", href: "/dashboard/interviews", icon: Target },
  { name: "Learning Paths", href: "/dashboard/learning", icon: BookOpen },
  { name: "Settings", href: "/dashboard/settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const logout = useAuthStore((state) => state.logout);

  return (
    <div className="w-64 h-screen border-r border-border bg-background/50 backdrop-blur-md flex flex-col justify-between hidden md:flex sticky top-0 z-40">
      <div className="p-6">
        <div className="flex items-center gap-2 mb-8">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
            <Sparkles className="text-white w-4 h-4" />
          </div>
          <span className="font-bold text-lg tracking-tight text-foreground">SPIP</span>
        </div>
        
        <nav className="space-y-1">
          {navItems.map((item) => {
            const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link key={item.name} href={item.href}>
                <span className={cn(
                  "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200",
                  isActive 
                    ? "bg-primary/10 text-primary" 
                    : "text-muted-foreground hover:bg-secondary hover:text-foreground"
                )}>
                  <item.icon className="w-4 h-4" />
                  {item.name}
                </span>
              </Link>
            );
          })}
        </nav>
      </div>

      <div className="p-6">
        <div className="glass-card p-4 rounded-xl mb-4 text-center border border-border">
          <h4 className="text-sm font-semibold mb-1 text-foreground">Upgrade to Pro</h4>
          <p className="text-xs text-muted-foreground mb-3">Get unlimited AI mock interviews.</p>
          <Button variant="default" className="w-full text-xs h-8">Upgrade</Button>
        </div>
        <button
          type="button"
          className="flex w-full items-center gap-2 justify-start text-muted-foreground hover:text-destructive px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 hover:bg-secondary"
          onClick={async () => {
            await logout();
            router.push("/login");
          }}
        >
          <LogOut className="w-4 h-4 mr-2" />
          Logout
        </button>
      </div>
    </div>
  );
}

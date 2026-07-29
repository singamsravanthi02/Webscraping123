'use client';

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Bell, Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useAuthStore } from "@/store/authStore";
import api from "@/lib/api";

export function DashboardNav() {
  const router = useRouter();
  const logout = useAuthStore((state) => state.logout);
  const user = useAuthStore((state) => state.user);
  const [pendingNotifications, setPendingNotifications] = useState<number>(0);

  useEffect(() => {
    let mounted = true;
    const loadNotifications = async () => {
      try {
        const response = await api.get("/notifications/me?unread_only=true&limit=1000");
        if (mounted) setPendingNotifications(response.data.length || 0);
      } catch {
        if (mounted) setPendingNotifications(0);
      }
    };
    const timer = window.setTimeout(() => {
      void loadNotifications();
    }, 0);
    const interval = window.setInterval(() => {
      void loadNotifications();
    }, 30000);
    return () => {
      mounted = false;
      window.clearTimeout(timer);
      window.clearInterval(interval);
    };
  }, []);

  const initials = useMemo(() => {
    const name = user?.fullName || user?.full_name || user?.email || "SP";
    return name
      .split(" ")
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase())
      .join("") || "SP";
  }, [user]);
  const avatarSrc = useMemo(() => {
    const picture = user?.profile_picture || "";
    return /^https?:\/\//i.test(picture) ? picture : undefined;
  }, [user]);

  return (
    <header className="h-16 border-b border-border bg-background/80 backdrop-blur-md flex items-center justify-between px-6 sticky top-0 z-30">
      <div className="flex items-center flex-1">
        <div className="relative w-full max-w-md hidden md:flex items-center">
          <Search className="absolute left-3 w-4 h-4 text-muted-foreground" />
          <Input 
            placeholder="Search jobs, skills, or interviews..." 
            className="pl-9 bg-secondary/50 border-transparent focus-visible:bg-background transition-colors rounded-full"
          />
        </div>
      </div>
      
      <div className="flex items-center gap-4">
        <button
          className="relative p-2 rounded-full hover:bg-secondary text-muted-foreground transition-colors"
          onClick={() => router.push("/dashboard/notifications")}
          type="button"
        >
          <Bell className="w-5 h-5" />
          {pendingNotifications > 0 && (
            <span className="absolute -top-0.5 -right-0.5 min-w-5 h-5 px-1 rounded-full bg-destructive text-[10px] leading-5 text-white border border-background">
              {pendingNotifications > 99 ? "99+" : pendingNotifications}
            </span>
          )}
        </button>

        <DropdownMenu>
          <DropdownMenuTrigger className="outline-none">
            <Avatar className="w-8 h-8 cursor-pointer ring-2 ring-transparent hover:ring-primary/20 transition-all">
              <AvatarImage src={avatarSrc} />
              <AvatarFallback>{initials}</AvatarFallback>
            </Avatar>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56 glass-card border-border/50">
            <DropdownMenuLabel>My Account</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem className="cursor-pointer" onSelect={() => router.push("/dashboard/settings")}>Profile</DropdownMenuItem>
            <DropdownMenuItem className="cursor-pointer" onSelect={() => router.push("/dashboard/settings")}>Settings</DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              className="text-destructive cursor-pointer"
              onClick={async () => {
                await logout();
                router.push("/login");
              }}
            >
              Log out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}

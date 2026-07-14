'use client';

import { Bell, Search, User } from "lucide-react";
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

export function DashboardNav() {
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
        <button className="relative p-2 rounded-full hover:bg-secondary text-muted-foreground transition-colors">
          <Bell className="w-5 h-5" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-destructive rounded-full border border-background"></span>
        </button>

        <DropdownMenu>
          <DropdownMenuTrigger className="outline-none">
            <Avatar className="w-8 h-8 cursor-pointer ring-2 ring-transparent hover:ring-primary/20 transition-all">
              <AvatarImage src="https://github.com/shadcn.png" />
              <AvatarFallback>ST</AvatarFallback>
            </Avatar>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56 glass-card border-border/50">
            <DropdownMenuLabel>My Account</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem className="cursor-pointer">Profile</DropdownMenuItem>
            <DropdownMenuItem className="cursor-pointer">Settings</DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem className="text-destructive cursor-pointer">Log out</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}

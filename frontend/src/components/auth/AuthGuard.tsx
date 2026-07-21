"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuthStore } from "@/store/authStore";
import { Loader2 } from "lucide-react";

export function AuthGuard({ children, allowedRoles }: { children: React.ReactNode, allowedRoles?: string[] }) {
  const { isAuthenticated, user, accessToken } = useAuthStore();
  const router = useRouter();
  const pathname = usePathname();
  const [isChecking, setIsChecking] = useState(true);

  useEffect(() => {
    // Basic check using localStorage if store is empty on initial hydration
    const token = accessToken || (typeof window !== "undefined" ? localStorage.getItem("accessToken") : null);
    
    if (!token) {
      router.replace(`/login?redirect=${pathname}`);
      return;
    }

    if (user) {
      if (allowedRoles && !allowedRoles.includes(user.role)) {
        router.replace("/dashboard");
        return;
      }
      
      // If profile is not complete, force to onboarding (unless already on onboarding)
      if (user.role === "student" && user.profile_completed === false && !pathname.startsWith("/onboarding")) {
        router.replace("/onboarding");
        return;
      }

      const timeout = window.setTimeout(() => setIsChecking(false), 0);
      return () => window.clearTimeout(timeout);
    } else {
      // If token exists but user is not loaded yet in store, wait a moment for hydration
      const timeout = window.setTimeout(() => {
        setIsChecking(false);
      }, 500);
      return () => window.clearTimeout(timeout);
    }
  }, [isAuthenticated, user, accessToken, router, pathname, allowedRoles]);

  if (isChecking || !isAuthenticated) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
      </div>
    );
  }

  return <>{children}</>;
}

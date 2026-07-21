import { create } from "zustand";
import { persist } from "zustand/middleware";
import { clearAuthStatusCookie } from "@/lib/auth";

export interface User {
  id: number;
  email: string;
  fullName?: string;
  full_name?: string;
  role: string;
  isActive: boolean;
  is_active?: boolean;
  profile_completed?: boolean;
}

interface AuthState {
  user: User | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  setAuth: (user: User, token: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      isAuthenticated: false,
      setAuth: (user, token) => set({ user, accessToken: token, isAuthenticated: true }),
      logout: async () => {
        if (typeof window !== "undefined") {
          const refreshToken = localStorage.getItem("refreshToken");
          if (refreshToken) {
            try {
              await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/auth/logout`, {
                method: "POST",
                headers: {
                  "Content-Type": "application/json",
                  "x-refresh-token": refreshToken
                }
              });
            } catch (error) {
              console.error("Failed to call logout API", error);
            }
          }
          localStorage.removeItem("accessToken");
          localStorage.removeItem("refreshToken");
          clearAuthStatusCookie();
        }
        set({ user: null, accessToken: null, isAuthenticated: false });
      },
    }),
    {
      name: "auth-storage", // stores in localStorage by default
    }
  )
);

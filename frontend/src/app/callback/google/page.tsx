"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2 } from "lucide-react";
import { useAuthStore } from "@/store/authStore";
import { toast } from "sonner";
import { setAuthStatusCookie } from "@/lib/auth";
import { FEATURE_FLAGS } from "@/lib/feature-flags";

function GoogleCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const code = searchParams.get("code");
  const [error, setError] = useState<string | null>(() => {
    if (!FEATURE_FLAGS.googleAuth) {
      return "Google authentication is disabled in development mode.";
    }
    return code ? null : "No authorization code provided by Google.";
  });

  useEffect(() => {
    if (!FEATURE_FLAGS.googleAuth) {
      return;
    }
    if (!code) {
      return;
    }

    const authenticate = async () => {
      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/auth/google/callback`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ code }),
        });

        if (!response.ok) {
          const errData = await response.json();
          throw new Error(errData.detail || "Google authentication failed");
        }

        const data = await response.json();
        localStorage.setItem("accessToken", data.access_token);
        localStorage.setItem("refreshToken", data.refresh_token);
        setAuthStatusCookie();

        // Fetch user profile to check if onboarding is complete
        try {
          const profileRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/users/me`, {
            headers: {
              Authorization: `Bearer ${data.access_token}`
            }
          });
          
          if (profileRes.ok) {
            const profileData = await profileRes.json();
            useAuthStore.getState().setAuth(profileData, data.access_token);
            
            if (profileData.profile_completed === false) {
              router.push("/onboarding");
            } else {
              router.push("/dashboard");
            }
          } else {
            router.push("/dashboard");
          }
        } catch {
          router.push("/dashboard");
        }
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "An error occurred during authentication.");
        toast.error("Authentication failed");
      }
    };

    authenticate();
  }, [router, code]);

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen">
        <h1 className="text-2xl font-bold text-red-500 mb-4">Authentication Error</h1>
        <p className="text-gray-600 mb-8">{error}</p>
        <button
          onClick={() => router.push("/login")}
          className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
        >
          Return to Login
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-screen">
      <Loader2 className="w-12 h-12 text-indigo-600 animate-spin mb-4" />
      <h1 className="text-xl font-medium text-gray-700">Verifying Google Sign In...</h1>
      <p className="text-sm text-gray-500 mt-2">Please wait while we log you in.</p>
    </div>
  );
}

export default function GoogleCallbackPage() {
  return (
    <Suspense fallback={<div className="flex flex-col items-center justify-center min-h-screen"><Loader2 className="w-12 h-12 text-indigo-600 animate-spin mb-4" /></div>}>
      <GoogleCallbackContent />
    </Suspense>
  );
}

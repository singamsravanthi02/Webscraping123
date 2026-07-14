"use client";

import { useEffect } from "react";
import { AlertTriangle, RefreshCcw } from "lucide-react";

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log the error to an error reporting service like Sentry
    console.error(error);
  }, [error]);

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-4 animate-in fade-in duration-500">
      <div className="bg-red-500/10 p-6 rounded-full mb-6">
        <AlertTriangle className="w-12 h-12 text-red-500" aria-hidden="true" />
      </div>
      <h2 className="text-2xl font-bold text-white mb-2" role="alert">
        Something went wrong!
      </h2>
      <p className="text-gray-400 max-w-md mb-8">
        We encountered an unexpected error while loading this dashboard component. Our engineering team has been notified.
      </p>
      <button
        onClick={() => reset()}
        className="flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-xl font-medium transition-colors"
        aria-label="Try again to load the page"
      >
        <RefreshCcw className="w-4 h-4" />
        Try again
      </button>
    </div>
  );
}

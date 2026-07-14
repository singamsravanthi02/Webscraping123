import { useEffect, useState, useCallback } from "react";
import { toast } from "sonner";

export function useProctoring() {
  const [tabSwitchCount, setTabSwitchCount] = useState(0);
  const [fullscreenViolations, setFullscreenViolations] = useState(0);
  const [isFullscreen, setIsFullscreen] = useState(false);

  const requestFullscreen = useCallback(() => {
    if (document.documentElement.requestFullscreen) {
      document.documentElement.requestFullscreen().catch(err => {
        console.error("Error attempting to enable fullscreen:", err.message);
      });
    }
  }, []);

  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === "hidden") {
        setTabSwitchCount(prev => {
          const newCount = prev + 1;
          toast.error(`Warning ${newCount}/3: Please do not switch tabs! Your test will be auto-submitted if you exceed the limit.`, {
            duration: 5000,
            className: "bg-red-50 text-red-900 border-red-200"
          });
          return newCount;
        });
      }
    };

    const handleFullscreenChange = () => {
      if (!document.fullscreenElement) {
        setIsFullscreen(false);
        setFullscreenViolations(prev => {
          const newCount = prev + 1;
          toast.error(`Warning: Exited fullscreen. Please click the button to return to fullscreen to continue your test.`);
          return newCount;
        });
      } else {
        setIsFullscreen(true);
      }
    };

    // Attempt to lock keyboard shortcuts (prevent refresh, etc.)
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "F5" || (e.ctrlKey && e.key === "r") || (e.metaKey && e.key === "r")) {
        e.preventDefault();
        toast.warning("Page refresh is disabled during the assessment.");
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);
    document.addEventListener("fullscreenchange", handleFullscreenChange);
    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      document.removeEventListener("fullscreenchange", handleFullscreenChange);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, []);

  return {
    tabSwitchCount,
    fullscreenViolations,
    isFullscreen,
    requestFullscreen,
  };
}

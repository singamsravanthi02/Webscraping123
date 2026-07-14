import { Loader2 } from "lucide-react";

export default function Loading() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh]">
      <Loader2 className="w-12 h-12 text-blue-500 animate-spin mb-4" />
      <h2 className="text-xl font-medium text-white">Loading data...</h2>
      <p className="text-gray-400 mt-2">Please wait while we fetch the latest information.</p>
    </div>
  );
}

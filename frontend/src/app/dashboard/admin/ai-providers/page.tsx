"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Activity, ArrowLeft, RefreshCcw, Server, ShieldAlert, ShieldCheck } from "lucide-react";
import api from "@/lib/api";

type ProviderRow = {
  provider: string;
  status: string;
  available: boolean;
  latency_ms: number | null;
  average_latency_ms: number;
  request_count: number;
  success_count: number;
  failure_count: number;
  fallback_count: number;
  cache_hit_count: number;
  cache_hit_rate: number;
  success_rate: number;
  current_model: string | null;
  last_failure: string | null;
  last_request_at: string | null;
  models: string[];
};

type ProviderOverview = {
  configured_mode: string;
  active_provider: string | null;
  queue_size: number;
  totals: {
    requests: number;
    failures: number;
    fallbacks: number;
    cache_hits: number;
    avg_latency_ms: number;
  };
  routing_decision: {
    feature: string | null;
    providers: string[];
    primary_provider: string | null;
    prompt_route: string | null;
  };
  routing_matrix: Record<string, string[]>;
  providers: ProviderRow[];
};

export default function AiProvidersPage() {
  const [data, setData] = useState<ProviderOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    const loadProviders = async () => {
      try {
        const response = await api.get<ProviderOverview>("/ai/providers");
        setData(response.data);
      } catch (error) {
        console.error("Failed to load AI providers", error);
        setData(null);
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    };

    void loadProviders();
  }, []);

  const refreshProviders = async () => {
    setRefreshing(true);
    try {
      const response = await api.get<ProviderOverview>("/ai/providers");
      setData(response.data);
    } catch (error) {
      console.error("Failed to load AI providers", error);
      setData(null);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-cyan-500 border-t-transparent" />
      </div>
    );
  }

  const providers = data?.providers ?? [];
  const cacheHitRate = data ? Math.round(((data.totals.cache_hits ?? 0) / Math.max((data.totals.requests ?? 0) + (data.totals.cache_hits ?? 0), 1)) * 100) : 0;
  const routingMatrix = Object.entries(data?.routing_matrix ?? {});

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500 text-white">
      <div className="flex flex-col gap-4 rounded-3xl border border-[#2a2a35] bg-[#1a1a24] p-8 shadow-2xl">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-cyan-500/20 bg-cyan-500/10 px-3 py-1 text-xs font-medium text-cyan-300">
              <Activity className="h-3.5 w-3.5" />
              AI Provider Monitor
            </div>
            <h1 className="text-3xl font-bold">Multi-Provider Orchestration</h1>
            <p className="mt-2 text-sm text-gray-400">
              Active mode: <span className="text-white">{data?.configured_mode || "AUTO"}</span>
              {" "}and current provider: <span className="text-white">{data?.active_provider || "none"}</span>
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => {
                void refreshProviders();
              }}
              className="inline-flex items-center gap-2 rounded-xl border border-[#2a2a35] bg-[#13131a] px-4 py-2 text-sm font-medium text-white transition-colors hover:border-cyan-500/50 hover:bg-[#17171f]"
            >
              <RefreshCcw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
              Refresh
            </button>
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-2 rounded-xl bg-cyan-500 px-4 py-2 text-sm font-medium text-slate-950 transition-colors hover:bg-cyan-400"
            >
              <ArrowLeft className="h-4 w-4" />
              Back
            </Link>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-5">
        <div className="rounded-2xl border border-[#2a2a35] bg-[#1a1a24] p-4">
          <div className="text-xs uppercase tracking-wide text-gray-400">Requests</div>
          <div className="mt-2 text-2xl font-bold">{data?.totals.requests ?? 0}</div>
        </div>
        <div className="rounded-2xl border border-[#2a2a35] bg-[#1a1a24] p-4">
          <div className="text-xs uppercase tracking-wide text-gray-400">Failures</div>
          <div className="mt-2 text-2xl font-bold">{data?.totals.failures ?? 0}</div>
        </div>
        <div className="rounded-2xl border border-[#2a2a35] bg-[#1a1a24] p-4">
          <div className="text-xs uppercase tracking-wide text-gray-400">Fallbacks</div>
          <div className="mt-2 text-2xl font-bold">{data?.totals.fallbacks ?? 0}</div>
        </div>
        <div className="rounded-2xl border border-[#2a2a35] bg-[#1a1a24] p-4">
          <div className="text-xs uppercase tracking-wide text-gray-400">Cache Hit %</div>
          <div className="mt-2 text-2xl font-bold">{cacheHitRate}%</div>
        </div>
        <div className="rounded-2xl border border-[#2a2a35] bg-[#1a1a24] p-4">
          <div className="text-xs uppercase tracking-wide text-gray-400">Queue Size</div>
          <div className="mt-2 text-2xl font-bold">{data?.queue_size ?? 0}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div className="rounded-2xl border border-[#2a2a35] bg-[#1a1a24] p-5">
          <div className="text-sm uppercase tracking-wide text-gray-400">Current Routing Decision</div>
          <div className="mt-2 text-lg font-semibold text-white">
            {data?.routing_decision?.feature || "No active AI request"}
          </div>
          <div className="mt-2 text-sm text-gray-400">
            {data?.routing_decision?.prompt_route || "Routing will appear after the next AI request."}
          </div>
        </div>
        <div className="rounded-2xl border border-[#2a2a35] bg-[#1a1a24] p-5">
          <div className="text-sm uppercase tracking-wide text-gray-400">Average Response Time</div>
          <div className="mt-2 text-lg font-semibold text-white">
            {data?.totals.avg_latency_ms ?? 0} ms
          </div>
          <div className="mt-2 text-sm text-gray-400">
            Active provider: <span className="text-white">{data?.active_provider || "none"}</span>
          </div>
        </div>
      </div>

      {routingMatrix.length > 0 && (
        <div className="rounded-2xl border border-[#2a2a35] bg-[#1a1a24] p-5">
          <div className="text-sm uppercase tracking-wide text-gray-400">Routing Matrix</div>
          <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
            {routingMatrix.map(([feature, providers]) => (
              <div key={feature} className="rounded-xl bg-[#13131a] p-3">
                <div className="text-sm font-semibold text-white">{feature}</div>
                <div className="mt-1 text-xs text-gray-400">{providers.join(" -> ")}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {providers.map((provider) => (
          <div key={provider.provider} className="rounded-2xl border border-[#2a2a35] bg-[#1a1a24] p-5">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="text-sm uppercase tracking-wide text-gray-400">{provider.provider}</div>
                <div className="mt-1 text-2xl font-bold">{provider.status}</div>
              </div>
              {provider.available ? (
                <div className="rounded-lg bg-green-500/10 p-2 text-green-400">
                  <ShieldCheck className="h-5 w-5" />
                </div>
              ) : (
                <div className="rounded-lg bg-red-500/10 p-2 text-red-400">
                  <ShieldAlert className="h-5 w-5" />
                </div>
              )}
            </div>

            <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
              <div className="rounded-xl bg-[#13131a] p-3">
                <div className="text-gray-400">Latency</div>
                <div className="mt-1 font-semibold">{provider.latency_ms ?? 0} ms</div>
              </div>
              <div className="rounded-xl bg-[#13131a] p-3">
                <div className="text-gray-400">Avg Latency</div>
                <div className="mt-1 font-semibold">{provider.average_latency_ms ?? 0} ms</div>
              </div>
              <div className="rounded-xl bg-[#13131a] p-3">
                <div className="text-gray-400">Requests</div>
                <div className="mt-1 font-semibold">{provider.request_count}</div>
              </div>
              <div className="rounded-xl bg-[#13131a] p-3">
                <div className="text-gray-400">Failures</div>
                <div className="mt-1 font-semibold">{provider.failure_count}</div>
              </div>
              <div className="rounded-xl bg-[#13131a] p-3">
                <div className="text-gray-400">Fallbacks</div>
                <div className="mt-1 font-semibold">{provider.fallback_count}</div>
              </div>
              <div className="rounded-xl bg-[#13131a] p-3">
                <div className="text-gray-400">Cache Hit %</div>
                <div className="mt-1 font-semibold">{provider.cache_hit_rate}%</div>
              </div>
              <div className="rounded-xl bg-[#13131a] p-3">
                <div className="text-gray-400">Success</div>
                <div className="mt-1 font-semibold">{provider.success_rate}%</div>
              </div>
            </div>

            <div className="mt-4 rounded-xl border border-[#2a2a35] bg-[#13131a] p-3">
              <div className="flex items-center gap-2 text-sm text-gray-400">
                <Server className="h-4 w-4" />
                Current model
              </div>
              <div className="mt-1 font-medium text-white">{provider.current_model || "none"}</div>
              {provider.last_failure && (
                <p className="mt-2 line-clamp-3 text-xs text-red-300">{provider.last_failure}</p>
              )}
              <p className="mt-2 text-xs text-gray-500">
                Last request: {provider.last_request_at || "none"}
              </p>
              {provider.models.length > 0 && (
                <p className="mt-2 text-xs text-gray-500">
                  {provider.models.join(", ")}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>

      {!providers.length && (
        <div className="rounded-2xl border border-dashed border-[#2a2a35] bg-[#1a1a24] p-10 text-center text-sm text-gray-400">
          No provider data available yet.
        </div>
      )}
    </div>
  );
}

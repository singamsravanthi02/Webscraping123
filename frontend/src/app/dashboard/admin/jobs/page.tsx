"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Briefcase, RefreshCcw, Server, ShieldAlert, ShieldCheck } from "lucide-react";
import api from "@/lib/api";

type JobSourceStat = {
  name: string;
  count: number;
};

type ProviderStatus = {
  name: string;
  status: string;
  jobs: number;
  latency_ms: number;
  failures: number;
  last_error?: string | null;
  children?: ProviderStatus[];
};

type JobMonitor = {
  status: string;
  scheduler_status: string;
  last_crawl_at: string | null;
  jobs_fetched: number;
  duplicates_removed: number;
  latency_ms: number;
  failures: number;
  cached: boolean;
  active_jobs: number;
  recent_queries: string[];
  sources: JobSourceStat[];
  provider_status: ProviderStatus[];
};

export default function JobMonitorPage() {
  const [data, setData] = useState<JobMonitor | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    try {
      const response = await api.get<JobMonitor>("/jobs/monitor");
      setData(response.data);
    } catch (error) {
      console.error("Failed to load job monitor", error);
      setData(null);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void load();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  if (loading) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-500 border-t-transparent" />
      </div>
    );
  }

  const healthy = data?.status === "healthy";
  const sources = data?.sources ?? [];
  const recentQueries = data?.recent_queries ?? [];
  const providerStatus = data?.provider_status ?? [];

  return (
    <div className="space-y-6 text-white">
      <div className="flex flex-col gap-4 rounded-3xl border border-[#2a2a35] bg-[#1a1a24] p-8 shadow-2xl">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-indigo-500/20 bg-indigo-500/10 px-3 py-1 text-xs font-medium text-indigo-300">
              <Briefcase className="h-3.5 w-3.5" />
              Job Discovery Monitor
            </div>
            <h1 className="text-3xl font-bold">Live crawl health</h1>
            <p className="mt-2 text-sm text-gray-400">
              Status: <span className="text-white">{data?.status || "unknown"}</span>
              {" "}and scheduler: <span className="text-white">{data?.scheduler_status || "unknown"}</span>
            </p>
          </div>
          <div className="flex gap-3">
            <button
              type="button"
              onClick={() => {
                setRefreshing(true);
                void load();
              }}
              className="inline-flex items-center gap-2 rounded-xl border border-[#2a2a35] bg-[#13131a] px-4 py-2 text-sm font-medium text-white transition-colors hover:border-indigo-500/50 hover:bg-[#17171f]"
            >
              <RefreshCcw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
              Refresh
            </button>
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-2 rounded-xl bg-indigo-500 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-400"
            >
              <ArrowLeft className="h-4 w-4" />
              Back
            </Link>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-5">
        <div className="rounded-2xl border border-[#2a2a35] bg-[#1a1a24] p-4">
          <div className="text-xs uppercase tracking-wide text-gray-400">Jobs Fetched</div>
          <div className="mt-2 text-2xl font-bold">{data?.jobs_fetched ?? 0}</div>
        </div>
        <div className="rounded-2xl border border-[#2a2a35] bg-[#1a1a24] p-4">
          <div className="text-xs uppercase tracking-wide text-gray-400">Duplicates Removed</div>
          <div className="mt-2 text-2xl font-bold">{data?.duplicates_removed ?? 0}</div>
        </div>
        <div className="rounded-2xl border border-[#2a2a35] bg-[#1a1a24] p-4">
          <div className="text-xs uppercase tracking-wide text-gray-400">Latency</div>
          <div className="mt-2 text-2xl font-bold">{Math.round(data?.latency_ms ?? 0)} ms</div>
        </div>
        <div className="rounded-2xl border border-[#2a2a35] bg-[#1a1a24] p-4">
          <div className="text-xs uppercase tracking-wide text-gray-400">Failures</div>
          <div className="mt-2 text-2xl font-bold">{data?.failures ?? 0}</div>
        </div>
        <div className="rounded-2xl border border-[#2a2a35] bg-[#1a1a24] p-4">
          <div className="text-xs uppercase tracking-wide text-gray-400">Active Jobs</div>
          <div className="mt-2 text-2xl font-bold">{data?.active_jobs ?? 0}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div className="rounded-2xl border border-[#2a2a35] bg-[#1a1a24] p-5">
          <div className="text-sm uppercase tracking-wide text-gray-400">Last Crawl</div>
          <div className="mt-2 text-lg font-semibold text-white">
            {data?.last_crawl_at ? new Date(data.last_crawl_at).toLocaleString() : "No crawl recorded"}
          </div>
          <div className="mt-2 flex items-center gap-2 text-sm text-gray-400">
            {healthy ? <ShieldCheck className="h-4 w-4 text-green-400" /> : <ShieldAlert className="h-4 w-4 text-red-400" />}
            {healthy ? "Crawl healthy" : "Crawl needs attention"}
          </div>
        </div>
        <div className="rounded-2xl border border-[#2a2a35] bg-[#1a1a24] p-5">
          <div className="text-sm uppercase tracking-wide text-gray-400">Recent Queries</div>
          <div className="mt-3 space-y-2">
            {recentQueries.slice(0, 5).length ? (
              recentQueries.slice(0, 5).map((query) => (
                <div key={query} className="rounded-xl bg-[#13131a] px-3 py-2 text-sm text-white">
                  {query}
                </div>
              ))
            ) : (
              <div className="text-sm text-gray-400">No recorded crawl queries yet.</div>
            )}
          </div>
        </div>
      </div>

      <div className="rounded-2xl border border-[#2a2a35] bg-[#1a1a24] p-5">
        <div className="flex items-center gap-2 text-sm uppercase tracking-wide text-gray-400">
          <Server className="h-4 w-4" />
          Source Breakdown
        </div>
        <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
          {sources.length ? (
            sources.map((source) => (
              <div key={source.name} className="rounded-xl bg-[#13131a] p-3">
                <div className="text-sm text-gray-400">{source.name}</div>
                <div className="mt-1 text-2xl font-bold text-white">{source.count}</div>
              </div>
            ))
          ) : (
            <div className="text-sm text-gray-400">No provider counts recorded yet.</div>
          )}
        </div>
      </div>

      <div className="rounded-2xl border border-[#2a2a35] bg-[#1a1a24] p-5">
        <div className="flex items-center gap-2 text-sm uppercase tracking-wide text-gray-400">
          <Server className="h-4 w-4" />
          Provider Status
        </div>
        <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
          {providerStatus.length ? (
            providerStatus.flatMap((provider) => [provider, ...(provider.children ?? [])]).map((provider) => (
              <div key={provider.name} className="rounded-xl bg-[#13131a] p-3">
                <div className="flex items-center justify-between gap-3">
                  <div className="text-sm font-medium text-white">{provider.name}</div>
                  <span className="rounded-full border border-white/10 px-2 py-0.5 text-xs text-gray-300">{provider.status}</span>
                </div>
                <div className="mt-2 text-xs text-gray-400">
                  {provider.jobs} jobs · {Math.round(provider.latency_ms || 0)} ms · {provider.failures} failures
                </div>
                {provider.last_error ? <div className="mt-2 text-xs text-amber-300">{provider.last_error}</div> : null}
              </div>
            ))
          ) : (
            <div className="text-sm text-gray-400">No provider status recorded yet.</div>
          )}
        </div>
      </div>
    </div>
  );
}

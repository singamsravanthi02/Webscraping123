"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from "recharts";
import { Server, Users, Activity, Zap, Cpu, Briefcase } from "lucide-react";
import { AdminAnalytics, AnalyticsOverview, getAnalyticsOverview } from "@/lib/analytics";

const EmptyState = ({ label }: { label: string }) => (
  <div className="flex h-[300px] items-center justify-center rounded-xl border border-dashed border-[#2a2a35] text-sm text-gray-400">
    {label}
  </div>
);

export const AdminDashboard = () => {
  const [admin, setAdmin] = useState<AdminAnalytics | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const overview: AnalyticsOverview = await getAnalyticsOverview();
        setAdmin(overview.admin);
      } catch (error) {
        console.error("Failed to load admin analytics", error);
        setAdmin(null);
      } finally {
        setIsLoading(false);
      }
    };

    fetchAnalytics();
  }, []);

  if (isLoading) {
    return <div className="h-full flex items-center justify-center min-h-[400px]"><div className="w-8 h-8 border-4 border-purple-500 border-t-transparent rounded-full animate-spin"></div></div>;
  }

  const apiUsageData = admin?.ai_usage ?? [];
  const activeUsersData = admin?.concurrent_users ?? [];

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-6 relative overflow-hidden">
          <div className="flex justify-between items-start mb-4">
            <h3 className="text-gray-400 font-medium">System Status</h3>
            <div className="p-2 bg-green-500/10 text-green-400 rounded-lg">
              <Server className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-bold text-white">{admin?.system_status || "Operational"}</div>
          <p className="text-sm text-green-400 mt-2 font-medium">Live backend health</p>
        </div>

        <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-6 relative overflow-hidden">
          <div className="flex justify-between items-start mb-4">
            <h3 className="text-gray-400 font-medium">Active Users</h3>
            <div className="p-2 bg-blue-500/10 text-blue-400 rounded-lg">
              <Users className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-bold text-white">{admin?.active_users ?? 0}</div>
          <p className="text-sm text-blue-400 mt-2 font-medium">Currently active</p>
        </div>

        <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-6 relative overflow-hidden">
          <div className="flex justify-between items-start mb-4">
            <h3 className="text-gray-400 font-medium">AI Requests</h3>
            <div className="p-2 bg-purple-500/10 text-purple-400 rounded-lg">
              <Zap className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-bold text-white">{admin?.ai_requests ?? 0}</div>
          <p className="text-sm text-gray-400 mt-2 font-medium">Recorded token usage rows</p>
        </div>

        <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-6 relative overflow-hidden">
          <div className="flex justify-between items-start mb-4">
            <h3 className="text-gray-400 font-medium">Assessments Taken</h3>
            <div className="p-2 bg-yellow-500/10 text-yellow-400 rounded-lg">
              <Activity className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-bold text-white">{admin?.assessments_taken ?? 0}</div>
          <p className="text-sm text-gray-400 mt-2 font-medium">Submitted attempts</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-6">
          <h3 className="text-gray-400 font-medium">Jobs Today</h3>
          <div className="mt-2 text-3xl font-bold text-white">{admin?.jobs_today ?? 0}</div>
        </div>
        <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-6">
          <h3 className="text-gray-400 font-medium">Job Searches</h3>
          <div className="mt-2 text-3xl font-bold text-white">{admin?.job_searches ?? 0}</div>
        </div>
        <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-6">
          <h3 className="text-gray-400 font-medium">Job Recommendations</h3>
          <div className="mt-2 text-3xl font-bold text-white">{admin?.job_recommendations ?? 0}</div>
        </div>
        <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-6">
          <h3 className="text-gray-400 font-medium">Avg Match Score</h3>
          <div className="mt-2 text-3xl font-bold text-white">{admin?.avg_job_match_score ?? 0}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-6">
          <div className="mb-4">
            <h3 className="text-lg font-semibold text-white">AI Requests</h3>
            <p className="text-sm text-gray-400">Daily call volume</p>
          </div>
          {apiUsageData.length ? (
            <div className="h-[300px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={apiUsageData}>
                  <defs>
                    <linearGradient id="colorCalls" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#2a2a35" />
                  <XAxis dataKey="day" axisLine={false} tickLine={false} tick={{ fill: "#9ca3af" }} dy={10} />
                  <YAxis axisLine={false} tickLine={false} tick={{ fill: "#9ca3af" }} dx={-10} />
                  <Tooltip contentStyle={{ backgroundColor: "#1a1a24", border: "1px solid #2a2a35", borderRadius: "8px", color: "#fff" }} />
                  <Area type="monotone" dataKey="calls" stroke="#8b5cf6" fillOpacity={1} fill="url(#colorCalls)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyState label="No AI usage data yet." />
          )}
        </div>

        <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-6">
          <div className="mb-4">
            <h3 className="text-lg font-semibold text-white">Session Activity</h3>
            <p className="text-sm text-gray-400">Live user session buckets</p>
          </div>
          {activeUsersData.length ? (
            <div className="h-[300px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={activeUsersData}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#2a2a35" />
                  <XAxis dataKey="time" axisLine={false} tickLine={false} tick={{ fill: "#9ca3af" }} dy={10} />
                  <YAxis axisLine={false} tickLine={false} tick={{ fill: "#9ca3af" }} dx={-10} />
                  <Tooltip contentStyle={{ backgroundColor: "#1a1a24", border: "1px solid #2a2a35", borderRadius: "8px", color: "#fff" }} />
                  <Line type="monotone" dataKey="users" stroke="#3b82f6" strokeWidth={3} dot={{ fill: "#3b82f6", strokeWidth: 2, r: 4 }} activeDot={{ r: 6, fill: "#3b82f6", stroke: "#93c5fd", strokeWidth: 4 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyState label="No session activity yet." />
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-6">
          <h3 className="text-lg font-semibold text-white mb-2">Jobs</h3>
          <div className="text-3xl font-bold text-white">{admin?.jobs ?? 0}</div>
        </div>
        <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-6">
          <h3 className="text-lg font-semibold text-white mb-2">Knowledge Docs</h3>
          <div className="text-3xl font-bold text-white">{admin?.documents ?? 0}</div>
        </div>
        <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-6">
          <h3 className="text-lg font-semibold text-white mb-2">Pending Notifications</h3>
          <div className="text-3xl font-bold text-white">{admin?.pending_notifications ?? 0}</div>
        </div>
      </div>

      {admin?.job_source_mix?.length ? (
        <div className="rounded-2xl border border-[#2a2a35] bg-[#1a1a24] p-6">
          <div className="mb-4">
            <h3 className="text-lg font-semibold text-white">Job Source Mix</h3>
            <p className="text-sm text-gray-400">Live distribution of discovered jobs by provider</p>
          </div>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            {admin.job_source_mix.map((source) => (
              <div key={source.name} className="rounded-xl bg-[#13131a] p-4">
                <div className="text-sm text-gray-400">{source.name}</div>
                <div className="mt-1 text-2xl font-bold text-white">{source.value}</div>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="p-2 bg-cyan-500/10 text-cyan-400 rounded-lg">
            <Cpu className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white">AI Provider Monitor</h3>
            <p className="text-sm text-gray-400">Check Gemini, NVIDIA, and Ollama health, latency, and active routing.</p>
          </div>
        </div>
        <Link
          href="/dashboard/admin/ai-providers"
          className="inline-flex items-center justify-center rounded-xl bg-cyan-500 px-4 py-2 text-sm font-medium text-slate-950 transition-colors hover:bg-cyan-400"
        >
          Open monitor
        </Link>
      </div>

      <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="p-2 bg-indigo-500/10 text-indigo-400 rounded-lg">
            <Briefcase className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white">Job Discovery Monitor</h3>
            <p className="text-sm text-gray-400">Inspect live sources, crawl latency, duplicates removed, and scheduler health.</p>
          </div>
        </div>
        <Link
          href="/dashboard/admin/jobs"
          className="inline-flex items-center justify-center rounded-xl bg-indigo-500 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-400"
        >
          Open monitor
        </Link>
      </div>
    </div>
  );
};

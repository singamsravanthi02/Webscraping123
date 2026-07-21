"use client";

import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from "recharts";
import { Briefcase, Building, CheckCircle2, TrendingUp } from "lucide-react";
import { AnalyticsOverview, PlacementAnalytics, getAnalyticsOverview } from "@/lib/analytics";

const COLORS = ["#8b5cf6", "#3b82f6", "#f59e0b", "#10b981", "#ef4444"];

const EmptyState = ({ label }: { label: string }) => (
  <div className="flex h-[300px] items-center justify-center rounded-xl border border-dashed border-[#2a2a35] text-sm text-gray-400">
    {label}
  </div>
);

export const PlacementDashboard = () => {
  const [placement, setPlacement] = useState<PlacementAnalytics | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const overview: AnalyticsOverview = await getAnalyticsOverview();
        setPlacement(overview.placement);
      } catch (error) {
        console.error("Failed to load placement analytics", error);
        setPlacement(null);
      } finally {
        setIsLoading(false);
      }
    };

    fetchAnalytics();
  }, []);

  if (isLoading) {
    return <div className="h-full flex items-center justify-center min-h-[400px]"><div className="w-8 h-8 border-4 border-purple-500 border-t-transparent rounded-full animate-spin"></div></div>;
  }

  const funnelData = placement?.funnel ?? [];
  const sourceData = placement?.source_mix ?? [];

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-6 relative overflow-hidden">
          <div className="flex justify-between items-start mb-4">
            <h3 className="text-gray-400 font-medium">Active Drives</h3>
            <div className="p-2 bg-blue-500/10 text-blue-400 rounded-lg">
              <Building className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-bold text-white">{placement?.active_drives ?? 0}</div>
        </div>

        <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-6 relative overflow-hidden">
          <div className="flex justify-between items-start mb-4">
            <h3 className="text-gray-400 font-medium">Recommendations</h3>
            <div className="p-2 bg-green-500/10 text-green-400 rounded-lg">
              <CheckCircle2 className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-bold text-white">{placement?.recommendations ?? 0}</div>
        </div>

        <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-6 relative overflow-hidden">
          <div className="flex justify-between items-start mb-4">
            <h3 className="text-gray-400 font-medium">Avg Match Score</h3>
            <div className="p-2 bg-purple-500/10 text-purple-400 rounded-lg">
              <TrendingUp className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-bold text-white">{placement?.avg_match_score ?? 0}%</div>
          <p className="text-sm text-green-400 mt-2 font-medium">
            Live recommendation quality
          </p>
        </div>

        <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-6 relative overflow-hidden">
          <div className="flex justify-between items-start mb-4">
            <h3 className="text-gray-400 font-medium">Job Bookmarks</h3>
            <div className="p-2 bg-yellow-500/10 text-yellow-400 rounded-lg">
              <Briefcase className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-bold text-white">{placement?.bookmarks ?? 0}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-6">
          <div className="mb-4">
            <h3 className="text-lg font-semibold text-white">Discovery Funnel</h3>
            <p className="text-sm text-gray-400">Live search and recommendation flow</p>
          </div>
          {funnelData.length ? (
            <div className="h-[300px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={funnelData} layout="vertical" margin={{ left: 30 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#2a2a35" />
                  <XAxis type="number" hide />
                  <YAxis dataKey="stage" type="category" axisLine={false} tickLine={false} tick={{ fill: "#9ca3af" }} />
                  <Tooltip cursor={{ fill: "#2a2a35" }} contentStyle={{ backgroundColor: "#1a1a24", border: "1px solid #2a2a35", borderRadius: "8px", color: "#fff" }} />
                  <Bar dataKey="count" fill="#8b5cf6" radius={[0, 4, 4, 0]} barSize={30} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyState label="No discovery activity yet." />
          )}
        </div>

        <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-6">
          <div className="mb-4">
            <h3 className="text-lg font-semibold text-white">Job Source Mix</h3>
            <p className="text-sm text-gray-400">Breakdown of live job ingestion sources</p>
          </div>
          {sourceData.length ? (
            <div className="h-[300px] w-full flex items-center justify-center">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={sourceData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {sourceData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ backgroundColor: "#1a1a24", border: "1px solid #2a2a35", borderRadius: "8px", color: "#fff" }} />
                </PieChart>
              </ResponsiveContainer>

              <div className="absolute right-12 flex flex-col gap-4">
                {sourceData.map((entry, index) => (
                  <div key={entry.name} className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full" style={{ backgroundColor: COLORS[index % COLORS.length] }} />
                    <span className="text-sm text-gray-300">{entry.name} ({entry.value})</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <EmptyState label="No job source data yet." />
          )}
        </div>
      </div>
    </div>
  );
};

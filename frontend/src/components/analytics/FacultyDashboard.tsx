"use client";

import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from "recharts";
import { Users, AlertTriangle, CheckCircle2, TrendingUp } from "lucide-react";
import { AnalyticsOverview, FacultyAnalytics, getAnalyticsOverview } from "@/lib/analytics";

const EmptyState = ({ label }: { label: string }) => (
  <div className="flex h-[300px] items-center justify-center rounded-xl border border-dashed border-[#2a2a35] text-sm text-gray-400">
    {label}
  </div>
);

export const FacultyDashboard = () => {
  const [faculty, setFaculty] = useState<FacultyAnalytics | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const overview: AnalyticsOverview = await getAnalyticsOverview();
        setFaculty(overview.faculty);
      } catch (error) {
        console.error("Failed to load faculty analytics", error);
        setFaculty(null);
      } finally {
        setIsLoading(false);
      }
    };

    fetchAnalytics();
  }, []);

  if (isLoading) {
    return <div className="h-full flex items-center justify-center min-h-[400px]"><div className="w-8 h-8 border-4 border-purple-500 border-t-transparent rounded-full animate-spin"></div></div>;
  }

  const gradeDistribution = faculty?.grade_distribution ?? [];
  const classPerformance = faculty?.class_performance ?? [];
  const topicMastery = faculty?.topic_mastery ?? [];

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-6 relative overflow-hidden">
          <div className="flex justify-between items-start mb-4">
            <h3 className="text-gray-400 font-medium">Total Students</h3>
            <div className="p-2 bg-blue-500/10 text-blue-400 rounded-lg">
              <Users className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-bold text-white">{faculty?.total_students ?? 0}</div>
        </div>

        <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-6 relative overflow-hidden">
          <div className="flex justify-between items-start mb-4">
            <h3 className="text-gray-400 font-medium">Class Average</h3>
            <div className="p-2 bg-purple-500/10 text-purple-400 rounded-lg">
              <TrendingUp className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-bold text-white">{faculty?.class_average ?? 0}%</div>
        </div>

        <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-6 relative overflow-hidden">
          <div className="flex justify-between items-start mb-4">
            <h3 className="text-gray-400 font-medium">At-Risk Students</h3>
            <div className="p-2 bg-red-500/10 text-red-400 rounded-lg">
              <AlertTriangle className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-bold text-white">{faculty?.at_risk_students ?? 0}</div>
          <p className="text-sm text-red-400 mt-2 flex items-center font-medium">
            Requires attention
          </p>
        </div>

        <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-6 relative overflow-hidden">
          <div className="flex justify-between items-start mb-4">
            <h3 className="text-gray-400 font-medium">Top Performers</h3>
            <div className="p-2 bg-green-500/10 text-green-400 rounded-lg">
              <CheckCircle2 className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-bold text-white">{faculty?.top_performers ?? 0}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-6">
          <div className="mb-4">
            <h3 className="text-lg font-semibold text-white">Grade Distribution</h3>
            <p className="text-sm text-gray-400">Number of students by score range</p>
          </div>
          {gradeDistribution.length ? (
            <div className="h-[300px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={gradeDistribution}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#2a2a35" />
                  <XAxis dataKey="range" axisLine={false} tickLine={false} tick={{ fill: "#9ca3af" }} dy={10} />
                  <YAxis axisLine={false} tickLine={false} tick={{ fill: "#9ca3af" }} dx={-10} />
                  <Tooltip cursor={{ fill: "#2a2a35" }} contentStyle={{ backgroundColor: "#1a1a24", border: "1px solid #2a2a35", borderRadius: "8px", color: "#fff" }} />
                  <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyState label="No assessment scores yet." />
          )}
        </div>

        <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-6">
          <div className="mb-4">
            <h3 className="text-lg font-semibold text-white">Class Average Trend</h3>
            <p className="text-sm text-gray-400">Weekly assessment scores</p>
          </div>
          {classPerformance.length ? (
            <div className="h-[300px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={classPerformance}>
                  <defs>
                    <linearGradient id="colorAvg" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#a855f7" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#a855f7" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#2a2a35" />
                  <XAxis dataKey="week" axisLine={false} tickLine={false} tick={{ fill: "#9ca3af" }} dy={10} />
                  <YAxis axisLine={false} tickLine={false} tick={{ fill: "#9ca3af" }} dx={-10} domain={[0, 100]} />
                  <Tooltip contentStyle={{ backgroundColor: "#1a1a24", border: "1px solid #2a2a35", borderRadius: "8px", color: "#fff" }} />
                  <Area type="monotone" dataKey="avg" stroke="#a855f7" fillOpacity={1} fill="url(#colorAvg)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyState label="No weekly trend available yet." />
          )}
        </div>
      </div>

      <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-6">
        <h3 className="text-lg font-semibold text-white mb-4">Topic Mastery</h3>
        {topicMastery.length ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-gray-400">
              <thead className="bg-[#13131a] text-gray-300">
                <tr>
                  <th className="px-4 py-3 rounded-tl-lg">Topic</th>
                  <th className="px-4 py-3">Correct</th>
                  <th className="px-4 py-3">Incorrect</th>
                  <th className="px-4 py-3 rounded-tr-lg">Total</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#2a2a35]">
                {topicMastery.map((topic) => (
                  <tr key={topic.topic}>
                    <td className="px-4 py-3 font-medium text-white">{topic.topic}</td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-1 bg-green-500/10 text-green-400 rounded-full">{topic.correct}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-1 bg-red-500/10 text-red-400 rounded-full">{topic.incorrect}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-1 bg-yellow-500/10 text-yellow-400 rounded-full">{topic.total}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState label="No topic mastery data yet." />
        )}
      </div>
    </div>
  );
};

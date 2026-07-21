"use client";

import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, LineChart, Line, Cell } from "recharts";
import { Target, TrendingUp, BrainCircuit, Activity, FileText } from "lucide-react";
import { CustomHeatmap } from "./CustomHeatmap";
import { AnalyticsOverview, StudentAnalytics, getAnalyticsOverview } from "@/lib/analytics";

const EmptyState = ({ label }: { label: string }) => (
  <div className="flex h-[300px] items-center justify-center rounded-xl border border-dashed border-[#2a2a35] text-sm text-gray-400">
    {label}
  </div>
);

export const StudentDashboard = () => {
  const [student, setStudent] = useState<StudentAnalytics | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const overview: AnalyticsOverview = await getAnalyticsOverview();
        setStudent(overview.student);
      } catch (error) {
        console.error("Failed to load student analytics", error);
        setStudent(null);
      } finally {
        setIsLoading(false);
      }
    };

    fetchAnalytics();
  }, []);

  if (isLoading) {
    return <div className="h-full flex items-center justify-center min-h-[400px]"><div className="w-8 h-8 border-4 border-purple-500 border-t-transparent rounded-full animate-spin"></div></div>;
  }

  const readiness = student?.readiness_score ?? 0;
  const performanceData = student?.test_performance ?? [];
  const subjectData = student?.subject_strengths?.map((item) => ({ subject: item.subject, score: item.score })) ?? [];
  const skillsData = student?.skills_breakdown ?? [];
  const heatmapData = student?.activity_heatmap ?? [];

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-6 relative overflow-hidden">
          <div className="flex justify-between items-start mb-4">
            <h3 className="text-gray-400 font-medium">Readiness Score</h3>
            <div className="p-2 bg-purple-500/10 text-purple-400 rounded-lg">
              <Target className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-bold text-white">{readiness ? `${readiness}%` : "N/A"}</div>
          <p className="text-sm text-green-400 mt-2 flex items-center font-medium">
            <TrendingUp className="w-4 h-4 mr-1" /> {readiness >= 80 ? "Ready for top tiers" : "Keep building"}
          </p>
        </div>

        <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-6 relative overflow-hidden">
          <div className="flex justify-between items-start mb-4">
            <h3 className="text-gray-400 font-medium">Resume Score</h3>
            <div className="p-2 bg-blue-500/10 text-blue-400 rounded-lg">
              <FileText className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-bold text-white">{student?.resume_score ?? "N/A"}</div>
          <p className="text-sm text-blue-400 mt-2 flex items-center font-medium">
            ATS Optimized
          </p>
        </div>

        <div className="bg-gradient-to-br from-purple-900/40 to-blue-900/40 border border-purple-500/30 rounded-2xl p-6 md:col-span-2 relative overflow-hidden">
          <div className="flex items-start gap-4">
            <div className="p-3 bg-purple-500/20 text-purple-300 rounded-xl">
              <BrainCircuit className="w-6 h-6" />
            </div>
            <div>
              <h3 className="font-bold text-white text-lg">AI Recommendation</h3>
              <p className="text-gray-300 mt-1 leading-relaxed text-sm">
                {student?.ai_recommendation || "Upload activity data to receive an AI recommendation."}
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-6">
          <div className="mb-4">
            <h3 className="text-lg font-semibold text-white">Learning Curve</h3>
            <p className="text-sm text-gray-400">Assessment scores over time</p>
          </div>
          {performanceData.length ? (
            <div className="h-[300px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={performanceData}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#2a2a35" />
                  <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: "#9ca3af" }} dy={10} />
                  <YAxis axisLine={false} tickLine={false} tick={{ fill: "#9ca3af" }} dx={-10} domain={[0, 100]} />
                  <Tooltip contentStyle={{ backgroundColor: "#1a1a24", border: "1px solid #2a2a35", borderRadius: "8px", color: "#fff" }} />
                  <Line type="monotone" dataKey="score" stroke="#a855f7" strokeWidth={3} dot={{ fill: "#a855f7", strokeWidth: 2, r: 4 }} activeDot={{ r: 6, fill: "#a855f7", stroke: "#d8b4fe", strokeWidth: 4 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyState label="No assessment history yet." />
          )}
        </div>

        <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-6">
          <div className="mb-4">
            <h3 className="text-lg font-semibold text-white">Skill Radar</h3>
            <p className="text-sm text-gray-400">Holistic view of proficiencies</p>
          </div>
          {skillsData.length ? (
            <div className="h-[300px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart cx="50%" cy="50%" outerRadius="70%" data={skillsData}>
                  <PolarGrid stroke="#2a2a35" />
                  <PolarAngleAxis dataKey="subject" tick={{ fill: "#9ca3af", fontSize: 12 }} />
                  <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                  <Radar name="Student" dataKey="A" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.4} strokeWidth={2} />
                  <Tooltip contentStyle={{ backgroundColor: "#1a1a24", border: "1px solid #2a2a35", borderRadius: "8px", color: "#fff" }} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyState label="No skills breakdown available yet." />
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-6 overflow-hidden">
          <div className="mb-4">
            <h3 className="text-lg font-semibold text-white flex items-center gap-2">
              <Activity className="w-5 h-5 text-purple-400" />
              Activity Heatmap
            </h3>
            <p className="text-sm text-gray-400">Consistency in mock interviews and tests</p>
          </div>
          <CustomHeatmap data={heatmapData} />
        </div>

        <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-6">
          <div className="mb-4">
            <h3 className="text-lg font-semibold text-white">Subject Strengths</h3>
            <p className="text-sm text-gray-400">Identify areas for improvement</p>
          </div>
          {subjectData.length ? (
            <div className="h-[200px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={subjectData} layout="vertical" margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#2a2a35" />
                  <XAxis type="number" hide domain={[0, 100]} />
                  <YAxis dataKey="subject" type="category" axisLine={false} tickLine={false} tick={{ fill: "#9ca3af" }} />
                  <Tooltip cursor={{ fill: "#2a2a35" }} contentStyle={{ backgroundColor: "#1a1a24", border: "1px solid #2a2a35", borderRadius: "8px", color: "#fff" }} />
                  <Bar dataKey="score" radius={[0, 4, 4, 0]}>
                    {subjectData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.score > 70 ? "#10b981" : entry.score > 55 ? "#f59e0b" : "#ef4444"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyState label="No subject data available yet." />
          )}
        </div>
      </div>
    </div>
  );
};

"use client";

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from "recharts";
import { Users, AlertTriangle, CheckCircle2, TrendingUp } from "lucide-react";

const gradeDistribution = [
  { range: '0-40', count: 5 },
  { range: '41-60', count: 15 },
  { range: '61-75', count: 35 },
  { range: '76-90', count: 40 },
  { range: '91-100', count: 12 },
];

const classPerformance = [
  { week: 'Week 1', avg: 55 },
  { week: 'Week 2', avg: 62 },
  { week: 'Week 3', avg: 58 },
  { week: 'Week 4', avg: 70 },
  { week: 'Week 5', avg: 74 },
];

export const FacultyDashboard = () => {
  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      
      {/* Top Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-6 relative overflow-hidden">
          <div className="flex justify-between items-start mb-4">
            <h3 className="text-gray-400 font-medium">Total Students</h3>
            <div className="p-2 bg-blue-500/10 text-blue-400 rounded-lg">
              <Users className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-bold text-white">107</div>
        </div>
        
        <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-6 relative overflow-hidden">
          <div className="flex justify-between items-start mb-4">
            <h3 className="text-gray-400 font-medium">Class Average</h3>
            <div className="p-2 bg-purple-500/10 text-purple-400 rounded-lg">
              <TrendingUp className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-bold text-white">72%</div>
        </div>

        <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-6 relative overflow-hidden">
          <div className="flex justify-between items-start mb-4">
            <h3 className="text-gray-400 font-medium">At-Risk Students</h3>
            <div className="p-2 bg-red-500/10 text-red-400 rounded-lg">
              <AlertTriangle className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-bold text-white">12</div>
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
          <div className="text-3xl font-bold text-white">24</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Grade Distribution */}
        <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-6">
          <div className="mb-4">
            <h3 className="text-lg font-semibold text-white">Grade Distribution</h3>
            <p className="text-sm text-gray-400">Number of students by score range</p>
          </div>
          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={gradeDistribution}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#2a2a35" />
                <XAxis dataKey="range" axisLine={false} tickLine={false} tick={{fill: '#9ca3af'}} dy={10} />
                <YAxis axisLine={false} tickLine={false} tick={{fill: '#9ca3af'}} dx={-10} />
                <Tooltip cursor={{fill: '#2a2a35'}} contentStyle={{ backgroundColor: '#1a1a24', border: '1px solid #2a2a35', borderRadius: '8px', color: '#fff' }} />
                <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Class Performance Over Time */}
        <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-6">
          <div className="mb-4">
            <h3 className="text-lg font-semibold text-white">Class Average Trend</h3>
            <p className="text-sm text-gray-400">Weekly aggregate mock test scores</p>
          </div>
          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={classPerformance}>
                <defs>
                  <linearGradient id="colorAvg" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#a855f7" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#a855f7" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#2a2a35" />
                <XAxis dataKey="week" axisLine={false} tickLine={false} tick={{fill: '#9ca3af'}} dy={10} />
                <YAxis axisLine={false} tickLine={false} tick={{fill: '#9ca3af'}} dx={-10} domain={[0, 100]} />
                <Tooltip contentStyle={{ backgroundColor: '#1a1a24', border: '1px solid #2a2a35', borderRadius: '8px', color: '#fff' }} />
                <Area type="monotone" dataKey="avg" stroke="#a855f7" fillOpacity={1} fill="url(#colorAvg)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
      
      {/* Subject Mastery Heatmap Simulation (Simplified Table) */}
      <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-6">
        <h3 className="text-lg font-semibold text-white mb-4">Topic Mastery (CSE Core)</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-gray-400">
            <thead className="bg-[#13131a] text-gray-300">
              <tr>
                <th className="px-4 py-3 rounded-tl-lg">Topic</th>
                <th className="px-4 py-3">Proficient ({">"}75%)</th>
                <th className="px-4 py-3">Intermediate (50-75%)</th>
                <th className="px-4 py-3 rounded-tr-lg">Needs Help ({"<"}50%)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#2a2a35]">
              <tr>
                <td className="px-4 py-3 font-medium text-white">Data Structures</td>
                <td className="px-4 py-3"><span className="px-2 py-1 bg-green-500/10 text-green-400 rounded-full">45 students</span></td>
                <td className="px-4 py-3"><span className="px-2 py-1 bg-yellow-500/10 text-yellow-400 rounded-full">30 students</span></td>
                <td className="px-4 py-3"><span className="px-2 py-1 bg-red-500/10 text-red-400 rounded-full">32 students</span></td>
              </tr>
              <tr>
                <td className="px-4 py-3 font-medium text-white">Operating Systems</td>
                <td className="px-4 py-3"><span className="px-2 py-1 bg-green-500/10 text-green-400 rounded-full">60 students</span></td>
                <td className="px-4 py-3"><span className="px-2 py-1 bg-yellow-500/10 text-yellow-400 rounded-full">35 students</span></td>
                <td className="px-4 py-3"><span className="px-2 py-1 bg-red-500/10 text-red-400 rounded-full">12 students</span></td>
              </tr>
              <tr>
                <td className="px-4 py-3 font-medium text-white">Computer Networks</td>
                <td className="px-4 py-3"><span className="px-2 py-1 bg-green-500/10 text-green-400 rounded-full">25 students</span></td>
                <td className="px-4 py-3"><span className="px-2 py-1 bg-yellow-500/10 text-yellow-400 rounded-full">50 students</span></td>
                <td className="px-4 py-3"><span className="px-2 py-1 bg-red-500/10 text-red-400 rounded-full">32 students</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

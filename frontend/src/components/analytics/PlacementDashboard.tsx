"use client";

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from "recharts";
import { Briefcase, Building, CheckCircle2, TrendingUp } from "lucide-react";

const funnelData = [
  { stage: 'Eligible', count: 350 },
  { stage: 'Applied', count: 280 },
  { stage: 'Aptitude Cleared', count: 180 },
  { stage: 'Tech Interview', count: 120 },
  { stage: 'Offered', count: 85 },
];

const companyData = [
  { name: 'Product Based', value: 35 },
  { name: 'Service Based', value: 50 },
  { name: 'Startups', value: 15 },
];
const COLORS = ['#8b5cf6', '#3b82f6', '#f59e0b'];

export const PlacementDashboard = () => {
  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      
      {/* Top Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-6 relative overflow-hidden">
          <div className="flex justify-between items-start mb-4">
            <h3 className="text-gray-400 font-medium">Active Drives</h3>
            <div className="p-2 bg-blue-500/10 text-blue-400 rounded-lg">
              <Building className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-bold text-white">14</div>
        </div>
        
        <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-6 relative overflow-hidden">
          <div className="flex justify-between items-start mb-4">
            <h3 className="text-gray-400 font-medium">Offers Generated</h3>
            <div className="p-2 bg-green-500/10 text-green-400 rounded-lg">
              <CheckCircle2 className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-bold text-white">85</div>
        </div>

        <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-6 relative overflow-hidden">
          <div className="flex justify-between items-start mb-4">
            <h3 className="text-gray-400 font-medium">Avg Package (LPA)</h3>
            <div className="p-2 bg-purple-500/10 text-purple-400 rounded-lg">
              <TrendingUp className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-bold text-white">7.5</div>
          <p className="text-sm text-green-400 mt-2 font-medium">
            +15% YoY
          </p>
        </div>

        <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-6 relative overflow-hidden">
          <div className="flex justify-between items-start mb-4">
            <h3 className="text-gray-400 font-medium">Pending Apps</h3>
            <div className="p-2 bg-yellow-500/10 text-yellow-400 rounded-lg">
              <Briefcase className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-bold text-white">420</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Placement Funnel */}
        <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-6">
          <div className="mb-4">
            <h3 className="text-lg font-semibold text-white">Placement Funnel</h3>
            <p className="text-sm text-gray-400">Drop-off rates across hiring stages</p>
          </div>
          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={funnelData} layout="vertical" margin={{ left: 30 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#2a2a35" />
                <XAxis type="number" hide />
                <YAxis dataKey="stage" type="category" axisLine={false} tickLine={false} tick={{fill: '#9ca3af'}} />
                <Tooltip cursor={{fill: '#2a2a35'}} contentStyle={{ backgroundColor: '#1a1a24', border: '1px solid #2a2a35', borderRadius: '8px', color: '#fff' }} />
                <Bar dataKey="count" fill="#8b5cf6" radius={[0, 4, 4, 0]} barSize={30} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Company Types */}
        <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-6">
          <div className="mb-4">
            <h3 className="text-lg font-semibold text-white">Company Distribution</h3>
            <p className="text-sm text-gray-400">Breakdown of recruiting companies</p>
          </div>
          <div className="h-[300px] w-full flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={companyData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {companyData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: '#1a1a24', border: '1px solid #2a2a35', borderRadius: '8px', color: '#fff' }} />
              </PieChart>
            </ResponsiveContainer>
            
            <div className="absolute right-12 flex flex-col gap-4">
              {companyData.map((entry, index) => (
                <div key={index} className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: COLORS[index] }} />
                  <span className="text-sm text-gray-300">{entry.name} ({entry.value}%)</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

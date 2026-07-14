"use client";

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from "recharts";
import { Server, Users, Activity, Zap } from "lucide-react";

const apiUsageData = [
  { day: 'Mon', calls: 12000 },
  { day: 'Tue', calls: 15000 },
  { day: 'Wed', calls: 14000 },
  { day: 'Thu', calls: 22000 },
  { day: 'Fri', calls: 18000 },
  { day: 'Sat', calls: 9000 },
  { day: 'Sun', calls: 11000 },
];

const activeUsersData = [
  { time: '08:00', users: 120 },
  { time: '12:00', users: 340 },
  { time: '16:00', users: 280 },
  { time: '20:00', users: 450 },
  { time: '24:00', users: 100 },
];

export const AdminDashboard = () => {
  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      
      {/* Top Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-6 relative overflow-hidden">
          <div className="flex justify-between items-start mb-4">
            <h3 className="text-gray-400 font-medium">System Status</h3>
            <div className="p-2 bg-green-500/10 text-green-400 rounded-lg">
              <Server className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-bold text-white">99.9%</div>
          <p className="text-sm text-green-400 mt-2 font-medium">Operational</p>
        </div>
        
        <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-6 relative overflow-hidden">
          <div className="flex justify-between items-start mb-4">
            <h3 className="text-gray-400 font-medium">Active Users</h3>
            <div className="p-2 bg-blue-500/10 text-blue-400 rounded-lg">
              <Users className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-bold text-white">450</div>
          <p className="text-sm text-blue-400 mt-2 font-medium">Currently online</p>
        </div>

        <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-6 relative overflow-hidden">
          <div className="flex justify-between items-start mb-4">
            <h3 className="text-gray-400 font-medium">API Calls (Gemini)</h3>
            <div className="p-2 bg-purple-500/10 text-purple-400 rounded-lg">
              <Zap className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-bold text-white">101k</div>
          <p className="text-sm text-gray-400 mt-2 font-medium">This week</p>
        </div>

        <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-6 relative overflow-hidden">
          <div className="flex justify-between items-start mb-4">
            <h3 className="text-gray-400 font-medium">Assessments Taken</h3>
            <div className="p-2 bg-yellow-500/10 text-yellow-400 rounded-lg">
              <Activity className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-bold text-white">12.5k</div>
          <p className="text-sm text-gray-400 mt-2 font-medium">Total platform</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* API Usage */}
        <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-6">
          <div className="mb-4">
            <h3 className="text-lg font-semibold text-white">API Usage (Gemini/LLM)</h3>
            <p className="text-sm text-gray-400">Weekly call volume</p>
          </div>
          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={apiUsageData}>
                <defs>
                  <linearGradient id="colorCalls" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#2a2a35" />
                <XAxis dataKey="day" axisLine={false} tickLine={false} tick={{fill: '#9ca3af'}} dy={10} />
                <YAxis axisLine={false} tickLine={false} tick={{fill: '#9ca3af'}} dx={-10} />
                <Tooltip contentStyle={{ backgroundColor: '#1a1a24', border: '1px solid #2a2a35', borderRadius: '8px', color: '#fff' }} />
                <Area type="monotone" dataKey="calls" stroke="#8b5cf6" fillOpacity={1} fill="url(#colorCalls)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Active Users */}
        <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-6">
          <div className="mb-4">
            <h3 className="text-lg font-semibold text-white">Concurrent Users</h3>
            <p className="text-sm text-gray-400">Today's active user load</p>
          </div>
          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={activeUsersData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#2a2a35" />
                <XAxis dataKey="time" axisLine={false} tickLine={false} tick={{fill: '#9ca3af'}} dy={10} />
                <YAxis axisLine={false} tickLine={false} tick={{fill: '#9ca3af'}} dx={-10} />
                <Tooltip contentStyle={{ backgroundColor: '#1a1a24', border: '1px solid #2a2a35', borderRadius: '8px', color: '#fff' }} />
                <Line 
                  type="monotone" 
                  dataKey="users" 
                  stroke="#3b82f6" 
                  strokeWidth={3}
                  dot={{ fill: '#3b82f6', strokeWidth: 2, r: 4 }}
                  activeDot={{ r: 6, fill: '#3b82f6', stroke: '#93c5fd', strokeWidth: 4 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
};

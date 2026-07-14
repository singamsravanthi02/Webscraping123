"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Sparkles, User, GraduationCap, Briefcase, Settings } from "lucide-react";
import dynamic from "next/dynamic";
import { Loader2 } from "lucide-react";

// Lazy load heavy recharts dashboards to reduce initial bundle size by ~40%
const LoadingPlaceholder = () => <div className="h-full flex items-center justify-center"><Loader2 className="w-8 h-8 animate-spin text-purple-500" /></div>;

const StudentDashboard = dynamic(() => import("@/components/analytics/StudentDashboard").then(m => m.StudentDashboard), { loading: LoadingPlaceholder });
const FacultyDashboard = dynamic(() => import("@/components/analytics/FacultyDashboard").then(m => m.FacultyDashboard), { loading: LoadingPlaceholder });
const PlacementDashboard = dynamic(() => import("@/components/analytics/PlacementDashboard").then(m => m.PlacementDashboard), { loading: LoadingPlaceholder });
const AdminDashboard = dynamic(() => import("@/components/analytics/AdminDashboard").then(m => m.AdminDashboard), { loading: LoadingPlaceholder });

const tabs = [
  { id: 'student', label: 'Student View', icon: User },
  { id: 'faculty', label: 'Faculty View', icon: GraduationCap },
  { id: 'placement', label: 'Placement Officer', icon: Briefcase },
  { id: 'admin', label: 'System Admin', icon: Settings },
];

export default function UnifiedAnalyticsDashboard() {
  const [activeTab, setActiveTab] = useState('student');

  return (
    <div className="flex flex-col h-full bg-slate-50 text-slate-900 p-8 max-w-7xl mx-auto rounded-3xl min-h-[calc(100vh-2rem)]">
      
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-3 text-slate-900">
            <Sparkles className="w-8 h-8 text-purple-600" />
            Platform Analytics
          </h1>
          <p className="text-slate-500 mt-2">Comprehensive insights across all roles and metrics.</p>
        </div>
        
        {/* Role Tabs */}
        <div className="flex p-1 bg-white border border-slate-200 rounded-xl overflow-x-auto w-full md:w-auto hide-scrollbar shadow-sm">
          {tabs.map(tab => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`relative flex items-center gap-2 px-4 py-2.5 text-sm font-medium rounded-lg transition-colors whitespace-nowrap ${
                  isActive ? 'text-white' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                }`}
              >
                {isActive && (
                  <motion.div
                    layoutId="activeTab"
                    className="absolute inset-0 bg-purple-600 rounded-lg shadow-lg"
                    initial={false}
                    transition={{ type: "spring", stiffness: 300, damping: 30 }}
                  />
                )}
                <span className="relative z-10 flex items-center gap-2">
                  <tab.icon className="w-4 h-4" />
                  {tab.label}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Content Area */}
      <div className="flex-1 relative">
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
            className="h-full"
          >
            {activeTab === 'student' && <StudentDashboard />}
            {activeTab === 'faculty' && <FacultyDashboard />}
            {activeTab === 'placement' && <PlacementDashboard />}
            {activeTab === 'admin' && <AdminDashboard />}
          </motion.div>
        </AnimatePresence>
      </div>

    </div>
  );
}

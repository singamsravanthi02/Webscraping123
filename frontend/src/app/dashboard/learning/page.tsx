"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { BookOpen, Sparkles, Upload, FileText, Search, Library, Plus } from "lucide-react";
import api from "@/lib/api";

type LearningSession = {
  id: number;
  title: string;
  subject?: string | null;
  created_at: string;
};

export default function LearningDashboard() {
  const router = useRouter();
  const [sessions, setSessions] = useState<LearningSession[]>([]);
  const [subject, setSubject] = useState("");
  const [title, setTitle] = useState("");
  const [isUploading, setIsUploading] = useState(false);

  const fetchSessions = useCallback(async () => {
    try {
      const res = await api.get("/learning/sessions");
      setSessions(res.data);
    } catch (error) {
      console.error(error);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void fetchSessions();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [fetchSessions]);

  const startSession = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title) return;
    try {
      const res = await api.post("/learning/sessions", { title, subject });
      router.push(`/dashboard/learning/chat/${res.data.id}`);
    } catch (error) {
      console.error(error);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    const formData = new FormData();
    formData.append("file", file);
    formData.append("title", file.name);
    formData.append("type", file.type.includes("pdf") ? "pdf" : "text");

    try {
      await api.post("/learning/resources/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });
      alert("Document successfully ingested into the knowledge base!");
    } catch (error) {
      console.error(error);
      alert("Failed to upload document.");
    } finally {
      setIsUploading(false);
      if (e.target) e.target.value = '';
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-12 animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* Header section */}
      <div className="flex justify-between items-center bg-white p-8 rounded-3xl border border-gray-200 shadow-xl relative overflow-hidden">
        <div className="absolute -top-24 -right-24 w-64 h-64 bg-blue-50 blur-3xl rounded-full" />
        <div className="absolute -bottom-24 -left-24 w-64 h-64 bg-purple-50 blur-3xl rounded-full" />
        
        <div className="relative z-10">
          <h1 className="text-4xl font-bold text-gray-900 mb-2 flex items-center gap-3">
            <Sparkles className="w-8 h-8 text-blue-600" />
            AI Learning Hub
          </h1>
          <p className="text-gray-600 text-lg max-w-xl">
            Your personalized AI tutor. Ask questions, generate flashcards, and master your subjects using trusted materials.
          </p>
        </div>
        
        <div className="relative z-10 flex flex-col gap-3">
          <label className="flex items-center gap-2 bg-white hover:bg-gray-50 border border-gray-200 text-gray-700 px-6 py-3 rounded-xl transition-colors font-medium cursor-pointer shadow-sm">
            {isUploading ? (
              <span className="animate-pulse">Ingesting...</span>
            ) : (
              <>
                <Upload className="w-5 h-5 text-gray-500" />
                Upload Material
              </>
            )}
            <input 
              type="file" 
              accept=".pdf,.txt" 
              className="hidden" 
              onChange={handleFileUpload} 
              disabled={isUploading}
            />
          </label>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Start New Session */}
        <div className="lg:col-span-1 bg-white border border-gray-200 rounded-3xl p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-gray-900 mb-6 flex items-center gap-2">
            <Plus className="w-5 h-5 text-purple-600" />
            New Study Session
          </h2>
          <form onSubmit={startSession} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Subject (Optional)</label>
              <input 
                type="text"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                placeholder="e.g. Data Structures, CN"
                className="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 text-gray-900 focus:outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500 transition-colors placeholder:text-gray-400"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Topic / Title</label>
              <input 
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Trees and Graphs"
                required
                className="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 text-gray-900 focus:outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500 transition-colors placeholder:text-gray-400"
              />
            </div>
            <button 
              type="submit"
              className="w-full mt-4 flex items-center justify-center gap-2 bg-purple-600 hover:bg-purple-700 text-white px-6 py-3 rounded-xl font-medium transition-colors shadow-md shadow-purple-500/20"
            >
              <BookOpen className="w-5 h-5" />
              Start Learning
            </button>
          </form>
        </div>

        {/* Recent Sessions */}
        <div className="lg:col-span-2">
          <h2 className="text-xl font-semibold text-gray-900 mb-6 flex items-center gap-2">
            <Library className="w-5 h-5 text-blue-600" />
            Recent Study Sessions
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {sessions.map((session) => (
              <div 
                key={session.id} 
                onClick={() => router.push(`/dashboard/learning/chat/${session.id}`)}
                className="bg-white border border-gray-200 rounded-2xl p-5 hover:border-blue-500/50 hover:shadow-md cursor-pointer transition-all group"
              >
                <div className="flex justify-between items-start mb-3">
                  <div className="p-2.5 rounded-lg bg-blue-50 text-blue-600 group-hover:bg-blue-100 transition-colors">
                    <FileText className="w-5 h-5" />
                  </div>
                  <span className="text-xs font-medium text-gray-400">
                    {new Date(session.created_at).toLocaleDateString()}
                  </span>
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-1">{session.title}</h3>
                {session.subject && (
                  <p className="text-sm text-gray-500">{session.subject}</p>
                )}
              </div>
            ))}
            
            {sessions.length === 0 && (
              <div className="col-span-full py-12 flex flex-col items-center justify-center text-center border-2 border-dashed border-gray-200 rounded-2xl bg-gray-50/50">
                <Search className="w-10 h-10 text-gray-400 mb-3" />
                <p className="text-gray-600 font-medium">No recent sessions found.</p>
                <p className="text-sm text-gray-500 mt-1">Start a new study session to begin learning.</p>
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}

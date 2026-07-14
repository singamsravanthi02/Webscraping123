"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Plus, Clock, Brain, UserPlus, Code2, FileText, ChevronRight, MessageSquare, Mic } from "lucide-react";
import api from "@/lib/api";

interface Interview {
  id: number;
  title: string;
  type: string;
  status: string;
  start_time: string;
}

const interviewTypes = [
  { id: "hr", title: "HR Interview", icon: UserPlus, color: "text-blue-500", bg: "bg-blue-500/10" },
  { id: "technical", title: "Technical Interview", icon: Brain, color: "text-purple-500", bg: "bg-purple-500/10" },
  { id: "behavioral", title: "Behavioral Interview", icon: MessageSquare, color: "text-green-500", bg: "bg-green-500/10" },
  { id: "coding", title: "Coding Interview", icon: Code2, color: "text-yellow-500", bg: "bg-yellow-500/10" },
  { id: "resume", title: "Resume Based", icon: FileText, color: "text-rose-500", bg: "bg-rose-500/10" }
];

export default function InterviewsDashboard() {
  const router = useRouter();
  const [interviews, setInterviews] = useState<Interview[]>([]);
  const [isCreating, setIsCreating] = useState(false);
  
  // New interview state
  const [selectedType, setSelectedType] = useState("hr");
  const [title, setTitle] = useState("");
  const [resumeText, setResumeText] = useState("");
  const [jobDescription, setJobDescription] = useState("");

  useEffect(() => {
    fetchInterviews();
  }, []);

  const fetchInterviews = async () => {
    try {
      const response = await api.get("/interviews");
      setInterviews(response.data);
    } catch (error) {
      console.error("Failed to fetch interviews:", error);
    }
  };

  const startNewInterview = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload = {
        title: title || `${selectedType.charAt(0).toUpperCase() + selectedType.slice(1)} Interview`,
        type: selectedType,
        resume_text: resumeText,
        job_description: jobDescription
      };
      const response = await api.post("/interviews", payload);
      router.push(`/dashboard/interviews/${response.data.id}/live`);
    } catch (error) {
      console.error("Failed to start interview:", error);
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-purple-400 to-blue-400">
            AI Interview Engine
          </h1>
          <p className="text-gray-400 mt-2">Master your interview skills with realistic AI-driven mock interviews.</p>
        </div>
        <button 
          onClick={() => setIsCreating(true)}
          className="flex items-center gap-2 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-500 hover:to-blue-500 text-white px-6 py-3 rounded-full font-medium transition-all shadow-[0_0_20px_rgba(124,58,237,0.3)]"
        >
          <Plus className="w-5 h-5" />
          New Interview
        </button>
      </div>

      {isCreating ? (
        <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-8 shadow-xl animate-in fade-in slide-in-from-bottom-4 duration-500">
          <h2 className="text-2xl font-semibold text-white mb-6">Configure Your Interview</h2>
          <form onSubmit={startNewInterview} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
              {interviewTypes.map(type => (
                <div 
                  key={type.id}
                  onClick={() => setSelectedType(type.id)}
                  className={`cursor-pointer border rounded-xl p-4 flex flex-col items-center justify-center gap-3 transition-all ${selectedType === type.id ? 'border-purple-500 bg-purple-500/10' : 'border-[#2a2a35] hover:border-[#3a3a45] bg-[#1e1e28]'}`}
                >
                  <div className={`p-3 rounded-full ${type.bg} ${type.color}`}>
                    <type.icon className="w-6 h-6" />
                  </div>
                  <span className="text-sm font-medium text-gray-200 text-center">{type.title}</span>
                </div>
              ))}
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-400 mb-2">Interview Title (Optional)</label>
                <input 
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Google Frontend Engineer Mock"
                  className="w-full bg-[#13131a] border border-[#2a2a35] rounded-xl px-4 py-3 text-white focus:outline-none focus:border-purple-500 transition-colors"
                />
              </div>

              {selectedType === 'resume' && (
                <div className="animate-in fade-in zoom-in duration-300">
                  <label className="block text-sm font-medium text-gray-400 mb-2">Paste Your Resume Content</label>
                  <textarea 
                    value={resumeText}
                    onChange={(e) => setResumeText(e.target.value)}
                    placeholder="Paste your resume text here..."
                    className="w-full h-32 bg-[#13131a] border border-[#2a2a35] rounded-xl px-4 py-3 text-white focus:outline-none focus:border-purple-500 transition-colors resize-none"
                    required
                  />
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-400 mb-2">Job Description (Optional, for better context)</label>
                <textarea 
                  value={jobDescription}
                  onChange={(e) => setJobDescription(e.target.value)}
                  placeholder="Paste the target job description here..."
                  className="w-full h-24 bg-[#13131a] border border-[#2a2a35] rounded-xl px-4 py-3 text-white focus:outline-none focus:border-purple-500 transition-colors resize-none"
                />
              </div>
            </div>

            <div className="flex justify-end gap-4 mt-8 pt-6 border-t border-[#2a2a35]">
              <button 
                type="button"
                onClick={() => setIsCreating(false)}
                className="px-6 py-3 rounded-xl font-medium text-gray-400 hover:text-white hover:bg-[#2a2a35] transition-colors"
              >
                Cancel
              </button>
              <button 
                type="submit"
                className="px-8 py-3 rounded-xl font-medium text-white bg-purple-600 hover:bg-purple-500 transition-colors shadow-lg shadow-purple-500/25"
              >
                Start Interview
              </button>
            </div>
          </form>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {interviews.map(interview => {
            const Icon = interviewTypes.find(t => t.id === interview.type)?.icon || Brain;
            const typeConfig = interviewTypes.find(t => t.id === interview.type);
            
            return (
              <div key={interview.id} className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-6 hover:border-purple-500/50 transition-all group">
                <div className="flex justify-between items-start mb-4">
                  <div className={`p-3 rounded-xl ${typeConfig?.bg || 'bg-purple-500/10'} ${typeConfig?.color || 'text-purple-500'}`}>
                    <Icon className="w-6 h-6" />
                  </div>
                  <span className={`px-3 py-1 rounded-full text-xs font-medium border ${
                    interview.status === 'completed' ? 'border-green-500/20 text-green-400 bg-green-500/10' : 
                    interview.status === 'in_progress' ? 'border-blue-500/20 text-blue-400 bg-blue-500/10' : 
                    'border-gray-500/20 text-gray-400 bg-gray-500/10'
                  }`}>
                    {interview.status.replace('_', ' ').toUpperCase()}
                  </span>
                </div>
                <h3 className="text-xl font-semibold text-white mb-2">{interview.title}</h3>
                <div className="flex items-center gap-2 text-sm text-gray-400 mb-6">
                  <Clock className="w-4 h-4" />
                  {new Date(interview.start_time).toLocaleDateString()}
                </div>
                
                {interview.status === 'completed' ? (
                  <button 
                    onClick={() => router.push(`/dashboard/interviews/${interview.id}/result`)}
                    className="w-full flex items-center justify-center gap-2 py-3 bg-[#2a2a35] hover:bg-[#3a3a45] text-white rounded-xl transition-colors font-medium"
                  >
                    View Results
                    <ChevronRight className="w-4 h-4" />
                  </button>
                ) : (
                  <button 
                    onClick={() => router.push(`/dashboard/interviews/${interview.id}/live`)}
                    className="w-full flex items-center justify-center gap-2 py-3 bg-purple-600/10 hover:bg-purple-600 text-purple-400 hover:text-white border border-purple-500/20 rounded-xl transition-all font-medium group-hover:border-purple-500/50"
                  >
                    Resume Interview
                    <ChevronRight className="w-4 h-4" />
                  </button>
                )}
              </div>
            );
          })}
          
          {interviews.length === 0 && (
            <div className="col-span-full py-20 flex flex-col items-center justify-center text-center border-2 border-dashed border-[#2a2a35] rounded-3xl">
              <div className="w-20 h-20 bg-purple-500/10 rounded-full flex items-center justify-center mb-6">
                <Mic className="w-10 h-10 text-purple-500" />
              </div>
              <h3 className="text-xl font-semibold text-white mb-2">No Interviews Yet</h3>
              <p className="text-gray-400 max-w-md mb-8">Ready to test your skills? Start a new mock interview and get real-time feedback powered by AI.</p>
              <button 
                onClick={() => setIsCreating(true)}
                className="bg-white text-black px-6 py-3 rounded-full font-medium hover:bg-gray-100 transition-colors"
              >
                Create Your First Interview
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

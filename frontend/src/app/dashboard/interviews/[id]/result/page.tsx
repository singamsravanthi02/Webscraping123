"use client";

import { useState, useEffect, use, useCallback, type ComponentType } from "react";
import { useRouter } from "next/navigation";
import { Trophy, MessageSquare, Brain, Target, ArrowLeft, Download, CheckCircle2, AlertTriangle, Lightbulb, BookOpen, Star, Code2 } from "lucide-react";
import api from "@/lib/api";
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
} from "recharts";

interface InterviewResult {
  confidence_score: number;
  communication_score: number;
  technical_score: number;
  problem_solving_score: number;
  overall_grade: number;
  feedback_summary: string;
  suggestions: string[];
  strengths: string[];
  weaknesses: string[];
  recommended_topics: string[];
  learning_plan: string;
}

interface TranscriptMessage {
  role: "system" | "user" | "ai";
  content: string;
}

type ScoreCardProps = {
  title: string;
  score: number;
  icon: ComponentType<{ className?: string }>;
  color: "purple" | "blue" | "green" | "rose" | "yellow";
};

const SCORE_CARD_STYLES: Record<ScoreCardProps["color"], { glow: string; icon: string; bar: string }> = {
  purple: { glow: "bg-purple-500/5 group-hover:bg-purple-500/10", icon: "bg-purple-500/10 text-purple-400", bar: "bg-purple-500" },
  blue: { glow: "bg-blue-500/5 group-hover:bg-blue-500/10", icon: "bg-blue-500/10 text-blue-400", bar: "bg-blue-500" },
  green: { glow: "bg-green-500/5 group-hover:bg-green-500/10", icon: "bg-green-500/10 text-green-400", bar: "bg-green-500" },
  rose: { glow: "bg-rose-500/5 group-hover:bg-rose-500/10", icon: "bg-rose-500/10 text-rose-400", bar: "bg-rose-500" },
  yellow: { glow: "bg-yellow-500/5 group-hover:bg-yellow-500/10", icon: "bg-yellow-500/10 text-yellow-400", bar: "bg-yellow-500" },
};

function ScoreCard({ title, score, icon: Icon, color }: ScoreCardProps) {
  const styles = SCORE_CARD_STYLES[color];
  return (
    <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-6 relative overflow-hidden group">
      <div className={`absolute top-0 right-0 w-32 h-32 rounded-full blur-3xl transition-colors ${styles.glow}`} />
      <div className="flex justify-between items-start mb-4 relative z-10">
        <div className={`p-3 rounded-xl ${styles.icon}`}>
          <Icon className="w-6 h-6" />
        </div>
        <span className="text-4xl font-bold text-white">{score || 0}<span className="text-lg text-gray-500">/10</span></span>
      </div>
      <h3 className="text-gray-400 font-medium relative z-10">{title}</h3>

      <div className="mt-4 h-2 w-full bg-[#2a2a35] rounded-full overflow-hidden relative z-10">
        <div
          className={`h-full rounded-full transition-all duration-1000 ease-out ${styles.bar}`}
          style={{ width: `${((score || 0) / 10) * 100}%` }}
        />
      </div>
    </div>
  );
}

export default function InterviewResult({ params }: { params: Promise<{ id: string }> }) {
  const router = useRouter();
  const { id } = use(params);
  const [result, setResult] = useState<InterviewResult | null>(null);
  const [transcript, setTranscript] = useState<TranscriptMessage[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchResult = useCallback(async () => {
    try {
      const res = await api.get<{ result: InterviewResult; messages: TranscriptMessage[] }>(`/interviews/${id}`);
      setResult(res.data.result);
      setTranscript(res.data.messages);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void fetchResult();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [fetchResult]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-purple-500"></div>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
        <AlertTriangle className="w-16 h-16 text-yellow-500 mb-4" />
        <h2 className="text-2xl font-bold text-white mb-2">Result Pending</h2>
        <p className="text-gray-400 mb-6">The evaluation is still being processed or the interview wasn&apos;t completed properly.</p>
        <button onClick={() => router.push('/dashboard/interviews')} className="bg-purple-600 text-white px-6 py-2 rounded-full">Go Back</button>
      </div>
    );
  }

  const radarData = [
    { subject: 'Overall', A: result.overall_grade || 0, fullMark: 10 },
    { subject: 'Technical', A: result.technical_score || 0, fullMark: 10 },
    { subject: 'Communication', A: result.communication_score || 0, fullMark: 10 },
    { subject: 'Confidence', A: result.confidence_score || 0, fullMark: 10 },
    { subject: 'Problem Solving', A: result.problem_solving_score || 0, fullMark: 10 },
  ];

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <button 
            onClick={() => router.push('/dashboard/interviews')}
            className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors mb-4 text-sm font-medium"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Dashboard
          </button>
          <h1 className="text-3xl font-bold text-white">Interview Evaluation Report</h1>
        </div>
        <button className="flex items-center gap-2 bg-[#2a2a35] hover:bg-[#3a3a45] text-white px-6 py-3 rounded-xl transition-colors font-medium">
          <Download className="w-5 h-5" />
          Export PDF
        </button>
      </div>

      {/* Scores Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
        <ScoreCard title="Overall Grade" score={result.overall_grade} icon={Trophy} color="purple" />
        <ScoreCard title="Technical Depth" score={result.technical_score} icon={Brain} color="blue" />
        <ScoreCard title="Communication" score={result.communication_score} icon={MessageSquare} color="green" />
        <ScoreCard title="Confidence" score={result.confidence_score} icon={Target} color="rose" />
        <ScoreCard title="Problem Solving" score={result.problem_solving_score} icon={Code2} color="yellow" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Column */}
        <div className="lg:col-span-2 space-y-8">
          
          <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-8">
            <h2 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-green-400" />
              Executive Summary
            </h2>
            <p className="text-gray-300 leading-relaxed">
              {result.feedback_summary}
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-8">
              <h2 className="text-lg font-semibold text-white mb-6 flex items-center gap-2">
                <Star className="w-5 h-5 text-yellow-400" />
                Strengths
              </h2>
              <ul className="space-y-3">
                {result.strengths?.map((item: string, idx: number) => (
                  <li key={idx} className="flex items-start gap-3">
                    <div className="w-1.5 h-1.5 rounded-full bg-green-500 mt-2" />
                    <span className="text-gray-300">{item}</span>
                  </li>
                )) || <li className="text-gray-500">None identified.</li>}
              </ul>
            </div>
            
            <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-8">
              <h2 className="text-lg font-semibold text-white mb-6 flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-rose-400" />
                Weaknesses
              </h2>
              <ul className="space-y-3">
                {result.weaknesses?.map((item: string, idx: number) => (
                  <li key={idx} className="flex items-start gap-3">
                    <div className="w-1.5 h-1.5 rounded-full bg-rose-500 mt-2" />
                    <span className="text-gray-300">{item}</span>
                  </li>
                )) || <li className="text-gray-500">None identified.</li>}
              </ul>
            </div>
          </div>

          <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-8">
            <h2 className="text-xl font-semibold text-white mb-6 flex items-center gap-2">
              <BookOpen className="w-5 h-5 text-blue-400" />
              Personalized Learning Plan
            </h2>
            <p className="text-gray-300 leading-relaxed mb-6">
              {result.learning_plan}
            </p>
            
            <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider mb-4">Recommended Topics to Study</h3>
            <div className="flex flex-wrap gap-2">
              {result.recommended_topics?.map((topic, idx) => (
                <span key={idx} className="px-3 py-1 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-400 text-sm">
                  {topic}
                </span>
              ))}
            </div>
          </div>
          
          <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-8">
            <h2 className="text-xl font-semibold text-white mb-6 flex items-center gap-2">
              <Lightbulb className="w-5 h-5 text-yellow-400" />
              Actionable Suggestions
            </h2>
            <ul className="space-y-4">
              {result.suggestions?.map((suggestion: string, idx: number) => (
                <li key={idx} className="flex gap-4 p-4 rounded-xl bg-[#2a2a35]/50 border border-[#2a2a35]">
                  <span className="flex-shrink-0 w-8 h-8 rounded-full bg-purple-500/10 text-purple-400 flex items-center justify-center font-semibold">
                    {idx + 1}
                  </span>
                  <p className="text-gray-300 pt-1">{suggestion}</p>
                </li>
              ))}
            </ul>
          </div>

        </div>

        {/* Right Column */}
        <div className="space-y-8">
          
          {/* Radar Chart */}
          <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-6">
            <h2 className="text-lg font-semibold text-white mb-4">Performance Radar</h2>
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart cx="50%" cy="50%" outerRadius="70%" data={radarData}>
                  <PolarGrid stroke="#2a2a35" />
                  <PolarAngleAxis dataKey="subject" tick={{ fill: '#9ca3af', fontSize: 11 }} />
                  <PolarRadiusAxis angle={30} domain={[0, 10]} tick={false} axisLine={false} />
                  <Radar
                    name="Student"
                    dataKey="A"
                    stroke="#a855f7"
                    strokeWidth={2}
                    fill="#a855f7"
                    fillOpacity={0.3}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Transcript Section */}
          <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-0 flex flex-col h-[600px]">
            <div className="p-6 border-b border-[#2a2a35]">
              <h2 className="text-xl font-semibold text-white">Interview Transcript</h2>
            </div>
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {transcript.filter(m => m.role !== 'system').map((msg, idx) => (
                <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm ${
                    msg.role === 'user' 
                      ? 'bg-[#2a2a35] text-white rounded-br-none' 
                      : 'bg-purple-500/10 border border-purple-500/20 text-gray-200 rounded-bl-none'
                  }`}>
                    <span className="block text-xs text-gray-500 mb-1 font-medium">
                      {msg.role === 'user' ? 'You' : 'AI Interviewer'}
                    </span>
                    <p className="leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

        </div>

      </div>

    </div>
  );
}

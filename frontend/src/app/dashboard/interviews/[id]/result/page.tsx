"use client";

import { useState, useEffect, useCallback, type ComponentType } from "react";
import { useRouter, usePathname } from "next/navigation";
import { Trophy, MessageSquare, Brain, Target, ArrowLeft, CheckCircle2, AlertTriangle, Lightbulb, BookOpen, Star, Code2, Share2, Printer, Sparkles, Timer } from "lucide-react";
import api from "@/lib/api";
import { parseInterviewBrief } from "@/lib/interview";
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

interface InterviewLockViolation {
  type: string;
  details?: string | null;
  recorded_at?: string | null;
}

interface TranscriptMessage {
  role: "system" | "user" | "ai";
  content: string;
  created_at?: string;
}

interface InterviewDetail {
  title: string;
  type: string;
  status: string;
  job_description?: string | null;
  start_time?: string;
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

function EmptyListItem() {
  return <li className="text-gray-500">None identified.</li>;
}

function clampScore(value: number) {
  return Math.max(0, Math.min(10, Math.round(value)));
}

export default function InterviewResult() {
  const router = useRouter();
  const pathname = usePathname();
  const id = pathname.split("/").filter(Boolean).at(-2) || "";
  const [result, setResult] = useState<InterviewResult | null>(null);
  const [transcript, setTranscript] = useState<TranscriptMessage[]>([]);
  const [lockViolations, setLockViolations] = useState<InterviewLockViolation[]>([]);
  const [interview, setInterview] = useState<InterviewDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const showGenerating = isGenerating || (!result && interview?.status === "completed");

  const fetchResult = useCallback(async () => {
    try {
      const res = await api.get<{ result: InterviewResult; messages: TranscriptMessage[]; lock_violations?: InterviewLockViolation[] } & InterviewDetail>(`/interviews/${id}`);
      setResult(res.data.result || null);
      setTranscript(res.data.messages);
      setLockViolations(res.data.lock_violations || []);
      setInterview({
        title: res.data.title,
        type: res.data.type,
        status: res.data.status,
        job_description: res.data.job_description,
        start_time: res.data.start_time,
      });
      setIsGenerating(res.data.status === "completed" && !res.data.result);
      return Boolean(res.data.result);
    } catch (error) {
      console.error(error);
      return false;
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    let interval: number | undefined;
    let cancelled = false;
    const poll = async () => {
      if (cancelled) return;
      const ready = await fetchResult();
      if (cancelled) return;
      if (ready) {
        setIsGenerating(false);
        if (interval) {
          window.clearInterval(interval);
          interval = undefined;
        }
      } else if (!interval) {
        interval = window.setInterval(() => {
          void poll();
        }, 2000);
      }
    };
    void poll();
    return () => {
      cancelled = true;
      if (interval) {
        window.clearInterval(interval);
      }
    };
  }, [fetchResult]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-purple-500"></div>
      </div>
    );
  }

  if (showGenerating) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-6">
        <div className="mb-4 rounded-full bg-purple-500/10 p-4">
          <Trophy className="w-10 h-10 text-purple-400 animate-pulse" />
        </div>
        <h2 className="text-2xl font-bold text-white mb-2">Generating your AI Report...</h2>
        <p className="text-gray-400 mb-4 max-w-md">
          We have ended the interview and are scoring the transcript in the background. This page refreshes automatically every few seconds.
        </p>
        <div className="h-2 w-64 overflow-hidden rounded-full bg-white/10">
          <div className="h-full w-1/3 animate-pulse rounded-full bg-purple-500" />
        </div>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
        <AlertTriangle className="w-16 h-16 text-yellow-500 mb-4" />
        <h2 className="text-2xl font-bold text-white mb-2">Result Pending</h2>
        <p className="text-gray-400 mb-6">The interview is still being processed or was not completed properly.</p>
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
  const meta = parseInterviewBrief(interview?.job_description, interview?.type, interview?.title);
  const isCoding = meta.mode === "coding";
  const qaPairs = transcript
    .filter((message) => message.role !== "system")
    .reduce<Array<{ question: string; answer: string; index: number }>>((pairs, message, index, list) => {
      if (message.role !== "ai") return pairs;
      const answer = list.slice(index + 1).find((entry) => entry.role === "user");
      pairs.push({
        question: message.content,
        answer: answer?.content || "",
        index: pairs.length + 1,
      });
      return pairs;
    }, []);
  const codingRubric = [
    { label: "Algorithm", score: clampScore(result.technical_score || 0) },
    { label: "Complexity", score: clampScore(result.problem_solving_score || 0) },
    { label: "Readability", score: clampScore(result.communication_score || 0) },
    { label: "Naming", score: clampScore(result.confidence_score || 0) },
    { label: "Optimization", score: clampScore(((result.technical_score || 0) + (result.problem_solving_score || 0)) / 2) },
    { label: "Edge cases", score: clampScore(((result.overall_grade || 0) + (result.problem_solving_score || 0)) / 2) },
    { label: "Alternative solution", score: clampScore(((result.overall_grade || 0) + 6) / 2) },
  ];
  const scoreSummary = Math.round((result.overall_grade || 0) * 10);
  const downloadPdf = () => window.print();
  const shareReport = async () => {
    const text = [
      `Interview report: ${meta.label}`,
      `Company: ${meta.company}`,
      `Overall grade: ${result.overall_grade || 0}/10`,
      `Strengths: ${(result.strengths || []).slice(0, 3).join(", ") || "None"}`,
      `Weaknesses: ${(result.weaknesses || []).slice(0, 3).join(", ") || "None"}`,
    ].join("\n");

    if (navigator.share) {
      await navigator.share({ title: "Interview report", text });
      return;
    }

    await navigator.clipboard.writeText(text);
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">

      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="space-y-3">
          <button
            onClick={() => router.push('/dashboard/interviews')}
            className="flex items-center gap-2 text-sm font-medium text-gray-400 transition-colors hover:text-white"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Dashboard
          </button>
          <div className="flex flex-wrap items-center gap-2 text-xs uppercase tracking-[0.3em] text-gray-500">
            <Sparkles className="h-4 w-4 text-purple-300" />
            Interview report
            <span className="rounded-full border border-white/10 bg-white/[0.03] px-3 py-1 text-[10px] tracking-[0.2em] text-gray-300">
              {meta.label}
            </span>
          </div>
          <h1 className="text-3xl font-bold text-white">Interview Evaluation Report</h1>
          <div className="flex flex-wrap gap-2">
            <span className="rounded-full border border-white/10 bg-white/[0.03] px-3 py-1 text-sm text-gray-300">{meta.company}</span>
            <span className="rounded-full border border-white/10 bg-white/[0.03] px-3 py-1 text-sm text-gray-300">{meta.difficulty}</span>
            <span className="rounded-full border border-white/10 bg-white/[0.03] px-3 py-1 text-sm text-gray-300">
              <Timer className="mr-1 inline h-4 w-4 text-sky-400" />
              {meta.durationMinutes} min
            </span>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <button
            onClick={downloadPdf}
            className="flex items-center gap-2 rounded-xl border border-white/10 bg-[#2a2a35] px-5 py-3 font-medium text-white transition-colors hover:bg-[#3a3a45]"
          >
            <Printer className="w-5 h-5" />
            Download PDF
          </button>
          <button
            onClick={() => void shareReport()}
            className="flex items-center gap-2 rounded-xl border border-purple-500/20 bg-purple-500/10 px-5 py-3 font-medium text-purple-200 transition-colors hover:bg-purple-500/20"
          >
            <Share2 className="w-5 h-5" />
            Share report
          </button>
        </div>
      </div>

      {/* Scores Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
        <ScoreCard title="Overall Grade" score={result.overall_grade} icon={Trophy} color="purple" />
        <ScoreCard title="Technical Depth" score={result.technical_score} icon={Brain} color="blue" />
        <ScoreCard title="Communication" score={result.communication_score} icon={MessageSquare} color="green" />
        <ScoreCard title="Confidence" score={result.confidence_score} icon={Target} color="rose" />
        <ScoreCard title="Problem Solving" score={result.problem_solving_score} icon={Code2} color="yellow" />
      </div>

      {isCoding ? (
        <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-8">
          <h2 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
            <Code2 className="w-5 h-5 text-cyan-400" />
            Coding Evaluation
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
            {codingRubric.map((item) => (
              <div key={item.label} className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                <div className="flex items-center justify-between gap-3">
                  <div className="text-sm font-medium text-gray-300">{item.label}</div>
                  <div className="text-sm font-semibold text-white">{item.score.toFixed(1)}/10</div>
                </div>
                <div className="mt-3 h-2 overflow-hidden rounded-full bg-[#2a2a35]">
                  <div className="h-full rounded-full bg-gradient-to-r from-cyan-500 to-purple-500" style={{ width: `${(item.score / 10) * 100}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : null}

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
                {result.strengths?.length
                  ? result.strengths.map((item: string, idx: number) => (
                      <li key={idx} className="flex items-start gap-3">
                        <div className="w-1.5 h-1.5 rounded-full bg-green-500 mt-2" />
                        <span className="text-gray-300">{item}</span>
                      </li>
                    ))
                  : <EmptyListItem />}
              </ul>
            </div>
            
            <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-8">
              <h2 className="text-lg font-semibold text-white mb-6 flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-rose-400" />
                Weaknesses
              </h2>
              <ul className="space-y-3">
                {result.weaknesses?.length
                  ? result.weaknesses.map((item: string, idx: number) => (
                      <li key={idx} className="flex items-start gap-3">
                        <div className="w-1.5 h-1.5 rounded-full bg-rose-500 mt-2" />
                        <span className="text-gray-300">{item}</span>
                      </li>
                    ))
                  : <EmptyListItem />}
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
              {result.recommended_topics?.length ? result.recommended_topics.map((topic, idx) => (
                <span key={idx} className="px-3 py-1 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-400 text-sm">
                  {topic}
                </span>
              )) : <span className="text-sm text-gray-500">No study topics were suggested.</span>}
            </div>
          </div>
          
          <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-8">
            <h2 className="text-xl font-semibold text-white mb-6 flex items-center gap-2">
              <Lightbulb className="w-5 h-5 text-yellow-400" />
              Actionable Suggestions
            </h2>
            <ul className="space-y-4">
              {result.suggestions?.length ? result.suggestions.map((suggestion: string, idx: number) => (
                <li key={idx} className="flex gap-4 p-4 rounded-xl bg-[#2a2a35]/50 border border-[#2a2a35]">
                  <span className="flex-shrink-0 w-8 h-8 rounded-full bg-purple-500/10 text-purple-400 flex items-center justify-center font-semibold">
                    {idx + 1}
                  </span>
                  <p className="text-gray-300 pt-1">{suggestion}</p>
                </li>
              )) : <li className="text-gray-500">No suggestions were generated.</li>}
            </ul>
          </div>

          <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-8">
            <h2 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-amber-400" />
              Proctoring Events
            </h2>
            {lockViolations.length ? (
              <ul className="space-y-3">
                {lockViolations.map((violation, idx) => (
                  <li key={`${violation.recorded_at || idx}`} className="p-4 rounded-xl bg-[#2a2a35]/50 border border-[#2a2a35]">
                    <p className="text-sm font-medium text-white">{violation.type.replaceAll("_", " ")}</p>
                    {violation.details && <p className="text-sm text-gray-300 mt-1">{violation.details}</p>}
                    {violation.recorded_at && <p className="text-xs text-gray-500 mt-2">{new Date(violation.recorded_at).toLocaleString()}</p>}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-gray-400 text-sm">No proctoring events were recorded.</p>
            )}
          </div>

          <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-8">
            <h2 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-purple-300" />
              Question Breakdown
            </h2>
            <div className="space-y-4">
              {qaPairs.length ? (
                qaPairs.map((pair) => (
                  <div key={`${pair.index}-${pair.question.slice(0, 12)}`} className="rounded-2xl border border-white/10 bg-white/[0.03] p-5">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div className="text-xs uppercase tracking-[0.2em] text-gray-500">Question {pair.index}</div>
                      <span className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-xs text-gray-300">
                        {pair.answer ? "Answered" : "Pending"}
                      </span>
                    </div>
                    <div className="mt-3 whitespace-pre-wrap text-sm leading-7 text-white">{pair.question}</div>
                    <div className="mt-4 text-xs uppercase tracking-[0.2em] text-gray-500">Answer</div>
                    <div className="mt-2 whitespace-pre-wrap text-sm leading-7 text-gray-300">
                      {pair.answer || "No answer captured."}
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-gray-400 text-sm">No question breakdown is available yet.</p>
              )}
            </div>
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

          <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-6">
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Target className="w-5 h-5 text-purple-300" />
              Session Snapshot
            </h2>
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                <div className="text-xs uppercase tracking-[0.2em] text-gray-500">Overall</div>
                <div className="mt-2 text-2xl font-bold text-white">{scoreSummary}%</div>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                <div className="text-xs uppercase tracking-[0.2em] text-gray-500">Questions</div>
                <div className="mt-2 text-2xl font-bold text-white">{qaPairs.length}</div>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                <div className="text-xs uppercase tracking-[0.2em] text-gray-500">Violations</div>
                <div className="mt-2 text-2xl font-bold text-white">{lockViolations.length}</div>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                <div className="text-xs uppercase tracking-[0.2em] text-gray-500">Mode</div>
                <div className="mt-2 text-sm font-semibold text-white">{meta.label}</div>
              </div>
            </div>
          </div>

          {/* Interview Log Section */}
          <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl p-0 flex flex-col h-[600px]">
            <div className="p-6 border-b border-[#2a2a35]">
              <h2 className="text-xl font-semibold text-white">Interview Log</h2>
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
                      {msg.role === 'user' ? 'You' : 'Interviewer'}
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

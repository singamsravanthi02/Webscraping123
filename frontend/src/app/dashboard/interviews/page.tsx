"use client";

import { useState, useEffect, useCallback, useMemo, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import {
  Plus,
  Clock,
  Brain,
  UserRound,
  Code2,
  ChevronRight,
  MessageSquare,
  Mic,
  Workflow,
  Building2,
  Sparkles,
  ShieldCheck,
  Timer,
  Target,
} from "lucide-react";
import api from "@/lib/api";
import { buildInterviewBrief, getInterviewDisplayTitle, parseInterviewBrief } from "@/lib/interview";

type Interview = {
  id: number;
  title: string;
  type: string;
  status: string;
  start_time: string;
  job_description?: string | null;
  resume_text?: string | null;
};

type InterviewPreset = {
  id: string;
  label: string;
  backendType: "hr" | "technical" | "behavioral" | "coding";
  icon: typeof Brain;
  description: string;
  focus: string;
  durationMinutes: number;
  questionTarget: number;
  accent: string;
  notes: string;
  companyHint: string;
};

const interviewPresets: InterviewPreset[] = [
  {
    id: "hr",
    label: "HR Interview",
    backendType: "hr",
    icon: UserRound,
    description: "Culture fit, motivation, communication, and campus-to-career readiness.",
    focus: "Behavioral introduction and team fit",
    durationMinutes: 20,
    questionTarget: 5,
    accent: "from-sky-500/20 to-cyan-500/5",
    notes: "Keep the tone warm and conversational.",
    companyHint: "Any company",
  },
  {
    id: "technical",
    label: "Technical Interview",
    backendType: "technical",
    icon: Brain,
    description: "Core fundamentals, problem solving, trade-offs, and architecture thinking.",
    focus: "Technical depth and practical reasoning",
    durationMinutes: 35,
    questionTarget: 5,
    accent: "from-violet-500/20 to-fuchsia-500/5",
    notes: "Ask one question at a time and wait for the answer.",
    companyHint: "Product or services company",
  },
  {
    id: "behavioral",
    label: "Behavioral Interview",
    backendType: "behavioral",
    icon: MessageSquare,
    description: "STAR stories, conflict handling, ownership, and collaboration examples.",
    focus: "Behavioral depth and reflection",
    durationMinutes: 25,
    questionTarget: 4,
    accent: "from-emerald-500/20 to-green-500/5",
    notes: "Probe for outcomes, impact, and lessons learned.",
    companyHint: "Team interview",
  },
  {
    id: "coding",
    label: "Coding Interview",
    backendType: "coding",
    icon: Code2,
    description: "Live coding, algorithm choice, complexity, edge cases, and test hygiene.",
    focus: "Sandboxed code execution and evaluation",
    durationMinutes: 45,
    questionTarget: 3,
    accent: "from-amber-500/20 to-yellow-500/5",
    notes: "Show the editor, visible tests, and execution console.",
    companyHint: "Engineering loop",
  },
  {
    id: "system_design",
    label: "System Design Interview",
    backendType: "technical",
    icon: Workflow,
    description: "Architecture, scale, bottlenecks, caching, queues, and data flow.",
    focus: "Scalable architecture and trade-offs",
    durationMinutes: 45,
    questionTarget: 4,
    accent: "from-cyan-500/20 to-blue-500/5",
    notes: "Treat it like a design review, not a trivia quiz.",
    companyHint: "Platform or infra team",
  },
  {
    id: "mock_company",
    label: "Mock Company Interview",
    backendType: "technical",
    icon: Building2,
    description: "A full mixed loop with company context, process questions, and technical depth.",
    focus: "Company-style panel simulation",
    durationMinutes: 40,
    questionTarget: 6,
    accent: "from-fuchsia-500/20 to-pink-500/5",
    notes: "Mix technical, behavioral, and communication checkpoints.",
    companyHint: "Target company",
  },
];

const difficultyOptions = ["Easy", "Medium", "Hard"];
const durationOptions = [15, 20, 25, 35, 45, 60];

function CardBadge({ children }: { children: ReactNode }) {
  return <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-gray-300">{children}</span>;
}

export default function InterviewsDashboard() {
  const router = useRouter();
  const [interviews, setInterviews] = useState<Interview[]>([]);
  const [isCreating, setIsCreating] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [selectedPresetId, setSelectedPresetId] = useState("technical");
  const [title, setTitle] = useState("");
  const [company, setCompany] = useState("Google");
  const [role, setRole] = useState("Frontend Engineer");
  const [difficulty, setDifficulty] = useState("Medium");
  const [durationMinutes, setDurationMinutes] = useState("35");
  const [notes, setNotes] = useState("");
  const [resumeText, setResumeText] = useState("");

  const selectedPreset = interviewPresets.find((preset) => preset.id === selectedPresetId) ?? interviewPresets[1];
  const visibleInterviews = useMemo(() => {
    const seen = new Set<string>();
    return interviews.filter((interview) => {
      const displayTitle = getInterviewDisplayTitle(interview.job_description, interview.type, interview.title);
      const key = `${displayTitle.trim().toLowerCase()}|${interview.type}|${interview.status}`;
      if (seen.has(key)) {
        return false;
      }
      seen.add(key);
      return true;
    });
  }, [interviews]);

  const fetchInterviews = useCallback(async () => {
    try {
      const response = await api.get<Interview[]>("/interviews");
      setInterviews(response.data);
    } catch (error) {
      console.error("Failed to fetch interviews:", error);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void fetchInterviews();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [fetchInterviews]);

  const startNewInterview = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      const payload = {
        title: title || `${company} ${selectedPreset.label}`,
        type: selectedPreset.backendType,
        resume_text: resumeText || null,
        job_description: buildInterviewBrief({
          mode: selectedPreset.id,
          label: selectedPreset.label,
          company: company.trim() || selectedPreset.companyHint,
          difficulty,
          durationMinutes: Number(durationMinutes) || selectedPreset.durationMinutes,
          focus: role.trim() ? `${selectedPreset.focus} for ${role.trim()}` : selectedPreset.focus,
          questionTarget: selectedPreset.questionTarget,
          resumeText: resumeText.trim() || undefined,
          notes: [selectedPreset.notes, notes.trim()].filter(Boolean).join(" "),
        }),
      };
      const response = await api.post("/interviews", payload);
      router.push(`/dashboard/interviews/${response.data.id}/live`);
    } catch (error) {
      console.error("Failed to start interview:", error);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="mx-auto max-w-7xl space-y-8 p-8">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-2 text-xs uppercase tracking-[0.3em] text-gray-500">
            <ShieldCheck className="h-4 w-4 text-emerald-400" />
            Enterprise interview platform
            <CardBadge>{visibleInterviews.length} sessions</CardBadge>
          </div>
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-purple-300 via-sky-300 to-emerald-300 bg-clip-text text-transparent">
              AI Interview Platform
            </h1>
            <p className="mt-2 max-w-2xl text-gray-400">
              Pick a round, set the company context, and launch a realistic interview flow with one question at a time.
            </p>
          </div>
        </div>

        <button
          onClick={() => setIsCreating((current) => !current)}
          className="inline-flex items-center gap-2 rounded-full bg-white px-5 py-3 font-medium text-black transition-colors hover:bg-gray-100"
        >
          <Plus className="h-5 w-5" />
          {isCreating ? "Close Builder" : "New Interview"}
        </button>
      </div>

      {isCreating ? (
        <div className="grid gap-6 xl:grid-cols-[1.3fr_0.9fr]">
          <section className="space-y-6 rounded-3xl border border-white/10 bg-[#12121a] p-6 shadow-2xl shadow-black/20">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-semibold text-white">Choose a round</h2>
                <p className="mt-1 text-sm text-gray-400">These presets shape the backend prompt and the interview room.</p>
              </div>
              <CardBadge>{selectedPreset.label}</CardBadge>
            </div>

            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {interviewPresets.map((preset) => {
                const Icon = preset.icon;
                const active = selectedPresetId === preset.id;
                return (
                  <button
                    key={preset.id}
                    type="button"
                    onClick={() => {
                      setSelectedPresetId(preset.id);
                      setDurationMinutes(String(preset.durationMinutes));
                    }}
                    className={`group rounded-2xl border p-4 text-left transition-all ${
                      active
                        ? "border-purple-400 bg-purple-500/10"
                        : "border-white/10 bg-white/[0.03] hover:border-white/20 hover:bg-white/[0.05]"
                    }`}
                  >
                    <div className={`mb-4 inline-flex rounded-2xl bg-gradient-to-br ${preset.accent} p-3`}>
                      <Icon className={`h-5 w-5 ${active ? "text-white" : "text-gray-200"}`} />
                    </div>
                    <div className="space-y-2">
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <h3 className="text-lg font-semibold text-white">{preset.label}</h3>
                          <p className="mt-1 text-sm text-gray-400">{preset.description}</p>
                        </div>
                        <ChevronRight className={`h-4 w-4 shrink-0 ${active ? "text-purple-300" : "text-gray-600"}`} />
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <CardBadge>{preset.durationMinutes} min</CardBadge>
                        <CardBadge>{preset.questionTarget} questions</CardBadge>
                        <CardBadge>{preset.companyHint}</CardBadge>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </section>

          <aside className="space-y-6 rounded-3xl border border-white/10 bg-[#101017] p-6">
            <div className="space-y-2">
              <h2 className="text-2xl font-semibold text-white">Configure the run</h2>
              <p className="text-sm text-gray-400">The setup gets stored with the interview so the live screen can read it back.</p>
            </div>

            <form onSubmit={startNewInterview} className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm text-gray-400">Interview title</label>
                <input
                  value={title}
                  onChange={(event) => setTitle(event.target.value)}
                  placeholder={`e.g. ${company} ${selectedPreset.label}`}
                  className="w-full rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-white outline-none transition-colors placeholder:text-gray-600 focus:border-purple-400"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-sm text-gray-400">Company</label>
                  <input
                    value={company}
                    onChange={(event) => setCompany(event.target.value)}
                    className="w-full rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-white outline-none transition-colors focus:border-purple-400"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm text-gray-400">Role</label>
                  <input
                    value={role}
                    onChange={(event) => setRole(event.target.value)}
                    className="w-full rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-white outline-none transition-colors focus:border-purple-400"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-sm text-gray-400">Difficulty</label>
                  <select
                    value={difficulty}
                    onChange={(event) => setDifficulty(event.target.value)}
                    className="w-full rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-white outline-none transition-colors focus:border-purple-400"
                  >
                    {difficultyOptions.map((option) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="space-y-2">
                  <label className="text-sm text-gray-400">Duration</label>
                  <select
                    value={durationMinutes}
                    onChange={(event) => setDurationMinutes(event.target.value)}
                    className="w-full rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-white outline-none transition-colors focus:border-purple-400"
                  >
                    {durationOptions.map((option) => (
                      <option key={option} value={option}>
                        {option} minutes
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-sm text-gray-400">Resume context</label>
                <textarea
                  value={resumeText}
                  onChange={(event) => setResumeText(event.target.value)}
                  placeholder="Paste the candidate resume or a short profile summary."
                  className="min-h-28 w-full rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-white outline-none transition-colors placeholder:text-gray-600 focus:border-purple-400"
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm text-gray-400">Additional notes</label>
                <textarea
                  value={notes}
                  onChange={(event) => setNotes(event.target.value)}
                  placeholder="Add special instructions, company hints, or role-specific context."
                  className="min-h-24 w-full rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-white outline-none transition-colors placeholder:text-gray-600 focus:border-purple-400"
                />
              </div>

              <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                <div className="flex items-center gap-2 text-sm text-gray-300">
                  <Timer className="h-4 w-4 text-sky-400" />
                  {selectedPreset.durationMinutes}-minute default run, {selectedPreset.questionTarget} question target
                </div>
                <div className="mt-2 text-sm text-gray-500">{selectedPreset.focus}</div>
              </div>

              <button
                type="submit"
                disabled={isSubmitting}
                className="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-purple-600 px-5 py-3 font-semibold text-white transition-colors hover:bg-purple-500 disabled:cursor-not-allowed disabled:bg-purple-600/60"
              >
                {isSubmitting ? "Starting..." : "Start Interview"}
              </button>
            </form>
          </aside>
        </div>
      ) : null}

      <section className="space-y-4">
        <div className="flex items-center gap-2 text-sm text-gray-400">
          <Clock className="h-4 w-4" />
          Recent sessions
        </div>
        <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
          {visibleInterviews.map((interview) => {
            const Icon = interviewPresets.find((preset) => preset.backendType === interview.type)?.icon ?? Brain;
            const displayTitle = getInterviewDisplayTitle(interview.job_description, interview.type, interview.title);
            const meta = parseInterviewBrief(interview.job_description, interview.type, interview.title);

            return (
              <div
                key={interview.id}
                className="group rounded-3xl border border-white/10 bg-[#12121a] p-6 transition-all hover:border-purple-500/40 hover:bg-white/[0.03]"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-3">
                    <Icon className="h-6 w-6 text-purple-300" />
                  </div>
                  <span
                    className={`rounded-full border px-3 py-1 text-xs font-medium ${
                      interview.status === "completed"
                        ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-300"
                        : interview.status === "in_progress"
                          ? "border-sky-500/20 bg-sky-500/10 text-sky-300"
                          : "border-white/10 bg-white/[0.03] text-gray-300"
                    }`}
                  >
                    {interview.status.replaceAll("_", " ").toUpperCase()}
                  </span>
                </div>

                <div className="mt-4 space-y-2">
                  <h3 className="text-xl font-semibold text-white">{displayTitle}</h3>
                  <p className="text-sm text-gray-400">{interview.title}</p>
                </div>

                <div className="mt-4 flex flex-wrap gap-2">
                  <CardBadge>{meta.company}</CardBadge>
                  <CardBadge>{meta.difficulty}</CardBadge>
                  <CardBadge>{meta.durationMinutes} min</CardBadge>
                </div>

                <div className="mt-4 flex items-center gap-2 text-sm text-gray-500">
                  <Target className="h-4 w-4" />
                  {meta.focus}
                </div>

                <div className="mt-6 flex items-center justify-between">
                  <div className="text-xs uppercase tracking-[0.2em] text-gray-500">
                    {new Date(interview.start_time).toLocaleDateString()}
                  </div>
                  <button
                    onClick={() =>
                      router.push(
                        interview.status === "completed"
                          ? `/dashboard/interviews/${interview.id}/result`
                          : `/dashboard/interviews/${interview.id}/live`
                      )
                    }
                    className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-4 py-2 text-sm text-white transition-colors hover:border-purple-400/40 hover:bg-purple-500/10"
                  >
                    {interview.status === "completed" ? "View Report" : "Resume Interview"}
                    <ChevronRight className="h-4 w-4" />
                  </button>
                </div>
              </div>
            );
          })}

          {visibleInterviews.length === 0 ? (
            <div className="col-span-full rounded-3xl border border-dashed border-white/15 bg-white/[0.02] p-14 text-center">
              <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-purple-500/10">
                <Mic className="h-8 w-8 text-purple-300" />
              </div>
              <h3 className="text-xl font-semibold text-white">No interviews yet</h3>
              <p className="mx-auto mt-2 max-w-lg text-gray-400">
                Create a session, run the pre-interview checks, and launch a realistic interview flow.
              </p>
              <button
                onClick={() => setIsCreating(true)}
                className="mt-8 inline-flex items-center gap-2 rounded-full bg-white px-5 py-3 font-medium text-black transition-colors hover:bg-gray-100"
              >
                <Sparkles className="h-4 w-4" />
                Create your first interview
              </button>
            </div>
          ) : null}
        </div>
      </section>
    </div>
  );
}

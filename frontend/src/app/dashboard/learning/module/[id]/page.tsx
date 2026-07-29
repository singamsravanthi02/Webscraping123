"use client";

import { useCallback, useEffect, useMemo, useState, type CSSProperties } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  BadgeCheck,
  BookOpen,
  ChevronRight,
  ChevronLeft,
  CheckCircle2,
  CircleDot,
  Loader2,
  MessageSquare,
  Send,
  Sparkles,
  TimerReset,
} from "lucide-react";
import api from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { FEATURE_FLAGS } from "@/lib/feature-flags";
import EnterpriseLearningWorkspace from "../../enterprise-workspace";

type RoadmapModule = {
  id: number;
  title: string;
  order: number;
  summary?: string | null;
  estimated_minutes: number;
  status: string;
  completed?: boolean;
  completed_at?: string | null;
  time_spent?: number;
  progress_percent?: number;
  source_chips?: string[];
};

type Roadmap = {
  id: number;
  title: string;
  subject?: string | null;
  difficulty?: string | null;
  estimated_hours: number;
  description?: string | null;
  source_chips?: string[];
  modules: RoadmapModule[];
  completed_modules: number;
  total_modules: number;
  completion_percent: number;
};

type QuizQuestion = {
  question: string;
  options: string[];
  answer_index: number;
  explanation: string;
};

type Flashcard = {
  front: string;
  back: string;
};

type ModuleDetail = {
  id: number;
  roadmap_id: number;
  roadmap_title: string;
  roadmap_subject?: string | null;
  roadmap_difficulty?: string | null;
  title: string;
  order: number;
  summary?: string | null;
  estimated_minutes: number;
  status: string;
  completed?: boolean;
  completed_at?: string | null;
  time_spent?: number;
  progress_percent?: number;
  theory?: string | null;
  institutional_notes?: string | null;
  important_questions?: string[];
  previous_year_questions?: string[];
  examples?: string[];
  diagrams?: string[];
  practice_quiz?: QuizQuestion[];
  flashcards?: Flashcard[];
  revision_notes?: string | null;
  resources?: { label?: string; url?: string }[];
  source_chips?: string[];
  retrieved_chunks?: {
    title?: string;
    score?: number;
    embedding_distance?: number;
    source_type?: string;
    chunk_index?: number;
    chunk_number?: number;
    page_number?: number | null;
    document_id?: number;
    metadata?: {
      title?: string;
      source?: string;
      subject?: string | null;
      department?: string | null;
      semester?: string | null;
      unit?: string | null;
      module?: string | null;
      url?: string | null;
      keywords?: string[];
    };
  }[];
};

type AssistantMessage = {
  role: "user" | "ai";
  content: string;
  citations?: {
    id: number;
    title: string;
    type: string;
    document?: string;
    source?: string;
    page?: number | null;
    chunk_number?: number | null;
    chunk_index?: number | null;
    similarity_score?: number;
    embedding_distance?: number;
    metadata?: {
      document_id?: number;
      subject?: string | null;
      department?: string | null;
      semester?: string | null;
      unit?: string | null;
      module?: string | null;
      url?: string | null;
      keywords?: string[];
    };
  }[];
};

type QuizState = {
  index: number;
  selected: number | null;
  answered: boolean;
  correct: boolean | null;
  score: number;
  finished: boolean;
  startedAt: number;
  weakTopics: string[];
};

const quickActions = [
  "Explain again",
  "Generate example",
  "Simplify this",
  "Translate to simple English",
  "Interview me on this module",
  "Generate MCQs",
  "Generate flashcards",
  "Summarize this module",
];

export default function LearningModulePage() {
  if (!FEATURE_FLAGS.learningRoadmap) {
    return <EnterpriseLearningWorkspace />;
  }

  return <LearningModulePageLegacy />;
}

function LearningModulePageLegacy() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const moduleId = Number(params?.id);

  const [moduleData, setModuleData] = useState<ModuleDetail | null>(null);
  const [roadmap, setRoadmap] = useState<Roadmap | null>(null);
  const [loading, setLoading] = useState(true);
  const [sectionLoading, setSectionLoading] = useState<"summary" | "quiz" | "flashcards" | null>(null);
  const [summaryText, setSummaryText] = useState<string>("");
  const [quizQuestions, setQuizQuestions] = useState<QuizQuestion[]>([]);
  const [flashcards, setFlashcards] = useState<Flashcard[]>([]);
  const [flashcardFlipped, setFlashcardFlipped] = useState<Record<number, boolean>>({});
  const [assistantMessages, setAssistantMessages] = useState<AssistantMessage[]>([]);
  const [assistantInput, setAssistantInput] = useState("");
  const [assistantBusy, setAssistantBusy] = useState(false);
  const [assistantOpen, setAssistantOpen] = useState(true);
  const [now, setNow] = useState(0);
  const [quizState, setQuizState] = useState<QuizState>({
    index: 0,
    selected: null,
    answered: false,
    correct: null,
    score: 0,
    finished: false,
    startedAt: 0,
    weakTopics: [],
  });

  const fetchModule = useCallback(async () => {
    if (!moduleId || Number.isNaN(moduleId)) {
      return;
    }
    setLoading(true);
    try {
      const moduleRes = await api.get<ModuleDetail>(`/learning/module/${moduleId}`);
      setModuleData(moduleRes.data);
      setSummaryText(moduleRes.data.theory || moduleRes.data.summary || "");
      setQuizQuestions(moduleRes.data.practice_quiz || []);
      setFlashcards(moduleRes.data.flashcards || []);
      setFlashcardFlipped({});
      setQuizState({
        index: 0,
        selected: null,
        answered: false,
        correct: null,
        score: 0,
        finished: false,
        startedAt: Date.now(),
        weakTopics: [],
      });
      setNow(Date.now());
      setAssistantMessages([
        {
          role: "ai",
          content: `Ask lesson questions about ${moduleRes.data.title}. I will stay on this module, cite the retrieved chunks, and avoid answering outside the lesson context.`,
        },
      ]);
      setAssistantOpen(true);
      const roadmapRes = await api.get<Roadmap>(`/learning/roadmap/${moduleRes.data.roadmap_id}`);
      setRoadmap(roadmapRes.data);
    } catch (error) {
      console.error(error);
      toast.error("Failed to load module");
    } finally {
      setLoading(false);
    }
  }, [moduleId]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void fetchModule();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [fetchModule]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setNow(Date.now());
    }, 30000);
    return () => window.clearInterval(timer);
  }, []);

  const currentQuestion = quizQuestions[quizState.index];
  const totalQuestions = quizQuestions.length;
  const accuracy = totalQuestions ? Math.round((quizState.score / totalQuestions) * 100) : 0;
  const timeSpentMinutes = quizState.startedAt ? Math.max(0, Math.round((now - quizState.startedAt) / 60000)) : 0;
  const currentModule = moduleData;

  const loadSection = async (section: "summary" | "quiz" | "flashcards") => {
    setSectionLoading(section);
    try {
      const res = await api.get(`/learning/module/${moduleId}/${section}`);
      const retrievedChunks = res.data.retrieved_chunks || [];
      const sourceChips = res.data.source_chips || [];
      setModuleData((current) =>
        current
          ? {
              ...current,
              retrieved_chunks: retrievedChunks.length ? retrievedChunks : current.retrieved_chunks,
              source_chips: sourceChips.length ? sourceChips : current.source_chips,
            }
          : current
      );
      if (section === "summary") {
        setSummaryText(res.data.content || "");
      } else if (section === "quiz") {
        setQuizQuestions(res.data.questions || []);
        setQuizState((current) => ({
          ...current,
          index: 0,
          selected: null,
          answered: false,
          correct: null,
          score: 0,
          finished: false,
          startedAt: Date.now(),
          weakTopics: [],
        }));
        setNow(Date.now());
      } else if (section === "flashcards") {
        setFlashcards(res.data.flashcards || []);
        setFlashcardFlipped({});
      }
    } catch (error) {
      console.error(error);
      toast.error(`Failed to load ${section}`);
    } finally {
      setSectionLoading(null);
    }
  };

  const completeModule = async () => {
    try {
      await api.post(`/learning/module/${moduleId}/complete`, { time_spent: timeSpentMinutes });
      toast.success("Module marked complete");
      await fetchModule();
    } catch (error) {
      console.error(error);
      toast.error("Failed to save progress");
    }
  };

  const sendAssistantMessage = async (prompt?: string) => {
    const content = (prompt ?? assistantInput).trim();
    if (!content || assistantBusy) {
      return;
    }
    setAssistantBusy(true);
    setAssistantInput("");
    setAssistantMessages((current) => [...current, { role: "user", content }]);
    try {
      const res = await api.post(`/learning/module/${moduleId}/chat`, { content });
      let answer = res.data?.content || "";
      const citations = res.data?.citations || [];
      try {
        const parsed = JSON.parse(answer);
        answer = parsed.concise_explanation || answer;
      } catch {
        // keep raw answer
      }
      setAssistantMessages((current) => [...current, { role: "ai", content: answer, citations }]);
    } catch (error) {
      console.error(error);
      toast.error("Assistant request failed");
    } finally {
      setAssistantBusy(false);
    }
  };

  const answerQuestion = (optionIndex: number) => {
    if (!currentQuestion || quizState.answered || quizState.finished) {
      return;
    }
    const isCorrect = optionIndex === currentQuestion.answer_index;
    setQuizState((current) => ({
      ...current,
      selected: optionIndex,
      answered: true,
      correct: isCorrect,
      score: isCorrect ? current.score + 1 : current.score,
      weakTopics: isCorrect ? current.weakTopics : [...current.weakTopics, currentQuestion.question.slice(0, 80)],
    }));
    if (isCorrect) {
      window.setTimeout(() => {
        nextQuestion();
      }, 1000);
    }
  };

  const nextQuestion = () => {
    if (!currentQuestion) {
      return;
    }
    const nextIndex = quizState.index + 1;
    if (nextIndex >= totalQuestions) {
      setQuizState((current) => ({
        ...current,
        finished: true,
      }));
      return;
    }
    setQuizState((current) => ({
      ...current,
      index: nextIndex,
      selected: null,
      answered: false,
      correct: null,
    }));
  };

  const quizSummary = useMemo(() => {
    if (!quizState.finished || !totalQuestions) {
      return null;
    }
    return {
      score: quizState.score,
      accuracy,
      weakTopics: Array.from(new Set(quizState.weakTopics)).slice(0, 5),
      timeSpentMinutes,
    };
  }, [accuracy, quizState.finished, quizState.score, quizState.weakTopics, timeSpentMinutes, totalQuestions]);

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="flex items-center gap-3 text-muted-foreground">
          <Loader2 className="h-5 w-5 animate-spin" />
          Loading learning module...
        </div>
      </div>
    );
  }

  if (!currentModule || !roadmap) {
    return (
      <div className="rounded-2xl border border-dashed border-border p-10 text-center text-muted-foreground">
        Module not found.
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-8">
      <div className="flex flex-col gap-4 border-b border-border/60 pb-5 lg:flex-row lg:items-end lg:justify-between">
        <div className="space-y-3">
          <Link href="/dashboard/learning" className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground">
            <ArrowLeft className="h-4 w-4" />
            Back to Learning Hub
          </Link>
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="secondary">{roadmap.subject || roadmap.title}</Badge>
              <Badge variant="outline">{roadmap.difficulty || "Intermediate"}</Badge>
              <Badge variant="outline">{roadmap.completion_percent}% complete</Badge>
            </div>
            <h1 className="text-3xl font-bold tracking-tight">{currentModule.title}</h1>
            <p className="max-w-3xl text-sm text-muted-foreground">
              {roadmap.description || "Structured learning with cached AI content, institutional context, and persistent progress."}
            </p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={() => void loadSection("summary")} disabled={sectionLoading === "summary"}>
            {sectionLoading === "summary" ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <BookOpen className="mr-2 h-4 w-4" />}
            Summary
          </Button>
          <Button variant="outline" onClick={() => void loadSection("quiz")} disabled={sectionLoading === "quiz"}>
            {sectionLoading === "quiz" ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <CheckCircle2 className="mr-2 h-4 w-4" />}
            Quiz
          </Button>
          <Button variant="outline" onClick={() => void loadSection("flashcards")} disabled={sectionLoading === "flashcards"}>
            {sectionLoading === "flashcards" ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Sparkles className="mr-2 h-4 w-4" />}
            Flashcards
          </Button>
          <Button onClick={() => void completeModule()}>
            <BadgeCheck className="mr-2 h-4 w-4" />
            Mark Complete
          </Button>
        </div>
      </div>

      <div
        className="grid grid-cols-1 gap-6 xl:[grid-template-columns:280px_minmax(0,1fr)_var(--assistant-width)]"
        style={{ "--assistant-width": assistantOpen ? "360px" : "56px" } as CSSProperties}
      >
        <Card className="border-border/60 shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Roadmap</CardTitle>
            <CardDescription>{roadmap.modules.length} modules</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="rounded-xl border border-border/60 bg-secondary/20 p-3">
              <div className="flex items-center justify-between text-sm">
                <span className="font-medium">{roadmap.completed_modules} done</span>
                <span className="text-muted-foreground">{roadmap.completion_percent}%</span>
              </div>
              <div className="mt-2 h-2 rounded-full bg-muted">
                <div className="h-2 rounded-full bg-primary" style={{ width: `${roadmap.completion_percent}%` }} />
              </div>
            </div>
            <div className="space-y-2">
              {roadmap.modules.map((module) => (
                <button
                  key={module.id}
                  onClick={() => router.push(`/dashboard/learning/module/${module.id}`)}
                  className={`w-full rounded-xl border px-3 py-3 text-left transition-colors ${
                    module.id === currentModule.id
                      ? "border-primary bg-primary/5"
                      : "border-border/60 bg-background hover:border-primary/30 hover:bg-secondary/30"
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="min-w-0">
                      <div className="truncate text-sm font-medium">{module.order}. {module.title}</div>
                      <div className="mt-1 text-xs text-muted-foreground">{module.estimated_minutes} min</div>
                    </div>
                    <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
                  </div>
                  {module.completed ? <div className="mt-2 text-xs text-emerald-600">Completed</div> : null}
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card className="border-border/60 shadow-sm">
            <CardHeader className="pb-3">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="secondary">{currentModule.progress_percent ?? 0}% progress</Badge>
                <Badge variant="outline">{currentModule.estimated_minutes} min</Badge>
                <Badge variant="outline">{currentModule.source_chips?.[0] || "AI Generated"}</Badge>
              </div>
              <CardTitle className="text-xl">Module Content</CardTitle>
              <CardDescription>Independent sections load from the roadmap cache and RAG context.</CardDescription>
            </CardHeader>
            <CardContent>
              <Tabs defaultValue="overview" className="space-y-4">
                <TabsList className="flex flex-wrap h-auto gap-2 bg-transparent p-0">
                  <TabsTrigger value="overview">Overview</TabsTrigger>
                  <TabsTrigger value="theory">Theory</TabsTrigger>
                  <TabsTrigger value="institution">Institution Notes</TabsTrigger>
                  <TabsTrigger value="examples">Examples</TabsTrigger>
                  <TabsTrigger value="quiz">Practice Quiz</TabsTrigger>
                  <TabsTrigger value="flashcards">Flashcards</TabsTrigger>
                  <TabsTrigger value="revision">Revision Notes</TabsTrigger>
                  <TabsTrigger value="resources">Resources</TabsTrigger>
                  <TabsTrigger value="sources">Sources</TabsTrigger>
                </TabsList>

                <TabsContent value="overview" className="space-y-4">
                  <div className="rounded-2xl border border-border/60 bg-secondary/20 p-5">
                    <p className="text-sm leading-7 text-foreground/90 whitespace-pre-wrap">
                      {currentModule.summary || summaryText || "Summary is cached in the module and will load here when available."}
                    </p>
                  </div>
                  <div className="grid gap-3 md:grid-cols-2">
                    <div className="rounded-2xl border border-border/60 p-4">
                      <div className="text-xs uppercase tracking-wide text-muted-foreground">Estimated Time Remaining</div>
                      <div className="mt-2 text-2xl font-semibold">{roadmap.modules.reduce((sum, item) => sum + (item.completed ? 0 : item.estimated_minutes), 0)} min</div>
                    </div>
                    <div className="rounded-2xl border border-border/60 p-4">
                      <div className="text-xs uppercase tracking-wide text-muted-foreground">Completion</div>
                      <div className="mt-2 text-2xl font-semibold">{roadmap.completion_percent}%</div>
                    </div>
                  </div>
                </TabsContent>

                <TabsContent value="theory" className="space-y-4">
                  <div className="rounded-2xl border border-border/60 bg-background p-5">
                    <p className="whitespace-pre-wrap leading-7 text-sm text-foreground/90">
                      {currentModule.theory || "Theory will be generated from retrieved institutional context and cached here."}
                    </p>
                  </div>
                </TabsContent>

                <TabsContent value="institution" className="space-y-4">
                  <div className="rounded-2xl border border-border/60 bg-background p-5">
                    <p className="whitespace-pre-wrap leading-7 text-sm text-foreground/90">
                      {currentModule.institutional_notes || "No institutional notes are cached yet."}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {(currentModule.source_chips || roadmap.source_chips || []).map((chip) => (
                      <Badge key={chip} variant="secondary">{chip}</Badge>
                    ))}
                  </div>
                </TabsContent>

                <TabsContent value="examples" className="space-y-4">
                  <div className="grid gap-3 md:grid-cols-2">
                    {(currentModule.examples || []).length ? currentModule.examples!.map((example) => (
                      <div key={example} className="rounded-2xl border border-border/60 p-4 text-sm leading-6">
                        {example}
                      </div>
                    )) : (
                      <div className="rounded-2xl border border-dashed border-border/60 p-6 text-sm text-muted-foreground">
                        Examples will appear after module content is generated.
                      </div>
                    )}
                  </div>
                </TabsContent>

                <TabsContent value="quiz" className="space-y-4">
                  {!quizQuestions.length ? (
                    <div className="rounded-2xl border border-dashed border-border/60 p-6 text-sm text-muted-foreground">
                      Quiz is not cached yet. Load it from the action button above.
                    </div>
                  ) : quizState.finished && quizSummary ? (
                    <div className="space-y-4">
                      <div className="rounded-2xl border border-border/60 bg-secondary/20 p-5">
                        <div className="flex items-center gap-2 text-sm uppercase tracking-wide text-muted-foreground">
                          <TimerReset className="h-4 w-4" />
                          Quiz Complete
                        </div>
                        <div className="mt-4 grid gap-4 md:grid-cols-3">
                          <div className="rounded-xl border border-border/60 p-4">
                            <div className="text-xs uppercase tracking-wide text-muted-foreground">Score</div>
                            <div className="mt-2 text-2xl font-semibold">{quizSummary.score}/{totalQuestions}</div>
                          </div>
                          <div className="rounded-xl border border-border/60 p-4">
                            <div className="text-xs uppercase tracking-wide text-muted-foreground">Accuracy</div>
                            <div className="mt-2 text-2xl font-semibold">{quizSummary.accuracy}%</div>
                          </div>
                          <div className="rounded-xl border border-border/60 p-4">
                            <div className="text-xs uppercase tracking-wide text-muted-foreground">Time</div>
                            <div className="mt-2 text-2xl font-semibold">{quizSummary.timeSpentMinutes} min</div>
                          </div>
                        </div>
                      </div>
                      <div className="rounded-2xl border border-border/60 p-5">
                        <div className="text-sm font-medium">Weak topics</div>
                        <div className="mt-3 flex flex-wrap gap-2">
                          {quizSummary.weakTopics.length ? quizSummary.weakTopics.map((topic) => (
                            <Badge key={topic} variant="secondary">{topic}</Badge>
                          )) : <span className="text-sm text-muted-foreground">No weak topics recorded.</span>}
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      <div className="rounded-2xl border border-border/60 p-5">
                        <div className="flex items-center justify-between text-sm text-muted-foreground">
                          <span>Question {quizState.index + 1} of {totalQuestions}</span>
                          <span>Score {quizState.score}</span>
                        </div>
                        <h3 className="mt-3 text-lg font-semibold">{currentQuestion?.question}</h3>
                        <div className="mt-4 grid gap-2">
                          {currentQuestion?.options.map((option, optionIndex) => {
                            const isSelected = quizState.selected === optionIndex;
                            const isCorrect = currentQuestion.answer_index === optionIndex;
                            const showCorrect = quizState.answered && isCorrect;
                            const showWrong = quizState.answered && isSelected && !isCorrect;
                            return (
                              <button
                                key={option}
                                type="button"
                                onClick={() => answerQuestion(optionIndex)}
                                className={`rounded-xl border px-4 py-3 text-left text-sm transition-colors ${
                                  showCorrect
                                    ? "border-emerald-500 bg-emerald-50 text-emerald-800"
                                    : showWrong
                                      ? "border-rose-500 bg-rose-50 text-rose-800"
                                      : isSelected
                                        ? "border-primary bg-primary/5"
                                        : "border-border/60 bg-background hover:border-primary/30 hover:bg-secondary/30"
                                }`}
                              >
                                {option}
                              </button>
                            );
                          })}
                        </div>

                        {quizState.answered ? (
                          <div className="mt-4 rounded-xl border border-border/60 bg-secondary/20 p-4">
                            <div className="flex items-center gap-2 text-sm font-medium">
                              {quizState.correct ? <CheckCircle2 className="h-4 w-4 text-emerald-600" /> : <CircleDot className="h-4 w-4 text-rose-600" />}
                              {quizState.correct ? "Correct" : "Incorrect"}
                            </div>
                            <p className="mt-2 text-sm text-muted-foreground">{currentQuestion?.explanation}</p>
                            {!quizState.correct ? (
                              <p className="mt-2 text-sm">
                                Correct answer: <span className="font-medium">{currentQuestion?.options[currentQuestion.answer_index]}</span>
                              </p>
                            ) : null}
                          </div>
                        ) : null}

                        <div className="mt-4 flex items-center justify-end gap-2">
                          {quizState.answered && !quizState.correct ? (
                            <Button onClick={nextQuestion}>Next</Button>
                          ) : null}
                        </div>
                      </div>
                    </div>
                  )}
                </TabsContent>

                <TabsContent value="flashcards" className="space-y-4">
                  {!flashcards.length ? (
                    <div className="rounded-2xl border border-dashed border-border/60 p-6 text-sm text-muted-foreground">
                      Flashcards are not cached yet. Load them from the action button above.
                    </div>
                  ) : (
                    <div className="grid gap-4 md:grid-cols-2">
                      {flashcards.map((card, index) => {
                        const flipped = !!flashcardFlipped[index];
                        return (
                          <button
                            key={`${card.front}-${index}`}
                            type="button"
                            onClick={() => setFlashcardFlipped((current) => ({ ...current, [index]: !current[index] }))}
                            className="group relative h-44 rounded-2xl border border-border/60 bg-background text-left [perspective:1200px]"
                          >
                            <div
                              className="absolute inset-0 transition-transform duration-500 [transform-style:preserve-3d]"
                              style={{ transform: flipped ? "rotateY(180deg)" : "rotateY(0deg)" }}
                            >
                              <div className="absolute inset-0 flex items-center justify-center rounded-2xl bg-secondary/30 p-5 [backface-visibility:hidden]">
                                <div className="text-center">
                                  <div className="mb-2 text-xs uppercase tracking-wide text-muted-foreground">Front</div>
                                  <div className="text-base font-medium">{card.front}</div>
                                </div>
                              </div>
                              <div className="absolute inset-0 flex items-center justify-center rounded-2xl bg-primary/5 p-5 [backface-visibility:hidden]" style={{ transform: "rotateY(180deg)" }}>
                                <div className="text-center">
                                  <div className="mb-2 text-xs uppercase tracking-wide text-muted-foreground">Back</div>
                                  <div className="text-sm leading-6 text-foreground">{card.back}</div>
                                </div>
                              </div>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  )}
                </TabsContent>

                <TabsContent value="revision" className="space-y-4">
                  <div className="rounded-2xl border border-border/60 bg-background p-5">
                    <p className="whitespace-pre-wrap leading-7 text-sm">{currentModule.revision_notes || "Revision notes are cached here after generation."}</p>
                  </div>
                </TabsContent>

                <TabsContent value="resources" className="space-y-4">
                  <div className="space-y-3">
                    {(currentModule.resources || []).length ? currentModule.resources!.map((resource, index) => (
                      <div key={`${resource.label || "resource"}-${index}`} className="rounded-2xl border border-border/60 p-4">
                        <div className="font-medium">{resource.label || "Resource"}</div>
                        {resource.url ? <div className="mt-1 text-sm text-muted-foreground">{resource.url}</div> : null}
                      </div>
                    )) : (
                      <div className="rounded-2xl border border-dashed border-border/60 p-6 text-sm text-muted-foreground">
                        No extra resources cached yet.
                      </div>
                    )}
                    {(currentModule.retrieved_chunks || []).length ? (
                      <div className="rounded-2xl border border-border/60 p-4">
                        <div className="mb-3 text-sm font-medium">Retrieved chunks</div>
                        <div className="space-y-2">
                          {currentModule.retrieved_chunks!.map((chunk, index) => (
                            <div key={`${chunk.title || "chunk"}-${index}`} className="rounded-xl bg-secondary/20 px-3 py-2 text-sm">
                              <div className="flex items-center justify-between gap-3">
                                <span className="truncate">{chunk.title || "Chunk"}</span>
                                <span className="text-muted-foreground">Score {(chunk.score || 0).toFixed(3)}</span>
                              </div>
                              <div className="mt-1 text-xs text-muted-foreground">
                                {chunk.source_type || "unknown"} | Chunk {chunk.chunk_index ?? index + 1}
                                {chunk.embedding_distance != null ? ` | Distance ${chunk.embedding_distance.toFixed(3)}` : ""}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : null}
                  </div>
                </TabsContent>

                <TabsContent value="sources" className="space-y-4">
                  <div className="space-y-3">
                    {(currentModule.retrieved_chunks || []).length ? currentModule.retrieved_chunks!.map((chunk, index) => (
                      <div key={`${chunk.document_id ?? "source"}-${chunk.chunk_index ?? index}`} className="rounded-2xl border border-border/60 p-4">
                        <div className="flex flex-wrap items-center gap-2">
                          <div className="font-medium">{chunk.metadata?.title || chunk.title || "Retrieved source"}</div>
                          <Badge variant="secondary">Score {(chunk.score || 0).toFixed(3)}</Badge>
                        </div>
                        <div className="mt-2 text-sm text-muted-foreground">
                          {chunk.metadata?.source || chunk.source_type || "unknown"}{" "}
                          | Chunk {(chunk.chunk_number ?? (chunk.chunk_index != null ? chunk.chunk_index + 1 : index + 1))}{" "}
                          | Page {chunk.page_number ?? "-"}
                        </div>
                        <div className="mt-2 text-xs text-muted-foreground">
                          {chunk.metadata?.subject ? `Subject: ${chunk.metadata.subject}` : "Subject: -"}
                          {chunk.metadata?.unit ? ` | Unit: ${chunk.metadata.unit}` : ""}
                          {chunk.metadata?.semester ? ` | Semester: ${chunk.metadata.semester}` : ""}
                          {chunk.metadata?.department ? ` | Department: ${chunk.metadata.department}` : ""}
                        </div>
                      </div>
                    )) : (
                      <div className="rounded-2xl border border-dashed border-border/60 p-6 text-sm text-muted-foreground">
                        Retrieved sources will appear here after the module pulls from RAG.
                      </div>
                    )}
                  </div>
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        </div>

        <Card className="border-border/60 shadow-sm">
          <CardHeader className={assistantOpen ? "pb-3" : "p-2"}>
            {assistantOpen ? (
              <>
                <div className="flex items-center gap-2 text-sm uppercase tracking-wide text-muted-foreground">
                  <MessageSquare className="h-4 w-4" />
                  AI Assistant
                </div>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <CardTitle className="text-lg">Right Sidebar</CardTitle>
                    <CardDescription>Contextual help for the current module only.</CardDescription>
                  </div>
                  <Button variant="ghost" size="icon" onClick={() => setAssistantOpen(false)} aria-label="Collapse assistant">
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </>
            ) : (
              <div className="flex items-center justify-center">
                <Button variant="ghost" size="icon" onClick={() => setAssistantOpen(true)} aria-label="Expand assistant">
                  <ChevronLeft className="h-4 w-4" />
                </Button>
              </div>
            )}
          </CardHeader>
          {assistantOpen ? (
            <CardContent className="space-y-4">
              <div className="flex flex-wrap gap-2">
                {(currentModule.source_chips || roadmap.source_chips || []).slice(0, 4).map((chip) => (
                  <Badge key={chip} variant="secondary">{chip}</Badge>
                ))}
              </div>

              <div className="space-y-3 rounded-2xl border border-border/60 bg-secondary/10 p-4">
                {assistantMessages.map((message, index) => (
                  <div key={`${message.role}-${index}`} className={`rounded-2xl px-3 py-2 text-sm ${message.role === "user" ? "ml-6 bg-primary/10" : "mr-6 bg-background border border-border/60"}`}>
                    <div className="mb-1 text-[11px] uppercase tracking-wide text-muted-foreground">{message.role === "user" ? "You" : "AI"}</div>
                    <div className="whitespace-pre-wrap leading-6">{message.content}</div>
                    {message.citations?.length ? (
                      <div className="mt-3 space-y-2">
                        <div className="text-[11px] uppercase tracking-wide text-muted-foreground">Retrieved chunks</div>
                        <div className="grid gap-2">
                          {message.citations.map((cite) => (
                            <div key={`${cite.id}-${cite.title}`} className="rounded-xl border border-border/60 bg-background px-3 py-2 text-xs">
                              <div className="flex flex-wrap items-center gap-2">
                                <Badge variant="outline">{cite.id}</Badge>
                                <span className="font-medium text-foreground">{cite.document || cite.title}</span>
                                <span className="text-muted-foreground">Score {(cite.similarity_score ?? 0).toFixed(3)}</span>
                              </div>
                              <div className="mt-1 text-muted-foreground">
                                Source: {cite.source || cite.type || "unknown"} | Page {cite.page ?? "-"} | Chunk {cite.chunk_number ?? (cite.chunk_index != null ? cite.chunk_index + 1 : "-")}
                              </div>
                              <div className="mt-1 text-muted-foreground">
                                {cite.metadata?.subject ? `Subject: ${cite.metadata.subject}` : "Subject: -"}
                                {cite.metadata?.unit ? ` | Unit: ${cite.metadata.unit}` : ""}
                                {cite.metadata?.semester ? ` | Semester: ${cite.metadata.semester}` : ""}
                                {cite.metadata?.department ? ` | Department: ${cite.metadata.department}` : ""}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : null}
                  </div>
                ))}
                {assistantBusy ? (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Thinking...
                  </div>
                ) : null}
              </div>

              <div className="space-y-2">
                <Textarea
                  value={assistantInput}
                  onChange={(e) => setAssistantInput(e.target.value)}
                  placeholder={`Ask about ${currentModule.title}`}
                  className="min-h-28"
                />
                <div className="flex justify-end">
                  <Button onClick={() => void sendAssistantMessage()}>
                    <Send className="mr-2 h-4 w-4" />
                    Ask
                  </Button>
                </div>
              </div>

              <div className="space-y-2">
                <div className="text-xs uppercase tracking-wide text-muted-foreground">Quick actions</div>
                <div className="flex flex-wrap gap-2">
                  {quickActions.map((action) => (
                    <button
                      key={action}
                      type="button"
                      onClick={() => void sendAssistantMessage(`${action} for ${currentModule.title}.`)}
                      className="rounded-full border border-border/60 px-3 py-1.5 text-xs hover:border-primary/30 hover:bg-primary/5"
                    >
                      {action}
                    </button>
                  ))}
                </div>
              </div>

              <div className="rounded-2xl border border-border/60 p-4">
                <div className="text-xs uppercase tracking-wide text-muted-foreground">Completion</div>
                <div className="mt-2 text-2xl font-semibold">{currentModule.progress_percent ?? 0}%</div>
                <p className="mt-2 text-sm text-muted-foreground">
                  {currentModule.completed ? "Completed" : "Still in progress"} | {currentModule.time_spent ?? 0} minutes logged
                </p>
              </div>
            </CardContent>
          ) : (
            <CardContent className="flex h-full items-center justify-center p-2" />
          )}
        </Card>
      </div>
    </div>
  );
}

"use client";

import { useMemo, useState, type FormEvent } from "react";
import { useSearchParams } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  BookOpen,
  ChevronRight,
  Files,
  Loader2,
  MessageSquare,
  Search,
  Send,
  Sparkles,
  ShieldCheck,
  FileText,
} from "lucide-react";
import api from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";

type Citation = {
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
  embedding_id?: string | null;
  metadata?: {
    document_id?: number;
    subject?: string | null;
    department?: string | null;
    semester?: string | null;
    unit?: string | null;
    module?: string | null;
    url?: string | null;
    keywords?: string[];
    source_page_url?: string | null;
    resource_url?: string | null;
    google_drive_file_id?: string | null;
    document_title?: string | null;
    resource_label?: string | null;
    ingestion_timestamp?: string | null;
  };
};

type SessionSummary = {
  id: number;
  title: string;
  subject?: string | null;
  created_at: string;
};

type SessionMessage = {
  id?: number;
  role: "system" | "user" | "ai";
  content: string;
  citations?: Citation[];
};

type SessionDetail = SessionSummary & {
  messages: SessionMessage[];
};

type ParsedAiMessage = {
  explanation: string;
  confidence: string;
  topics: string[];
  answerMode: string;
  usedRag: boolean;
  usedGemini: boolean;
  hybrid: boolean;
  retrievalConfidence: number;
  institutionalInformation: string;
  generalExplanation: string;
  importantNotes: string[];
  recommendedReading: string[];
  practiceQuestions: string[];
  interviewTips: string[];
  realWorldApplications: string[];
  followUpQuestions: string[];
};

type GeneratedMaterial = {
  type: string;
  result: {
    material_type?: string;
    topic?: string;
    summary_markdown?: string;
    flashcards?: Array<{ front: string; back: string }>;
    questions?: Array<{ question: string; options: string[]; answer_index: number; explanation: string }>;
    key_points?: string[];
    cheat_sheet?: string;
  };
  citations?: Citation[];
};

const SUBJECT_OPTIONS = ["CSE", "AIML", "ECE", "Operating Systems", "Database Management Systems", "Computer Networks", "Machine Learning", "Data Structures"];

const ACTIONS = [
  { label: "Quiz", prompt: "Generate 5 MCQs from the retrieved institutional material for this topic." },
  { label: "Flashcards", prompt: "Generate flashcards from the retrieved institutional material for this topic." },
  { label: "Notes", prompt: "Summarize this topic into concise learning notes from the retrieved institutional material." },
];

function parseAiMessage(content: string): ParsedAiMessage {
  const toList = (value: unknown) => (Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : []);
  try {
    const parsed = JSON.parse(content);
    return {
      explanation: parsed.concise_explanation || parsed.general_explanation || content,
      confidence: parsed.confidence_level || "Unknown",
      topics: toList(parsed.related_topics),
      answerMode: parsed.answer_mode || "general",
      usedRag: Boolean(parsed.used_rag),
      usedGemini: parsed.used_gemini !== false,
      hybrid: Boolean(parsed.hybrid),
      retrievalConfidence: Number(parsed.retrieval_confidence ?? 0),
      institutionalInformation: parsed.institutional_information || "",
      generalExplanation: parsed.general_explanation || "",
      importantNotes: toList(parsed.important_notes),
      recommendedReading: toList(parsed.recommended_reading),
      practiceQuestions: toList(parsed.practice_questions),
      interviewTips: toList(parsed.interview_tips),
      realWorldApplications: toList(parsed.real_world_applications),
      followUpQuestions: toList(parsed.follow_up_questions),
    };
  } catch {
    return {
      explanation: content,
      confidence: "Unknown",
      topics: [],
      answerMode: "general",
      usedRag: false,
      usedGemini: true,
      hybrid: false,
      retrievalConfidence: 0,
      institutionalInformation: "",
      generalExplanation: "",
      importantNotes: [],
      recommendedReading: [],
      practiceQuestions: [],
      interviewTips: [],
      realWorldApplications: [],
      followUpQuestions: [],
    };
  }
}

function normalizeSessionMessage(message: SessionMessage): SessionMessage {
  return {
    ...message,
    role: message.role === "system" ? "ai" : message.role,
  };
}

export default function EnterpriseLearningWorkspace() {
  const searchParams = useSearchParams();
  const initialTopic = searchParams.get("q")?.trim() || "";
  const queryClient = useQueryClient();

  const [selectedSessionId, setSelectedSessionId] = useState<number | null>(null);
  const [creatingSession, setCreatingSession] = useState(false);
  const [sending, setSending] = useState(false);
  const [searchValue, setSearchValue] = useState(initialTopic);
  const [subject, setSubject] = useState("CSE");
  const [composer, setComposer] = useState("");
  const [generatedMaterial, setGeneratedMaterial] = useState<GeneratedMaterial | null>(null);

  const sessionsQuery = useQuery({
    queryKey: ["learning-sessions"],
    queryFn: async () => {
      const res = await api.get<SessionSummary[]>("/learning/sessions");
      return Array.isArray(res.data) ? res.data : [];
    },
  });

  const sessions = useMemo(() => sessionsQuery.data ?? [], [sessionsQuery.data]);
  const visibleSessions = useMemo(() => {
    const seen = new Set<string>();
    return sessions.filter((session) => {
      const key = `${(session.title || "").trim().toLowerCase()}|${(session.subject || "").trim().toLowerCase()}`;
      if (seen.has(key)) {
        return false;
      }
      seen.add(key);
      return true;
    });
  }, [sessions]);
  const loadingSessions = sessionsQuery.isPending;
  const activeSessionId = selectedSessionId ?? sessions[0]?.id ?? null;
  const activeSessionCache = activeSessionId ? queryClient.getQueryData<SessionDetail>(["learning-session", activeSessionId]) : undefined;

  const activeSessionQuery = useQuery({
    queryKey: ["learning-session", activeSessionId ?? "none"],
    queryFn: async () => {
      if (!activeSessionId) {
        return null;
      }
      const res = await api.get<SessionDetail>(`/learning/sessions/${activeSessionId}`);
      return {
        ...res.data,
        messages: (res.data.messages || []).map(normalizeSessionMessage),
      };
    },
    enabled: activeSessionId !== null && !activeSessionCache,
  });

  const activeSession = (activeSessionQuery.data ?? activeSessionCache ?? null) as SessionDetail | null;

  const latestAiMessage = useMemo(() => {
    const messages = activeSession?.messages || [];
    return [...messages].reverse().find((message) => message.role === "ai");
  }, [activeSession]);

  const sourceCitations = useMemo(() => {
    const citations = new Map<string, Citation>();
    const currentCitations = generatedMaterial?.citations?.length ? generatedMaterial.citations : latestAiMessage?.citations || [];
    for (const citation of currentCitations) {
      const key = `${citation.metadata?.resource_url || citation.metadata?.source_page_url || citation.id}-${citation.chunk_index ?? citation.chunk_number ?? citation.id}`;
      if (!citations.has(key)) {
        citations.set(key, citation);
      }
    }
    return Array.from(citations.values());
  }, [generatedMaterial, latestAiMessage]);

  const startTopicSession = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const topic = searchValue.trim();
    if (!topic) {
      return;
    }

    setCreatingSession(true);
    try {
      const res = await api.post<SessionSummary>("/learning/sessions", {
        title: topic,
        subject: subject.trim() || null,
      });
      const session = res.data;
      queryClient.setQueryData<SessionSummary[]>(["learning-sessions"], (current = []) => [
        session,
        ...current.filter((item) => item.id !== session.id),
      ]);
      queryClient.setQueryData<SessionDetail>(["learning-session", session.id], {
        ...session,
        messages: [],
      });
      const sessionId = res.data.id;
      setSelectedSessionId(sessionId);
      setSearchValue(topic);
      const prompt = `Teach me ${topic} from the institutional course materials only. Cite the retrieved documents.`;
      const userMessage: SessionMessage = { role: "user", content: prompt };
      queryClient.setQueryData<SessionDetail>(["learning-session", sessionId], (current) => {
        const base = current ?? { ...session, messages: [] };
        return {
          ...base,
          messages: [...base.messages, userMessage],
        };
      });
      const chat = await api.post<SessionMessage>(`/learning/sessions/${sessionId}/chat`, { content: prompt });
      const aiMessage = normalizeSessionMessage(chat.data);
      queryClient.setQueryData<SessionDetail>(["learning-session", sessionId], (current) => {
        const base = current ?? { ...session, messages: [userMessage] };
        return {
          ...base,
          messages: [...base.messages, aiMessage],
        };
      });
      await queryClient.invalidateQueries({ queryKey: ["learning-sessions"] });
    } catch (error) {
      console.error(error);
      toast.error("Failed to start learning session");
    } finally {
      setCreatingSession(false);
    }
  };

  const sendMessage = async (messageText?: string) => {
    const text = (messageText ?? composer).trim();
    if (!text || !activeSessionId || sending) {
      return;
    }

    setSending(true);
    setComposer("");
    const userMessage: SessionMessage = { role: "user", content: text };
    queryClient.setQueryData<SessionDetail>(["learning-session", activeSessionId], (current) =>
      current
        ? {
            ...current,
            messages: [...current.messages, userMessage],
          }
        : {
            id: activeSessionId,
            title: activeSession?.title || activeSessionTitle,
            subject: currentSubject || null,
            created_at: activeSession?.created_at || new Date().toISOString(),
            messages: [userMessage],
          }
    );

    try {
      const res = await api.post<SessionMessage>(`/learning/sessions/${activeSessionId}/chat`, { content: text });
      const aiMessage = normalizeSessionMessage(res.data);
      queryClient.setQueryData<SessionDetail>(["learning-session", activeSessionId], (current) =>
        current
          ? {
              ...current,
              messages: [...current.messages, aiMessage],
            }
          : {
              id: activeSessionId,
              title: activeSession?.title || activeSessionTitle,
              subject: currentSubject || null,
              created_at: activeSession?.created_at || new Date().toISOString(),
              messages: [userMessage, aiMessage],
            }
      );
      await queryClient.invalidateQueries({ queryKey: ["learning-sessions"] });
    } catch (error) {
      console.error(error);
      toast.error("Learning assistant request failed");
    } finally {
      setSending(false);
    }
  };

  const runAction = async (label: string, prompt: string) => {
    if (!activeSessionId) {
      toast.error("Start a session first");
      return;
    }

    if (label === "Quiz" || label === "Flashcards" || label === "Notes") {
      const type = label === "Quiz" ? "quiz" : label === "Flashcards" ? "flashcards" : "summary";
      setGeneratedMaterial(null);
      try {
        const res = await api.post("/learning/generate", {
          type,
          topic: activeSession?.title || searchValue || "Learning topic",
        });
        const result = res.data?.result || {};
        setGeneratedMaterial({
          type: label,
          result: typeof result === "string" ? JSON.parse(result) : result,
          citations: res.data?.citations || [],
        });
      } catch (error) {
        console.error(error);
        toast.error(`Failed to generate ${label.toLowerCase()}`);
      }
      return;
    }

    await sendMessage(prompt);
  };

  const currentSubject = activeSession?.subject || subject;
  const activeSessionTitle = activeSession?.title || searchValue || "Learning workspace";
  const parsedLatest = latestAiMessage ? parseAiMessage(latestAiMessage.content) : null;
  const renderList = (items: string[]) =>
    items.length ? (
      <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-muted-foreground">
        {items.map((item, index) => (
          <li key={`${item}-${index}`}>{item}</li>
        ))}
      </ul>
    ) : null;

  return (
    <div className="space-y-6 pb-8">
      <div className="rounded-3xl border border-border/60 bg-gradient-to-br from-background via-background to-secondary/20 p-6 shadow-sm">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm uppercase tracking-wide text-muted-foreground">
              <Sparkles className="h-4 w-4" />
              Institutional AI Tutor
            </div>
            <h1 className="text-3xl font-bold tracking-tight">Search a topic, open a conversation, and learn from Sreyas materials only.</h1>
            <p className="max-w-3xl text-sm text-muted-foreground">
              Start with a subject, search the course material, and keep every answer grounded in retrieved institutional documents with citations.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge variant="secondary">{visibleSessions.length} sessions</Badge>
            <Badge variant="secondary">{activeSession?.messages?.length || 0} messages</Badge>
            <Badge variant="secondary">{sourceCitations.length} sources</Badge>
          </div>
        </div>
        <form onSubmit={startTopicSession} className="mt-6 grid gap-3 lg:grid-cols-[220px_minmax(0,1fr)_auto]">
          <select
            value={subject}
            onChange={(event) => setSubject(event.target.value)}
            className="h-12 rounded-xl border border-border/60 bg-background px-3 text-sm outline-none focus:border-primary"
          >
            {SUBJECT_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              value={searchValue}
              onChange={(event) => setSearchValue(event.target.value)}
              placeholder="Search a topic, subject, or question"
              className="h-12 w-full rounded-xl border border-border/60 bg-background pl-10 pr-3 text-sm outline-none focus:border-primary"
            />
          </div>
          <Button type="submit" disabled={creatingSession || !searchValue.trim()}>
            {creatingSession ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <BookOpen className="mr-2 h-4 w-4" />}
            Start learning
          </Button>
        </form>
      </div>

      <div className="grid gap-6 xl:grid-cols-[300px_minmax(0,1fr)_340px]">
        <Card className="border-border/60 shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Conversation history</CardTitle>
            <CardDescription>Resume or create focused study sessions.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
              {loadingSessions ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Loading sessions...
                </div>
              ) : visibleSessions.length ? (
                visibleSessions.map((session) => (
                  <button
                    key={session.id}
                    type="button"
                    onClick={() => {
                      setSelectedSessionId(session.id);
                      setGeneratedMaterial(null);
                    }}
                    className={`w-full rounded-2xl border px-4 py-3 text-left transition-colors ${
                      session.id === activeSessionId
                        ? "border-primary bg-primary/5"
                        : "border-border/60 bg-background hover:border-primary/30 hover:bg-secondary/30"
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="truncate text-sm font-medium">{session.title}</div>
                      <div className="mt-1 text-xs text-muted-foreground">{session.subject || "General study"}</div>
                    </div>
                    <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
                  </div>
                </button>
              ))
            ) : (
              <div className="rounded-2xl border border-dashed border-border/60 p-6 text-sm text-muted-foreground">
                No sessions yet. Start from the search bar above.
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="border-border/60 shadow-sm">
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2 text-sm uppercase tracking-wide text-muted-foreground">
                <MessageSquare className="h-4 w-4" />
                Learning chat
              </div>
              <CardTitle className="text-xl">{activeSessionTitle}</CardTitle>
              <CardDescription>
                {currentSubject || "General"} | {activeSession ? `${activeSession.messages.length} messages` : "No active session"}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-4 rounded-2xl border border-border/60 bg-secondary/10 p-4">
              {loadingSessions || (activeSessionId !== null && activeSessionQuery.isPending && !activeSession) ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Loading conversation...
                </div>
              ) : activeSession?.messages?.length ? (
                activeSession.messages.map((message, index) => {
                  const parsed = message.role === "ai" ? parseAiMessage(message.content) : null;
                  return (
                    <div key={`${message.role}-${index}`} className={`rounded-2xl px-4 py-3 text-sm ${message.role === "user" ? "ml-8 bg-primary/10" : "mr-8 border border-border/60 bg-background"}`}>
                      <div className="mb-1 text-[11px] uppercase tracking-wide text-muted-foreground">
                        {message.role === "user" ? "You" : "Tutor"}
                      </div>
                      <div className="whitespace-pre-wrap leading-6">{message.role === "ai" && parsed ? parsed.explanation : message.content}</div>
                      {message.role === "ai" && parsed?.confidence ? (
                        <div className={`mt-3 inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs font-medium ${
                          parsed.confidence === "High" ? "bg-emerald-100 text-emerald-700" : parsed.confidence === "Medium" ? "bg-amber-100 text-amber-700" : "bg-rose-100 text-rose-700"
                        }`}>
                          <ShieldCheck className="h-3.5 w-3.5" />
                          {parsed.confidence} confidence
                        </div>
                      ) : null}
                      {message.role === "ai" && parsed ? (
                        <div className="mt-3 flex flex-wrap gap-2">
                  <Badge variant="secondary">{parsed.answerMode === "general" ? "Gemini only" : parsed.hybrid ? "Hybrid RAG + Gemini" : "Gemini"}</Badge>
                          {parsed.usedRag ? <Badge variant="secondary">RAG used</Badge> : <Badge variant="secondary">No institutional sources</Badge>}
                          {parsed.usedGemini ? <Badge variant="secondary">Gemini answered</Badge> : null}
                          {parsed.retrievalConfidence ? <Badge variant="secondary">Retrieval {(parsed.retrievalConfidence * 100).toFixed(0)}%</Badge> : null}
                        </div>
                      ) : null}
                      {message.role === "ai" && parsed?.institutionalInformation ? (
                        <div className="mt-4 rounded-2xl border border-border/60 bg-secondary/20 p-4">
                          <div className="text-[11px] uppercase tracking-wide text-muted-foreground">Institutional information</div>
                          <div className="mt-2 whitespace-pre-wrap leading-6">{parsed.institutionalInformation}</div>
                        </div>
                      ) : null}
                      {message.role === "ai" && parsed?.generalExplanation ? (
                        <div className="mt-4 rounded-2xl border border-border/60 bg-background p-4">
                          <div className="text-[11px] uppercase tracking-wide text-muted-foreground">General explanation</div>
                          <div className="mt-2 whitespace-pre-wrap leading-6">{parsed.generalExplanation}</div>
                        </div>
                      ) : null}
                      {message.role === "ai" && (parsed?.importantNotes.length || parsed?.recommendedReading.length || parsed?.practiceQuestions.length || parsed?.interviewTips.length || parsed?.realWorldApplications.length) ? (
                        <div className="mt-4 grid gap-3 lg:grid-cols-2">
                          {parsed?.importantNotes.length ? (
                            <div className="rounded-2xl border border-border/60 bg-background p-4">
                              <div className="text-[11px] uppercase tracking-wide text-muted-foreground">Important notes</div>
                              {renderList(parsed.importantNotes)}
                            </div>
                          ) : null}
                          {parsed?.recommendedReading.length ? (
                            <div className="rounded-2xl border border-border/60 bg-background p-4">
                              <div className="text-[11px] uppercase tracking-wide text-muted-foreground">Recommended reading</div>
                              {renderList(parsed.recommendedReading)}
                            </div>
                          ) : null}
                          {parsed?.practiceQuestions.length ? (
                            <div className="rounded-2xl border border-border/60 bg-background p-4">
                              <div className="text-[11px] uppercase tracking-wide text-muted-foreground">Practice questions</div>
                              {renderList(parsed.practiceQuestions)}
                            </div>
                          ) : null}
                          {parsed?.interviewTips.length ? (
                            <div className="rounded-2xl border border-border/60 bg-background p-4">
                              <div className="text-[11px] uppercase tracking-wide text-muted-foreground">Interview tips</div>
                              {renderList(parsed.interviewTips)}
                            </div>
                          ) : null}
                          {parsed?.realWorldApplications.length ? (
                            <div className="rounded-2xl border border-border/60 bg-background p-4 lg:col-span-2">
                              <div className="text-[11px] uppercase tracking-wide text-muted-foreground">Real-world applications</div>
                              {renderList(parsed.realWorldApplications)}
                            </div>
                          ) : null}
                        </div>
                      ) : null}
                      {message.citations?.length ? (
                        <div className="mt-4 space-y-2">
                          <div className="text-[11px] uppercase tracking-wide text-muted-foreground">Sources</div>
                          {message.citations.map((citation) => (
                            <div key={`${citation.id}-${citation.title}`} className="rounded-xl border border-border/60 bg-background px-3 py-2 text-xs">
                              <div className="flex flex-wrap items-center gap-2">
                                <Badge variant="secondary">[{citation.id}]</Badge>
                                <span className="font-medium text-foreground">{citation.document || citation.title}</span>
                                <span className="text-muted-foreground">Score {(citation.similarity_score ?? 0).toFixed(3)}</span>
                              </div>
                              <div className="mt-1 text-muted-foreground">
                                {citation.metadata?.resource_label || citation.source || citation.type || "source"} | Page {citation.page ?? "-"} | Chunk {citation.chunk_number ?? (citation.chunk_index != null ? citation.chunk_index + 1 : "-")}
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : null}
                    </div>
                  );
                })
              ) : (
                <div className="rounded-2xl border border-dashed border-border/60 bg-background p-8 text-center text-sm text-muted-foreground">
                  Pick a topic to start a grounded learning session.
                </div>
              )}
              {sending ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Thinking...
                </div>
              ) : null}
            </div>

            <form
              onSubmit={(event) => {
                event.preventDefault();
                void sendMessage();
              }}
              className="space-y-3"
            >
              <Textarea
                value={composer}
                onChange={(event) => setComposer(event.target.value)}
                placeholder={`Ask about ${activeSessionTitle}`}
                className="min-h-28"
                disabled={!activeSessionId}
              />
              <div className="flex items-center justify-between gap-3">
                <div className="flex flex-wrap gap-2">
                  {ACTIONS.map((action) => (
                    <button
                      key={action.label}
                      type="button"
                      onClick={() => void runAction(action.label, action.prompt.replace("this topic", activeSessionTitle))}
                      className="rounded-full border border-border/60 px-3 py-1.5 text-xs hover:border-primary/30 hover:bg-primary/5"
                    >
                      {action.label}
                    </button>
                  ))}
                </div>
                <Button type="submit" disabled={!composer.trim() || !activeSessionId || sending}>
                  <Send className="mr-2 h-4 w-4" />
                  Send
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        <Card className="border-border/60 shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Source panel</CardTitle>
            <CardDescription>Every response should trace back to the retrieved documents.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {sourceCitations.length ? (
              sourceCitations.map((citation) => (
                <div key={`${citation.id}-${citation.title}`} className="rounded-2xl border border-border/60 p-4">
                  <div className="flex items-center gap-2">
                    <Files className="h-4 w-4 text-muted-foreground" />
                    <div className="font-medium">{citation.document || citation.title}</div>
                  </div>
                  <div className="mt-2 text-xs text-muted-foreground">
                    {citation.metadata?.department || citation.source || "source"} | {citation.metadata?.semester || "semester n/a"}
                  </div>
                  <div className="mt-1 text-xs text-muted-foreground">
                    Page {citation.page ?? "-"} | Chunk {citation.chunk_number ?? (citation.chunk_index != null ? citation.chunk_index + 1 : "-")}
                  </div>
                  <div className="mt-1 text-xs text-muted-foreground">
                    {citation.metadata?.resource_label || "resource"} | Score {(citation.similarity_score ?? 0).toFixed(3)}
                  </div>
                  {citation.metadata?.source_page_url ? (
                    <a
                      href={citation.metadata.source_page_url}
                      target="_blank"
                      rel="noreferrer"
                      className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
                    >
                      Open source
                      <ChevronRight className="h-3 w-3" />
                    </a>
                  ) : null}
                </div>
              ))
            ) : (
              <div className="rounded-2xl border border-dashed border-border/60 p-6 text-sm text-muted-foreground">
                No institutional sources used. Answered using Gemini.
              </div>
            )}

            <div className="rounded-2xl border border-border/60 bg-secondary/10 p-4">
                <div className="mt-3 flex flex-wrap gap-2">
                  {ACTIONS.map((action) => (
                    <button
                      key={`right-${action.label}`}
                    type="button"
                    onClick={() => void runAction(action.label, action.prompt.replace("this topic", activeSessionTitle))}
                    className="rounded-full border border-border/60 px-3 py-1.5 text-xs hover:border-primary/30 hover:bg-background"
                  >
                    {action.label}
                  </button>
                ))}
              </div>
            </div>

            {generatedMaterial ? (
              <div className="space-y-3 rounded-2xl border border-border/60 p-4">
                <div className="flex items-center gap-2 text-sm font-medium">
                  <FileText className="h-4 w-4" />
                  Generated {generatedMaterial.type}
                </div>
                {generatedMaterial.result.summary_markdown ? (
                  <p className="whitespace-pre-wrap text-sm text-muted-foreground">{generatedMaterial.result.summary_markdown}</p>
                ) : null}
                {generatedMaterial.result.key_points?.length ? (
                  <div className="space-y-2">
                    {generatedMaterial.result.key_points.slice(0, 4).map((point, index) => (
                      <div key={`${point}-${index}`} className="rounded-xl bg-secondary/20 px-3 py-2 text-sm text-muted-foreground">
                        {point}
                      </div>
                    ))}
                  </div>
                ) : null}
                {generatedMaterial.result.questions?.length ? (
                  <div className="space-y-2">
                    {generatedMaterial.result.questions.slice(0, 3).map((question, index) => (
                      <div key={`${question.question}-${index}`} className="rounded-xl bg-secondary/20 px-3 py-2 text-sm">
                        <div className="font-medium">{question.question}</div>
                        <div className="mt-1 text-xs text-muted-foreground">{question.explanation}</div>
                      </div>
                    ))}
                  </div>
                ) : null}
                {generatedMaterial.result.flashcards?.length ? (
                  <div className="space-y-2">
                    {generatedMaterial.result.flashcards.slice(0, 3).map((card, index) => (
                      <div key={`${card.front}-${index}`} className="rounded-xl bg-secondary/20 px-3 py-2 text-sm">
                        <div className="font-medium">{card.front}</div>
                        <div className="mt-1 text-xs text-muted-foreground">{card.back}</div>
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>
            ) : null}

            {parsedLatest && !parsedLatest.usedRag ? (
              <div className="rounded-2xl border border-border/60 bg-secondary/10 p-4 text-sm text-muted-foreground">
                Gemini answered directly without institutional retrieval.
              </div>
            ) : null}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

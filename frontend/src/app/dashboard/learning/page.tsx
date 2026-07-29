"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { BookOpen, FileText, Loader2, Plus, Sparkles, Upload, PlayCircle, ChevronRight } from "lucide-react";
import api from "@/lib/api";
import { FEATURE_FLAGS } from "@/lib/feature-flags";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";
import EnterpriseLearningWorkspace from "./enterprise-workspace";

type LearningModule = {
  id: number;
  title: string;
  order: number;
  estimated_minutes: number;
  completed?: boolean;
  progress_percent?: number;
};

type LearningRoadmap = {
  id: number;
  title: string;
  subject?: string | null;
  difficulty?: string | null;
  estimated_hours: number;
  description?: string | null;
  source_chips?: string[];
  modules: LearningModule[];
  completed_modules: number;
  total_modules: number;
  completion_percent: number;
  created_at: string;
};

type LearningSession = {
  id: number;
  title: string;
  subject?: string | null;
  created_at: string;
};

export default function LearningHubPage() {
  if (!FEATURE_FLAGS.learningRoadmap) {
    return <EnterpriseLearningWorkspace />;
  }

  return <LegacyLearningHubPage />;
}

function LegacyLearningHubPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialTopic = searchParams.get("q")?.trim() ?? "";
  const [roadmaps, setRoadmaps] = useState<LearningRoadmap[]>([]);
  const [sessions, setSessions] = useState<LearningSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [roadmapBusy, setRoadmapBusy] = useState(false);
  const [sessionBusy, setSessionBusy] = useState(false);
  const [uploadBusy, setUploadBusy] = useState(false);
  const [roadmapTitle, setRoadmapTitle] = useState(initialTopic);
  const [roadmapSubject, setRoadmapSubject] = useState("");
  const [roadmapDifficulty, setRoadmapDifficulty] = useState("Intermediate");
  const [roadmapHours, setRoadmapHours] = useState("8");
  const [sessionTitle, setSessionTitle] = useState("");
  const [sessionSubject, setSessionSubject] = useState("");
  const [resourceTitle, setResourceTitle] = useState("");
  const [resourceSubject, setResourceSubject] = useState("");
  const [resourceFile, setResourceFile] = useState<File | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [roadmapsRes, sessionsRes] = await Promise.all([api.get("/learning/roadmaps"), api.get("/learning/sessions")]);
      setRoadmaps(roadmapsRes.data || []);
      setSessions(sessionsRes.data || []);
    } catch (error) {
      console.error(error);
      toast.error("Failed to load learning hub");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void fetchData();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [fetchData]);

  const createRoadmap = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const title = roadmapTitle.trim();
    if (!title) {
      return;
    }

    setRoadmapBusy(true);
    try {
      const res = await api.post("/learning/roadmap", {
        title,
        subject: roadmapSubject.trim() || null,
        difficulty: roadmapDifficulty || null,
        estimated_hours: Number(roadmapHours) || null,
      });
      toast.success("Learning roadmap ready");
      setRoadmapTitle("");
      setRoadmapSubject("");
      setRoadmapDifficulty("Intermediate");
      setRoadmapHours("8");
      await fetchData();
      const firstModuleId = res.data?.modules?.[0]?.id;
      if (firstModuleId) {
        router.push(`/dashboard/learning/module/${firstModuleId}`);
      }
    } catch (error) {
      console.error(error);
      toast.error("Failed to build roadmap");
    } finally {
      setRoadmapBusy(false);
    }
  };

  const startSession = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const title = sessionTitle.trim();
    if (!title) {
      return;
    }

    setSessionBusy(true);
    try {
      const res = await api.post("/learning/sessions", {
        title,
        subject: sessionSubject.trim() || null,
      });
      toast.success("Study session created");
      router.push(`/dashboard/learning/chat/${res.data.id}`);
    } catch (error) {
      console.error(error);
      toast.error("Failed to start session");
    } finally {
      setSessionBusy(false);
    }
  };

  const uploadResource = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!resourceFile) {
      toast.error("Pick a file first");
      return;
    }

    const form = event.currentTarget;
    setUploadBusy(true);
    try {
      const formData = new FormData();
      formData.append("title", resourceTitle.trim() || resourceFile.name);
      formData.append("type", resourceFile.name.toLowerCase().endsWith(".pdf") ? "pdf" : "text");
      if (resourceSubject.trim()) {
        formData.append("subject", resourceSubject.trim());
      }
      formData.append("file", resourceFile);
      await api.post("/learning/resources/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      toast.success("Resource uploaded");
      setResourceTitle("");
      setResourceSubject("");
      setResourceFile(null);
      form.reset();
    } catch (error) {
      console.error(error);
      toast.error("Upload failed");
    } finally {
      setUploadBusy(false);
    }
  };

  const totalModules = roadmaps.reduce((sum, roadmap) => sum + (roadmap.total_modules || roadmap.modules.length), 0);
  const completedModules = roadmaps.reduce((sum, roadmap) => sum + (roadmap.completed_modules || 0), 0);
  const activeRoadmaps = roadmaps.length;

  return (
    <div className="space-y-8 pb-8">
      <div className="rounded-3xl border border-border/60 bg-gradient-to-br from-background via-background to-secondary/20 p-6 shadow-sm">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-sm uppercase tracking-wide text-muted-foreground">
              <Sparkles className="h-4 w-4" />
              Enterprise Learning Hub
            </div>
            <h1 className="text-3xl font-bold tracking-tight">Roadmap first. Lessons second. Assistant always stays to the side.</h1>
            <p className="max-w-3xl text-sm text-muted-foreground">
              Generate structured learning roadmaps, open module lessons, practice with quizzes and flashcards, and pull answers from the retrieved knowledge base instead of a generic chat box.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge variant="secondary">{activeRoadmaps} roadmaps</Badge>
            <Badge variant="secondary">{totalModules} modules</Badge>
            <Badge variant="secondary">{completedModules} completed</Badge>
          </div>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[360px_minmax(0,1fr)]">
        <div className="space-y-6">
          <Card className="border-border/60 shadow-sm">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Plus className="h-4 w-4" />
                Create roadmap
              </CardTitle>
              <CardDescription>Generate a module-by-module plan with AI.</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={createRoadmap} className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Title</label>
                  <input
                    value={roadmapTitle}
                    onChange={(event) => setRoadmapTitle(event.target.value)}
                    placeholder="Data Structures"
                    className="w-full rounded-xl border border-border/60 bg-background px-3 py-2 text-sm outline-none focus:border-primary"
                  />
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Subject</label>
                    <input
                      value={roadmapSubject}
                      onChange={(event) => setRoadmapSubject(event.target.value)}
                      placeholder="Computer Science"
                      className="w-full rounded-xl border border-border/60 bg-background px-3 py-2 text-sm outline-none focus:border-primary"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Difficulty</label>
                    <input
                      value={roadmapDifficulty}
                      onChange={(event) => setRoadmapDifficulty(event.target.value)}
                      placeholder="Intermediate"
                      className="w-full rounded-xl border border-border/60 bg-background px-3 py-2 text-sm outline-none focus:border-primary"
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Estimated hours</label>
                  <input
                    value={roadmapHours}
                    onChange={(event) => setRoadmapHours(event.target.value)}
                    inputMode="numeric"
                    placeholder="8"
                    className="w-full rounded-xl border border-border/60 bg-background px-3 py-2 text-sm outline-none focus:border-primary"
                  />
                </div>
                <Button type="submit" className="w-full" disabled={roadmapBusy}>
                  {roadmapBusy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <BookOpen className="mr-2 h-4 w-4" />}
                  Generate roadmap
                </Button>
              </form>
            </CardContent>
          </Card>

          <Card className="border-border/60 shadow-sm">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <PlayCircle className="h-4 w-4" />
                Secondary study session
              </CardTitle>
              <CardDescription>Keep a focused assistant session for quick follow-up questions.</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={startSession} className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Session title</label>
                  <input
                    value={sessionTitle}
                    onChange={(event) => setSessionTitle(event.target.value)}
                    placeholder="Trees and Graphs"
                    className="w-full rounded-xl border border-border/60 bg-background px-3 py-2 text-sm outline-none focus:border-primary"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Subject</label>
                  <input
                    value={sessionSubject}
                    onChange={(event) => setSessionSubject(event.target.value)}
                    placeholder="Algorithms"
                    className="w-full rounded-xl border border-border/60 bg-background px-3 py-2 text-sm outline-none focus:border-primary"
                  />
                </div>
                <Button type="submit" variant="outline" className="w-full" disabled={sessionBusy}>
                  {sessionBusy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Sparkles className="mr-2 h-4 w-4" />}
                  Start study session
                </Button>
              </form>
            </CardContent>
          </Card>

          <Card className="border-border/60 shadow-sm">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Upload className="h-4 w-4" />
                Upload study material
              </CardTitle>
              <CardDescription>Send PDFs or text files into the learning knowledge base.</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={uploadResource} className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Title</label>
                  <input
                    value={resourceTitle}
                    onChange={(event) => setResourceTitle(event.target.value)}
                    placeholder="Operating Systems Notes"
                    className="w-full rounded-xl border border-border/60 bg-background px-3 py-2 text-sm outline-none focus:border-primary"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Subject</label>
                  <input
                    value={resourceSubject}
                    onChange={(event) => setResourceSubject(event.target.value)}
                    placeholder="OS"
                    className="w-full rounded-xl border border-border/60 bg-background px-3 py-2 text-sm outline-none focus:border-primary"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">File</label>
                  <input
                    type="file"
                    accept=".pdf,.txt,.docx,.pptx"
                    onChange={(event) => setResourceFile(event.target.files?.[0] ?? null)}
                    className="w-full rounded-xl border border-border/60 bg-background px-3 py-2 text-sm"
                  />
                  {resourceFile ? <p className="text-xs text-muted-foreground">{resourceFile.name}</p> : null}
                </div>
                <Button type="submit" variant="secondary" className="w-full" disabled={uploadBusy}>
                  {uploadBusy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <FileText className="mr-2 h-4 w-4" />}
                  Upload material
                </Button>
              </form>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card className="border-border/60 shadow-sm">
            <CardHeader>
              <CardTitle className="text-lg">Roadmaps</CardTitle>
              <CardDescription>Open a module to study, quiz, mark completion, and keep the assistant in the lesson view.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {loading ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Loading roadmaps...
                </div>
              ) : roadmaps.length ? (
                roadmaps.map((roadmap) => (
                  <div key={roadmap.id} className="rounded-2xl border border-border/60 p-4">
                    <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                      <div className="space-y-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <h3 className="text-base font-semibold">{roadmap.title}</h3>
                          <Badge variant="secondary">{roadmap.completion_percent}% complete</Badge>
                          <Badge variant="outline">{roadmap.difficulty || "Intermediate"}</Badge>
                        </div>
                        <p className="text-sm text-muted-foreground">{roadmap.subject || roadmap.description || "AI generated learning plan"}</p>
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          const firstModule = roadmap.modules[0];
                          if (firstModule) {
                            router.push(`/dashboard/learning/module/${firstModule.id}`);
                          }
                        }}
                        disabled={!roadmap.modules.length}
                      >
                        Open
                        <ChevronRight className="ml-2 h-4 w-4" />
                      </Button>
                    </div>

                    <div className="mt-4 grid gap-2">
                      {roadmap.modules.map((module) => (
                        <button
                          key={module.id}
                          type="button"
                          onClick={() => router.push(`/dashboard/learning/module/${module.id}`)}
                          className="flex items-center justify-between gap-3 rounded-xl border border-border/60 px-3 py-3 text-left text-sm hover:border-primary/30 hover:bg-secondary/30"
                        >
                          <div className="min-w-0">
                            <div className="font-medium">
                              {module.order}. {module.title}
                            </div>
                            <div className="mt-1 text-xs text-muted-foreground">
                              {module.estimated_minutes} min
                              {module.progress_percent != null ? ` | ${module.progress_percent}% progress` : ""}
                            </div>
                          </div>
                          <Badge variant={module.completed ? "default" : "secondary"}>{module.completed ? "Done" : "Open"}</Badge>
                        </button>
                      ))}
                    </div>
                  </div>
                ))
              ) : (
                <div className="rounded-2xl border border-dashed border-border/60 p-8 text-sm text-muted-foreground">
                  No roadmaps yet. Generate one from the form on the left.
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="border-border/60 shadow-sm">
            <CardHeader>
              <CardTitle className="text-lg">Recent study sessions</CardTitle>
              <CardDescription>Resume a focused assistant session when you want a quick follow-up answer.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-3 md:grid-cols-2">
              {sessions.length ? (
                sessions.map((session) => (
                  <Link
                    key={session.id}
                    href={`/dashboard/learning/chat/${session.id}`}
                    className="rounded-2xl border border-border/60 p-4 transition-colors hover:border-primary/30 hover:bg-secondary/30"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="truncate text-sm font-medium">{session.title}</div>
                        <div className="mt-1 text-xs text-muted-foreground">{session.subject || "General"}</div>
                      </div>
                      <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
                    </div>
                  </Link>
                ))
              ) : (
                <div className="col-span-full rounded-2xl border border-dashed border-border/60 p-8 text-sm text-muted-foreground">
                  No study sessions yet.
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { AlertCircle, BookOpen, CheckCircle, Database, FileText, Layers, RefreshCw, Upload } from "lucide-react";
import api from "@/lib/api";

type KnowledgeDocument = {
  id: number;
  title: string;
  status: string;
  source: string;
};

type KnowledgeStats = {
  documents: number;
  chunks: number;
  embeddings: number;
  completed: number;
  processing: number;
  failed: number;
};

export default function KnowledgeAdminDashboard() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [message, setMessage] = useState("");
  const [syncMessage, setSyncMessage] = useState("");
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [stats, setStats] = useState<KnowledgeStats>({ documents: 0, chunks: 0, embeddings: 0, completed: 0, processing: 0, failed: 0 });

  const loadKnowledge = useCallback(async () => {
    try {
      const [statusRes, statsRes] = await Promise.all([api.get("/knowledge/status"), api.get("/knowledge/stats")]);
      setDocuments(Array.isArray(statusRes.data) ? statusRes.data : []);
      setStats(statsRes.data || { documents: 0, chunks: 0, embeddings: 0, completed: 0, processing: 0, failed: 0 });
    } catch {
      setDocuments([]);
      setStats({ documents: 0, chunks: 0, embeddings: 0, completed: 0, processing: 0, failed: 0 });
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadKnowledge();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [loadKnowledge]);

  const handleUpload = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!file) return;

    const form = event.currentTarget;
    setUploading(true);
    setMessage("");

    const formData = new FormData();
    formData.append("file", file);
    formData.append("title", file.name);

    try {
      const response = await api.post("/knowledge/upload", formData);
      setMessage(response.data?.message || "Upload successful. Document queued for processing.");
      setFile(null);
      form.reset();
      await loadKnowledge();
    } catch (error: unknown) {
      const detail = typeof error === "object" && error && "response" in error
        ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : null;
      setMessage(typeof detail === "string" ? detail : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const syncSreyasContent = async () => {
    setSyncing(true);
    setSyncMessage("");
    try {
      const response = await api.post("/knowledge/sreyas/sync");
      setSyncMessage(
        `Synced ${response.data?.documents || 0} documents, ${response.data?.chunks || 0} chunks, ${response.data?.embeddings || 0} embeddings.`
      );
      await loadKnowledge();
    } catch (error: unknown) {
      const detail = typeof error === "object" && error && "response" in error
        ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : null;
      setSyncMessage(typeof detail === "string" ? detail : "Sreyas sync failed");
    } finally {
      setSyncing(false);
    }
  };

  const completedCount = documents.filter((doc) => doc.status === "completed").length;
  const processingCount = documents.filter((doc) => doc.status === "pending" || doc.status === "processing").length;
  const failedCount = documents.filter((doc) => doc.status === "failed").length;

  return (
    <div className="mx-auto flex min-h-[calc(100vh-2rem)] max-w-7xl flex-col rounded-3xl bg-slate-50 p-8 text-slate-900">
      <div className="mb-8">
        <h1 className="flex items-center gap-3 text-3xl font-bold">
          <BookOpen className="h-8 w-8 text-blue-600" />
          Enterprise Knowledge Engine
        </h1>
        <p className="mt-2 text-slate-500">Manage document ingestion and monitor the institutional knowledge base.</p>
      </div>

      <div className="mb-8 grid grid-cols-1 gap-6 lg:grid-cols-3 xl:grid-cols-6">
        <StatCard icon={Database} label="Total Documents" value={stats.documents || documents.length} tone="blue" />
        <StatCard icon={Layers} label="Completed" value={stats.completed || completedCount} tone="purple" />
        <StatCard icon={RefreshCw} label="Processing" value={stats.processing || processingCount} tone="green" />
        <StatCard icon={Layers} label="Chunks" value={stats.chunks || 0} tone="emerald" />
        <StatCard icon={CheckCircle} label="Embeddings" value={stats.embeddings || 0} tone="sky" />
        <StatCard icon={AlertCircle} label="Failed" value={stats.failed || failedCount} tone="rose" />
      </div>

      <div className="grid gap-8 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-xl font-bold">Upload document</h2>
          <form onSubmit={handleUpload} className="space-y-4">
            <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50 p-6">
              <label className="flex cursor-pointer flex-col items-center gap-2 text-sm text-slate-500">
                <Upload className="h-6 w-6 text-blue-600" />
                <span>Choose a PDF, DOCX, PPTX, TXT, or MD file</span>
                <input
                  type="file"
                  accept=".pdf,.docx,.pptx,.txt,.md"
                  onChange={(event) => setFile(event.target.files?.[0] || null)}
                  className="hidden"
                />
              </label>
              {file ? <p className="mt-3 text-sm font-medium text-slate-900">{file.name}</p> : null}
            </div>
            <button
              type="submit"
              disabled={!file || uploading}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 py-2.5 font-medium text-white transition-colors hover:bg-blue-700 disabled:opacity-50"
            >
              {uploading ? <RefreshCw className="h-5 w-5 animate-spin" /> : <Upload className="h-5 w-5" />}
              {uploading ? "Processing..." : "Process Document"}
            </button>
          </form>

          {message ? (
            <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">
              {message}
            </div>
          ) : null}

          <button
            type="button"
            onClick={syncSreyasContent}
            disabled={syncing}
            className="mt-6 inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-900 transition-colors hover:bg-slate-50 disabled:opacity-50"
          >
            {syncing ? <RefreshCw className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
            {syncing ? "Syncing..." : "Sync Sreyas content"}
          </button>

          {syncMessage ? (
            <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">
              {syncMessage}
            </div>
          ) : null}
        </div>

        <div className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-xl font-bold">Recent ingestions</h2>
          <div className="space-y-3">
            {documents.slice(0, 3).map((doc) => (
              <div
                key={doc.id}
                className="flex items-center justify-between rounded-xl border border-slate-100 bg-slate-50 p-4 transition-colors hover:bg-slate-100"
              >
                <div className="flex items-center gap-3">
                  <FileText className="h-8 w-8 text-slate-400" />
                  <div>
                    <p className="text-sm font-medium text-slate-900">{doc.title}</p>
                    <p className="text-xs text-slate-500">Source: {doc.source}</p>
                  </div>
                </div>
                <span
                  className={`rounded-full px-3 py-1 text-xs font-medium ${
                    doc.status === "completed" ? "bg-green-100 text-green-700" : "bg-amber-100 text-amber-700"
                  }`}
                >
                  {doc.status.toUpperCase()}
                </span>
              </div>
            ))}
          </div>
          {documents.length === 0 ? (
            <p className="mt-4 text-sm text-slate-500">No documents available yet.</p>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  tone,
}: {
  icon: typeof Database;
  label: string;
  value: number;
  tone: "blue" | "purple" | "green" | "emerald" | "sky" | "rose";
}) {
  const toneClasses: Record<typeof tone, string> = {
    blue: "bg-blue-50 text-blue-600",
    purple: "bg-purple-50 text-purple-600",
    green: "bg-green-50 text-green-600",
    emerald: "bg-emerald-50 text-emerald-600",
    sky: "bg-sky-50 text-sky-600",
    rose: "bg-rose-50 text-rose-600",
  };

  return (
    <div className="flex items-center gap-4 rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
      <div className={`rounded-xl p-4 ${toneClasses[tone]}`}>
        <Icon className="h-6 w-6" />
      </div>
      <div>
        <p className="text-sm font-medium text-slate-500">{label}</p>
        <p className="text-2xl font-bold">{value}</p>
      </div>
    </div>
  );
}

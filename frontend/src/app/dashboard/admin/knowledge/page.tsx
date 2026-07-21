"use client";

import { useEffect, useState } from "react";
import { Upload, BookOpen, Database, RefreshCw, FileText, Layers, CheckCircle, AlertCircle } from "lucide-react";

export default function KnowledgeAdminDashboard() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState("");
  const [documents, setDocuments] = useState<Array<{ id: number; title: string; status: string; source: string }>>([]);

  useEffect(() => {
    const loadDocuments = async () => {
      try {
        const token = localStorage.getItem("accessToken");
        const res = await fetch("http://localhost:8000/api/v1/knowledge/status", {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (!res.ok) return;
        const data = await res.json();
        setDocuments(Array.isArray(data) ? data : []);
      } catch {
        setDocuments([]);
      }
    };

    loadDocuments();
  }, []);

  const completedCount = documents.filter((doc) => doc.status === "completed").length;
  const processingCount = documents.filter((doc) => doc.status === "pending" || doc.status === "processing").length;

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setUploading(true);
    const formData = new FormData();
    formData.append("file", file);
    formData.append("title", file.name);

    try {
      const token = localStorage.getItem("accessToken");
      const res = await fetch("http://localhost:8000/api/v1/knowledge/upload", {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`
        },
        body: formData,
      });
      
      const data = await res.json();
      if (res.ok) {
        setMessage("Upload successful! Document queued for processing.");
        setFile(null);
      } else {
        setMessage(data.detail || "Upload failed");
      }
    } catch {
      setMessage("Upload failed due to network error.");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-50 text-slate-900 p-8 max-w-7xl mx-auto rounded-3xl min-h-[calc(100vh-2rem)]">
      
      <div className="mb-8">
        <h1 className="text-3xl font-bold flex items-center gap-3">
          <BookOpen className="w-8 h-8 text-blue-600" />
          Enterprise Knowledge Engine
        </h1>
        <p className="text-slate-500 mt-2">Manage document ingestion, monitor vector databases, and review AI content generation.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        {/* Stats Cards */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 flex items-center gap-4">
          <div className="p-4 bg-blue-50 text-blue-600 rounded-xl">
            <Database className="w-6 h-6" />
          </div>
          <div>
            <p className="text-sm text-slate-500 font-medium">Total Documents</p>
            <p className="text-2xl font-bold">{documents.length}</p>
          </div>
        </div>
        
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 flex items-center gap-4">
          <div className="p-4 bg-purple-50 text-purple-600 rounded-xl">
            <Layers className="w-6 h-6" />
          </div>
          <div>
            <p className="text-sm text-slate-500 font-medium">Completed</p>
            <p className="text-2xl font-bold">{completedCount}</p>
          </div>
        </div>
        
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 flex items-center gap-4">
          <div className="p-4 bg-green-50 text-green-600 rounded-xl">
            <RefreshCw className="w-6 h-6" />
          </div>
          <div>
            <p className="text-sm text-slate-500 font-medium">Processing</p>
            <p className="text-2xl font-bold">{processingCount}</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Upload Center */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
          <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
            <Upload className="w-5 h-5" />
            Upload Document
          </h2>
          
          <form onSubmit={handleUpload} className="space-y-4">
            <div className="border-2 border-dashed border-slate-200 rounded-xl p-8 text-center hover:bg-slate-50 transition-colors">
              <input
                type="file"
                id="file-upload"
                className="hidden"
                accept=".pdf,.docx,.pptx,.txt,.md"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
              />
              <label htmlFor="file-upload" className="cursor-pointer flex flex-col items-center">
                <FileText className="w-10 h-10 text-slate-400 mb-3" />
                <span className="text-sm font-medium text-blue-600">Click to browse</span>
                <span className="text-xs text-slate-500 mt-1">PDF, DOCX, PPTX, TXT, MD up to 50MB</span>
              </label>
            </div>
            
            {file && (
              <div className="flex items-center gap-2 text-sm text-slate-700 bg-slate-50 p-3 rounded-lg border border-slate-200">
                <CheckCircle className="w-4 h-4 text-green-500" />
                {file.name}
              </div>
            )}
            
            {message && (
              <div className={`p-3 rounded-lg text-sm flex items-center gap-2 ${message.includes('success') ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
                {message.includes('success') ? <CheckCircle className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
                {message}
              </div>
            )}

            <button
              type="submit"
              disabled={!file || uploading}
              className="w-full py-2.5 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {uploading ? (
                <RefreshCw className="w-5 h-5 animate-spin" />
              ) : (
                "Process Document"
              )}
            </button>
          </form>
        </div>
        
        {/* Recent Processing */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
          <h2 className="text-xl font-bold mb-4">Recent Ingestions</h2>
          
          <div className="space-y-3">
            {(documents.slice(0, 3)).map((doc) => (
              <div key={doc.id} className="flex items-center justify-between p-4 rounded-xl border border-slate-100 bg-slate-50 hover:bg-slate-100 transition-colors">
                <div className="flex items-center gap-3">
                  <FileText className="w-8 h-8 text-slate-400" />
                  <div>
                    <p className="font-medium text-sm text-slate-900">{doc.title}</p>
                    <p className="text-xs text-slate-500">Source: {doc.source}</p>
                  </div>
                </div>
                <div>
                  <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                    doc.status === 'completed' ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'
                  }`}>
                    {doc.status.toUpperCase()}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

    </div>
  );
}

"use client";

import { useState, useEffect, useRef, use, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Send, ArrowLeft, Loader2, BrainCircuit, FileText, CheckCircle2, ChevronRight, BookMarked, ShieldCheck, AlertCircle } from "lucide-react";
import api from "@/lib/api";
import { FEATURE_FLAGS } from "@/lib/feature-flags";
import EnterpriseLearningWorkspace from "../../enterprise-workspace";

interface Citation {
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
}

interface Message {
  id?: number;
  role: "system" | "user" | "ai";
  content: string; // For AI, this will be JSON stringified structured data
  citations?: Citation[];
}

interface LearningSession {
  id: number;
  title: string;
  subject?: string | null;
  messages: Message[];
}

interface QuizData {
  questions: Array<{
    question: string;
    options: string[];
    answer_index: number;
    explanation: string;
  }>;
}

interface FlashcardData {
  flashcards: Array<{
    front: string;
    back: string;
  }>;
}

interface StudyMaterialData {
  material_type?: string;
  topic?: string;
  summary_markdown?: string;
  flashcards?: FlashcardData["flashcards"];
  questions?: QuizData["questions"];
  key_points?: string[];
  cheat_sheet?: string;
}

export default function LearningChat(props: { params: Promise<{ id: string }> }) {
  if (!FEATURE_FLAGS.learningRoadmap) {
    return <EnterpriseLearningWorkspace />;
  }

  return <LearningChatLegacy {...props} />;
}

function LearningChatLegacy({ params }: { params: Promise<{ id: string }> }) {
  const router = useRouter();
  const { id } = use(params);
  
  const [session, setSession] = useState<LearningSession | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [isGenerating, setIsGenerating] = useState<string | null>(null);
  
  const [studyMaterial, setStudyMaterial] = useState<{ type: string; content: QuizData | FlashcardData | StudyMaterialData | string; citations?: Citation[] } | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const fetchSession = useCallback(async () => {
    try {
      const res = await api.get<LearningSession>(`/learning/sessions/${id}`);
      setSession(res.data);
      setMessages(res.data.messages || []);
    } catch (error) {
      console.error(error);
    }
  }, [id]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void fetchSession();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [fetchSession]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  const sendMessage = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!inputText.trim()) return;
    
    const userMsg: Message = { role: "user", content: inputText };
    setMessages(prev => [...prev, userMsg]);
    setInputText("");
    setIsTyping(true);
    
    try {
      const res = await api.post(`/learning/sessions/${id}/chat`, { content: userMsg.content });
      setMessages(prev => [...prev, res.data]);
    } catch (error) {
      console.error(error);
    } finally {
      setIsTyping(false);
    }
  };

  const generateMaterial = async (type: string) => {
    setIsGenerating(type);
    const placeholderContent =
      type === "quiz"
        ? { questions: [] }
        : type === "flashcards"
          ? { flashcards: [] }
          : { summary_markdown: "" };
    setStudyMaterial({ type, content: placeholderContent, citations: [] });
    try {
      const res = await api.post<{ result: QuizData | FlashcardData | StudyMaterialData | string; citations?: Citation[] }>(`/learning/generate`, { type, topic: session?.title });
      const raw = res.data.result;
      let content: QuizData | FlashcardData | StudyMaterialData | string = raw;
      if (typeof raw === "string") {
        try {
          content = JSON.parse(raw);
        } catch {
          content = placeholderContent;
        }
      }
      setStudyMaterial({ type, content, citations: res.data.citations || [] });
    } catch (error) {
      console.error(error);
    } finally {
      setIsGenerating(null);
    }
  };

  // Helper renderers for inline study tools
  const renderQuiz = (data: QuizData) => {
    if (!data || !data.questions) return <p className="text-gray-600">Invalid quiz data generated.</p>;
    return (
      <div className="space-y-6">
        <h3 className="text-xl font-bold flex items-center gap-2 text-gray-900"><CheckCircle2 className="text-green-500" /> Practice Quiz</h3>
        {data.questions.map((q, i: number) => (
          <div key={i} className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
            <p className="font-medium text-gray-900 mb-4">{i+1}. {q.question}</p>
            <div className="space-y-2">
              {q.options.map((opt: string, j: number) => (
                <div key={j} className="p-3 rounded-lg bg-gray-50 border border-gray-200 hover:border-purple-500 hover:bg-purple-50 cursor-pointer transition-colors text-sm text-gray-700">
                  {opt}
                </div>
              ))}
            </div>
            <details className="mt-4 text-sm text-gray-500 group cursor-pointer">
              <summary className="font-medium hover:text-purple-600 transition-colors">Show Answer</summary>
              <div className="mt-2 p-3 bg-green-50 border border-green-200 text-green-800 rounded-lg">
                <span className="font-semibold">Correct:</span> {q.options[q.answer_index]} <br/>
                <span className="text-gray-600 block mt-1">{q.explanation}</span>
              </div>
            </details>
          </div>
        ))}
      </div>
    );
  };

  const renderFlashcards = (data: FlashcardData) => {
    if (!data || !data.flashcards) return <p className="text-gray-600">Invalid flashcard data generated.</p>;
    return (
      <div className="space-y-6">
        <h3 className="text-xl font-bold flex items-center gap-2 text-gray-900"><BookMarked className="text-yellow-500" /> Flashcards</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {data.flashcards.map((f, i: number) => (
            <div key={i} className="group perspective-1000 w-full h-40">
              <div className="relative w-full h-full transition-transform duration-500 transform-style-preserve-3d group-hover:rotate-y-180">
                {/* Front */}
                <div className="absolute w-full h-full backface-hidden flex items-center justify-center p-6 bg-white border border-gray-200 rounded-xl shadow-sm">
                  <p className="text-center font-medium text-gray-900">{f.front}</p>
                </div>
                {/* Back */}
                <div className="absolute w-full h-full flex items-center justify-center p-6 bg-purple-50 border border-purple-200 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                  <p className="text-center text-sm text-purple-900">{f.back}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  // Helper to parse AI JSON response
  const parseAIContent = (content: string) => {
    try {
      const parsed = JSON.parse(content);
      return {
        explanation: parsed.concise_explanation || content,
        confidence: parsed.confidence_level || 'Unknown',
        topics: parsed.related_topics || []
      };
    } catch {
      return { explanation: content, confidence: 'Unknown', topics: [] };
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-theme(spacing.16))] -m-6 lg:-m-8 bg-gray-50 text-gray-900">
      {/* Header */}
      <div className="flex items-center justify-between p-4 bg-white border-b border-gray-200 z-10 shadow-sm">
        <div className="flex items-center gap-4">
          <button onClick={() => router.push('/dashboard/learning')} className="p-2 hover:bg-gray-100 rounded-full transition-colors text-gray-500">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="font-semibold text-gray-900">{session?.title || "Learning session"}</h1>
            <p className="text-xs text-purple-600 font-medium">{session?.subject || "General Study"}</p>
          </div>
        </div>
        
        {/* Generation Tools */}
        <div className="flex items-center gap-2">
          <button 
            onClick={() => generateMaterial('summary')}
            disabled={!!isGenerating}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium bg-white border border-gray-200 hover:bg-gray-50 text-gray-700 disabled:opacity-50 transition-colors shadow-sm"
          >
            {isGenerating === 'summary' ? <Loader2 className="w-4 h-4 animate-spin text-gray-400" /> : <FileText className="w-4 h-4 text-blue-500" />}
            <span className="hidden md:inline">Summary</span>
          </button>
          <button 
            onClick={() => generateMaterial('quiz')}
            disabled={!!isGenerating}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium bg-white border border-gray-200 hover:bg-gray-50 text-gray-700 disabled:opacity-50 transition-colors shadow-sm"
          >
            {isGenerating === 'quiz' ? <Loader2 className="w-4 h-4 animate-spin text-gray-400" /> : <CheckCircle2 className="w-4 h-4 text-green-500" />}
            <span className="hidden md:inline">Quiz</span>
          </button>
          <button 
            onClick={() => generateMaterial('flashcards')}
            disabled={!!isGenerating}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium bg-white border border-gray-200 hover:bg-gray-50 text-gray-700 disabled:opacity-50 transition-colors shadow-sm"
          >
            {isGenerating === 'flashcards' ? <Loader2 className="w-4 h-4 animate-spin text-gray-400" /> : <BookMarked className="w-4 h-4 text-yellow-500" />}
            <span className="hidden md:inline">Flashcards</span>
          </button>
        </div>
      </div>

      {/* Main Layout Area */}
      <div className="flex-1 flex overflow-hidden">
        
        {/* Chat Area */}
        <div className={`flex-1 flex flex-col ${studyMaterial ? 'hidden md:flex border-r border-gray-200' : 'flex'}`}>
          <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6">
            
            {messages.length === 0 && (
              <div className="h-full flex flex-col items-center justify-center text-center opacity-70">
                <BrainCircuit className="w-16 h-16 text-purple-500 mb-4" />
                <p className="text-xl font-medium text-gray-900">Hello! I&apos;m your study assistant.</p>
                <p className="text-sm mt-2 max-w-sm text-gray-500">Use the summary, quiz, and flashcard tools first. Ask follow-up questions only when you need clarification on {session?.title}.</p>
              </div>
            )}

            {messages.map((msg, idx) => {
              const isUser = msg.role === 'user';
              let aiData = { explanation: msg.content, confidence: 'Unknown', topics: [] };
              if (!isUser && msg.role !== 'system') {
                aiData = parseAIContent(msg.content);
              }

              return (
                <div key={idx} className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[85%] ${
                    isUser 
                      ? 'bg-blue-600 text-white rounded-2xl rounded-br-none px-5 py-3 shadow-sm' 
                      : 'bg-white border border-gray-200 text-gray-800 rounded-2xl rounded-bl-none px-5 py-4 shadow-sm w-full'
                  }`}>
                    
                    {!isUser && (
                      <div className="flex items-center justify-between mb-3 border-b border-gray-100 pb-2">
                        <div className="flex items-center gap-2">
                          <div className="w-6 h-6 rounded bg-purple-100 flex items-center justify-center">
                            <BrainCircuit className="w-3.5 h-3.5 text-purple-600" />
                          </div>
                          <span className="font-semibold text-sm text-gray-900">Study Assistant</span>
                        </div>
                        
                        {aiData.confidence && aiData.confidence !== 'Unknown' && (
                          <div className={`flex items-center gap-1 text-xs font-medium px-2 py-1 rounded-full ${
                            aiData.confidence === 'High' ? 'bg-green-100 text-green-700' :
                            aiData.confidence === 'Medium' ? 'bg-yellow-100 text-yellow-700' :
                            'bg-red-100 text-red-700'
                          }`}>
                            {aiData.confidence === 'High' ? <ShieldCheck className="w-3 h-3" /> : <AlertCircle className="w-3 h-3" />}
                            {aiData.confidence} Confidence
                          </div>
                        )}
                      </div>
                    )}
                    
                    <div className={`leading-relaxed whitespace-pre-wrap text-sm ${!isUser ? 'prose prose-sm max-w-none prose-p:leading-relaxed prose-headings:text-gray-900 text-gray-700' : ''}`}>
                      {isUser ? msg.content : aiData.explanation}
                    </div>

                    {/* Citations block */}
                    {!isUser && msg.citations && msg.citations.length > 0 && (
                      <div className="mt-4 pt-3 border-t border-gray-100">
                        <p className="text-xs font-semibold text-gray-500 mb-2">SOURCES</p>
                        <div className="flex flex-wrap gap-2">
                          {msg.citations.map((cite, i) => (
                            <div key={i} className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-gray-50 text-xs font-medium text-gray-600 border border-gray-200 hover:border-blue-300 hover:bg-blue-50 cursor-pointer transition-colors">
                              <span className="text-blue-600 font-bold">[{cite.id}]</span>
                              <span className="truncate max-w-[200px]">{cite.title}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    {/* Related Topics block */}
                    {!isUser && aiData.topics && aiData.topics.length > 0 && (
                      <div className="mt-4 flex flex-wrap gap-2">
                        {aiData.topics.map((topic: string, i: number) => (
                          <button 
                            key={i} 
                            onClick={() => { setInputText(`Tell me more about ${topic}`); document.getElementById('chat-input')?.focus(); }}
                            className="text-xs px-2.5 py-1 rounded-full bg-purple-50 text-purple-700 border border-purple-200 hover:bg-purple-100 transition-colors"
                          >
                            Explore: {topic}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
            
            {isTyping && (
              <div className="flex justify-start">
                 <div className="bg-white border border-gray-200 rounded-2xl rounded-bl-none px-4 py-3 shadow-sm flex gap-1.5 items-center">
                   <div className="w-5 h-5 rounded bg-purple-100 flex items-center justify-center mr-2">
                      <BrainCircuit className="w-3 h-3 text-purple-600" />
                   </div>
                   <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" />
                   <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce delay-100" />
                   <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce delay-200" />
                 </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="p-4 bg-white border-t border-gray-200 shadow-sm">
            <form onSubmit={sendMessage} className="flex items-end gap-2 max-w-4xl mx-auto relative">
              <div className="flex-1 bg-gray-50 border border-gray-300 rounded-2xl overflow-hidden focus-within:border-blue-500 focus-within:ring-2 focus-within:ring-blue-500/20 transition-all shadow-inner">
                <textarea
                  id="chat-input"
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  placeholder="Ask a question..."
                  className="w-full max-h-32 min-h-[56px] p-4 bg-transparent text-gray-900 focus:outline-none resize-none placeholder:text-gray-400"
                  rows={1}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      sendMessage();
                    }
                  }}
                />
              </div>
              <button
                type="submit"
                disabled={!inputText.trim() || isTyping}
                className="h-14 w-14 flex items-center justify-center bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 disabled:text-gray-500 text-white rounded-2xl transition-all shadow-md"
              >
                <Send className="w-5 h-5" />
              </button>
            </form>
          </div>
        </div>

        {/* Study Material Sidebar (Slide in) */}
        {studyMaterial && (
          <div className="w-full md:w-[450px] lg:w-[500px] bg-white border-l border-gray-200 flex flex-col animate-in slide-in-from-right-8 duration-300 z-20">
            <div className="p-4 border-b border-gray-200 flex justify-between items-center bg-gray-50">
              <h2 className="font-semibold flex items-center gap-2 text-gray-900">
                {studyMaterial.type === 'summary' && <FileText className="w-4 h-4 text-blue-600" />}
                {studyMaterial.type === 'quiz' && <CheckCircle2 className="w-4 h-4 text-green-600" />}
                {studyMaterial.type === 'flashcards' && <BookMarked className="w-4 h-4 text-yellow-600" />}
                <span className="capitalize">{studyMaterial.type}</span>
              </h2>
              <button onClick={() => setStudyMaterial(null)} className="text-gray-400 hover:text-gray-700 p-1 rounded hover:bg-gray-200 transition-colors">
                <ChevronRight className="w-5 h-5" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-6 bg-gray-50/50">
              {studyMaterial.type === 'summary' && (
                <div className="prose prose-sm max-w-none text-gray-700">
                  <div
                    dangerouslySetInnerHTML={{
                      __html: (() => {
                        if (typeof studyMaterial.content === "string") {
                          return studyMaterial.content.replace(/\n/g, "<br/>");
                        }
                        const content = studyMaterial.content as StudyMaterialData;
                        return (content.summary_markdown || "").replace(/\n/g, "<br/>");
                      })(),
                    }}
                  />
                  {typeof studyMaterial.content !== "string" && (studyMaterial.content as StudyMaterialData).key_points?.length ? (
                    <ul className="mt-4 list-disc pl-5 space-y-1 text-gray-700">
                      {(studyMaterial.content as StudyMaterialData).key_points!.map((point, index) => (
                        <li key={index}>{point}</li>
                      ))}
                    </ul>
                  ) : null}
                </div>
              )}
              {studyMaterial.type === 'quiz' && (
                typeof studyMaterial.content === "string"
                  ? null
                  : 'questions' in (studyMaterial.content as QuizData)
                    ? renderQuiz(studyMaterial.content as QuizData)
                    : null
              )}
              {studyMaterial.type === 'flashcards' && (
                typeof studyMaterial.content === "string"
                  ? null
                  : 'flashcards' in (studyMaterial.content as FlashcardData)
                    ? renderFlashcards(studyMaterial.content as FlashcardData)
                    : null
              )}
              {studyMaterial.citations?.length ? (
                <div className="mt-6 space-y-3">
                  <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-600">Sources</h3>
                  <div className="space-y-2">
                    {studyMaterial.citations.map((cite) => (
                      <div key={`${cite.id}-${cite.title}`} className="rounded-xl border border-gray-200 bg-white p-3 text-sm">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-semibold text-gray-600">[{cite.id}]</span>
                          <span className="font-medium text-gray-900">{cite.document || cite.title}</span>
                          <span className="text-gray-500">Score {(cite.similarity_score ?? 0).toFixed(3)}</span>
                        </div>
                        <div className="mt-1 text-xs text-gray-500">
                          {cite.source || cite.type || "unknown"} | Page {cite.page ?? "-"} | Chunk {cite.chunk_number ?? (cite.chunk_index != null ? cite.chunk_index + 1 : "-")}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}
            </div>
          </div>
        )}

      </div>
    </div>
  );
}

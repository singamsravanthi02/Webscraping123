"use client";

import { useState, useEffect, useRef, use } from "react";
import { useRouter } from "next/navigation";
import { Mic, MicOff, Send, Maximize, Minimize, StopCircle, User, Loader2 } from "lucide-react";
import api from "@/lib/api";

interface Message {
  id?: number;
  role: "system" | "user" | "ai";
  content: string;
}

export default function LiveInterview({ params }: { params: Promise<{ id: string }> }) {
  const router = useRouter();
  const { id } = use(params);
  
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState("");
  const [isVoiceMode, setIsVoiceMode] = useState(true);
  const [isRecording, setIsRecording] = useState(false);
  const [isAiThinking, setIsAiThinking] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [timer, setTimer] = useState(0);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const recognitionRef = useRef<any>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Initialize Speech Recognition
  useEffect(() => {
    if (typeof window !== "undefined") {
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (SpeechRecognition) {
        recognitionRef.current = new SpeechRecognition();
        recognitionRef.current.continuous = false;
        recognitionRef.current.interimResults = false;
        
        recognitionRef.current.onresult = (event: any) => {
          const text = event.results[0][0].transcript;
          setInputText(text);
          sendMessage(text);
        };
        
        recognitionRef.current.onend = () => {
          setIsRecording(false);
        };
      }
    }
  }, [id]); // Add id to dependency array, but it's mostly to run once on client

  useEffect(() => {
    startInterviewSession();
    const interval = setInterval(() => setTimer(t => t + 1), 1000);
    return () => clearInterval(interval);
  }, [id]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isAiThinking]);

  const startInterviewSession = async () => {
    setIsAiThinking(true);
    try {
      // First check if it already started, wait, actually our backend throws if already started.
      // We should ideally fetch first, if pending, start.
      const getRes = await api.get(`/interviews/${id}`);
      if (getRes.data.status === 'pending') {
        const res = await api.post(`/interviews/${id}/start`);
        const initialMsg: Message = { role: "ai", content: res.data.content };
        setMessages([initialMsg]);
        speak(initialMsg.content);
      } else {
        // Load existing messages
        const res = await api.get(`/interviews/${id}`);
        const chat = res.data.messages.filter((m: any) => m.role !== 'system');
        setMessages(chat);
        // Do not speak on resume
      }
    } catch (error) {
      console.error(error);
    } finally {
      setIsAiThinking(false);
    }
  };

  const speak = (text: string) => {
    if (!isVoiceMode || !('speechSynthesis' in window)) return;
    
    // Stop any current speech
    window.speechSynthesis.cancel();
    
    const utterance = new SpeechSynthesisUtterance(text);
    
    // Try to find a good English voice
    const voices = window.speechSynthesis.getVoices();
    const preferredVoice = voices.find(v => v.lang.includes('en-US') && v.name.includes('Google')) || voices[0];
    if (preferredVoice) {
      utterance.voice = preferredVoice;
    }
    
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    
    window.speechSynthesis.speak(utterance);
  };

  const toggleRecording = () => {
    if (isRecording) {
      recognitionRef.current?.stop();
      setIsRecording(false);
    } else {
      window.speechSynthesis.cancel(); // Stop AI speaking when user starts talking
      setInputText("");
      recognitionRef.current?.start();
      setIsRecording(true);
    }
  };

  const sendMessage = async (text: string = inputText) => {
    if (!text.trim()) return;
    
    const userMsg: Message = { role: "user", content: text };
    setMessages(prev => [...prev, userMsg]);
    setInputText("");
    setIsAiThinking(true);
    
    try {
      const res = await api.post(`/interviews/${id}/message`, { content: text });
      const aiMsg: Message = { role: "ai", content: res.data.content };
      setMessages(prev => [...prev, aiMsg]);
      speak(aiMsg.content);
    } catch (error) {
      console.error(error);
    } finally {
      setIsAiThinking(false);
    }
  };

  const endInterview = async () => {
    if (!confirm("Are you sure you want to end the interview?")) return;
    window.speechSynthesis.cancel();
    setIsAiThinking(true);
    try {
      await api.post(`/interviews/${id}/end`);
      router.push(`/dashboard/interviews/${id}/result`);
    } catch (error) {
      console.error(error);
      setIsAiThinking(false);
    }
  };

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      containerRef.current?.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60).toString().padStart(2, '0');
    const s = (seconds % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  return (
    <div ref={containerRef} className="flex flex-col h-screen bg-[#0f0f13] text-white">
      {/* Header */}
      <div className="flex items-center justify-between p-4 bg-[#1a1a24] border-b border-[#2a2a35] z-10">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 bg-[#2a2a35] px-3 py-1.5 rounded-full text-sm font-medium">
            <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
            Live
          </div>
          <span className="font-mono text-gray-400">{formatTime(timer)}</span>
        </div>
        
        <div className="flex items-center gap-3">
          <button 
            onClick={() => setIsVoiceMode(!isVoiceMode)}
            className={`px-4 py-2 rounded-full text-sm font-medium transition-colors border ${isVoiceMode ? 'border-purple-500 text-purple-400 bg-purple-500/10' : 'border-gray-600 text-gray-400 bg-transparent'}`}
          >
            Voice Mode
          </button>
          <button 
            onClick={toggleFullscreen}
            className="p-2 text-gray-400 hover:text-white hover:bg-[#2a2a35] rounded-full transition-colors"
          >
            {isFullscreen ? <Minimize className="w-5 h-5" /> : <Maximize className="w-5 h-5" />}
          </button>
          <button 
            onClick={endInterview}
            className="flex items-center gap-2 bg-red-500/10 text-red-500 border border-red-500/50 hover:bg-red-500 hover:text-white px-4 py-2 rounded-full text-sm font-medium transition-all"
          >
            <StopCircle className="w-4 h-4" />
            End Interview
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex overflow-hidden">
        {/* Animated AI Visualizer */}
        <div className="hidden lg:flex flex-1 flex-col items-center justify-center border-r border-[#2a2a35] relative overflow-hidden bg-gradient-to-b from-[#13131a] to-[#0f0f13]">
          
          {/* Abstract Glowing Orb for AI */}
          <div className="relative flex items-center justify-center w-64 h-64">
            {/* Pulsing rings when thinking or speaking */}
            <div className={`absolute inset-0 border-2 border-purple-500 rounded-full ${isAiThinking || (!isAiThinking && messages.length > 0 && messages[messages.length-1].role === 'ai') ? 'animate-ping opacity-20' : 'opacity-0'}`} />
            <div className={`absolute inset-4 border-2 border-blue-500 rounded-full ${isAiThinking || (!isAiThinking && messages.length > 0 && messages[messages.length-1].role === 'ai') ? 'animate-ping opacity-40 delay-150' : 'opacity-0'}`} />
            
            {/* Core Orb */}
            <div className={`w-32 h-32 rounded-full bg-gradient-to-br from-purple-500 to-blue-500 shadow-[0_0_50px_rgba(124,58,237,0.5)] transition-all duration-700 ${isAiThinking ? 'scale-110 shadow-[0_0_80px_rgba(124,58,237,0.8)]' : ''} flex items-center justify-center`}>
               {isAiThinking ? <Loader2 className="w-10 h-10 text-white animate-spin" /> : <User className="w-12 h-12 text-white/80" />}
            </div>
          </div>
          
          <div className="mt-8 text-center">
            <h2 className="text-xl font-semibold bg-clip-text text-transparent bg-gradient-to-r from-purple-400 to-blue-400">AI Interviewer</h2>
            <p className="text-gray-500 mt-2 text-sm">{isAiThinking ? 'Analyzing and typing...' : 'Listening'}</p>
          </div>
        </div>

        {/* Chat Transcript */}
        <div className="flex-1 flex flex-col max-w-3xl w-full mx-auto">
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {messages.map((msg, idx) => (
              <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[85%] rounded-2xl px-5 py-4 ${
                  msg.role === 'user' 
                    ? 'bg-purple-600 text-white rounded-br-none' 
                    : 'bg-[#1a1a24] border border-[#2a2a35] text-gray-200 rounded-bl-none'
                }`}>
                  <p className="leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                </div>
              </div>
            ))}
            {isAiThinking && (
              <div className="flex justify-start">
                <div className="bg-[#1a1a24] border border-[#2a2a35] rounded-2xl rounded-bl-none px-5 py-4">
                   <div className="flex gap-1">
                     <span className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" />
                     <span className="w-2 h-2 bg-gray-500 rounded-full animate-bounce delay-100" />
                     <span className="w-2 h-2 bg-gray-500 rounded-full animate-bounce delay-200" />
                   </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="p-4 bg-[#1a1a24] border-t border-[#2a2a35]">
            <form onSubmit={(e) => { e.preventDefault(); sendMessage(); }} className="flex items-end gap-2">
              {isVoiceMode && (
                <button
                  type="button"
                  onClick={toggleRecording}
                  className={`p-4 rounded-xl flex-shrink-0 transition-all ${
                    isRecording 
                      ? 'bg-red-500 hover:bg-red-600 text-white shadow-[0_0_20px_rgba(239,68,68,0.5)] animate-pulse' 
                      : 'bg-[#2a2a35] hover:bg-[#3a3a45] text-gray-400 hover:text-white'
                  }`}
                >
                  {isRecording ? <Mic className="w-6 h-6" /> : <MicOff className="w-6 h-6" />}
                </button>
              )}
              
              <div className="flex-1 bg-[#13131a] border border-[#2a2a35] rounded-xl overflow-hidden focus-within:border-purple-500 transition-colors">
                <textarea
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  placeholder={isVoiceMode && isRecording ? "Listening..." : "Type your response..."}
                  className="w-full max-h-32 min-h-[56px] p-4 bg-transparent text-white focus:outline-none resize-none"
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
                disabled={!inputText.trim() || isAiThinking}
                className="p-4 bg-purple-600 hover:bg-purple-500 disabled:bg-purple-600/50 disabled:cursor-not-allowed text-white rounded-xl transition-all"
              >
                <Send className="w-6 h-6" />
              </button>
            </form>
            {isVoiceMode && (
              <p className="text-center text-xs text-gray-500 mt-3">
                Pro tip: Use headphones for the best voice mode experience.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

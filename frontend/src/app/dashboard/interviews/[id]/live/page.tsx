"use client";

import dynamic from "next/dynamic";
import { useState, useEffect, useRef, useCallback, type ComponentType } from "react";
import { useRouter, usePathname } from "next/navigation";
import {
  Mic,
  MicOff,
  Send,
  Maximize,
  Minimize,
  StopCircle,
  Video,
  Loader2,
  ShieldCheck,
  ShieldAlert,
  Wifi,
  WifiOff,
  Play,
  RotateCcw,
  Brain,
  Code2,
  Sparkles,
  Timer,
  EyeOff,
} from "lucide-react";
import api from "@/lib/api";
import { getInterviewDisplayTitle, parseInterviewBrief } from "@/lib/interview";

const MonacoEditor = dynamic(() => import("@monaco-editor/react"), {
  ssr: false,
  loading: () => (
    <div className="mt-4 min-h-[360px] rounded-2xl border border-white/10 bg-[#07070a] p-4 text-sm text-gray-500">
      Loading editor...
    </div>
  ),
});

type PyodideRuntime = {
  setStdout: (options: { batched: (text: string) => void }) => void;
  setStderr: (options: { batched: (text: string) => void }) => void;
  globals: { set: (name: string, value: unknown) => void };
  runPythonAsync: (code: string) => Promise<unknown>;
};

declare global {
  interface Window {
    loadPyodide?: (options: { indexURL: string }) => Promise<PyodideRuntime>;
  }
}

type Message = {
  id?: number;
  role: "system" | "user" | "ai";
  content: string;
  created_at?: string;
};

type InterviewLockViolation = {
  type: string;
  details?: string | null;
  recorded_at?: string | null;
};

type InterviewDetail = {
  id: number;
  title: string;
  type: string;
  status: "pending" | "in_progress" | "completed" | "abandoned";
  start_time: string;
  end_time?: string | null;
  resume_text?: string | null;
  job_description?: string | null;
  lock_violations?: InterviewLockViolation[];
  messages?: Message[];
};

type CodeRunResult = {
  language: string;
  compiler?: string | null;
  success: boolean;
  status: string;
  stdout: string;
  stderr: string;
  compiler_output: string;
  compiler_error: string;
  program_output: string;
  program_error: string;
  message?: string | null;
};

type SpeechRecognitionEventLike = {
  results: Array<Array<{ transcript: string }>>;
};

type SpeechRecognitionLike = {
  continuous: boolean;
  interimResults: boolean;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
};

type BrowserChecks = {
  online: boolean;
  secureContext: boolean;
  mediaDevices: boolean;
  fullscreen: boolean;
  speechSynthesis: boolean;
  speechRecognition: boolean;
};

type CodeLanguage = "javascript" | "python" | "java" | "cpp";

const CODE_STARTERS: Record<CodeLanguage, string> = {
  javascript: `function solve(stdin) {
  return stdin;
}

console.log(solve(stdin));`,
  python: `def solve(stdin_value):
    return stdin_value

print(solve(stdin_value))`,
  java: `import java.util.*;

public class Main {
  static String solve(String stdin) {
    return stdin;
  }

  public static void main(String[] args) {
    Scanner scanner = new Scanner(System.in);
    String input = scanner.useDelimiter("\\\\A").hasNext() ? scanner.useDelimiter("\\\\A").next() : "";
    System.out.print(solve(input));
  }
}`,
  cpp: `#include <bits/stdc++.h>
using namespace std;

string solve(const string& stdin_value) {
  return stdin_value;
}

int main() {
  ios::sync_with_stdio(false);
  cin.tie(nullptr);
  string input((istreambuf_iterator<char>(cin)), istreambuf_iterator<char>());
  cout << solve(input);
  return 0;
}`,
};

const VISIBLE_TESTS = [
  "Visible test 1: sample input should pass.",
  "Visible test 2: empty or edge input should not crash.",
  "Visible test 3: larger input should stay within limits.",
];

const JS_RUNNER_SRC = String.raw`<!doctype html>
<html>
  <body>
    <script>
      const post = (payload) => parent.postMessage({ source: "interview-js-runner", ...payload }, "*");
      const format = (value) => {
        if (typeof value === "string") return value;
        if (value === undefined) return "";
        try {
          return JSON.stringify(value, null, 2);
        } catch (error) {
          return String(value);
        }
      };
      const join = (...parts) => parts.map(format).join(" ");
      const consoleShim = {
        log: (...args) => post({ type: "log", value: join(...args) }),
        info: (...args) => post({ type: "log", value: join(...args) }),
        warn: (...args) => post({ type: "log", value: join(...args) }),
        error: (...args) => post({ type: "error", value: join(...args) }),
      };
      window.addEventListener("message", async (event) => {
        if (!event.data || event.data.source !== "interview-host") return;
        const { code, stdin } = event.data;
        try {
          post({ type: "status", value: "Running in sandbox..." });
          const fn = new Function("stdin", "console", '"use strict";\\n' + code);
          const result = fn(stdin, consoleShim);
          if (result && typeof result.then === "function") {
            const resolved = await result;
            post({ type: "result", value: resolved === undefined ? "Execution complete." : format(resolved) });
            return;
          }
          post({ type: "result", value: result === undefined ? "Execution complete." : format(result) });
        } catch (error) {
          post({ type: "error", value: error && error.message ? error.message : String(error) });
        }
      });
    </script>
  </body>
</html>`;

function formatDuration(seconds: number) {
  const safe = Math.max(0, Math.floor(seconds));
  const minutes = Math.floor(safe / 60);
  const remaining = safe % 60;
  return `${String(minutes).padStart(2, "0")}:${String(remaining).padStart(2, "0")}`;
}

function buildQuestionPairs(messages: Message[]) {
  const conversation = messages.filter((message) => message.role !== "system");
  const pairs: Array<{ question: string; answer: string; questionIndex: number }> = [];

  conversation.forEach((message, index) => {
    if (message.role !== "ai") return;
    const answer = conversation.slice(index + 1).find((entry) => entry.role === "user");
    pairs.push({
      question: message.content,
      answer: answer?.content || "",
      questionIndex: pairs.length + 1,
    });
  });

  return pairs;
}

function createBrowserChecks(): BrowserChecks {
  if (typeof window === "undefined") {
    return {
      online: true,
      secureContext: true,
      mediaDevices: true,
      fullscreen: true,
      speechSynthesis: true,
      speechRecognition: true,
    };
  }

  const speechWindow = window as Window & {
    SpeechRecognition?: new () => SpeechRecognitionLike;
    webkitSpeechRecognition?: new () => SpeechRecognitionLike;
  };

  return {
    online: navigator.onLine,
    secureContext: window.isSecureContext,
    mediaDevices: Boolean(navigator.mediaDevices?.getUserMedia),
    fullscreen: Boolean(document.fullscreenEnabled),
    speechSynthesis: Boolean(window.speechSynthesis),
    speechRecognition: Boolean(speechWindow.SpeechRecognition || speechWindow.webkitSpeechRecognition),
  };
}

function useBrowserChecks() {
  const [checks, setChecks] = useState<BrowserChecks>(createBrowserChecks());

  useEffect(() => {
    const update = () => setChecks(createBrowserChecks());
    update();
    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    return () => {
      window.removeEventListener("online", update);
      window.removeEventListener("offline", update);
    };
  }, []);

  return checks;
}

async function loadPyodideRuntime() {
  if (!window.loadPyodide) {
    await new Promise<void>((resolve, reject) => {
      const existing = document.querySelector('script[data-pyodide="true"]');
      if (existing) {
        existing.addEventListener("load", () => resolve(), { once: true });
        existing.addEventListener("error", () => reject(new Error("Failed to load Python sandbox.")), { once: true });
        return;
      }

      const script = document.createElement("script");
      script.dataset.pyodide = "true";
      script.src = "https://cdn.jsdelivr.net/pyodide/v0.26.2/full/pyodide.js";
      script.async = true;
      script.onload = () => resolve();
      script.onerror = () => reject(new Error("Failed to load Python sandbox."));
      document.head.appendChild(script);
    });
  }

  const loadPyodide = window.loadPyodide;
  if (!loadPyodide) {
    throw new Error("Failed to load Python sandbox.");
  }

  return loadPyodide({ indexURL: "https://cdn.jsdelivr.net/pyodide/v0.26.2/full/" });
}

export default function LiveInterview() {
  const router = useRouter();
  const pathname = usePathname();
  const id = pathname.split("/").filter(Boolean).at(-2) || "";

  const [interview, setInterview] = useState<InterviewDetail | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [phase, setPhase] = useState<"loading" | "preflight" | "active" | "ending">("loading");
  const [inputText, setInputText] = useState("");
  const [codeLanguage, setCodeLanguage] = useState<CodeLanguage>("javascript");
  const [code, setCode] = useState(CODE_STARTERS.javascript);
  const [stdinValue, setStdinValue] = useState("sample input");
  const [runLog, setRunLog] = useState<string[]>(["Code runner ready."]);
  const [isRunningCode, setIsRunningCode] = useState(false);
  const [isStarting, setIsStarting] = useState(false);
  const [isSendingAnswer, setIsSendingAnswer] = useState(false);
  const [isEnding, setIsEnding] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [voiceEnabled, setVoiceEnabled] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [rulesAccepted, setRulesAccepted] = useState(false);
  const [cameraStatus, setCameraStatus] = useState<"idle" | "checking" | "ready" | "error">("idle");
  const [micStatus, setMicStatus] = useState<"idle" | "checking" | "ready" | "error">("idle");
  const [warningText, setWarningText] = useState("");
  const [violationCount, setViolationCount] = useState(0);
  const [now, setNow] = useState(0);
  const [runnerReady, setRunnerReady] = useState(false);
  const [sessionStartedAt, setSessionStartedAt] = useState<number | null>(null);

  const containerRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const cameraStreamRef = useRef<MediaStream | null>(null);
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const jsRunnerRef = useRef<HTMLIFrameElement | null>(null);
  const pyodideRef = useRef<PyodideRuntime | null>(null);
  const lastSpokenQuestionRef = useRef("");
  const activeSessionRef = useRef(false);
  const endedRef = useRef(false);
  const lastActivityRef = useRef(0);
  const idleViolationRef = useRef(false);
  const violationCountRef = useRef(0);
  const codingDraftLoadedRef = useRef(false);
  const runCodeRef = useRef<() => void>(() => {});
  const submitAnswerRef = useRef<() => void>(() => {});
  const browserChecks = useBrowserChecks();
  const draftStorageKey = `spip:interview:${id}:coding-draft`;

  const meta = parseInterviewBrief(interview?.job_description, interview?.type, interview?.title);
  const displayTitle = getInterviewDisplayTitle(interview?.job_description, interview?.type, interview?.title);
  const questionPairs = buildQuestionPairs(messages);
  const currentQuestion = [...messages].reverse().find((message) => message.role === "ai")?.content || "";
  const currentQuestionNumber = Math.max(1, questionPairs.length || (currentQuestion ? 1 : 0));
  const progress = Math.min((questionPairs.length / Math.max(meta.questionTarget, 1)) * 100, 100);
  const elapsedSeconds = sessionStartedAt ? Math.floor((now - sessionStartedAt) / 1000) : 0;
  const timeRemaining = Math.max(meta.durationMinutes * 60 - elapsedSeconds, 0);
  const isCoding = meta.mode === "coding";
  const canUseVoice = browserChecks.speechRecognition && (meta.mode === "hr" || meta.mode === "behavioral");
  const canStart =
    rulesAccepted &&
    browserChecks.online &&
    browserChecks.secureContext &&
    browserChecks.mediaDevices &&
    browserChecks.fullscreen &&
    cameraStatus === "ready" &&
    micStatus === "ready" &&
    !isStarting;

  const speak = useCallback((text: string) => {
    if (!voiceEnabled || !browserChecks.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    const voices = window.speechSynthesis.getVoices();
    const preferred = voices.find((voice) => voice.lang.includes("en") && voice.name.toLowerCase().includes("google")) || voices[0];
    if (preferred) {
      utterance.voice = preferred;
    }
    utterance.rate = 1;
    utterance.pitch = 1;
    window.speechSynthesis.speak(utterance);
  }, [browserChecks.speechSynthesis, voiceEnabled]);

  const clearCodingDraft = useCallback(() => {
    try {
      window.localStorage.removeItem(draftStorageKey);
    } catch (error) {
      console.error(error);
    }
  }, [draftStorageKey]);

  const refreshInterview = useCallback(async () => {
    const response = await api.get<InterviewDetail>(`/interviews/${id}`);
    setInterview(response.data);
    setMessages(response.data.messages?.filter((message) => message.role !== "system") || []);
    const count = response.data.lock_violations?.length || 0;
    setViolationCount(count);
    violationCountRef.current = count;
    const nextVoice = parseInterviewBrief(response.data.job_description, response.data.type, response.data.title).mode;
    setVoiceEnabled(nextVoice === "hr" || nextVoice === "behavioral");
    const startedAt = response.data.status === "in_progress" ? new Date(response.data.start_time).getTime() : null;
    setSessionStartedAt(startedAt);
    lastActivityRef.current = startedAt || Date.now();
    setPhase(response.data.status === "completed" ? "ending" : response.data.status === "in_progress" ? "active" : "preflight");

    const nextMeta = parseInterviewBrief(response.data.job_description, response.data.type, response.data.title);
    if (nextMeta.mode === "coding" && !codingDraftLoadedRef.current) {
      codingDraftLoadedRef.current = true;
      try {
        const raw = window.localStorage.getItem(draftStorageKey);
        if (raw) {
          const draft = JSON.parse(raw) as Partial<{ code: string; codeLanguage: CodeLanguage; stdinValue: string }>;
          if (draft.codeLanguage && draft.codeLanguage !== codeLanguage) {
            setCodeLanguage(draft.codeLanguage);
          }
          if (typeof draft.code === "string" && draft.code.trim()) {
            setCode(draft.code);
          }
          if (typeof draft.stdinValue === "string") {
            setStdinValue(draft.stdinValue);
          }
          setRunLog((current) => (current.length === 1 && current[0] === "Code runner ready." ? ["Draft restored from this browser."] : current));
        }
      } catch (error) {
        console.error(error);
      }
    }

    if (response.data.status === "completed") {
      clearCodingDraft();
      router.replace(`/dashboard/interviews/${id}/result`);
    }
  }, [clearCodingDraft, codeLanguage, draftStorageKey, id, router]);

  const finishInterview = useCallback(async (force = false) => {
    if (endedRef.current || isEnding) return;
    if (!force && !window.confirm("Are you sure you want to end the interview?")) return;

    endedRef.current = true;
    activeSessionRef.current = false;
    setPhase("ending");
    setIsEnding(true);
    window.speechSynthesis?.cancel?.();

    try {
      await api.post(`/interviews/${id}/end`);
      clearCodingDraft();
      router.push(`/dashboard/interviews/${id}/result`);
    } catch (error) {
      console.error(error);
      endedRef.current = false;
      activeSessionRef.current = true;
      setPhase("active");
      setIsEnding(false);
    }
  }, [clearCodingDraft, id, isEnding, router]);

  const recordViolation = useCallback(async (type: string, details: string) => {
    if (!activeSessionRef.current || endedRef.current) return;

    const nextCount = violationCountRef.current + 1;
    violationCountRef.current = nextCount;
    setViolationCount(nextCount);
    setWarningText(details);

    try {
      await api.post(`/interviews/${id}/lock-violations`, {
        violation_type: type,
        details,
      });
    } catch (error) {
      console.error(error);
    }

    if (nextCount >= 5) {
      setWarningText("Interview terminated after repeated proctoring violations.");
      void finishInterview(true);
    } else if (nextCount >= 3) {
      setWarningText("Warning: proctoring rules have been breached three times.");
    }
  }, [finishInterview, id]);

  const startInterview = useCallback(async () => {
    if (!interview) return;
    setIsStarting(true);
    try {
      if (!document.fullscreenElement && containerRef.current?.requestFullscreen) {
        await containerRef.current.requestFullscreen();
      }
      setIsFullscreen(Boolean(document.fullscreenElement));

      if (interview.status === "pending") {
        const response = await api.post(`/interviews/${id}/start`);
        const firstQuestion: Message = response.data;
        setMessages([firstQuestion]);
        setInterview((current) => (current ? { ...current, status: "in_progress" } : current));
        const startedAt = Date.now();
        setSessionStartedAt(startedAt);
        lastActivityRef.current = startedAt;
        speak(firstQuestion.content);
      } else {
        const startedAt = sessionStartedAt || Date.now();
        setSessionStartedAt(startedAt);
        lastActivityRef.current = startedAt;
      }

      activeSessionRef.current = true;
      endedRef.current = false;
      setPhase("active");
      setWarningText("");
    } catch (error) {
      console.error(error);
      setWarningText("Could not enter fullscreen or start the interview.");
    } finally {
      setIsStarting(false);
    }
  }, [id, interview, sessionStartedAt, speak]);

  const submitAnswer = useCallback(async (value?: string) => {
    if (!interview || isSendingAnswer || isEnding || phase !== "active") return;

    const answer = isCoding ? code.trim() : (value ?? inputText).trim();
    if (!answer) return;

    setIsSendingAnswer(true);
    setWarningText("");

    setMessages((current) => [...current, { role: "user", content: answer }]);
    if (!isCoding) {
      setInputText("");
    } else {
      setRunLog((current) => [...current, "Submitted to the interviewer for evaluation."]);
    }

    try {
      const response = await api.post<Message>(`/interviews/${id}/message`, { content: answer });
      setMessages((current) => [...current, response.data]);
      speak(response.data.content);
      if (isCoding) {
        setRunLog((current) => [...current, "AI reviewer: new question or follow-up received."]);
      }
    } catch (error) {
      console.error(error);
      setWarningText("The interviewer could not respond right now.");
    } finally {
      setIsSendingAnswer(false);
    }
  }, [code, id, inputText, interview, isCoding, isEnding, isSendingAnswer, phase, speak]);

  const runCode = useCallback(async () => {
    if (!isCoding) return;
    if (!code.trim()) return;

    setIsRunningCode(true);
    setRunLog(["Running code..."]);
    try {
      if (codeLanguage === "javascript") {
        const runner = jsRunnerRef.current?.contentWindow;
        if (!runnerReady || !runner) {
          setRunLog(["JavaScript runner is still loading."]);
          return;
        }
        runner.postMessage(
          {
            source: "interview-host",
            code,
            stdin: stdinValue,
          },
          "*"
        );
        return;
      }

      if (codeLanguage === "python") {
        const pyodide = pyodideRef.current || (await loadPyodideRuntime());
        pyodideRef.current = pyodide;
        const output: string[] = [];
        pyodide.setStdout({ batched: (text: string) => output.push(text) });
        pyodide.setStderr({ batched: (text: string) => output.push(text) });
        pyodide.globals.set("stdin_value", stdinValue);
        const result = await pyodide.runPythonAsync(code);
        if (result !== undefined) {
          output.push(String(result));
        }
        setRunLog(output.length ? output : ["Execution complete."]);
        return;
      }

      const response = await api.post<CodeRunResult>("/interviews/code-run", {
        language: codeLanguage,
        code,
        stdin: stdinValue,
      });
      const payload = response.data;
      const stdout = payload.stdout.trim();
      const stderr = payload.stderr.trim();
      const compilerOutput = payload.compiler_output.trim();
      const compilerError = payload.compiler_error.trim();
      const message = payload.message?.trim();
      setRunLog([stdout || compilerOutput || message || "Execution complete.", stderr || compilerError].filter(Boolean));
    } catch (error) {
      console.error(error);
      setRunLog([error instanceof Error ? error.message : "Code runner failed."]);
    } finally {
      setIsRunningCode(false);
    }
  }, [code, codeLanguage, isCoding, runnerReady, stdinValue]);

  const resetCode = useCallback(() => {
    setCode(CODE_STARTERS[codeLanguage]);
    setStdinValue("sample input");
    setRunLog(["Code runner reset."]);
  }, [codeLanguage]);

  useEffect(() => {
    runCodeRef.current = () => {
      void runCode();
    };
  }, [runCode]);

  useEffect(() => {
    submitAnswerRef.current = () => {
      void submitAnswer();
    };
  }, [submitAnswer]);

  useEffect(() => {
    if (!isCoding || typeof window === "undefined") return;
    try {
      window.localStorage.setItem(
        draftStorageKey,
        JSON.stringify({
          code,
          codeLanguage,
          stdinValue,
        })
      );
    } catch (error) {
      console.error(error);
    }
  }, [code, codeLanguage, draftStorageKey, isCoding, stdinValue]);

  useEffect(() => {
    if (!isCoding) return;
    const handleShortcut = (event: KeyboardEvent) => {
      if (!(event.ctrlKey || event.metaKey)) return;
      if (event.key === "Enter" && event.shiftKey) {
        event.preventDefault();
        submitAnswerRef.current();
      } else if (event.key === "Enter") {
        event.preventDefault();
        runCodeRef.current();
      } else if (event.key.toLowerCase() === "r") {
        event.preventDefault();
        resetCode();
      }
    };

    window.addEventListener("keydown", handleShortcut);
    return () => window.removeEventListener("keydown", handleShortcut);
  }, [isCoding, resetCode]);

  const toggleRecording = useCallback(() => {
    if (!canUseVoice) {
      window.alert("Voice input is not supported in this browser.");
      return;
    }

    if (!recognitionRef.current) {
      window.alert("Speech recognition is not available in this browser.");
      return;
    }

    const recognition = recognitionRef.current;
    if (isRecording) {
      recognition.stop();
      setIsRecording(false);
      return;
    }

    window.speechSynthesis.cancel();
    recognition.start();
    setIsRecording(true);
  }, [canUseVoice, isRecording]);

  const testCamera = useCallback(async () => {
    setCameraStatus("checking");
    try {
      cameraStreamRef.current?.getTracks().forEach((track) => track.stop());
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
      cameraStreamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      setCameraStatus("ready");
    } catch (error) {
      console.error(error);
      setCameraStatus("error");
    }
  }, []);

  const testMic = useCallback(async () => {
    setMicStatus("checking");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
      stream.getTracks().forEach((track) => track.stop());
      setMicStatus("ready");
    } catch (error) {
      console.error(error);
      setMicStatus("error");
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void refreshInterview();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [refreshInterview]);

  useEffect(() => {
    const speechWindow = window as Window & {
      SpeechRecognition?: new () => SpeechRecognitionLike;
      webkitSpeechRecognition?: new () => SpeechRecognitionLike;
    };
    const SpeechRecognition = speechWindow.SpeechRecognition || speechWindow.webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.onresult = (event: SpeechRecognitionEventLike) => {
        const text = event.results[0][0].transcript;
        setInputText(text);
        void submitAnswer(text);
      };
      recognition.onend = () => {
        setIsRecording(false);
      };
      recognitionRef.current = recognition;
    }
  }, [submitAnswer]);

  useEffect(() => {
    const onMessage = (event: MessageEvent) => {
      if (event.data?.source !== "interview-js-runner") return;
      if (event.source !== jsRunnerRef.current?.contentWindow) return;

      if (event.data.type === "log") {
        setRunLog((current) => [...current, event.data.value]);
      }
      if (event.data.type === "status") {
        setRunLog((current) => [...current, event.data.value]);
      }
      if (event.data.type === "result") {
        setRunLog((current) => [...current, event.data.value]);
      }
      if (event.data.type === "error") {
        setRunLog((current) => [...current, `Error: ${event.data.value}`]);
      }
    };

    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, []);

  useEffect(() => {
    if (phase !== "active") return;

    const markActivity = () => {
      lastActivityRef.current = Date.now();
      idleViolationRef.current = false;
    };

    const handleVisibilityChange = () => {
      if (document.visibilityState === "hidden") {
        void recordViolation("tab_switch", "Tab switch detected during interview.");
      }
    };

    const handleBlur = () => {
      void recordViolation("window_blur", "Window lost focus during interview.");
    };

    const handleFullscreenChange = () => {
      setIsFullscreen(Boolean(document.fullscreenElement));
      if (!document.fullscreenElement) {
        void recordViolation("fullscreen_exit", "Exited fullscreen during interview.");
      }
    };

    const handleContextMenu = (event: MouseEvent) => {
      event.preventDefault();
      void recordViolation("right_click", "Right-click detected during interview.");
    };

    const handlePaste = () => {
      void recordViolation("paste", "Paste action detected during interview.");
    };

    const handleCopy = () => {
      void recordViolation("copy", "Copy action detected during interview.");
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      markActivity();
      const key = event.key.toLowerCase();
      const devtoolsShortcut =
        (event.ctrlKey || event.metaKey) && (key === "u" || key === "r" || (event.shiftKey && ["i", "j", "c"].includes(key)));
      if (key === "f12" || devtoolsShortcut) {
        event.preventDefault();
        void recordViolation("developer_tools", "Developer tools shortcut detected during interview.");
      }
    };

  const idleTimer = window.setInterval(() => {
      const nowTs = Date.now();
      const idleFor = nowTs - lastActivityRef.current;
      if (idleFor > 90_000 && !idleViolationRef.current) {
        idleViolationRef.current = true;
        void recordViolation("idle", "No keyboard or mouse activity detected.");
        lastActivityRef.current = nowTs;
      }
      setNow(nowTs);
    }, 1000);

    const monitorTimer = window.setTimeout(() => {
      if (window.screen.width < window.outerWidth || window.screenLeft !== 0) {
        void recordViolation("multi_monitor_warning", "Potential multi-monitor setup detected.");
      }
    }, 1000);

    document.addEventListener("visibilitychange", handleVisibilityChange);
    window.addEventListener("blur", handleBlur);
    document.addEventListener("fullscreenchange", handleFullscreenChange);
    document.addEventListener("contextmenu", handleContextMenu);
    document.addEventListener("paste", handlePaste);
    document.addEventListener("copy", handleCopy);
    document.addEventListener("keydown", handleKeyDown);
    document.addEventListener("mousemove", markActivity);
    document.addEventListener("mousedown", markActivity);
    document.addEventListener("scroll", markActivity, true);
    document.addEventListener("touchstart", markActivity);

    return () => {
      window.clearInterval(idleTimer);
      window.clearTimeout(monitorTimer);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      window.removeEventListener("blur", handleBlur);
      document.removeEventListener("fullscreenchange", handleFullscreenChange);
      document.removeEventListener("contextmenu", handleContextMenu);
      document.removeEventListener("paste", handlePaste);
      document.removeEventListener("copy", handleCopy);
      document.removeEventListener("keydown", handleKeyDown);
      document.removeEventListener("mousemove", markActivity);
      document.removeEventListener("mousedown", markActivity);
      document.removeEventListener("scroll", markActivity, true);
      document.removeEventListener("touchstart", markActivity);
    };
  }, [phase, recordViolation]);

  useEffect(() => {
    if (phase !== "active" || !currentQuestion) return;
    if (!voiceEnabled) return;
    if (lastSpokenQuestionRef.current === currentQuestion) return;
    lastSpokenQuestionRef.current = currentQuestion;
    speak(currentQuestion);
  }, [currentQuestion, phase, speak, voiceEnabled]);

  useEffect(() => {
    if (!interview) return;
    if (interview.status === "completed") {
      router.replace(`/dashboard/interviews/${id}/result`);
    }
  }, [id, interview, router]);

  useEffect(() => {
    if (!cameraStreamRef.current || !videoRef.current) return;
    videoRef.current.srcObject = cameraStreamRef.current;
  }, [cameraStatus, phase]);

  useEffect(() => {
    return () => {
      cameraStreamRef.current?.getTracks().forEach((track) => track.stop());
      window.speechSynthesis?.cancel?.();
    };
  }, []);

  useEffect(() => {
    if (phase !== "active" || !sessionStartedAt) return;
    const deadline = sessionStartedAt + meta.durationMinutes * 60 * 1000;
    const delay = Math.max(deadline - Date.now(), 0);
    const timeout = window.setTimeout(() => {
      void finishInterview(true);
    }, delay);
    return () => window.clearTimeout(timeout);
  }, [finishInterview, meta.durationMinutes, phase, sessionStartedAt]);

  if (!interview || phase === "loading") {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Loader2 className="h-12 w-12 animate-spin text-purple-400" />
      </div>
    );
  }

  if (phase === "preflight" && interview.status === "pending") {
    return (
      <div ref={containerRef} className="min-h-screen bg-[#0b0b10] px-6 py-8 text-white">
        <div className="mx-auto grid max-w-7xl gap-6 xl:grid-cols-[1.1fr_0.9fr]">
          <section className="space-y-6 rounded-3xl border border-white/10 bg-[#111118] p-6">
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2 text-xs uppercase tracking-[0.3em] text-gray-500">
                <ShieldCheck className="h-4 w-4 text-emerald-400" />
                Pre-interview check
              </div>
              <h1 className="text-3xl font-bold text-white">{displayTitle}</h1>
              <p className="max-w-3xl text-gray-400">
                Run the camera and microphone checks, confirm the rules, and start the interview in fullscreen.
              </p>
            </div>

            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                <div className="text-xs uppercase tracking-[0.2em] text-gray-500">Company</div>
                <div className="mt-2 text-lg font-semibold text-white">{meta.company}</div>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                <div className="text-xs uppercase tracking-[0.2em] text-gray-500">Difficulty</div>
                <div className="mt-2 text-lg font-semibold text-white">{meta.difficulty}</div>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                <div className="text-xs uppercase tracking-[0.2em] text-gray-500">Duration</div>
                <div className="mt-2 text-lg font-semibold text-white">{meta.durationMinutes} minutes</div>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                <div className="text-xs uppercase tracking-[0.2em] text-gray-500">Question target</div>
                <div className="mt-2 text-lg font-semibold text-white">{meta.questionTarget}</div>
              </div>
            </div>

            <div className="rounded-3xl border border-white/10 bg-black/20 p-5">
              <div className="flex items-center gap-2 text-sm font-medium text-gray-300">
                <Video className="h-4 w-4 text-sky-400" />
                Camera preview
              </div>
              <div className="mt-4 overflow-hidden rounded-2xl border border-white/10 bg-black">
                <video ref={videoRef} autoPlay muted playsInline className="h-64 w-full object-cover" />
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <button
                type="button"
                onClick={testCamera}
                className="rounded-2xl border border-white/10 bg-white/[0.03] px-5 py-4 text-left transition-colors hover:border-purple-400/40 hover:bg-purple-500/10"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 font-medium text-white">
                    <Video className="h-4 w-4 text-sky-400" />
                    Test camera
                  </div>
                  {cameraStatus === "ready" ? <ShieldCheck className="h-4 w-4 text-emerald-400" /> : <ShieldAlert className="h-4 w-4 text-gray-500" />}
                </div>
                <p className="mt-2 text-sm text-gray-400">
                  {cameraStatus === "ready" ? "Camera is live." : cameraStatus === "checking" ? "Requesting camera access..." : cameraStatus === "error" ? "Camera test failed." : "Camera not tested yet."}
                </p>
              </button>

              <button
                type="button"
                onClick={testMic}
                className="rounded-2xl border border-white/10 bg-white/[0.03] px-5 py-4 text-left transition-colors hover:border-purple-400/40 hover:bg-purple-500/10"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 font-medium text-white">
                    <Mic className="h-4 w-4 text-emerald-400" />
                    Test microphone
                  </div>
                  {micStatus === "ready" ? <ShieldCheck className="h-4 w-4 text-emerald-400" /> : <ShieldAlert className="h-4 w-4 text-gray-500" />}
                </div>
                <p className="mt-2 text-sm text-gray-400">
                  {micStatus === "ready" ? "Microphone permission is ready." : micStatus === "checking" ? "Requesting microphone access..." : micStatus === "error" ? "Microphone test failed." : "Microphone not tested yet."}
                </p>
              </button>
            </div>

            <div className="rounded-3xl border border-white/10 bg-white/[0.03] p-5">
              <div className="flex items-center gap-2 text-sm font-medium text-gray-300">
                <Sparkles className="h-4 w-4 text-purple-300" />
                Rules
              </div>
              <ul className="mt-4 space-y-2 text-sm text-gray-400">
                <li>Stay in fullscreen once the interview begins.</li>
                <li>Keep your camera and microphone checked before starting.</li>
                <li>No copy/paste, right-click, tab switching, or devtools.</li>
                <li>The interview will warn on three violations and end on five.</li>
              </ul>
              <label className="mt-5 flex items-center gap-3 rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-gray-300">
                <input type="checkbox" checked={rulesAccepted} onChange={(event) => setRulesAccepted(event.target.checked)} />
                I understand the proctoring rules and the interview flow.
              </label>
            </div>

              <button
                type="button"
                onClick={() => void startInterview()}
                disabled={!canStart}
                className="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-purple-600 px-5 py-4 font-semibold text-white transition-colors hover:bg-purple-500 disabled:cursor-not-allowed disabled:bg-purple-600/50"
              >
                <Play className="h-4 w-4" />
                Enter Fullscreen to Start
              </button>

            {!browserChecks.online || !browserChecks.secureContext || !browserChecks.mediaDevices || !browserChecks.fullscreen ? (
              <div className="rounded-2xl border border-amber-500/20 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
                Browser checks are incomplete. Online, secure context, media devices, and fullscreen support are required.
              </div>
            ) : null}
          </section>

          <aside className="space-y-6 rounded-3xl border border-white/10 bg-[#111118] p-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-semibold text-white">Browser status</h2>
                <p className="text-sm text-gray-400">Live checks before the interview starts.</p>
              </div>
              <div className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-xs text-gray-300">
                {meta.mode.replaceAll("_", " ").toUpperCase()}
              </div>
            </div>

            <div className="grid gap-3">
      <StatusRow label="Internet" ok={browserChecks.online} okText="Connected" badText="Offline" icon={browserChecks.online ? Wifi : WifiOff} />
              <StatusRow label="Secure context" ok={browserChecks.secureContext} okText="HTTPS/local secure" badText="Not secure" icon={ShieldCheck} />
              <StatusRow label="Media devices" ok={browserChecks.mediaDevices} okText="Available" badText="Unavailable" icon={Video} />
              <StatusRow label="Fullscreen" ok={browserChecks.fullscreen} okText="Supported" badText="Unavailable" icon={Maximize} />
              <StatusRow label="Speech support" ok={browserChecks.speechRecognition || browserChecks.speechSynthesis} okText="Supported" badText="Limited" icon={Mic} />
            </div>

            <div className="rounded-3xl border border-white/10 bg-black/20 p-5">
              <div className="flex items-center gap-2 text-sm font-medium text-gray-300">
                <EyeOff className="h-4 w-4 text-gray-500" />
                Interview brief
              </div>
              <div className="mt-4 space-y-3 text-sm text-gray-400">
                <p>Target focus: {meta.focus}</p>
                <p>Prompt mode: {meta.label}</p>
                <p>Warnings: {violationCount}</p>
                <p>Current time in session: {formatDuration(elapsedSeconds)}</p>
              </div>
            </div>

            <div className="rounded-3xl border border-white/10 bg-white/[0.03] p-5">
              <div className="flex items-center gap-2 text-sm font-medium text-gray-300">
                <Timer className="h-4 w-4 text-sky-400" />
                Session timer
              </div>
              <div className="mt-3 text-3xl font-semibold text-white">{formatDuration(timeRemaining)}</div>
              <p className="mt-2 text-sm text-gray-400">The timer starts when the interview begins.</p>
            </div>

            {warningText ? (
              <div className="rounded-3xl border border-amber-500/20 bg-amber-500/10 p-5 text-sm text-amber-100">
                {warningText}
              </div>
            ) : null}
          </aside>
        </div>
      </div>
    );
  }

  return (
    <div ref={containerRef} className="flex min-h-screen flex-col bg-[#0b0b10] text-white overflow-hidden">
      <iframe ref={jsRunnerRef} title="JavaScript runner" sandbox="allow-scripts" srcDoc={JS_RUNNER_SRC} onLoad={() => setRunnerReady(true)} className="hidden" />

      <main className="flex-1 p-4 grid gap-4 lg:grid-cols-[1fr_320px] xl:grid-cols-[1fr_400px]">
        <div className="relative rounded-3xl border border-white/10 bg-[#111118] overflow-hidden flex flex-col items-center justify-center">
          <div className="relative flex items-center justify-center">
            <div className={`absolute h-48 w-48 rounded-full bg-purple-500/20 blur-xl ${isSendingAnswer ? "animate-pulse" : ""}`} />
            <div className="relative flex h-32 w-32 items-center justify-center rounded-full border border-purple-500/30 bg-purple-500/10 backdrop-blur-md">
              <Brain className="h-12 w-12 text-purple-300" />
            </div>
          </div>
          
          <div className="absolute bottom-6 left-6 right-6 text-center">
             <div className="bg-black/60 backdrop-blur-md border border-white/10 rounded-2xl p-4 inline-block max-w-2xl mx-auto shadow-2xl">
                <p className="text-lg leading-relaxed text-white whitespace-pre-wrap">
                  {currentQuestion || "Connecting..."}
                </p>
             </div>
          </div>

          <div className="absolute top-6 left-6 flex flex-wrap gap-2">
            <div className="rounded-full bg-black/60 backdrop-blur-md border border-white/10 px-3 py-1.5 text-xs text-gray-300">
              {meta.company} - {meta.difficulty}
            </div>
            <div className="rounded-full bg-purple-500/20 border border-purple-500/30 px-3 py-1.5 text-xs text-purple-300">
              AI Interviewer
            </div>
          </div>
          
          {warningText && (
            <div className="absolute top-6 right-6 rounded-2xl bg-amber-500/10 border border-amber-500/20 px-4 py-2 text-xs text-amber-100 max-w-xs">
              {warningText}
            </div>
          )}
        </div>

        <div className="flex flex-col gap-4 h-full">
           <div className="relative h-64 rounded-3xl border border-white/10 bg-black overflow-hidden shrink-0">
             <video ref={videoRef} autoPlay muted playsInline className="h-full w-full object-cover" />
             <div className="absolute bottom-3 left-3 rounded-full bg-black/60 backdrop-blur-md border border-white/10 px-3 py-1 text-xs text-white">
               You
             </div>
             {isRecording && (
                <div className="absolute top-3 right-3 flex items-center gap-2 rounded-full bg-red-500/20 border border-red-500/30 px-2 py-1 text-xs text-red-300">
                  <div className="h-2 w-2 rounded-full bg-red-500 animate-pulse" />
                  Recording
                </div>
             )}
           </div>

           <div className="flex-1 rounded-3xl border border-white/10 bg-[#111118] p-5 flex flex-col min-h-0">
              {isCoding ? (
                 <div className="flex-1 flex flex-col min-h-0">
                    <div className="flex justify-between items-center mb-3">
                       <select value={codeLanguage} onChange={(e) => {
                          const nextLang = e.target.value as CodeLanguage;
                          setCodeLanguage(nextLang);
                          setCode(CODE_STARTERS[nextLang]);
                       }} className="bg-black/40 border border-white/10 rounded-full px-3 py-1 text-xs text-gray-300 outline-none">
                          <option value="javascript">JS</option>
                          <option value="python">Python</option>
                          <option value="java">Java</option>
                          <option value="cpp">C++</option>
                       </select>
                       <div className="flex items-center gap-2">
                          <button type="button" onClick={runCode} disabled={isRunningCode} className="text-xs bg-white/5 border border-white/10 rounded-full px-3 py-1 hover:bg-white/10 flex items-center gap-1 disabled:opacity-50">
                             {isRunningCode ? <Loader2 className="h-3 w-3 animate-spin" /> : <Play className="h-3 w-3" />}
                             Run Code
                          </button>
                       </div>
                    </div>
                    <div className="flex-1 rounded-2xl border border-white/10 overflow-hidden bg-[#07070a] min-h-0">
                        <MonacoEditor
                          height="100%"
                          language={codeLanguage === "cpp" ? "cpp" : codeLanguage}
                          theme="vs-dark"
                          value={code}
                          onChange={(val) => setCode(val || "")}
                          options={{ minimap: { enabled: false }, fontSize: 13, wordWrap: "on" }}
                        />
                    </div>
                    {runLog.length > 0 && (
                      <div className="h-24 mt-3 rounded-xl border border-white/10 bg-[#07070a] p-2 overflow-y-auto font-mono text-[10px] text-sky-100 whitespace-pre-wrap">
                         {runLog.join("\n")}
                      </div>
                    )}
                 </div>
              ) : (
                 <form onSubmit={(e) => { e.preventDefault(); void submitAnswer(); }} className="flex-1 flex flex-col min-h-0">
                    <div className="text-sm font-medium text-gray-400 mb-2 flex justify-between items-center">
                       Text Fallback
                       <span className="text-xs text-gray-500">Press Enter to submit</span>
                    </div>
                    <textarea 
                       value={inputText}
                       onChange={e => setInputText(e.target.value)}
                       onKeyDown={e => {
                          if (e.key === 'Enter' && !e.shiftKey) {
                             e.preventDefault();
                             void submitAnswer();
                          }
                       }}
                       placeholder="Type your answer if voice is unavailable..."
                       className="flex-1 resize-none rounded-2xl border border-white/10 bg-black/20 p-4 text-sm leading-relaxed text-gray-300 outline-none focus:border-purple-500/30 transition-colors"
                    />
                 </form>
              )}
           </div>
        </div>
      </main>

      <footer className="border-t border-white/10 bg-[#07070a] px-6 py-4 flex items-center justify-between">
         <div className="flex items-center gap-4">
           <div className="text-xl font-bold text-white tracking-widest">{formatDuration(elapsedSeconds)}</div>
           <div className="h-4 w-px bg-white/20" />
           <div className="text-sm text-gray-400">Q {currentQuestionNumber}/{meta.questionTarget}</div>
           {violationCount > 0 && (
             <div className="ml-4 rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-1 text-xs text-amber-300">
               {violationCount} warning{violationCount > 1 ? 's' : ''}
             </div>
           )}
         </div>

         <div className="flex items-center gap-4">
            {canUseVoice && (
               <button type="button" onClick={toggleRecording} className={`flex h-14 w-14 items-center justify-center rounded-full transition-all ${isRecording ? "bg-red-500 text-white hover:bg-red-600 shadow-[0_0_20px_rgba(239,68,68,0.4)]" : "bg-white/10 text-gray-300 hover:bg-white/20"}`}>
                 {isRecording ? <Mic className="h-6 w-6" /> : <MicOff className="h-6 w-6" />}
               </button>
            )}

            <button type="button" onClick={() => void submitAnswer()} disabled={isSendingAnswer || (isCoding ? !code.trim() : !inputText.trim())} className="flex h-14 px-8 items-center justify-center gap-2 rounded-full bg-purple-600 text-white font-medium transition-all hover:bg-purple-500 disabled:opacity-50 disabled:cursor-not-allowed">
               {isSendingAnswer ? <Loader2 className="h-5 w-5 animate-spin" /> : <Send className="h-5 w-5" />}
               Submit Answer
            </button>
         </div>

         <div className="flex items-center gap-3">
            <button type="button" onClick={() => void finishInterview()} className="flex items-center justify-center h-12 w-12 rounded-full bg-white/5 border border-white/10 text-red-400 hover:bg-red-500/10 hover:border-red-500/30 transition-all" title="End Interview">
               <StopCircle className="h-5 w-5" />
            </button>
            <button type="button" onClick={() => { if (!document.fullscreenElement) { void containerRef.current?.requestFullscreen?.(); } else { void document.exitFullscreen(); } }} className="flex items-center justify-center h-12 w-12 rounded-full bg-white/5 border border-white/10 text-gray-400 hover:bg-white/10 transition-all" title="Toggle Fullscreen">
               {isFullscreen ? <Minimize className="h-5 w-5" /> : <Maximize className="h-5 w-5" />}
            </button>
         </div>
      </footer>
    </div>
  );
}

function StatusRow({
  label,
  ok,
  okText,
  badText,
  icon: Icon,
}: {
  label: string;
  ok: boolean;
  okText: string;
  badText: string;
  icon: ComponentType<{ className?: string }>;
}) {
  return (
    <div className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3">
      <div className="flex items-center gap-2">
        <Icon className={`h-4 w-4 ${ok ? "text-emerald-400" : "text-gray-500"}`} />
        <span className="text-sm text-gray-300">{label}</span>
      </div>
      <span className={`text-sm ${ok ? "text-emerald-300" : "text-gray-500"}`}>{ok ? okText : badText}</span>
    </div>
  );
}

function Pill({ label }: { label: string }) {
  return <span className="rounded-full border border-white/10 bg-white/[0.03] px-3 py-1 text-xs text-gray-300">{label}</span>;
}

"use client";

import { useState, useEffect, useCallback } from "react";
import { Maximize2, ShieldAlert, Clock, ChevronRight, ChevronLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useProctoring } from "@/hooks/useProctoring";

import { useRouter } from "next/navigation";
import { use } from "react";
import api from "@/lib/api";

interface Question {
  id: number;
  type: string;
  content: string;
  options: string[];
}

interface Assessment {
  id: number;
  title: string;
  duration_minutes: number;
}

export default function AssessmentTestSandbox({ params }: { params: Promise<{ id: string }> }) {
  const router = useRouter();
  const { id } = use(params);
  
  const { tabSwitchCount, fullscreenViolations, isFullscreen, requestFullscreen } = useProctoring();
  const [currentQIndex, setCurrentQIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [timeLeft, setTimeLeft] = useState(0);
  
  const [questions, setQuestions] = useState<Question[]>([]);
  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [attemptId, setAttemptId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const startAssessment = useCallback(async () => {
    try {
      const res = await api.post<{ questions: Question[]; assessment: Assessment; attempt_id: number }>(`/assessments/${id}/start`);
      setQuestions(res.data.questions);
      setAssessment(res.data.assessment);
      setAttemptId(res.data.attempt_id);
      setTimeLeft(res.data.assessment.duration_minutes * 60);
    } catch (error) {
      console.error(error);
      alert("Failed to start assessment.");
    } finally {
      setIsLoading(false);
    }
  }, [id]);

  const submitAssessment = useCallback(async () => {
    if (isSubmitting || !attemptId) return;
    setIsSubmitting(true);
    
    const payload = {
      attempt_id: attemptId,
      answers: Object.entries(answers).map(([qId, ans]) => ({
        question_id: parseInt(qId),
        user_answer: ans,
        time_taken_seconds: 0
      })),
      tab_switch_count: tabSwitchCount,
      fullscreen_violations: fullscreenViolations
    };
    
    try {
      const res = await api.post("/assessments/submit", payload);
      // Store result in sessionStorage for the result page to read
      sessionStorage.setItem(`assessment_result_${id}`, JSON.stringify(res.data));
      
      // Exit fullscreen
      if (document.fullscreenElement) {
        document.exitFullscreen();
      }
      
      router.push(`/dashboard/assessments/${id}/result`);
    } catch (error) {
      console.error(error);
      alert("Failed to submit assessment.");
      setIsSubmitting(false);
    }
  }, [attemptId, answers, fullscreenViolations, id, isSubmitting, router, tabSwitchCount]);

  useEffect(() => {
    if (isFullscreen) {
      const timer = window.setTimeout(() => {
        void startAssessment();
      }, 0);
      return () => window.clearTimeout(timer);
    }
  }, [isFullscreen, startAssessment]);
  
  useEffect(() => {
    if (timeLeft > 0 && isFullscreen && !isSubmitting) {
      const timer = setInterval(() => {
        setTimeLeft((prev) => {
          if (prev <= 1) {
            clearInterval(timer);
            void submitAssessment();
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
      return () => clearInterval(timer);
    }
  }, [timeLeft, isFullscreen, isSubmitting, submitAssessment]);

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const handleSelectOption = (qId: number, option: string) => {
    setAnswers(prev => ({ ...prev, [qId]: option }));
  };

  if (!isFullscreen) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[70vh] text-center space-y-6">
        <div className="w-20 h-20 bg-red-50 rounded-full flex items-center justify-center">
          <ShieldAlert className="w-10 h-10 text-red-600" />
        </div>
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Proctored Assessment</h2>
          <p className="text-gray-500 mt-2 max-w-md mx-auto">
            This assessment requires fullscreen mode. Do not exit fullscreen or switch tabs during the test.
          </p>
        </div>
        <Button 
          onClick={requestFullscreen} 
          size="lg"
          className="bg-indigo-600 hover:bg-indigo-700 text-white"
        >
          <Maximize2 className="w-4 h-4 mr-2" /> Enter Fullscreen to Start
        </Button>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[70vh]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
        <p className="mt-4 text-gray-500 font-medium">Preparing your assessment...</p>
      </div>
    );
  }

  const currentQ = questions[currentQIndex];
  
  if (!currentQ) return <div className="p-8 text-center">No questions found.</div>;

  return (
    <div className="flex flex-col h-[calc(100vh-2rem)]">
      {/* Top Bar */}
      <div className="flex items-center justify-between bg-white border-b border-gray-200 px-6 py-4 mb-6 rounded-t-xl">
        <div>
          <h1 className="font-bold text-gray-900">{assessment?.title || "Assessment"}</h1>
          <div className="flex space-x-4 mt-1">
            <span className="text-xs font-medium text-red-600 flex items-center">
              <ShieldAlert className="w-3 h-3 mr-1" /> Proctored Mode Active
            </span>
            <span className="text-xs font-medium text-gray-500">
              Warnings: {tabSwitchCount}/3
            </span>
          </div>
        </div>
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2 bg-indigo-50 px-4 py-2 rounded-lg border border-indigo-100">
            <Clock className="w-4 h-4 text-indigo-600" />
            <span className="font-mono font-bold text-indigo-700 text-lg">
              {formatTime(timeLeft)}
            </span>
          </div>
          <Button 
            variant="destructive" 
            onClick={submitAssessment}
            disabled={isSubmitting}
          >
            {isSubmitting ? "Submitting..." : "Submit Test"}
          </Button>
        </div>
      </div>

      <div className="flex flex-1 gap-6 px-4 pb-4">
        {/* Question Area */}
        <div className="flex-1">
          <Card className="h-full border-gray-200 shadow-sm">
            <CardContent className="p-8">
              <div className="mb-6 pb-6 border-b border-gray-100">
                <span className="text-sm font-bold text-indigo-600 tracking-wider uppercase">
                  Question {currentQIndex + 1} of {questions.length}
                </span>
                <h2 className="text-xl font-medium text-gray-900 mt-4 leading-relaxed">
                  {currentQ.content}
                </h2>
              </div>
              
              <div className="space-y-4">
                {currentQ.options?.map((option, idx) => {
                  const isSelected = answers[currentQ.id] === option;
                  return (
                    <div 
                      key={idx}
                      onClick={() => handleSelectOption(currentQ.id, option)}
                      className={`p-4 rounded-xl border-2 cursor-pointer transition-all flex items-center ${
                        isSelected 
                          ? "border-indigo-600 bg-indigo-50/50" 
                          : "border-gray-200 hover:border-indigo-300 hover:bg-gray-50"
                      }`}
                    >
                      <div className={`w-5 h-5 rounded-full border flex items-center justify-center mr-3 ${
                        isSelected ? "border-indigo-600" : "border-gray-300"
                      }`}>
                        {isSelected && <div className="w-2.5 h-2.5 bg-indigo-600 rounded-full" />}
                      </div>
                      <span className={`font-medium ${isSelected ? "text-indigo-900" : "text-gray-700"}`}>
                        {option}
                      </span>
                    </div>
                  );
                })}
              </div>

              <div className="flex justify-between items-center mt-12 pt-6 border-t border-gray-100">
                <Button 
                  variant="outline" 
                  disabled={currentQIndex === 0}
                  onClick={() => setCurrentQIndex(prev => prev - 1)}
                >
                  <ChevronLeft className="w-4 h-4 mr-2" /> Previous
                </Button>
                <Button 
                  className="bg-indigo-600 hover:bg-indigo-700"
                  disabled={currentQIndex === questions.length - 1}
                  onClick={() => setCurrentQIndex(prev => prev + 1)}
                >
                  Next <ChevronRight className="w-4 h-4 ml-2" />
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Question Palette Sidebar */}
        <div className="w-72 hidden md:block">
          <Card className="h-full border-gray-200 shadow-sm">
            <CardContent className="p-4">
              <h3 className="font-bold text-gray-900 mb-4 text-sm uppercase tracking-wider">Question Palette</h3>
              <div className="grid grid-cols-4 gap-2">
                {questions.map((q, idx) => {
                  const isAnswered = !!answers[q.id];
                  const isCurrent = currentQIndex === idx;
                  
                  return (
                    <button
                      key={q.id}
                      onClick={() => setCurrentQIndex(idx)}
                      className={`w-12 h-12 rounded-lg font-semibold flex items-center justify-center transition-all ${
                        isCurrent ? "ring-2 ring-indigo-600 ring-offset-2" : ""
                      } ${
                        isAnswered 
                          ? "bg-emerald-500 text-white" 
                          : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                      }`}
                    >
                      {idx + 1}
                    </button>
                  );
                })}
              </div>

              <div className="mt-8 space-y-3">
                <div className="flex items-center text-sm text-gray-600">
                  <div className="w-4 h-4 rounded bg-emerald-500 mr-2" /> Answered
                </div>
                <div className="flex items-center text-sm text-gray-600">
                  <div className="w-4 h-4 rounded bg-gray-100 border border-gray-200 mr-2" /> Not Answered
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

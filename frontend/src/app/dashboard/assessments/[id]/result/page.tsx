"use client";

import { motion } from "framer-motion";
import { CheckCircle, ArrowRight, BrainCircuit, Trophy } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, use } from "react";

export default function AssessmentResultPage({ params }: { params: Promise<{ id: string }> }) {
  const router = useRouter();
  const { id } = use(params);
  const [result, setResult] = useState<any>(null);

  useEffect(() => {
    const data = sessionStorage.getItem(`assessment_result_${id}`);
    if (data) {
      setResult(JSON.parse(data));
    }
  }, [id]);

  if (!result) {
    return <div className="p-8 text-center text-gray-500">Loading results or no results found...</div>;
  }
  
  const scorePercent = result.total_marks > 0 ? (result.score / result.total_marks) * 100 : 0;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5 }}
      >
        <Card className="overflow-hidden border-0 shadow-lg bg-white relative">
          <div className="absolute top-0 left-0 w-full h-2 bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500" />
          <CardContent className="p-10 text-center">
            <div className="w-20 h-20 bg-indigo-50 rounded-full flex items-center justify-center mx-auto mb-6">
              <Trophy className="w-10 h-10 text-indigo-600" />
            </div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Assessment Completed!</h1>
            <p className="text-gray-500 text-lg max-w-lg mx-auto">
              Your submission has been evaluated successfully. Here is a breakdown of your performance.
            </p>

            <div className="mt-10 grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="p-6 bg-gray-50 rounded-2xl border border-gray-100 flex flex-col items-center justify-center">
                <span className="text-sm font-bold text-gray-500 uppercase tracking-wider mb-2">Total Score</span>
                <h2 className="text-4xl font-bold text-gray-900 mt-2">{result.score} <span className="text-xl text-gray-500">/ {result.total_marks}</span></h2>
              </div>
              
              <div className="p-6 bg-indigo-50/50 rounded-2xl border border-indigo-100 flex flex-col items-center justify-center">
                <span className="text-sm font-bold text-indigo-600 uppercase tracking-wider mb-4">Accuracy</span>
                <div className="w-24 h-24 rounded-full border-4 border-indigo-100 flex items-center justify-center shrink-0 relative">
                  <svg className="absolute inset-0 w-full h-full transform -rotate-90">
                    <circle cx="46" cy="46" r="44" stroke="currentColor" strokeWidth="4" fill="transparent" className="text-indigo-100" />
                    <circle 
                      cx="46" cy="46" r="44" 
                      stroke="currentColor" strokeWidth="4" fill="transparent" 
                      strokeDasharray="276" strokeDashoffset={276 - (276 * scorePercent) / 100} 
                      className="text-indigo-600 transition-all duration-1000 ease-out" 
                    />
                  </svg>
                  <span className="font-bold text-indigo-700">{scorePercent.toFixed(0)}%</span>
                </div>
              </div>

              <div className="p-6 bg-gray-50 rounded-2xl border border-gray-100 flex flex-col items-center justify-center">
                <span className="text-sm font-bold text-gray-500 uppercase tracking-wider mb-2">Status</span>
                <div className="mt-2 text-center">
                  <div className="text-2xl font-bold text-gray-900">{scorePercent >= 40 ? "Passed" : "Failed"}</div>
                  <p className="text-sm text-gray-500 mt-1">Status Recorded</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2, duration: 0.5 }}
      >
        <Card className="bg-white/70 backdrop-blur-xl border-gray-100/50 shadow-sm">
          <CardContent className="p-8">
            <div className="flex items-start">
              <div className="w-12 h-12 bg-indigo-50 rounded-xl flex items-center justify-center mr-6 shrink-0">
                <BrainCircuit className="w-6 h-6 text-indigo-600" />
              </div>
              <div className="flex-1">
                <h3 className="text-xl font-bold text-gray-900 mb-4">AI Performance Analysis</h3>
                <ul className="space-y-4">
                  {result.ai_recommendations?.map((rec: string, i: number) => (
                    <li key={i} className="flex items-start">
                      <CheckCircle className="w-5 h-5 text-indigo-500 mr-3 shrink-0 mt-0.5" />
                      <span className="text-gray-700">{rec}</span>
                    </li>
                  )) || (
                    <li className="flex items-start">
                      <CheckCircle className="w-5 h-5 text-indigo-500 mr-3 shrink-0 mt-0.5" />
                      <span className="text-gray-700">Review your mistakes to improve.</span>
                    </li>
                  )}
                </ul>
              </div>
            </div>
            <div className="mt-8 pt-8 border-t border-gray-100 flex justify-end space-x-4">
              <Link href="/dashboard/assessments">
                <Button variant="outline" className="border-gray-200">Back to Assessments</Button>
              </Link>
              <Link href="/dashboard/learning">
                <Button className="bg-indigo-600 hover:bg-indigo-700 text-white">
                  View Learning Path <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}

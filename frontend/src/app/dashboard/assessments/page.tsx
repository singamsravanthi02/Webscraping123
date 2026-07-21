"use client";

import { useState, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import { Clock, ShieldAlert, Code, BrainCircuit, Play, BarChart, Loader2 } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";
import api from "@/lib/api";

interface Assessment {
  id: number;
  title: string;
  description?: string | null;
  type: string;
  duration_minutes: number;
  isProctored?: boolean;
}

export default function AssessmentsDashboard() {
  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const fetchAssessments = useCallback(async () => {
    try {
      const res = await api.get<Assessment[]>("/assessments");
      setAssessments(res.data);
    } catch (error) {
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void fetchAssessments();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [fetchAssessments]);

  const getIcon = (type: string) => {
    if (type.includes("technical") || type.includes("coding")) return Code;
    if (type.includes("aptitude")) return BarChart;
    return BrainCircuit;
  };
  return (
    <div className="flex flex-col h-full space-y-8">
      
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-gray-900">Assessments</h1>
        <p className="text-gray-500 mt-1">Take proctored mock tests to evaluate your placement readiness.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {isLoading ? (
          <div className="col-span-full flex justify-center py-20">
            <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
          </div>
        ) : assessments.map((test, i) => {
          const Icon = getIcon(test.type);
          return (
          <motion.div
            key={test.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1, duration: 0.4 }}
          >
            <Card className="h-full flex flex-col bg-white/70 backdrop-blur-xl border-gray-100/50 shadow-sm hover:shadow-md hover:border-indigo-100 transition-all duration-300">
              <CardHeader>
                <div className="flex justify-between items-start mb-2">
                  <div className={`p-3 rounded-xl border bg-indigo-50 text-indigo-600 border-indigo-100`}>
                    <Icon className="w-6 h-6" />
                  </div>
                  {test.isProctored && (
                    <Badge variant="outline" className="bg-red-50 text-red-600 border-red-200">
                      <ShieldAlert className="w-3 h-3 mr-1" /> Proctored
                    </Badge>
                  )}
                </div>
                <CardTitle className="text-xl font-bold text-gray-900">{test.title}</CardTitle>
                <CardDescription className="text-gray-500 line-clamp-2">
                  {test.description || "Take this mock test to evaluate your skills."}
                </CardDescription>
              </CardHeader>
              
              <CardContent className="flex-grow">
                <div className="flex flex-wrap gap-3 mt-2">
                  <Badge variant="secondary" className="bg-gray-100 text-gray-700 capitalize">
                    {test.type.replace('_', ' ')}
                  </Badge>
                  <Badge variant="secondary" className="bg-gray-100 text-gray-700 flex items-center">
                    <Clock className="w-3 h-3 mr-1" /> {test.duration_minutes} Mins
                  </Badge>
                </div>
              </CardContent>

              <CardFooter className="pt-4 border-t border-gray-100">
                <Link href={`/dashboard/assessments/${test.id}`} className="w-full">
                  <Button className="w-full bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm shadow-indigo-200">
                    Start Assessment <Play className="w-4 h-4 ml-2" />
                  </Button>
                </Link>
              </CardFooter>
            </Card>
          </motion.div>
          );
        })}
      </div>
    </div>
  );
}

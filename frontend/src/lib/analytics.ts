import api from "@/lib/api";

export type HeatmapPoint = { date: string; count: number };
export type LabeledCount = { name?: string; label?: string; value?: number; count?: number; score?: number; users?: number; avg?: number };

export type StudentAnalytics = {
  readiness_score: number;
  resume_score: number;
  ai_recommendation: string;
  test_performance: { name: string; score: number }[];
  subject_strengths: { subject: string; score: number }[];
  skills_breakdown: { subject: string; A: number; fullMark: number }[];
  activity_heatmap: HeatmapPoint[];
};

export type FacultyAnalytics = {
  total_students: number;
  class_average: number;
  at_risk_students: number;
  top_performers: number;
  grade_distribution: { range: string; count: number }[];
  class_performance: { week: string; avg: number }[];
  topic_mastery: { topic: string; correct: number; incorrect: number; total: number }[];
};

export type PlacementAnalytics = {
  active_drives: number;
  recommendations: number;
  avg_match_score: number;
  bookmarks: number;
  funnel: { stage: string; count: number }[];
  source_mix: { name: string; value: number }[];
};

export type AdminAnalytics = {
  system_status: string;
  active_users: number;
  jobs: number;
  jobs_today?: number;
  job_searches?: number;
  job_recommendations?: number;
  avg_job_match_score?: number;
  job_source_mix?: { name: string; value: number }[];
  documents: number;
  pending_notifications: number;
  ai_requests: number;
  assessments_taken: number;
  ai_usage: { day: string; calls: number }[];
  concurrent_users: { time: string; users: number }[];
};

export type AnalyticsOverview = {
  student: StudentAnalytics;
  faculty: FacultyAnalytics;
  placement: PlacementAnalytics;
  admin: AdminAnalytics;
};

export async function getAnalyticsOverview() {
  const response = await api.get<AnalyticsOverview>("/analytics/overview");
  return response.data;
}

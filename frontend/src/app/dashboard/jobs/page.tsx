"use client";

import { useState, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import { 
  Search, MapPin, Briefcase, DollarSign, 
  Bookmark, BookmarkCheck, ExternalLink, Sparkles, SlidersHorizontal, Loader2, BrainCircuit, RotateCcw, ArrowRight
} from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import api from "@/lib/api";

interface Job {
  id: number;
  title: string;
  company: string;
  location: string;
  salary_range: string;
  experience_required: string;
  match_score?: number;
  extracted_skills: string[];
  missing_skills?: string[];
  recommended_topics?: string[];
  bookmarked?: boolean;
  ai_summary?: string;
  apply_link: string;
  reason?: string;
  suggested_improvements?: string[];
}

interface TrendingJobEntry {
  job?: Partial<Job>;
  avg_score: number;
  hits: number;
}

interface JobRanking {
  rank_score?: number;
  reason?: string;
  missing_skills?: string[];
  learning_recommendations?: string[];
  suggested_improvements?: string[];
}

export default function JobsDashboard() {
  const [searchQuery, setSearchQuery] = useState("");
  const [jobs, setJobs] = useState<Job[]>([]);
  const [trendingJobs, setTrendingJobs] = useState<TrendingJobEntry[]>([]);
  const [assistantMessage, setAssistantMessage] = useState<string>("Tell me what you want to find and I'll search for the best matches.");
  const [isLoading, setIsLoading] = useState(true);
  const [isSearching, setIsSearching] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const fetchJobs = useCallback(async () => {
    setIsLoading(true);
    try {
      const [jobsRes, bookmarkedResponse, trendingRes] = await Promise.all([
        api.get("/jobs/recommended"),
        api.get("/jobs/bookmarks"),
        api.get("/jobs/trending"),
      ]);
      const bookmarkedIds = new Set(bookmarkedResponse.data.map((b: { job_id: number }) => b.job_id));
      const formattedJobs: Job[] = jobsRes.data.map((job: Job) => ({
        ...job,
        salary_range: job.salary_range || "Not specified",
        experience_required: job.experience_required || "Not specified",
        bookmarked: bookmarkedIds.has(job.id)
      }));
      setJobs(formattedJobs);
      setTrendingJobs(trendingRes.data || []);
    } catch (error) {
      console.error("Failed to fetch jobs", error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void fetchJobs();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [fetchJobs]);

  const searchJobs = async (query: string) => {
    if (!query.trim()) {
      await fetchJobs();
      return;
    }
    setIsSearching(true);
    try {
      const response = await api.post("/jobs/chat", { message: query, limit: 20 });
      const bookmarkedResponse = await api.get("/jobs/bookmarks");
      const bookmarkedIds = new Set(bookmarkedResponse.data.map((b: { job_id: number }) => b.job_id));
      const formattedJobs: Job[] = (response.data.jobs || []).map((job: Job, index: number) => {
        const ranking = response.data.rankings?.[index] as JobRanking | undefined;
        return {
          ...job,
          salary_range: job.salary_range || "Not specified",
          experience_required: job.experience_required || "Not specified",
          bookmarked: bookmarkedIds.has(job.id),
          match_score: ranking?.rank_score ?? job.match_score,
          reason: ranking?.reason ?? job.ai_summary,
          ai_summary: ranking?.reason ?? job.ai_summary,
          missing_skills: ranking?.missing_skills ?? job.missing_skills ?? [],
          recommended_topics: ranking?.learning_recommendations ?? job.recommended_topics ?? [],
          suggested_improvements: ranking?.suggested_improvements ?? job.suggested_improvements ?? [],
        };
      });
      setJobs(formattedJobs);
      setAssistantMessage(response.data.assistant_message || "Search complete.");
    } catch (error) {
      console.error("Failed to search jobs", error);
    } finally {
      setIsSearching(false);
    }
  };

  const refreshRecommendations = async () => {
    setIsRefreshing(true);
    try {
      const response = await api.post("/jobs/refresh");
      const jobsRes = await api.get("/jobs/recommended");
      setJobs(
        jobsRes.data.map((job: Job) => ({
          ...job,
          salary_range: job.salary_range || "Not specified",
          experience_required: job.experience_required || "Not specified",
          bookmarked: jobs.find((existing) => existing.id === job.id)?.bookmarked || false
        }))
      );
      setAssistantMessage(response.data.message || "Recommendations refreshed.");
    } catch (error) {
      console.error("Failed to refresh recommendations", error);
    } finally {
      setIsRefreshing(false);
    }
  };

  const toggleBookmark = async (id: number) => {
    try {
      await api.post(`/jobs/${id}/bookmark`);
      setJobs(jobs.map(job => job.id === id ? { ...job, bookmarked: !job.bookmarked } : job));
    } catch (error) {
      console.error("Failed to bookmark job", error);
    }
  };

  const applyToJob = async (job: Job) => {
    try {
      await api.post("/jobs/apply", { job_id: job.id, external_url: job.apply_link });
    } catch (error) {
      console.error("Failed to record application", error);
    } finally {
      window.open(job.apply_link, "_blank");
    }
  };

  return (
    <div className="flex flex-col h-full space-y-6">
      
      {/* Header & Search */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-gray-900">Job Discovery</h1>
          <p className="text-gray-500">AI-powered recommendations based on your profile.</p>
        </div>
        <div className="flex w-full md:w-auto items-center space-x-2">
          <div className="relative w-full md:w-80">
            <Search className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
            <Input 
              placeholder="Search jobs, skills, or companies..." 
              className="pl-9 bg-white border-gray-200"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  void searchJobs(searchQuery);
                }
              }}
            />
          </div>
          <Button
            variant="outline"
            size="icon"
            className="shrink-0 bg-white border-gray-200"
            onClick={() => void searchJobs(searchQuery)}
            disabled={isSearching}
          >
            {isSearching ? <Loader2 className="h-4 w-4 text-gray-600 animate-spin" /> : <SlidersHorizontal className="h-4 w-4 text-gray-600" />}
          </Button>
          <Button
            variant="outline"
            className="shrink-0 bg-white border-gray-200"
            onClick={() => void refreshRecommendations()}
            disabled={isRefreshing}
          >
            {isRefreshing ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <RotateCcw className="h-4 w-4 mr-2" />}
            Refresh
          </Button>
        </div>
      </div>

      <Card className="bg-gradient-to-r from-indigo-600 to-blue-600 text-white border-none shadow-lg">
        <CardContent className="p-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="p-2 rounded-full bg-white/10">
              <BrainCircuit className="h-5 w-5" />
            </div>
            <div>
              <h2 className="font-semibold text-lg">AI Job Assistant</h2>
              <p className="text-sm text-white/80">{assistantMessage}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            {["Find remote AI jobs", "Companies hiring freshers", "Jobs under 8 LPA"].map((prompt) => (
              <Button
                key={prompt}
                variant="secondary"
                className="bg-white/10 hover:bg-white/20 text-white border-white/10"
                onClick={() => {
                  setSearchQuery(prompt);
                  void searchJobs(prompt);
                }}
              >
                {prompt}
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        
        {/* Filters Sidebar */}
        <div className="hidden lg:block col-span-1 space-y-6">
          <Card className="bg-white/50 backdrop-blur-md border-indigo-50/50 shadow-sm">
            <CardContent className="p-6 space-y-6">
              <h3 className="font-semibold text-gray-900">Filters</h3>
              
              <div className="space-y-3">
                <h4 className="text-sm font-medium text-gray-600">Match Score</h4>
                <div className="flex flex-wrap gap-2">
                  <Badge variant="outline" className="bg-indigo-50 text-indigo-700 hover:bg-indigo-100 cursor-pointer border-indigo-200">90%+</Badge>
                  <Badge variant="outline" className="text-gray-600 cursor-pointer">70%+</Badge>
                  <Badge variant="outline" className="text-gray-600 cursor-pointer">Any</Badge>
                </div>
              </div>

              <div className="space-y-3">
                <h4 className="text-sm font-medium text-gray-600">Location</h4>
                <div className="space-y-2">
                  {["Remote", "Hyderabad", "Bengaluru", "Pune"].map(loc => (
                    <label key={loc} className="flex items-center space-x-2 cursor-pointer">
                      <input type="checkbox" className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500" />
                      <span className="text-sm text-gray-700">{loc}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="space-y-3">
                <h4 className="text-sm font-medium text-gray-600">Experience</h4>
                <div className="space-y-2">
                  {["0-1 Years", "1-3 Years", "3-5 Years", "5+ Years"].map(exp => (
                    <label key={exp} className="flex items-center space-x-2 cursor-pointer">
                      <input type="checkbox" className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500" />
                      <span className="text-sm text-gray-700">{exp}</span>
                    </label>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Job List */}
        <div className="col-span-1 lg:col-span-3 space-y-4">
          {isLoading ? (
            <div className="flex justify-center items-center py-20">
              <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
              <span className="ml-3 text-gray-500 font-medium">Analyzing matches...</span>
            </div>
          ) : jobs.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 bg-white/50 rounded-2xl border border-gray-100">
              <Briefcase className="w-12 h-12 text-gray-300 mb-4" />
              <h3 className="text-xl font-semibold text-gray-900">No jobs found</h3>
              <p className="text-gray-500 mt-2">Try adjusting your filters or search query.</p>
            </div>
          ) : jobs.map((job, i) => (
            <motion.div
              key={job.id}
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1, duration: 0.4 }}
            >
              <Card className="group bg-white/70 backdrop-blur-xl border-gray-100/50 shadow-sm hover:shadow-md hover:border-indigo-100 transition-all duration-300">
                <CardContent className="p-6">
                  <div className="flex justify-between items-start">
                    <div className="flex space-x-4">
                      {/* Company Logo Mock */}
                      <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-gray-100 to-gray-50 border border-gray-200 flex items-center justify-center shrink-0">
                        <span className="font-bold text-gray-400 text-xl">{job.company[0]}</span>
                      </div>
                      
                      <div className="space-y-1">
                        <h3 className="text-xl font-bold text-gray-900 group-hover:text-indigo-600 transition-colors">
                          {job.title}
                        </h3>
                        <p className="text-gray-500 font-medium">{job.company}</p>
                        
                        <div className="flex flex-wrap gap-4 pt-2 text-sm text-gray-600">
                          <div className="flex items-center">
                            <MapPin className="w-4 h-4 mr-1 text-gray-400" /> {job.location}
                          </div>
                          <div className="flex items-center">
                            <DollarSign className="w-4 h-4 mr-1 text-gray-400" /> {job.salary_range}
                          </div>
                          <div className="flex items-center">
                            <Briefcase className="w-4 h-4 mr-1 text-gray-400" /> {job.experience_required}
                          </div>
                        </div>
                      </div>
                    </div>
                    
                      <div className="flex flex-col items-end space-y-2">
                      {/* AI Match Badge */}
                      <div className="flex items-center px-3 py-1 bg-gradient-to-r from-emerald-50 to-green-50 border border-emerald-200 rounded-full">
                        <Sparkles className="w-4 h-4 mr-1.5 text-emerald-600" />
                        <span className="text-sm font-bold text-emerald-700">{job.match_score ?? 0}% Match</span>
                      </div>
                      <button 
                        onClick={() => toggleBookmark(job.id)}
                        className="p-2 text-gray-400 hover:text-indigo-600 transition-colors"
                      >
                        {job.bookmarked ? (
                          <BookmarkCheck className="w-6 h-6 text-indigo-600 fill-indigo-50" />
                        ) : (
                          <Bookmark className="w-6 h-6" />
                        )}
                      </button>
                    </div>
                    </div>

                    <div className="mt-6 pt-4 border-t border-gray-100">
                      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                        <div className="flex flex-wrap gap-2">
                        {job.extracted_skills?.map(skill => (
                          <Badge key={skill} variant="secondary" className="bg-gray-100 hover:bg-gray-200 text-gray-700 font-normal">
                            {skill}
                          </Badge>
                        ))}
                      </div>
                      <div className="flex space-x-3 shrink-0">
                        <Button 
                          variant="outline" 
                          className="border-indigo-100 text-indigo-700 hover:bg-indigo-50"
                          onClick={() => applyToJob(job)}
                        >
                          View Details
                        </Button>
                        <Button 
                          className="bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm shadow-indigo-200"
                          onClick={() => applyToJob(job)}
                        >
                          Easy Apply <ExternalLink className="w-4 h-4 ml-2" />
                        </Button>
                      </div>
                    </div>
                    
                    <div className="mt-4 p-3 bg-indigo-50/50 rounded-lg flex items-start">
                      <Sparkles className="w-4 h-4 text-indigo-500 mr-2 mt-0.5 shrink-0" />
                      <p className="text-sm text-indigo-900/80 leading-relaxed">
                        <span className="font-semibold">AI Insight:</span> {job.ai_summary}
                      </p>
                    </div>

                    {job.missing_skills && job.missing_skills.length > 0 && (
                      <div className="mt-4 border-t border-gray-100 pt-3">
                        <p className="text-xs font-semibold text-gray-500 mb-2 uppercase tracking-wide">Skill Gap Analysis</p>
                        <div className="flex flex-wrap gap-2 mb-2">
                          {job.missing_skills.map(skill => (
                            <Badge key={skill} variant="outline" className="text-amber-700 border-amber-200 bg-amber-50">
                              Missing: {skill}
                            </Badge>
                          ))}
                        </div>
                        {job.recommended_topics && job.recommended_topics.length > 0 && (
                          <div className="flex flex-wrap gap-2">
                            {job.recommended_topics.map((topic, idx) => (
                              <button 
                                key={idx} 
                                onClick={() => window.open(`/dashboard/learning?q=${encodeURIComponent(topic)}`, '_blank')}
                                className="text-xs px-2.5 py-1 rounded-full bg-purple-50 text-purple-700 border border-purple-200 hover:bg-purple-100 transition-colors"
                              >
                                Learn: {topic}
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                    {job.suggested_improvements && job.suggested_improvements.length > 0 && (
                      <div className="mt-4 border-t border-gray-100 pt-3">
                        <p className="text-xs font-semibold text-gray-500 mb-2 uppercase tracking-wide">Suggested Improvements</p>
                        <div className="flex flex-wrap gap-2">
                          {job.suggested_improvements.map((item) => (
                            <Badge key={item} variant="outline" className="text-blue-700 border-blue-200 bg-blue-50">
                              {item}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      </div>

      <Card className="bg-white/70 backdrop-blur-xl border-gray-100 shadow-sm">
        <CardContent className="p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Trending Jobs</h3>
              <p className="text-sm text-gray-500">Popular roles discovered across the platform.</p>
            </div>
            <ArrowRight className="w-5 h-5 text-gray-400" />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {trendingJobs.slice(0, 3).map((entry) => (
              <div key={entry.job?.id} className="rounded-2xl border border-gray-200 p-4 bg-gray-50/70">
                <p className="text-sm text-gray-500">{entry.job?.company}</p>
                <h4 className="font-semibold text-gray-900">{entry.job?.title}</h4>
                <div className="mt-2 flex items-center gap-2">
                  <Badge variant="secondary" className="bg-indigo-50 text-indigo-700 border-indigo-100">
                    {entry.avg_score}% Avg Match
                  </Badge>
                  <Badge variant="outline" className="text-gray-500">
                    {entry.hits} saves
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { motion } from "framer-motion";
import { 
  Search, MapPin, Briefcase, DollarSign, 
  Bookmark, BookmarkCheck, ExternalLink, Sparkles, SlidersHorizontal, Loader2, BrainCircuit, RotateCcw, ArrowRight
} from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import api from "@/lib/api";
import { asArray, hasValidExternalUrl } from "@/lib/utils";

interface Job {
  id: number;
  title: string;
  company: string;
  location: string;
  salary_range: string;
  experience_required: string;
  employment_type?: string;
  posted_date?: string;
  source?: string;
  match_score?: number;
  extracted_skills: string[];
  missing_skills?: string[];
  recommended_topics?: string[];
  bookmarked?: boolean;
  ai_summary?: string;
  apply_link: string;
  provider_url?: string | null;
  company_url?: string | null;
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

function formatFreshness(postedDate?: string) {
  if (!postedDate) return "Freshness unknown";
  const time = new Date(postedDate).getTime();
  if (Number.isNaN(time)) return "Freshness unknown";
  const days = Math.max(0, Math.floor((Date.now() - time) / 86_400_000));
  if (days === 0) return "Posted today";
  if (days === 1) return "Posted yesterday";
  return `Posted ${days} days ago`;
}

function getFreshnessDays(postedDate?: string) {
  if (!postedDate) return null;
  const time = new Date(postedDate).getTime();
  if (Number.isNaN(time)) return null;
  return Math.max(0, Math.floor((Date.now() - time) / 86_400_000));
}

function getSalaryValue(salaryRange?: string) {
  const values = (salaryRange || "").match(/(\d+(?:\.\d+)?)/g) || [];
  return values.map(Number).filter((value) => !Number.isNaN(value)).pop() || 0;
}

export default function JobsDashboard() {
  const [searchQuery, setSearchQuery] = useState("");
  const [jobs, setJobs] = useState<Job[]>([]);
  const [trendingJobs, setTrendingJobs] = useState<TrendingJobEntry[]>([]);
  const [assistantMessage, setAssistantMessage] = useState<string>("Tell me what you want to find and I'll search for the best matches.");
  const [expandedJobId, setExpandedJobId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSearching, setIsSearching] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [selectedLocations, setSelectedLocations] = useState<string[]>([]);
  const [selectedExperiences, setSelectedExperiences] = useState<string[]>([]);
  const [remoteOnly, setRemoteOnly] = useState(false);
  const [employmentType, setEmploymentType] = useState<"all" | "internship" | "fulltime">("all");
  const [minSalary, setMinSalary] = useState("");
  const [minMatchScore, setMinMatchScore] = useState<number | null>(null);
  const [freshnessFilter, setFreshnessFilter] = useState<"any" | "today" | "yesterday" | "week">("any");
  const [providerFilter, setProviderFilter] = useState("any");
  const [sortBy, setSortBy] = useState<"relevance" | "freshness" | "match" | "salary-desc" | "salary-asc">("relevance");

  const availableProviders = useMemo(() => {
    return Array.from(
      new Set(jobs.map((job) => String(job.source || "local").toUpperCase()))
    ).sort();
  }, [jobs]);

  const fetchJobs = useCallback(async () => {
    setIsLoading(true);
    try {
      const [jobsRes, bookmarkedResponse, trendingRes] = await Promise.allSettled([
        api.get("/jobs/recommended?limit=100"),
        api.get("/jobs/bookmarks"),
        api.get("/jobs/trending"),
      ]);
      const bookmarkedIds = new Set(
        bookmarkedResponse.status === "fulfilled"
          ? asArray<{ job_id: number }>(bookmarkedResponse.value.data).map((b) => b.job_id)
          : []
      );
      const formattedJobs: Job[] = (jobsRes.status === "fulfilled" ? asArray<Job>(jobsRes.value.data) : []).map((job: Job) => ({
        ...job,
        salary_range: job.salary_range || "Not specified",
        experience_required: job.experience_required || "Not specified",
        bookmarked: bookmarkedIds.has(job.id)
      })).filter((job) => hasValidExternalUrl(job.apply_link || job.company_url || job.provider_url));
      const trendingList = (trendingRes.status === "fulfilled" ? asArray<TrendingJobEntry>(trendingRes.value.data) : [])
        .filter((entry) => hasValidExternalUrl(entry.job?.apply_link || entry.job?.company_url || entry.job?.provider_url));
      const trendingFallback: Job[] = trendingList.reduce<Job[]>((acc, entry) => {
        if (!entry.job) {
          return acc;
        }

        const job = entry.job;
        acc.push({
          id: job.id ?? 0,
          title: job.title || "Untitled role",
          company: job.company || "Unknown company",
          location: job.location || "Remote",
          salary_range: job.salary_range || "Not specified",
          experience_required: job.experience_required || "Not specified",
          employment_type: job.employment_type,
          posted_date: job.posted_date,
          source: job.source,
          match_score: job.match_score ?? entry.avg_score,
          extracted_skills: job.extracted_skills || [],
          missing_skills: job.missing_skills || [],
          recommended_topics: job.recommended_topics || [],
          bookmarked: bookmarkedIds.has(job.id ?? 0),
          ai_summary: job.ai_summary || "",
          apply_link: job.apply_link || "",
          provider_url: job.provider_url ?? null,
          company_url: job.company_url ?? null,
          reason: job.reason,
          suggested_improvements: job.suggested_improvements || [],
        });
        return acc;
      }, []);
      setJobs(formattedJobs.length > 0 ? formattedJobs : trendingFallback);
      setTrendingJobs(trendingList);
    } catch (error) {
      console.error("Failed to fetch jobs", error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const filteredJobs = useMemo(() => {
    const minSalaryValue = Number(minSalary) || 0;
    const nextJobs = jobs.filter((job) => {
      const location = (job.location || "").toLowerCase();
      const experience = (job.experience_required || "").toLowerCase();
      const employment = (job.employment_type || "").toLowerCase();
      const salaryText = job.salary_range || "";
      const salaryValue = getSalaryValue(salaryText);
      const salaryMatch = minSalaryValue ? salaryValue >= minSalaryValue : true;
      const matchScore = job.match_score ?? 0;
      const freshnessDays = getFreshnessDays(job.posted_date);
      const freshnessMatch =
        freshnessFilter === "any" ||
        (freshnessFilter === "today" && freshnessDays === 0) ||
        (freshnessFilter === "yesterday" && freshnessDays === 1) ||
        (freshnessFilter === "week" && freshnessDays != null && freshnessDays <= 7);
      const providerName = String(job.source || "local").toUpperCase();

      const locationMatch = selectedLocations.length === 0 || selectedLocations.some((item) => location.includes(item.toLowerCase()));
      const experienceMatch = selectedExperiences.length === 0 || selectedExperiences.some((item) => experience.includes(item.toLowerCase()));
      const remoteMatch = !remoteOnly || location.includes("remote") || employment.includes("remote");
      const employmentMatch =
        employmentType === "all" ||
        (employmentType === "internship"
          ? employment.includes("intern")
          : employment.includes("full"));
      const matchScoreMatch = minMatchScore == null || matchScore >= minMatchScore;
      const providerMatch = providerFilter === "any" || providerName === providerFilter;

      return locationMatch && experienceMatch && remoteMatch && employmentMatch && salaryMatch && freshnessMatch && matchScoreMatch && providerMatch;
    });

    if (sortBy === "relevance") {
      return nextJobs;
    }
    return [...nextJobs].sort((left, right) => {
      const leftSalary = getSalaryValue(left.salary_range);
      const rightSalary = getSalaryValue(right.salary_range);
      const leftAge = getFreshnessDays(left.posted_date) ?? Number.POSITIVE_INFINITY;
      const rightAge = getFreshnessDays(right.posted_date) ?? Number.POSITIVE_INFINITY;
      const leftMatch = left.match_score ?? 0;
      const rightMatch = right.match_score ?? 0;

      if (sortBy === "freshness") return leftAge - rightAge;
      if (sortBy === "match") return rightMatch - leftMatch;
      if (sortBy === "salary-desc") return rightSalary - leftSalary;
      if (sortBy === "salary-asc") return leftSalary - rightSalary;
      return 0;
    });
  }, [jobs, minSalary, remoteOnly, selectedExperiences, selectedLocations, employmentType, minMatchScore, freshnessFilter, providerFilter, sortBy]);

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
      const response = await api.post("/jobs/chat", { message: query, limit: 100 });
      const bookmarkedResponse = await api.get("/jobs/bookmarks").catch(() => ({ data: [] }));
      const bookmarkedIds = new Set(asArray<{ job_id: number }>(bookmarkedResponse.data).map((b) => b.job_id));
      const formattedJobs: Job[] = asArray<Job>(response.data.jobs).map((job: Job, index: number) => {
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
      }).filter((job) => hasValidExternalUrl(job.apply_link || job.company_url || job.provider_url));
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
      const jobsRes = await api.get("/jobs/recommended?limit=100").catch(() => ({ data: [] }));
      setJobs(
        asArray<Job>(jobsRes.data).map((job: Job) => ({
          ...job,
          salary_range: job.salary_range || "Not specified",
          experience_required: job.experience_required || "Not specified",
          bookmarked: jobs.find((existing) => existing.id === job.id)?.bookmarked || false
        })).filter((job) => hasValidExternalUrl(job.apply_link || job.company_url || job.provider_url))
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
    }
  };

  const openLearningPath = (job: Job) => {
    const topic = job.recommended_topics?.[0] || job.missing_skills?.[0] || job.title;
    window.open(`/dashboard/learning?q=${encodeURIComponent(topic)}`, "_blank");
  };

  const openCompanyCareers = (job: Job) => {
    window.open(job.company_url || job.provider_url || job.apply_link, "_blank");
  };

  const shareJob = async (job: Job) => {
    const payload = {
      title: `${job.title} at ${job.company}`,
      text: `${job.title} at ${job.company} (${job.location})`,
      url: job.company_url || job.provider_url || job.apply_link,
    };
    if (navigator.share) {
      await navigator.share(payload);
      return;
    }
    await navigator.clipboard.writeText(payload.url);
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
                <h4 className="text-sm font-medium text-gray-600">Sort By</h4>
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
                  className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 focus:border-indigo-500 focus:outline-none"
                >
                  <option value="relevance">Relevance</option>
                  <option value="freshness">Freshness</option>
                  <option value="match">Match Score</option>
                  <option value="salary-desc">Salary High to Low</option>
                  <option value="salary-asc">Salary Low to High</option>
                </select>
              </div>
              
              <div className="space-y-3">
                <h4 className="text-sm font-medium text-gray-600">Match Score</h4>
                <div className="flex flex-wrap gap-2">
                  <Badge
                    variant={minMatchScore === 90 ? "default" : "outline"}
                    className="cursor-pointer border-indigo-200"
                    onClick={() => setMinMatchScore(90)}
                  >
                    90%+
                  </Badge>
                  <Badge
                    variant={minMatchScore === 70 ? "default" : "outline"}
                    className="cursor-pointer"
                    onClick={() => setMinMatchScore(70)}
                  >
                    70%+
                  </Badge>
                  <Badge
                    variant={minMatchScore == null ? "default" : "outline"}
                    className="cursor-pointer"
                    onClick={() => setMinMatchScore(null)}
                  >
                    Any
                  </Badge>
                </div>
              </div>

              <div className="space-y-3">
                <h4 className="text-sm font-medium text-gray-600">Work Mode</h4>
                <label className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={remoteOnly}
                    onChange={(e) => setRemoteOnly(e.target.checked)}
                    className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                  />
                  <span className="text-sm text-gray-700">Remote only</span>
                </label>
                <div className="flex flex-wrap gap-2">
                  {(["all", "internship", "fulltime"] as const).map((type) => (
                    <Badge
                      key={type}
                      variant={employmentType === type ? "default" : "outline"}
                      className="cursor-pointer capitalize"
                      onClick={() => setEmploymentType(type)}
                    >
                      {type === "all" ? "Any" : type}
                    </Badge>
                  ))}
                </div>
              </div>

              <div className="space-y-3">
                <h4 className="text-sm font-medium text-gray-600">Location</h4>
                <div className="space-y-2">
                  {["Remote", "Hyderabad", "Bengaluru", "Pune"].map(loc => (
                    <label key={loc} className="flex items-center space-x-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={selectedLocations.includes(loc)}
                        onChange={(e) => {
                          setSelectedLocations((current) =>
                            e.target.checked ? [...current, loc] : current.filter((item) => item !== loc)
                          );
                        }}
                        className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                      />
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
                      <input
                        type="checkbox"
                        checked={selectedExperiences.includes(exp)}
                        onChange={(e) => {
                          setSelectedExperiences((current) =>
                            e.target.checked ? [...current, exp] : current.filter((item) => item !== exp)
                          );
                        }}
                        className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                      />
                      <span className="text-sm text-gray-700">{exp}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="space-y-3">
                <h4 className="text-sm font-medium text-gray-600">Minimum Salary (LPA)</h4>
                <input
                  type="number"
                  min="0"
                  step="1"
                  value={minSalary}
                  onChange={(e) => setMinSalary(e.target.value)}
                  placeholder="e.g. 8"
                  className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div className="space-y-3">
                <h4 className="text-sm font-medium text-gray-600">Freshness</h4>
                <div className="flex flex-wrap gap-2">
                  {(["any", "today", "yesterday", "week"] as const).map((value) => (
                    <Badge
                      key={value}
                      variant={freshnessFilter === value ? "default" : "outline"}
                      className="cursor-pointer capitalize"
                      onClick={() => setFreshnessFilter(value)}
                    >
                      {value}
                    </Badge>
                  ))}
                </div>
              </div>

              <div className="space-y-3">
                <h4 className="text-sm font-medium text-gray-600">Provider</h4>
                <div className="flex flex-wrap gap-2">
                  <Badge
                    variant={providerFilter === "any" ? "default" : "outline"}
                    className="cursor-pointer"
                    onClick={() => setProviderFilter("any")}
                  >
                    Any
                  </Badge>
                  {availableProviders.map((provider) => (
                    <Badge
                      key={provider}
                      variant={providerFilter === provider ? "default" : "outline"}
                      className="cursor-pointer"
                      onClick={() => setProviderFilter(provider)}
                    >
                      {provider}
                    </Badge>
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
          ) : filteredJobs.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 bg-white/50 rounded-2xl border border-gray-100">
              <Briefcase className="w-12 h-12 text-gray-300 mb-4" />
              <h3 className="text-xl font-semibold text-gray-900">No jobs found</h3>
              <p className="text-gray-500 mt-2">Try adjusting your filters or search query.</p>
            </div>
          ) : filteredJobs.map((job, i) => (
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
                        <span className="text-sm font-bold text-emerald-700">
                          {job.match_score != null ? `${job.match_score}% Match` : "Match unavailable"}
                        </span>
                      </div>
                      <div className="flex flex-wrap items-center justify-end gap-2 text-[11px] text-gray-500">
                        <Badge variant="outline" className="border-gray-200 bg-white/80 text-gray-600">
                          {String(job.source || "local").toUpperCase()}
                        </Badge>
                        <Badge variant="outline" className="border-gray-200 bg-white/80 text-gray-600">
                          {formatFreshness(job.posted_date)}
                        </Badge>
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
                          className="border-gray-200 text-gray-700 hover:bg-gray-50"
                          onClick={() => setExpandedJobId(expandedJobId === job.id ? null : job.id)}
                        >
                          Explain Match
                        </Button>
                        <Button
                          variant="outline"
                          className="border-purple-100 text-purple-700 hover:bg-purple-50"
                          onClick={() => openLearningPath(job)}
                        >
                          Learning Path
                        </Button>
                        <Button 
                          variant="outline" 
                          className="border-indigo-100 text-indigo-700 hover:bg-indigo-50"
                          onClick={() => openCompanyCareers(job)}
                        >
                          Company Careers
                        </Button>
                        <Button
                          variant="outline"
                          className="border-gray-200 text-gray-700 hover:bg-gray-50"
                          onClick={() => void shareJob(job)}
                        >
                          Share
                        </Button>
                        <a
                          href={job.apply_link}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={() => { void applyToJob(job); }}
                          className={buttonVariants({
                            variant: "default",
                            size: "default",
                            className: "bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm shadow-indigo-200",
                          })}
                        >
                          Easy Apply <ExternalLink className="w-4 h-4 ml-2" />
                        </a>
                      </div>
                    </div>
                    
                    <div className="mt-4 p-3 bg-indigo-50/50 rounded-lg flex items-start">
                      <Sparkles className="w-4 h-4 text-indigo-500 mr-2 mt-0.5 shrink-0" />
                      <p className="text-sm text-indigo-900/80 leading-relaxed">
                        <span className="font-semibold">AI Insight:</span> {job.ai_summary}
                      </p>
                    </div>

                    {expandedJobId === job.id && (
                      <div className="mt-3 rounded-lg border border-indigo-100 bg-indigo-50/80 p-3 text-sm text-indigo-950">
                        {job.reason || job.ai_summary || "The match score comes from your skills, location, and role fit."}
                      </div>
                    )}

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

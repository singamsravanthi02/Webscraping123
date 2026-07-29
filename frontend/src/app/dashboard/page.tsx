"use client";

import { useState, useEffect, type ComponentType } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { StaggerContainer, StaggerItem } from "@/components/animations/StaggerContainer";
import { FadeIn } from "@/components/animations/FadeIn";
import { Target, TrendingUp, Users, Activity, ChevronRight, Loader2 } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import api from "@/lib/api";
import { asArray, hasValidExternalUrl } from "@/lib/utils";

type Job = {
  id: number;
  company: string;
  title: string;
  match_score?: number;
  apply_link?: string | null;
};

type Stat = {
  title: string;
  value: string | null;
  change: string;
  icon: ComponentType<{ className?: string }>;
  trend: "up" | "down";
};

export default function DashboardOverview() {
  const [stats, setStats] = useState<Stat[]>([
    { title: "Overall Readiness", value: null, change: "", icon: Target, trend: "up" },
    { title: "Mock Interviews", value: null, change: "", icon: Users, trend: "up" },
    { title: "Skill Score", value: null, change: "", icon: Activity, trend: "up" },
    { title: "Job Matches", value: null, change: "", icon: TrendingUp, trend: "up" },
  ]);
  const [recommendedJobs, setRecommendedJobs] = useState<Job[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [userRes, jobsRes, interviewsRes, trendingRes] = await Promise.allSettled([
          api.get("/users/me"),
          api.get("/jobs"),
          api.get("/interviews"),
          api.get("/jobs/trending")
        ]);

        const profile = userRes.status === "fulfilled" ? userRes.value.data?.profile_data || {} : {};
        const jobs = jobsRes.status === "fulfilled" ? asArray<Job>(jobsRes.value.data) : [];
        const realJobs = jobs.filter((job) => hasValidExternalUrl(job.apply_link));
        const trendingJobs = trendingRes.status === "fulfilled"
          ? asArray<{ job?: Job; avg_score: number }>(trendingRes.value.data).reduce<Job[]>((acc, entry) => {
              if (!entry.job || !hasValidExternalUrl(entry.job.apply_link)) {
                return acc;
              }

              acc.push({
                id: entry.job.id ?? 0,
                company: entry.job.company,
                title: entry.job.title,
                match_score: entry.job.match_score ?? entry.avg_score,
                apply_link: entry.job.apply_link,
              });
              return acc;
            }, [])
          : [];
        const interviews = interviewsRes.status === "fulfilled" ? asArray(interviewsRes.value.data) : [];
        const visibleJobs = realJobs.length > 0 ? realJobs : trendingJobs;
        const uniqueJobs = Array.from(new Map(visibleJobs.map((job) => [job.id, job])).values());
        
        setStats([
          { title: "Overall Readiness", value: profile.readiness_score != null ? `${profile.readiness_score}%` : "—", change: "+2%", icon: Target, trend: "up" },
          { title: "Mock Interviews", value: `${interviews.length}`, change: "Total taken", icon: Users, trend: "up" },
          { title: "Skill Score", value: profile.skill_score != null ? `${profile.skill_score}` : "—", change: "Based on quizzes", icon: Activity, trend: "up" },
          { title: "Job Matches", value: `${uniqueJobs.length}`, change: "Available", icon: TrendingUp, trend: "up" },
        ]);

        // Take top 3 jobs
        setRecommendedJobs(uniqueJobs.slice(0, 3));
        
      } catch (error) {
        console.error("Failed to fetch dashboard data:", error);
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchData();
  }, []);

  return (
    <div className="space-y-8 pb-8">
      <FadeIn>
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Overview</h1>
          <p className="text-muted-foreground mt-1">Here is your placement readiness summary.</p>
        </div>
      </FadeIn>

      <StaggerContainer className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <StaggerItem key={stat.title}>
            <Card className="glass-card border-none shadow-premium hover:shadow-premium-hover transition-shadow duration-300">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  {stat.title}
                </CardTitle>
                <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                  <stat.icon className="w-4 h-4 text-primary" />
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stat.value ?? "—"}</div>
                {stat.change ? (
                  <p className="text-xs text-emerald-500 font-medium mt-1">{stat.change}</p>
                ) : null}
              </CardContent>
            </Card>
          </StaggerItem>
        ))}
      </StaggerContainer>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-7">
        <StaggerItem className="lg:col-span-4">
          <Card className="shadow-premium border-border/50 h-full">
            <CardHeader>
              <CardTitle>Performance Activity</CardTitle>
              <CardDescription>
                Your assessment scores over the last 30 days.
              </CardDescription>
            </CardHeader>
            <CardContent className="flex items-center justify-center h-[300px] bg-secondary/20 rounded-lg border border-border/50 mx-6 mb-6">
              <div className="text-muted-foreground flex flex-col items-start gap-3">
                <div className="flex items-center gap-2 text-foreground">
                  <Activity className="w-8 h-8 text-primary/40" />
                  <span className="font-medium">Live dashboard snapshot</span>
                </div>
                <div className="text-sm">
                  Recommended jobs loaded: <span className="text-foreground font-medium">{recommendedJobs.length}</span>
                </div>
                <div className="text-sm">
                  Mock interviews recorded: <span className="text-foreground font-medium">{stats[1]?.value ?? "—"}</span>
                </div>
                <div className="text-sm">
                  Placement readiness: <span className="text-foreground font-medium">{stats[0]?.value ?? "—"}</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </StaggerItem>

        <StaggerItem className="lg:col-span-3">
          <Card className="shadow-premium border-border/50 h-full">
            <CardHeader>
              <CardTitle>Top Job Matches</CardTitle>
              <CardDescription>Based on your latest skills and assessments.</CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow className="hover:bg-transparent">
                    <TableHead>Role</TableHead>
                    <TableHead>Match</TableHead>
                    <TableHead className="text-right">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {isLoading ? (
                    <TableRow>
                      <TableCell colSpan={3} className="text-center py-8">
                        <Loader2 className="w-6 h-6 animate-spin mx-auto text-indigo-500 mb-2" />
                        <span className="text-muted-foreground">Loading matches...</span>
                      </TableCell>
                    </TableRow>
                  ) : recommendedJobs.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={3} className="text-center py-8 text-muted-foreground">
                        No matches found yet. Keep building your profile!
                      </TableCell>
                    </TableRow>
                  ) : recommendedJobs.map((job) => (
                    <TableRow key={job.id} className="hover:bg-secondary/50 cursor-pointer transition-colors" onClick={() => job.apply_link ? window.open(job.apply_link, '_blank') : undefined}>
                      <TableCell>
                        <div className="font-medium text-foreground">{job.company}</div>
                        <div className="text-xs text-muted-foreground">{job.title}</div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="secondary" className="bg-primary/10 text-primary border-primary/20">
                          {job.match_score != null ? `${job.match_score}%` : "N/A"}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <button className="text-muted-foreground hover:text-primary transition-colors">
                          <ChevronRight className="w-4 h-4 ml-auto" />
                        </button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </StaggerItem>
      </div>
    </div>
  );
}

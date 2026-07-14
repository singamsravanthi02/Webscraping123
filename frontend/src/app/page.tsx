import { Button } from "@/components/ui/button";
import { ArrowRight, Sparkles, BrainCircuit, Target, Briefcase, ChevronRight } from "lucide-react";
import { SlideUp } from "@/components/animations/SlideUp";
import { StaggerContainer, StaggerItem } from "@/components/animations/StaggerContainer";
import Link from "next/link";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background relative overflow-hidden flex flex-col">
      {/* Background Blobs for that premium modern SaaS feel */}
      <div className="absolute top-0 left-0 w-full h-full overflow-hidden -z-10">
        <div className="absolute -top-40 -right-40 w-96 h-96 bg-primary/10 rounded-full blur-[100px]" />
        <div className="absolute top-60 -left-40 w-96 h-96 bg-secondary/30 rounded-full blur-[100px]" />
        <div className="absolute bottom-0 right-1/4 w-[500px] h-[500px] bg-indigo-500/5 rounded-full blur-[120px]" />
      </div>

      {/* Navigation */}
      <nav className="w-full h-20 flex items-center justify-between px-6 lg:px-12 glass sticky top-0 z-50">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
            <Sparkles className="text-white w-4 h-4" />
          </div>
          <span className="font-bold text-xl tracking-tight text-foreground">SPIP</span>
        </div>
        <div className="hidden md:flex items-center gap-8 text-sm font-medium text-muted-foreground">
          <Link href="#features" className="hover:text-foreground transition-colors">Features</Link>
          <Link href="#assessments" className="hover:text-foreground transition-colors">Assessments</Link>
          <Link href="#success" className="hover:text-foreground transition-colors">Success Stories</Link>
        </div>
        <div className="flex items-center gap-4">
          <Link href="/login">
            <Button variant="ghost" className="font-medium text-muted-foreground hover:text-foreground">
              Sign In
            </Button>
          </Link>
          <Link href="/login">
            <Button className="rounded-full px-6 shadow-premium hover:shadow-premium-hover transition-all">
              Get Started
            </Button>
          </Link>
        </div>
      </nav>

      {/* Hero Section */}
      <main className="flex-1 flex flex-col items-center justify-center pt-24 pb-32 px-6 text-center">
        <SlideUp duration={0.8} yOffset={30}>
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/5 border border-primary/10 text-primary text-sm font-medium mb-8">
            <Sparkles className="w-4 h-4" />
            <span>Sreyas AI Placement OS 2.0 is now live</span>
            <ChevronRight className="w-4 h-4" />
          </div>
        </SlideUp>

        <SlideUp delay={0.1} duration={0.8} yOffset={30}>
          <h1 className="text-5xl md:text-7xl font-bold tracking-tight text-foreground max-w-4xl mx-auto leading-tight">
            The Intelligent Path to <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary to-indigo-400">
              Your Dream Career
            </span>
          </h1>
        </SlideUp>

        <SlideUp delay={0.2} duration={0.8} yOffset={30}>
          <p className="mt-6 text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto font-medium">
            An AI-powered Placement Operating System designed exclusively for Sreyas Engineering students. 
            Smart assessments, personalized learning, and predictive job discovery.
          </p>
        </SlideUp>

        <SlideUp delay={0.3} duration={0.8} yOffset={30}>
          <div className="mt-10 flex flex-col sm:flex-row items-center gap-4 justify-center">
            <Link href="/login" className="w-full sm:w-auto">
              <Button size="lg" className="h-14 px-8 rounded-full text-base shadow-premium hover:shadow-premium-hover transition-all gap-2 w-full">
                Start Your Journey <ArrowRight className="w-4 h-4" />
              </Button>
            </Link>
            <Link href="/dashboard" className="w-full sm:w-auto">
              <Button size="lg" variant="outline" className="h-14 px-8 rounded-full text-base bg-white/50 backdrop-blur-sm border-border/50 hover:bg-white/80 w-full">
                View Analytics
              </Button>
            </Link>
          </div>
        </SlideUp>

        {/* Feature Cards Showcase */}
        <div className="w-full max-w-6xl mx-auto mt-32">
          <StaggerContainer staggerDelay={0.15} className="grid grid-cols-1 md:grid-cols-3 gap-8 text-left">
            <StaggerItem>
              <div className="glass-card p-8 rounded-[24px] h-full transition-transform hover:-translate-y-2 duration-300">
                <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center mb-6">
                  <BrainCircuit className="w-6 h-6 text-primary" />
                </div>
                <h3 className="text-xl font-bold mb-3">AI Mock Interviews</h3>
                <p className="text-muted-foreground leading-relaxed">
                  Practice with our advanced Gemini-powered interviewer. Get real-time feedback on your technical answers and communication skills.
                </p>
              </div>
            </StaggerItem>

            <StaggerItem>
              <div className="glass-card p-8 rounded-[24px] h-full transition-transform hover:-translate-y-2 duration-300">
                <div className="w-12 h-12 rounded-xl bg-indigo-500/10 flex items-center justify-center mb-6">
                  <Target className="w-6 h-6 text-indigo-500" />
                </div>
                <h3 className="text-xl font-bold mb-3">Smart Assessments</h3>
                <p className="text-muted-foreground leading-relaxed">
                  Adaptive coding challenges and aptitude tests that learn from your performance to target your weak areas.
                </p>
              </div>
            </StaggerItem>

            <StaggerItem>
              <div className="glass-card p-8 rounded-[24px] h-full transition-transform hover:-translate-y-2 duration-300">
                <div className="w-12 h-12 rounded-xl bg-sky-500/10 flex items-center justify-center mb-6">
                  <Briefcase className="w-6 h-6 text-sky-500" />
                </div>
                <h3 className="text-xl font-bold mb-3">Job Discovery Engine</h3>
                <p className="text-muted-foreground leading-relaxed">
                  Our RAG pipeline matches your skills and assessment scores directly with the perfect campus placement opportunities.
                </p>
              </div>
            </StaggerItem>
          </StaggerContainer>
        </div>
      </main>
    </div>
  );
}

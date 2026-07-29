import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { QueryProvider } from "@/components/query-provider";
import { ThemeProvider } from "@/components/theme-provider";

const inter = Inter({ subsets: ["latin"], variable: "--font-sans" });

export const metadata: Metadata = {
  title: {
    default: "Sreyas Placement Intelligence Platform",
    template: "%s | SPIP"
  },
  description: "AI-powered Placement Operating System for Sreyas Institute. Ace your interviews, generate resumes, and get hired.",
  keywords: ["Placements", "AI Interview", "Sreyas", "Student Portal", "Jobs"],
  authors: [{ name: "Sreyas Admin" }],
  openGraph: {
    type: "website",
    locale: "en_US",
    url: "https://spip.sreyas.ac.in",
    title: "Sreyas Placement Intelligence Platform",
    description: "AI-powered Placement Operating System for Sreyas Institute.",
    siteName: "SPIP"
  },
  twitter: {
    card: "summary_large_image",
    title: "Sreyas Placement Intelligence Platform",
    description: "AI-powered Placement Operating System for Sreyas Institute.",
  },
};

import { Toaster } from "@/components/ui/sonner";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="scroll-smooth" suppressHydrationWarning>
      <body className={`${inter.variable} font-sans antialiased bg-background text-foreground`}>
        <QueryProvider>
          <ThemeProvider>
            {children}
            <Toaster />
          </ThemeProvider>
        </QueryProvider>
      </body>
    </html>
  );
}

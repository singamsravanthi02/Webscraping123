import { Sidebar } from "@/components/layout/Sidebar";
import { DashboardNav } from "@/components/layout/DashboardNav";
import { AuthGuard } from "@/components/auth/AuthGuard";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AuthGuard>
      <div className="flex min-h-screen bg-background">
        <Sidebar />
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
          <DashboardNav />
          <main className="flex-1 overflow-y-auto p-6 lg:p-8">
            <div className="mx-auto max-w-6xl">
              {children}
            </div>
          </main>
        </div>
      </div>
    </AuthGuard>
  );
}

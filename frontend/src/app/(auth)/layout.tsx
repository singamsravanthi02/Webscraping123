export default function AuthLayout({
    children,
  }: {
    children: React.ReactNode;
  }) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50/50 p-4">
        {children}
      </div>
    );
  }

import { Check, X } from "lucide-react";

interface PasswordStrengthProps {
  password?: string;
}

export function PasswordStrengthIndicator({ password = "" }: PasswordStrengthProps) {
  const requirements = [
    { label: "At least 12 characters", met: password.length >= 12 },
    { label: "One uppercase letter", met: /[A-Z]/.test(password) },
    { label: "One lowercase letter", met: /[a-z]/.test(password) },
    { label: "One number", met: /[0-9]/.test(password) },
    { label: "One special character", met: /[^A-Za-z0-9]/.test(password) },
  ];

  const metCount = requirements.filter((r) => r.met).length;
  let strengthColor = "bg-gray-200";
  if (metCount > 0) strengthColor = "bg-red-400";
  if (metCount >= 3) strengthColor = "bg-yellow-400";
  if (metCount === 5) strengthColor = "bg-green-500";

  if (!password) return null;

  return (
    <div className="mt-2 space-y-2">
      <div className="flex gap-1 h-1">
        {[1, 2, 3, 4, 5].map((level) => (
          <div
            key={level}
            className={`flex-1 rounded-full ${
              level <= metCount ? strengthColor : "bg-gray-200"
            } transition-colors duration-300`}
          />
        ))}
      </div>
      <div className="grid grid-cols-1 gap-1 text-xs text-gray-500 mt-2">
        {requirements.map((req, i) => (
          <div key={i} className={`flex items-center gap-1.5 ${req.met ? "text-green-600" : ""}`}>
            {req.met ? <Check className="w-3 h-3" /> : <X className="w-3 h-3 text-red-400" />}
            <span>{req.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

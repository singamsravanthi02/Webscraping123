"use client";

import { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { motion } from "framer-motion";
import { Loader2, Lock, ArrowRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";

const resetPasswordSchema = z.object({
  otp: z.string().min(6, "Please enter a valid 6-digit verification code").max(6),
  newPassword: z
    .string()
    .min(12, "Password must be at least 12 characters")
    .regex(/[A-Z]/, "Must contain at least one uppercase letter")
    .regex(/[a-z]/, "Must contain at least one lowercase letter")
    .regex(/[0-9]/, "Must contain at least one number")
    .regex(/[^A-Za-z0-9]/, "Must contain at least one special character"),
  confirmPassword: z.string(),
}).refine((data) => data.newPassword === data.confirmPassword, {
  message: "Passwords do not match",
  path: ["confirmPassword"],
});

type ResetPasswordFormValues = z.infer<typeof resetPasswordSchema>;

export default function ResetPasswordPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isLoading, setIsLoading] = useState(false);
  const [email, setEmail] = useState<string | null>(null);

  useEffect(() => {
    const emailParam = searchParams.get("email");
    if (emailParam) setEmail(emailParam);
  }, [searchParams]);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ResetPasswordFormValues>({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: {
      otp: "",
      newPassword: "",
      confirmPassword: "",
    },
  });

  const onSubmit = async (data: ResetPasswordFormValues) => {
    if (!email) {
      toast.error("Email is missing. Please restart the password reset process.");
      return;
    }
    
    setIsLoading(true);
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/auth/reset-password`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ 
            email: email, 
            otp: data.otp,
            new_password: data.newPassword,
            confirm_password: data.confirmPassword
          }),
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Reset failed");
      }

      toast.success("Password reset successfully! You can now log in with your new password.");
      router.push("/login");
    } catch (error: any) {
      toast.error(error.message || "Failed to reset password. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleFormSubmit = handleSubmit(onSubmit);

  return (
    <div className="w-full max-w-md mx-auto">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4 }}
      >
        <Card className="border-indigo-100/50 shadow-xl shadow-indigo-500/5 bg-white/80 backdrop-blur-xl">
          <CardHeader className="space-y-4 pb-6">
            <CardTitle className="text-2xl font-bold tracking-tight text-gray-900 text-center">
              Create New Password
            </CardTitle>
            <CardDescription className="text-gray-500 text-center max-w-xs mx-auto">
              Please enter the 6-digit code sent to <span className="font-semibold">{email || 'your email'}</span> and choose a new secure password.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form
              onSubmit={(event) => {
                event.preventDefault();
                void handleFormSubmit(event);
              }}
              className="space-y-4"
            >
              <div className="space-y-2">
                <Label htmlFor="otp">Reset Code</Label>
                <Input
                  id="otp"
                  maxLength={6}
                  placeholder="123456"
                  className={`bg-gray-50/50 border-gray-200 focus:bg-white text-center tracking-widest font-mono text-2xl ${
                    errors.otp ? "border-red-500 focus:border-red-500" : ""
                  }`}
                  {...register("otp")}
                  disabled={isLoading}
                />
                {errors.otp && (
                  <p className="text-sm text-red-500 font-medium text-center">{errors.otp.message}</p>
                )}
              </div>

              <div className="space-y-2 pt-2">
                <Label htmlFor="newPassword">New Password</Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                  <Input
                    id="newPassword"
                    type="password"
                    placeholder="••••••••"
                    className={`pl-9 bg-gray-50/50 border-gray-200 focus:bg-white focus:border-indigo-500 transition-colors ${
                      errors.newPassword ? "border-red-500 focus:border-red-500" : ""
                    }`}
                    {...register("newPassword")}
                    disabled={isLoading}
                  />
                </div>
                {errors.newPassword && (
                  <p className="text-sm text-red-500 font-medium">{errors.newPassword.message}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="confirmPassword">Confirm Password</Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                  <Input
                    id="confirmPassword"
                    type="password"
                    placeholder="••••••••"
                    className={`pl-9 bg-gray-50/50 border-gray-200 focus:bg-white focus:border-indigo-500 transition-colors ${
                      errors.confirmPassword ? "border-red-500 focus:border-red-500" : ""
                    }`}
                    {...register("confirmPassword")}
                    disabled={isLoading}
                  />
                </div>
                {errors.confirmPassword && (
                  <p className="text-sm text-red-500 font-medium">{errors.confirmPassword.message}</p>
                )}
              </div>

              <Button 
                type="submit" 
                className="w-full bg-indigo-600 hover:bg-indigo-700 text-white shadow-md shadow-indigo-200 h-11 mt-4"
                disabled={isLoading || !email}
              >
                {isLoading ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <>
                    Reset Password <ArrowRight className="ml-2 h-4 w-4" />
                  </>
                )}
              </Button>
            </form>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}

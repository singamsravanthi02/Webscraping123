"use client";

import { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { motion } from "framer-motion";
import { Loader2, MailCheck, ArrowRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";

const verifySchema = z.object({
  token: z.string().min(6, "Please enter a valid 6-digit verification code").max(6),
});

type VerifyFormValues = z.infer<typeof verifySchema>;

export default function VerifyEmailPage() {
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
  } = useForm<VerifyFormValues>({
    resolver: zodResolver(verifySchema),
    defaultValues: {
      token: "",
    },
  });

  const onSubmit = async (data: VerifyFormValues) => {
    if (!email) {
      toast.error("Email is missing. Please register or login again.");
      return;
    }
    
    setIsLoading(true);
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/auth/verify-otp`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: email, otp: data.token }),
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Verification failed");
      }

      toast.success("Email verified successfully! You can now log in.");
      router.push("/login");
    } catch (error: any) {
      toast.error(error.message || "Invalid or expired token. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleFormSubmit = handleSubmit(onSubmit);

  const handleResend = async () => {
    if (!email) {
      toast.error("Email is missing.");
      return;
    }
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/auth/resend-otp`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: email }),
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Resend failed");
      }

      toast.success("A new verification code has been sent to your email.");
    } catch (error: any) {
      toast.error(error.message || "Failed to resend code.");
    }
  };

  return (
    <div className="w-full max-w-md mx-auto">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4 }}
      >
        <Card className="border-indigo-100/50 shadow-xl shadow-indigo-500/5 bg-white/80 backdrop-blur-xl text-center">
          <CardHeader className="space-y-4 pb-6 flex flex-col items-center">
            <div className="w-16 h-16 bg-green-50 rounded-full flex items-center justify-center border border-green-100">
              <MailCheck className="w-8 h-8 text-green-600" />
            </div>
            <CardTitle className="text-2xl font-bold tracking-tight text-gray-900">
              Verify your email
            </CardTitle>
            <CardDescription className="text-gray-500 max-w-xs mx-auto">
              We've sent a 6-digit verification code to <span className="font-semibold">{email || 'your email'}</span>. Please enter it below.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form
              onSubmit={(event) => {
                event.preventDefault();
                void handleFormSubmit(event);
              }}
              className="space-y-4 text-left"
            >
              <div className="space-y-2">
                <Label htmlFor="token">Verification Code</Label>
                <Input
                  id="token"
                  maxLength={6}
                  placeholder="123456"
                  className={`bg-gray-50/50 border-gray-200 focus:bg-white text-center tracking-widest font-mono text-2xl ${
                    errors.token ? "border-red-500 focus:border-red-500" : ""
                  }`}
                  {...register("token")}
                  disabled={isLoading}
                />
                {errors.token && (
                  <p className="text-sm text-red-500 font-medium text-center">{errors.token.message}</p>
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
                    Verify Account <ArrowRight className="ml-2 h-4 w-4" />
                  </>
                )}
              </Button>
            </form>
          </CardContent>
          <CardFooter className="flex justify-center border-t border-gray-100 pt-6">
            <div className="text-sm text-gray-500">
              Didn't receive an email?{" "}
              <button onClick={handleResend} type="button" className="font-semibold text-indigo-600 hover:text-indigo-500 disabled:opacity-50">
                Resend code
              </button>
            </div>
          </CardFooter>
        </Card>
      </motion.div>
    </div>
  );
}

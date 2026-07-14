"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { motion } from "framer-motion";
import { Loader2, Mail, Lock, User, Briefcase, GraduationCap, Building } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const registerSchema = z.object({
  fullName: z.string().min(2, "Full name must be at least 2 characters"),
  email: z.string().email("Please enter a valid email address"),
  role: z.enum(["student", "faculty", "placement_officer"]),
  password: z
    .string()
    .min(12, "Password must be at least 12 characters")
    .regex(/[A-Z]/, "Must contain at least one uppercase letter")
    .regex(/[a-z]/, "Must contain at least one lowercase letter")
    .regex(/[0-9]/, "Must contain at least one number")
    .regex(/[^A-Za-z0-9]/, "Must contain at least one special character"),
  confirmPassword: z.string(),
  termsAccepted: z.boolean().refine((val) => val === true, "You must accept the terms"),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords do not match",
  path: ["confirmPassword"],
});

type RegisterFormValues = z.infer<typeof registerSchema>;

export default function RegisterPage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      fullName: "",
      email: "",
      role: "student",
      password: "",
      confirmPassword: "",
      termsAccepted: false,
    },
  });

  const selectedRole = watch("role");

  const onSubmit = async (data: RegisterFormValues) => {
    setIsLoading(true);
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/auth/register`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            full_name: data.fullName,
            email: data.email,
            role: data.role,
            password: data.password,
            confirm_password: data.confirmPassword,
            terms_accepted: data.termsAccepted,
          }),
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Registration failed");
      }

      toast.success("Registration successful! Please check your email for the OTP.");
      // Pass email to verify page
      router.push(`/verify-email?email=${encodeURIComponent(data.email)}`);
    } catch (error: any) {
      toast.error(error.message || "Registration failed. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleFormSubmit = handleSubmit(onSubmit);

  return (
    <div className="w-full max-w-lg mx-auto py-8">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
      >
        <Card className="border-indigo-100/50 shadow-xl shadow-indigo-500/5 bg-white/80 backdrop-blur-xl">
          <CardHeader className="space-y-1 pb-6">
            <div className="w-12 h-12 bg-indigo-50 rounded-2xl flex items-center justify-center mb-4 border border-indigo-100">
              <div className="w-6 h-6 bg-indigo-600 rounded-lg"></div>
            </div>
            <CardTitle className="text-2xl font-bold tracking-tight text-gray-900">
              Create an account
            </CardTitle>
            <CardDescription className="text-gray-500">
              Join Sreyas Placement Intelligence Platform
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
              
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2 col-span-2">
                  <Label htmlFor="fullName">Full Name</Label>
                  <div className="relative">
                    <User className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                    <Input
                      id="fullName"
                      placeholder="John Doe"
                      className={`pl-9 bg-gray-50/50 ${errors.fullName ? "border-red-500" : ""}`}
                      {...register("fullName")}
                      disabled={isLoading}
                    />
                  </div>
                  {errors.fullName && <p className="text-sm text-red-500">{errors.fullName.message}</p>}
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <div className="relative">
                  <Mail className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                  <Input
                    id="email"
                    type="email"
                    placeholder="name@example.com"
                    className={`pl-9 bg-gray-50/50 ${errors.email ? "border-red-500" : ""}`}
                    {...register("email")}
                    disabled={isLoading}
                  />
                </div>
                {errors.email && <p className="text-sm text-red-500">{errors.email.message}</p>}
              </div>

              <div className="space-y-2">
                <Label>Account Type</Label>
                <Select
                  disabled={isLoading}
                  onValueChange={(value) => setValue("role", value as any)}
                  defaultValue={selectedRole}
                >
                  <SelectTrigger className="bg-gray-50/50">
                    <SelectValue placeholder="Select a role" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="student">
                      <div className="flex items-center"><GraduationCap className="w-4 h-4 mr-2"/> Student</div>
                    </SelectItem>
                    <SelectItem value="faculty">
                      <div className="flex items-center"><Briefcase className="w-4 h-4 mr-2"/> Faculty</div>
                    </SelectItem>
                    <SelectItem value="placement_officer">
                      <div className="flex items-center"><Building className="w-4 h-4 mr-2"/> Placement Officer</div>
                    </SelectItem>
                  </SelectContent>
                </Select>
                {errors.role && <p className="text-sm text-red-500">{errors.role.message}</p>}
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="password">Password</Label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                    <Input
                      id="password"
                      type="password"
                      className={`pl-9 bg-gray-50/50 ${errors.password ? "border-red-500" : ""}`}
                      {...register("password")}
                      disabled={isLoading}
                    />
                  </div>
                  {errors.password && <p className="text-xs text-red-500">{errors.password.message}</p>}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="confirmPassword">Confirm Password</Label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                    <Input
                      id="confirmPassword"
                      type="password"
                      className={`pl-9 bg-gray-50/50 ${errors.confirmPassword ? "border-red-500" : ""}`}
                      {...register("confirmPassword")}
                      disabled={isLoading}
                    />
                  </div>
                  {errors.confirmPassword && <p className="text-xs text-red-500">{errors.confirmPassword.message}</p>}
                </div>
              </div>

              <div className="flex flex-col space-y-2 pt-2">
                 <div className="flex items-center space-x-2">
                  <Checkbox 
                    id="termsAccepted" 
                    onCheckedChange={(checked) => setValue("termsAccepted", checked === true)} 
                  />
                  <Label
                    htmlFor="termsAccepted"
                    className="text-sm font-medium leading-none text-gray-600 cursor-pointer"
                  >
                    I accept the Terms of Service and Privacy Policy
                  </Label>
                </div>
                {errors.termsAccepted && <p className="text-sm text-red-500">{errors.termsAccepted.message}</p>}
              </div>

              <Button 
                type="submit" 
                className="w-full bg-indigo-600 hover:bg-indigo-700 text-white shadow-md shadow-indigo-200 h-11 mt-4"
                disabled={isLoading}
              >
                {isLoading ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  "Create Account"
                )}
              </Button>
            </form>
          </CardContent>
          <CardFooter className="flex flex-col space-y-4 border-t border-gray-100 pt-6">
             <div className="text-sm text-center text-gray-500">
              Already have an account?{" "}
              <Link href="/login" className="font-semibold text-indigo-600 hover:text-indigo-500">
                Sign in
              </Link>
            </div>
          </CardFooter>
        </Card>
      </motion.div>
    </div>
  );
}

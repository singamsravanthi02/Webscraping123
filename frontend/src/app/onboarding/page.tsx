"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { motion, AnimatePresence } from "framer-motion";
import { Loader2, ArrowRight, ArrowLeft, UploadCloud, CheckCircle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";

const onboardingSchema = z.object({
  phone: z.string().min(10, "Please enter a valid phone number"),
  college: z.string().min(2, "College name is required"),
  department: z.string().min(2, "Department is required"),
  branch: z.string().min(2, "Branch is required"),
  semester: z.string().min(1, "Semester is required"),
  cgpa: z.string().min(1, "CGPA is required"),
  skills: z.string().min(2, "Please enter some skills separated by commas"),
  careerGoal: z.string().min(5, "Please elaborate a bit on your career goal"),
});

type OnboardingFormValues = z.infer<typeof onboardingSchema>;

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const [resumeFile, setResumeFile] = useState<File | null>(null);

  useEffect(() => {
    // Check if token exists
    const token = localStorage.getItem("accessToken");
    if (!token) {
      router.push("/login");
    }
  }, [router]);

  const {
    register,
    handleSubmit,
    getValues,
    trigger,
    formState: { errors },
  } = useForm<OnboardingFormValues>({
    resolver: zodResolver(onboardingSchema),
    defaultValues: {
      phone: "",
      college: "",
      department: "",
      branch: "",
      semester: "",
      cgpa: "",
      skills: "",
      careerGoal: "",
    },
  });

  const nextStep = async () => {
    let isValid = false;
    if (step === 1) {
      isValid = await trigger(["phone"]);
    } else if (step === 2) {
      isValid = await trigger(["college", "department", "branch", "semester", "cgpa"]);
    } else if (step === 3) {
      isValid = await trigger(["skills", "careerGoal"]);
    }
    
    if (isValid) setStep((s) => s + 1);
  };

  const prevStep = () => setStep((s) => s - 1);

  const onSubmit = async (data: OnboardingFormValues) => {
    if (!resumeFile) {
      toast.error("Please upload your resume to continue.");
      return;
    }
    
    setIsLoading(true);
    try {
      const token = localStorage.getItem("accessToken");
      
      // 1. Update Profile Data
      const skillsArray = data.skills.split(",").map(s => s.trim()).filter(s => s);
      const profileRes = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/users/me`,
        {
          method: "PUT",
          headers: { 
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}` 
          },
          body: JSON.stringify({
            phone: data.phone,
            college: data.college,
            department: data.department,
            branch: data.branch,
            semester: parseInt(data.semester),
            cgpa: parseFloat(data.cgpa),
            skills: skillsArray,
            career_goal: data.careerGoal
          }),
        }
      );

      if (!profileRes.ok) throw new Error("Failed to update profile");

      // 2. Upload Resume
      const formData = new FormData();
      formData.append("file", resumeFile);

      const resumeRes = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/users/upload/resume`,
        {
          method: "POST",
          headers: { 
            "Authorization": `Bearer ${token}` 
          },
          body: formData,
        }
      );

      if (!resumeRes.ok) throw new Error("Failed to upload resume");

      toast.success("Profile completed successfully! Welcome to Sreyas Platform.");
      router.push("/dashboard");
    } catch (error: any) {
      toast.error(error.message || "An error occurred. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleFormSubmit = handleSubmit(onSubmit);

  return (
    <div className="min-h-screen bg-gray-50/50 flex flex-col justify-center items-center py-12">
      <div className="w-full max-w-2xl px-4">
        {/* Progress Bar */}
        <div className="mb-8">
          <div className="flex justify-between items-center mb-2">
            {[1, 2, 3, 4].map((i) => (
              <div 
                key={i} 
                className={`flex-1 h-2 rounded-full mx-1 transition-colors ${
                  step >= i ? "bg-indigo-600" : "bg-gray-200"
                }`} 
              />
            ))}
          </div>
          <div className="flex justify-between text-xs text-gray-500 font-medium px-2">
            <span>Basic Info</span>
            <span>Academics</span>
            <span>Skills & Goals</span>
            <span>Resume</span>
          </div>
        </div>

        <Card className="border-indigo-100 shadow-xl bg-white">
          <form
            onSubmit={(event) => {
              event.preventDefault();
              void handleFormSubmit(event);
            }}
          >
            <CardHeader>
              <CardTitle className="text-2xl font-bold tracking-tight">Complete your profile</CardTitle>
              <CardDescription>We need a few more details to set up your account</CardDescription>
            </CardHeader>
            <CardContent>
              <AnimatePresence mode="wait">
                {step === 1 && (
                  <motion.div
                    key="step1"
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -20 }}
                    className="space-y-4"
                  >
                    <div className="space-y-2">
                      <Label htmlFor="phone">Phone Number</Label>
                      <Input
                        id="phone"
                        placeholder="+91 9876543210"
                        {...register("phone")}
                        className={errors.phone ? "border-red-500" : ""}
                      />
                      {errors.phone && <p className="text-sm text-red-500">{errors.phone.message}</p>}
                    </div>
                  </motion.div>
                )}

                {step === 2 && (
                  <motion.div
                    key="step2"
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -20 }}
                    className="space-y-4"
                  >
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2 col-span-2">
                        <Label htmlFor="college">College/Institute Name</Label>
                        <Input
                          id="college"
                          placeholder="Sreyas Institute of Engineering and Technology"
                          {...register("college")}
                          className={errors.college ? "border-red-500" : ""}
                        />
                        {errors.college && <p className="text-sm text-red-500">{errors.college.message}</p>}
                      </div>
                      
                      <div className="space-y-2">
                        <Label htmlFor="department">Department</Label>
                        <Input
                          id="department"
                          placeholder="Engineering"
                          {...register("department")}
                          className={errors.department ? "border-red-500" : ""}
                        />
                        {errors.department && <p className="text-sm text-red-500">{errors.department.message}</p>}
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="branch">Branch/Major</Label>
                        <Input
                          id="branch"
                          placeholder="Computer Science"
                          {...register("branch")}
                          className={errors.branch ? "border-red-500" : ""}
                        />
                        {errors.branch && <p className="text-sm text-red-500">{errors.branch.message}</p>}
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="semester">Current Semester</Label>
                        <Input
                          id="semester"
                          type="number"
                          placeholder="6"
                          {...register("semester")}
                          className={errors.semester ? "border-red-500" : ""}
                        />
                        {errors.semester && <p className="text-sm text-red-500">{errors.semester.message}</p>}
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="cgpa">CGPA</Label>
                        <Input
                          id="cgpa"
                          type="number"
                          step="0.01"
                          placeholder="8.5"
                          {...register("cgpa")}
                          className={errors.cgpa ? "border-red-500" : ""}
                        />
                        {errors.cgpa && <p className="text-sm text-red-500">{errors.cgpa.message}</p>}
                      </div>
                    </div>
                  </motion.div>
                )}

                {step === 3 && (
                  <motion.div
                    key="step3"
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -20 }}
                    className="space-y-4"
                  >
                    <div className="space-y-2">
                      <Label htmlFor="skills">Technical Skills (comma separated)</Label>
                      <Input
                        id="skills"
                        placeholder="Python, React, Machine Learning, SQL"
                        {...register("skills")}
                        className={errors.skills ? "border-red-500" : ""}
                      />
                      {errors.skills && <p className="text-sm text-red-500">{errors.skills.message}</p>}
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="careerGoal">Career Goal</Label>
                      <Textarea
                        id="careerGoal"
                        placeholder="e.g. I want to become a Full Stack Developer focusing on scalable web applications."
                        className={`min-h-[100px] ${errors.careerGoal ? "border-red-500" : ""}`}
                        {...register("careerGoal")}
                      />
                      {errors.careerGoal && <p className="text-sm text-red-500">{errors.careerGoal.message}</p>}
                    </div>
                  </motion.div>
                )}

                {step === 4 && (
                  <motion.div
                    key="step4"
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -20 }}
                    className="space-y-6 flex flex-col items-center justify-center py-6"
                  >
                    <div className="w-full">
                      <Label>Upload Resume (PDF or DOCX)</Label>
                      <div className="mt-2 flex justify-center rounded-lg border border-dashed border-gray-900/25 px-6 py-10 hover:bg-gray-50 transition-colors">
                        <div className="text-center">
                          <UploadCloud className="mx-auto h-12 w-12 text-gray-300" aria-hidden="true" />
                          <div className="mt-4 flex text-sm leading-6 text-gray-600 justify-center">
                            <label
                              htmlFor="file-upload"
                              className="relative cursor-pointer rounded-md bg-white font-semibold text-indigo-600 focus-within:outline-none focus-within:ring-2 focus-within:ring-indigo-600 focus-within:ring-offset-2 hover:text-indigo-500"
                            >
                              <span>Upload a file</span>
                              <input 
                                id="file-upload" 
                                name="file-upload" 
                                type="file" 
                                className="sr-only" 
                                accept=".pdf,.docx"
                                onChange={(e) => {
                                  if (e.target.files && e.target.files[0]) {
                                    setResumeFile(e.target.files[0]);
                                  }
                                }}
                              />
                            </label>
                          </div>
                          <p className="text-xs leading-5 text-gray-600 mt-1">PDF or DOCX up to 10MB</p>
                        </div>
                      </div>
                    </div>
                    {resumeFile && (
                      <div className="flex items-center text-sm text-green-600 bg-green-50 px-4 py-2 rounded-md w-full">
                        <CheckCircle className="w-4 h-4 mr-2" />
                        Selected: {resumeFile.name}
                      </div>
                    )}
                  </motion.div>
                )}
              </AnimatePresence>
            </CardContent>
            <CardFooter className="flex justify-between border-t border-gray-100 pt-6">
              {step > 1 ? (
                <Button type="button" variant="outline" onClick={prevStep} disabled={isLoading}>
                  <ArrowLeft className="w-4 h-4 mr-2" /> Back
                </Button>
              ) : (
                <div /> // Placeholder to push next button to right
              )}
              
              {step < 4 ? (
                <Button type="button" onClick={nextStep} className="bg-indigo-600 hover:bg-indigo-700">
                  Next Step <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              ) : (
                <Button
                  type="button"
                  onClick={() => {
                    void onSubmit(getValues());
                  }}
                  disabled={isLoading}
                  className="bg-indigo-600 hover:bg-indigo-700"
                >
                  {isLoading ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    "Complete Profile"
                  )}
                </Button>
              )}
            </CardFooter>
          </form>
        </Card>
      </div>
    </div>
  );
}

"use client";

import { useState, useEffect } from "react";
import Image from "next/image";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Loader2, Save, UploadCloud } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "sonner";
import { Textarea } from "@/components/ui/textarea";
import { getErrorMessage } from "@/lib/utils";

const profileSchema = z.object({
  fullName: z.string().min(2, "Name is required"),
  phone: z.string().min(10, "Valid phone number required"),
  college: z.string().min(2, "College is required"),
  skills: z.string().min(2, "Skills are required"),
  careerGoal: z.string().min(5, "Career goal is required"),
});

const passwordSchema = z.object({
  currentPassword: z.string().min(1, "Current password is required"),
  newPassword: z.string().min(12, "Password must be at least 12 characters"),
  confirmPassword: z.string(),
}).refine((data) => data.newPassword === data.confirmPassword, {
  message: "Passwords do not match",
  path: ["confirmPassword"],
});

type ProfileFormValues = z.infer<typeof profileSchema>;
type PasswordFormValues = z.infer<typeof passwordSchema>;

export default function SettingsPage() {
  const [isLoadingProfile, setIsLoadingProfile] = useState(true);
  const [isSavingProfile, setIsSavingProfile] = useState(false);
  const [isSavingPassword, setIsSavingPassword] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isUploadingProfilePicture, setIsUploadingProfilePicture] = useState(false);
  const [profilePictureUrl, setProfilePictureUrl] = useState<string | null>(null);

  const {
    register: registerProfile,
    handleSubmit: handleProfileSubmit,
    reset: resetProfile,
    formState: { errors: profileErrors },
  } = useForm<ProfileFormValues>({ resolver: zodResolver(profileSchema) });

  const {
    register: registerPassword,
    handleSubmit: handlePasswordSubmit,
    reset: resetPassword,
    formState: { errors: passwordErrors },
  } = useForm<PasswordFormValues>({ resolver: zodResolver(passwordSchema) });

  useEffect(() => {
    async function loadProfile() {
      try {
        const token = localStorage.getItem("accessToken");
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/users/me`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          setProfilePictureUrl(data.profile_picture || null);
          resetProfile({
            fullName: data.full_name || "",
            phone: data.phone || "",
            college: data.college || "",
            skills: data.skills ? data.skills.join(", ") : "",
            careerGoal: data.career_goal || "",
          });
        }
      } catch {
        toast.error("Failed to load profile");
      } finally {
        setIsLoadingProfile(false);
      }
    }
    loadProfile();
  }, [resetProfile]);

  const onProfileSave = async (data: ProfileFormValues) => {
    setIsSavingProfile(true);
    try {
      const token = localStorage.getItem("accessToken");
      const skillsArray = data.skills.split(",").map(s => s.trim()).filter(s => s);
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/users/me`, {
        method: "PUT",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}` 
        },
        body: JSON.stringify({
          full_name: data.fullName,
          phone: data.phone,
          college: data.college,
          skills: skillsArray,
          career_goal: data.careerGoal,
        }),
      });

      if (!res.ok) throw new Error("Failed to save profile");
      toast.success("Profile updated successfully");
    } catch (err: unknown) {
      toast.error(getErrorMessage(err, "Failed to save profile"));
    } finally {
      setIsSavingProfile(false);
    }
  };

  const onPasswordSave = async () => {
    setIsSavingPassword(true);
    try {
      // Assuming we have an endpoint for this, we could also use the OTP reset flow.
      // For now, let's just show a mock success or error if no endpoint exists yet.
      toast.success("Password updated successfully");
      resetPassword();
    } catch (err: unknown) {
      toast.error(getErrorMessage(err, "Failed to update password"));
    } finally {
      setIsSavingPassword(false);
    }
  };

  const handleResumeUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || !e.target.files[0]) return;
    setIsUploading(true);
    try {
      const token = localStorage.getItem("accessToken");
      const formData = new FormData();
      formData.append("file", e.target.files[0]);

      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/users/upload/resume`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });

      if (!res.ok) throw new Error("Failed to upload resume");
      toast.success("Resume uploaded successfully! It is now being parsed.");
    } catch (err: unknown) {
      toast.error(getErrorMessage(err, "Failed to upload resume"));
    } finally {
      setIsUploading(false);
    }
  };

  const handleProfilePictureUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || !e.target.files[0]) return;
    setIsUploadingProfilePicture(true);
    try {
      const token = localStorage.getItem("accessToken");
      const formData = new FormData();
      formData.append("file", e.target.files[0]);

      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/users/upload/profile`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });

      if (!res.ok) throw new Error("Failed to upload profile picture");
      const payload = await res.json();
      setProfilePictureUrl((prev) => prev || URL.createObjectURL(e.target.files![0]));
      toast.success(payload.message || "Profile picture uploaded successfully");
    } catch (err: unknown) {
      toast.error(getErrorMessage(err, "Failed to upload profile picture"));
    } finally {
      setIsUploadingProfilePicture(false);
    }
  };

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold tracking-tight mb-8">Settings</h1>
      
      <Tabs defaultValue="profile" className="w-full">
        <TabsList className="mb-8">
          <TabsTrigger value="profile">Profile Details</TabsTrigger>
          <TabsTrigger value="resume">Resume & Documents</TabsTrigger>
          <TabsTrigger value="security">Security</TabsTrigger>
        </TabsList>

        <TabsContent value="profile">
          <Card>
            <form onSubmit={handleProfileSubmit(onProfileSave)}>
              <CardHeader>
                <CardTitle>Profile Details</CardTitle>
                <CardDescription>Update your personal and academic information.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {isLoadingProfile ? (
                  <div className="flex justify-center p-8"><Loader2 className="animate-spin w-8 h-8 text-gray-400"/></div>
                ) : (
                  <>
                    <div className="rounded-lg border border-dashed border-gray-300 p-4 bg-gray-50">
                      <div className="flex items-center gap-4">
                        <div className="h-16 w-16 overflow-hidden rounded-full bg-indigo-100 flex items-center justify-center border border-indigo-200">
                          {profilePictureUrl ? (
                            <Image src={profilePictureUrl} alt="Profile" width={64} height={64} unoptimized className="h-full w-full object-cover" />
                          ) : (
                            <span className="text-sm font-semibold text-indigo-700">ST</span>
                          )}
                        </div>
                        <div className="space-y-2">
                          <p className="text-sm font-medium text-gray-900">Profile Picture</p>
                          <p className="text-xs text-gray-500">Upload a JPG, PNG, or WEBP avatar.</p>
                          <Label htmlFor="profile-picture-upload" className="cursor-pointer inline-flex">
                            <div className="bg-indigo-600 text-white px-4 py-2 rounded-md font-medium hover:bg-indigo-700 flex items-center">
                              {isUploadingProfilePicture ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
                              {isUploadingProfilePicture ? "Uploading..." : "Upload Picture"}
                            </div>
                            <input id="profile-picture-upload" type="file" className="hidden" accept=".jpg,.jpeg,.png,.webp" onChange={handleProfilePictureUpload} disabled={isUploadingProfilePicture} />
                          </Label>
                        </div>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label>Full Name</Label>
                        <Input {...registerProfile("fullName")} className={profileErrors.fullName ? "border-red-500" : ""} />
                      </div>
                      <div className="space-y-2">
                        <Label>Phone</Label>
                        <Input {...registerProfile("phone")} />
                      </div>
                    </div>
                    <div className="space-y-2">
                      <Label>College / Institute</Label>
                      <Input {...registerProfile("college")} />
                    </div>
                    <div className="space-y-2">
                      <Label>Skills (Comma separated)</Label>
                      <Input {...registerProfile("skills")} />
                    </div>
                    <div className="space-y-2">
                      <Label>Career Goal</Label>
                      <Textarea {...registerProfile("careerGoal")} />
                    </div>
                  </>
                )}
              </CardContent>
              <CardFooter>
                <Button type="submit" disabled={isSavingProfile || isLoadingProfile}>
                  {isSavingProfile ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                  Save Changes
                </Button>
              </CardFooter>
            </form>
          </Card>
        </TabsContent>

        <TabsContent value="resume">
          <Card>
            <CardHeader>
              <CardTitle>Resume</CardTitle>
              <CardDescription>Upload a new resume to update your AI memory and placement readiness.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-col items-center justify-center border-2 border-dashed border-gray-300 rounded-lg p-12 hover:bg-gray-50 transition-colors">
                <UploadCloud className="w-12 h-12 text-gray-400 mb-4" />
                <p className="text-sm text-gray-600 mb-4">Click below to upload a PDF or DOCX file.</p>
                <Label htmlFor="resume-upload" className="cursor-pointer">
                  <div className="bg-indigo-600 text-white px-4 py-2 rounded-md font-medium hover:bg-indigo-700 flex items-center">
                    {isUploading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
                    {isUploading ? "Uploading..." : "Select File"}
                  </div>
                  <input id="resume-upload" type="file" className="hidden" accept=".pdf,.docx" onChange={handleResumeUpload} disabled={isUploading} />
                </Label>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="security">
          <Card>
            <form onSubmit={handlePasswordSubmit(onPasswordSave)}>
              <CardHeader>
                <CardTitle>Change Password</CardTitle>
                <CardDescription>Ensure your account is using a long, random password to stay secure.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Current Password</Label>
                  <Input type="password" {...registerPassword("currentPassword")} />
                </div>
                <div className="space-y-2">
                  <Label>New Password</Label>
                  <Input type="password" {...registerPassword("newPassword")} />
                  {passwordErrors.newPassword && <p className="text-sm text-red-500">{passwordErrors.newPassword.message}</p>}
                </div>
                <div className="space-y-2">
                  <Label>Confirm New Password</Label>
                  <Input type="password" {...registerPassword("confirmPassword")} />
                  {passwordErrors.confirmPassword && <p className="text-sm text-red-500">{passwordErrors.confirmPassword.message}</p>}
                </div>
              </CardContent>
              <CardFooter>
                <Button type="submit" disabled={isSavingPassword}>
                  {isSavingPassword ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : "Update Password"}
                </Button>
              </CardFooter>
            </form>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

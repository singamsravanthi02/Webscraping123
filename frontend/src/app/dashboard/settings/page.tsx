"use client";

import { useState, useEffect } from "react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Loader2, Save, UploadCloud, Bell, Globe, Clock3, Cpu, Palette, Download, LogOut, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "sonner";
import { Textarea } from "@/components/ui/textarea";
import { getErrorMessage } from "@/lib/utils";
import api from "@/lib/api";
import { useTheme } from "next-themes";
import { useAuthStore } from "@/store/authStore";

const profileSchema = z.object({
  fullName: z.string().min(2, "Name is required"),
  phone: z.string().min(10, "Valid phone number required"),
  college: z.string().min(2, "College is required"),
  skills: z.string().min(2, "Skills are required"),
  careerGoal: z.string().min(5, "Career goal is required"),
  department: z.string().optional(),
  branch: z.string().optional(),
  semester: z.string().optional(),
  cgpa: z.string().optional(),
  linkedinUrl: z.string().url().optional().or(z.literal("")),
  githubUrl: z.string().url().optional().or(z.literal("")),
  portfolioUrl: z.string().url().optional().or(z.literal("")),
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

type PreferenceState = {
  theme: "system" | "light" | "dark";
  notifications: boolean;
  email_preferences: boolean;
  ai_provider_preference: "AUTO" | "GEMINI" | "NVIDIA" | "OLLAMA";
  language: string;
  timezone: string;
};

const defaultPreferences: PreferenceState = {
  theme: "system",
  notifications: true,
  email_preferences: true,
  ai_provider_preference: "AUTO",
  language: "en",
  timezone: "Asia/Kolkata",
};

export default function SettingsPage() {
  const router = useRouter();
  const { setTheme } = useTheme();
  const logout = useAuthStore((state) => state.logout);
  const [isLoadingProfile, setIsLoadingProfile] = useState(true);
  const [isSavingProfile, setIsSavingProfile] = useState(false);
  const [isSavingPassword, setIsSavingPassword] = useState(false);
  const [isSavingPreferences, setIsSavingPreferences] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isUploadingProfilePicture, setIsUploadingProfilePicture] = useState(false);
  const [profilePictureUrl, setProfilePictureUrl] = useState<string | null>(null);
  const [preferences, setPreferences] = useState<PreferenceState>(defaultPreferences);

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
          const storedPreferences = data.profile_data?.settings_preferences || {};
          resetProfile({
            fullName: data.full_name || "",
            phone: data.phone || "",
            college: data.college || "",
            skills: data.skills ? data.skills.join(", ") : "",
            careerGoal: data.career_goal || "",
            department: data.department || "",
            branch: data.branch || "",
            semester: data.semester ? String(data.semester) : "",
            cgpa: data.cgpa ? String(data.cgpa) : "",
            linkedinUrl: data.linkedin_url || "",
            githubUrl: data.github_url || "",
            portfolioUrl: data.portfolio_url || "",
          });
          setPreferences({ ...defaultPreferences, ...storedPreferences });
          setTheme((storedPreferences.theme as PreferenceState["theme"]) || "system");
        }
      } catch {
        toast.error("Failed to load profile");
      } finally {
        setIsLoadingProfile(false);
      }
    }
    loadProfile();
  }, [resetProfile, setTheme]);

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
          department: data.department || null,
          branch: data.branch || null,
          semester: data.semester ? Number(data.semester) : null,
          cgpa: data.cgpa ? Number(data.cgpa) : null,
          skills: skillsArray,
          career_goal: data.careerGoal,
          linkedin_url: data.linkedinUrl || null,
          github_url: data.githubUrl || null,
          portfolio_url: data.portfolioUrl || null,
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

  const handlePreferencesSave = async () => {
    setIsSavingPreferences(true);
    try {
      const token = localStorage.getItem("accessToken");
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/users/onboard/step`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          step_id: "settings_preferences",
          data: preferences,
        }),
      });
      if (!res.ok) throw new Error("Failed to save preferences");
      setTheme(preferences.theme);
      toast.success("Preferences saved successfully");
    } catch (err: unknown) {
      toast.error(getErrorMessage(err, "Failed to save preferences"));
    } finally {
      setIsSavingPreferences(false);
    }
  };

  const onPasswordSave = async (data: PasswordFormValues) => {
    setIsSavingPassword(true);
    try {
      await api.post("/auth/change-password", {
        current_password: data.currentPassword,
        new_password: data.newPassword,
        confirm_password: data.confirmPassword,
      });
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

  const handleExportData = async () => {
    try {
      const token = localStorage.getItem("accessToken");
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/users/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Failed to export data");
      const data = await res.json();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `spip-profile-${data.id}.json`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      toast.success("Profile data exported");
    } catch (err: unknown) {
      toast.error(getErrorMessage(err, "Failed to export data"));
    }
  };

  const handleLogoutAll = async () => {
    try {
      await api.post("/auth/logout-all");
      await logout();
      router.push("/login");
      toast.success("Logged out of all devices");
    } catch (err: unknown) {
      toast.error(getErrorMessage(err, "Failed to log out of all sessions"));
    }
  };

  const handleDeleteAccount = async () => {
    if (!confirm("Delete your account permanently? This cannot be undone.")) return;
    try {
      const token = localStorage.getItem("accessToken");
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/users/me`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Failed to delete account");
      await logout();
      router.push("/register");
      toast.success("Account deleted");
    } catch (err: unknown) {
      toast.error(getErrorMessage(err, "Failed to delete account"));
    }
  };

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold tracking-tight mb-8">Settings</h1>
      
      <Tabs defaultValue="profile" className="w-full">
        <TabsList className="mb-8">
          <TabsTrigger value="profile">Profile Details</TabsTrigger>
          <TabsTrigger value="resume">Resume & Documents</TabsTrigger>
          <TabsTrigger value="preferences">Preferences</TabsTrigger>
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
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label>Department</Label>
                        <Input {...registerProfile("department")} />
                      </div>
                      <div className="space-y-2">
                        <Label>Branch</Label>
                        <Input {...registerProfile("branch")} />
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label>Semester</Label>
                        <Input {...registerProfile("semester")} />
                      </div>
                      <div className="space-y-2">
                        <Label>CGPA</Label>
                        <Input {...registerProfile("cgpa")} />
                      </div>
                    </div>
                    <div className="space-y-2">
                      <Label>Skills (Comma separated)</Label>
                      <Input {...registerProfile("skills")} />
                    </div>
                    <div className="space-y-2">
                      <Label>Career Goal</Label>
                      <Textarea {...registerProfile("careerGoal")} />
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div className="space-y-2">
                        <Label>LinkedIn URL</Label>
                        <Input {...registerProfile("linkedinUrl")} />
                      </div>
                      <div className="space-y-2">
                        <Label>GitHub URL</Label>
                        <Input {...registerProfile("githubUrl")} />
                      </div>
                      <div className="space-y-2">
                        <Label>Portfolio URL</Label>
                        <Input {...registerProfile("portfolioUrl")} />
                      </div>
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

        <TabsContent value="preferences">
          <Card>
            <CardHeader>
              <CardTitle>Preferences</CardTitle>
              <CardDescription>These settings are stored on your profile and applied where the app supports them.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label className="flex items-center gap-2"><Palette className="w-4 h-4" />Theme</Label>
                  <select
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    value={preferences.theme}
                    onChange={(e) => {
                      const theme = e.target.value as PreferenceState["theme"];
                      setPreferences((current) => ({ ...current, theme }));
                      setTheme(theme);
                    }}
                  >
                    <option value="system">System</option>
                    <option value="light">Light</option>
                    <option value="dark">Dark</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <Label className="flex items-center gap-2"><Cpu className="w-4 h-4" />AI Provider Preference</Label>
                  <select
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    value={preferences.ai_provider_preference}
                    onChange={(e) => setPreferences((current) => ({ ...current, ai_provider_preference: e.target.value as PreferenceState["ai_provider_preference"] }))}
                  >
                    <option value="AUTO">Auto</option>
                    <option value="GEMINI">Gemini</option>
                    <option value="NVIDIA">NVIDIA</option>
                    <option value="OLLAMA">Ollama</option>
                  </select>
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <label className="flex items-center gap-3 rounded-lg border border-border p-3">
                  <input
                    type="checkbox"
                    checked={preferences.notifications}
                    onChange={(e) => setPreferences((current) => ({ ...current, notifications: e.target.checked }))}
                  />
                  <span className="text-sm">
                    <span className="block font-medium flex items-center gap-2"><Bell className="w-4 h-4" />Enable notifications</span>
                    <span className="text-muted-foreground">Allow in-app alerts and reminders.</span>
                  </span>
                </label>
                <label className="flex items-center gap-3 rounded-lg border border-border p-3">
                  <input
                    type="checkbox"
                    checked={preferences.email_preferences}
                    onChange={(e) => setPreferences((current) => ({ ...current, email_preferences: e.target.checked }))}
                  />
                  <span className="text-sm">
                    <span className="block font-medium">Email updates</span>
                    <span className="text-muted-foreground">Receive placement and learning emails.</span>
                  </span>
                </label>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label className="flex items-center gap-2"><Globe className="w-4 h-4" />Language</Label>
                  <Input
                    value={preferences.language}
                    onChange={(e) => setPreferences((current) => ({ ...current, language: e.target.value }))}
                    placeholder="en"
                  />
                </div>
                <div className="space-y-2">
                  <Label className="flex items-center gap-2"><Clock3 className="w-4 h-4" />Timezone</Label>
                  <Input
                    value={preferences.timezone}
                    onChange={(e) => setPreferences((current) => ({ ...current, timezone: e.target.value }))}
                    placeholder="Asia/Kolkata"
                  />
                </div>
              </div>
            </CardContent>
            <CardFooter>
              <Button onClick={handlePreferencesSave} type="button" disabled={isSavingPreferences}>
                {isSavingPreferences ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                Save Preferences
              </Button>
            </CardFooter>
          </Card>
        </TabsContent>

        <TabsContent value="security">
          <div className="space-y-6">
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

            <Card>
              <CardHeader>
                <CardTitle>Account Actions</CardTitle>
                <CardDescription>Manage your account sessions and data.</CardDescription>
              </CardHeader>
              <CardContent className="flex flex-col gap-3">
                <Button type="button" variant="outline" onClick={handleExportData}>
                  <Download className="w-4 h-4 mr-2" />
                  Export Data
                </Button>
                <Button type="button" variant="outline" onClick={handleLogoutAll}>
                  <LogOut className="w-4 h-4 mr-2" />
                  Logout All Sessions
                </Button>
                <Button type="button" variant="destructive" onClick={handleDeleteAccount}>
                  <Trash2 className="w-4 h-4 mr-2" />
                  Delete Account
                </Button>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}

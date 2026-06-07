// =============================================================================
// VeriField Nexus — Settings & Profile Page
// =============================================================================
// Tabbed configuration page supporting premium User Profile settings, 
// Change of Password, Avatar customization, and System Trust Engine configurations.
// =============================================================================

"use client";

import { useState, useEffect, useRef } from "react";
import { 
  Settings as SettingsIcon, Save, Loader2, ShieldCheck, MapPin, 
  Image as ImageIcon, Clock, Check, User as UserIcon, Lock, Key, Mail, 
  Building, Eye, EyeOff, CheckCircle2, AlertCircle, Camera, LogOut 
} from "lucide-react";
import { 
  fetchSettings, updateSettings, fetchMe, updateProfile, changePassword, uploadAvatar 
} from "@/lib/api";
import { useToast } from "@/components/Toast";
import type { User } from "@/lib/types";

export default function SettingsPage() {
  const toast = useToast();
  const [activeTab, setActiveTab] = useState<"profile" | "system">("profile");
  
  // --- Profile States ---
  const [user, setUser] = useState<User | null>(null);
  const [fullName, setFullName] = useState("");
  const [avatarUrl, setAvatarUrl] = useState("");
  const [isSavingProfile, setIsSavingProfile] = useState(false);
  const [customAvatarInput, setCustomAvatarInput] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isUploading, setIsUploading] = useState(false);

  const handleAvatarFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size > 5 * 1024 * 1024) {
      toast.error("File Too Large", "Profile picture must be under 5MB.");
      return;
    }

    setIsUploading(true);
    try {
      const res = await uploadAvatar(file);
      setAvatarUrl(res.avatar_url);
      toast.success("Image Uploaded", "Temporary preview updated. Don't forget to click Save Profile Details!");
    } catch (err: any) {
      console.error("Failed to upload avatar:", err);
      toast.error("Upload Failed", err.message || "Could not upload image file.");
    } finally {
      setIsUploading(false);
    }
  };

  // --- Password States ---
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isChangingPassword, setIsChangingPassword] = useState(false);

  // --- System Settings States ---
  const [gpsWeight, setGpsWeight] = useState(30);
  const [imageWeight, setImageWeight] = useState(40);
  const [frequencyWeight, setFrequencyWeight] = useState(30);
  const [gpsMaxDistance, setGpsMaxDistance] = useState(5.0);
  const [maxSubmissions, setMaxSubmissions] = useState(10);
  const [imageHashThreshold, setImageHashThreshold] = useState(12);
  const [suspiciousHoursStart, setSuspiciousHoursStart] = useState(2);
  const [suspiciousHoursEnd, setSuspiciousHoursEnd] = useState(5);
  
  const [isLoading, setIsLoading] = useState(true);
  const [isSavingSystem, setIsSavingSystem] = useState(false);

  useEffect(() => {
    loadAllData();
  }, []);

  const loadAllData = async () => {
    setIsLoading(true);
    try {
      // Load both settings and user details in parallel
      const [settingsData, userData] = await Promise.all([
        fetchSettings().catch(() => null),
        fetchMe().catch(() => null)
      ]);

      if (settingsData) {
        setGpsWeight(settingsData.gps_weight);
        setImageWeight(settingsData.image_weight);
        setFrequencyWeight(settingsData.frequency_weight);
        setGpsMaxDistance(settingsData.gps_max_distance_km);
        setMaxSubmissions(settingsData.max_submissions_per_hour);
        setImageHashThreshold(settingsData.image_hash_threshold);
        setSuspiciousHoursStart(settingsData.suspicious_hours_start);
        setSuspiciousHoursEnd(settingsData.suspicious_hours_end);
      }

      if (userData) {
        setUser(userData);
        setFullName(userData.full_name || "");
        setAvatarUrl(userData.avatar_url || "");
      }
    } catch (err) {
      console.error("Failed to load settings data:", err);
      toast.error("Error Loading", "Could not synchronize server parameters.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!fullName.trim()) {
      toast.error("Validation Error", "Full Name is required.");
      return;
    }
    setIsSavingProfile(true);
    try {
      const updated = await updateProfile({
        full_name: fullName,
        avatar_url: avatarUrl,
      });
      setUser(updated);
      toast.success("Profile Updated", "Your information was saved successfully.");
      
      // Proactively refresh the sidebar / window event if anyone is listening
      if (typeof window !== "undefined") {
        window.dispatchEvent(new Event("vf_profile_updated"));
      }
    } catch (err: any) {
      console.error("Failed to update profile:", err);
      toast.error("Update Failed", err.message || "Unable to update profile fields.");
    } finally {
      setIsSavingProfile(false);
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword.length < 8) {
      toast.error("Weak Password", "New password must be at least 8 characters.");
      return;
    }
    if (newPassword !== confirmPassword) {
      toast.error("Mismatch", "Passwords do not match.");
      return;
    }

    setIsChangingPassword(true);
    try {
      await changePassword(newPassword);
      toast.success("Password Updated", "Security credentials changed successfully.");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err: any) {
      console.error("Failed to change password:", err);
      toast.error("Password Reset Failed", err.message || "Unable to reset user credentials.");
    } finally {
      setIsChangingPassword(false);
    }
  };

  const handleSaveSystem = async () => {
    setIsSavingSystem(true);
    try {
      await updateSettings({
        gps_weight: gpsWeight,
        image_weight: imageWeight,
        frequency_weight: frequencyWeight,
        gps_max_distance_km: gpsMaxDistance,
        max_submissions_per_hour: maxSubmissions,
        image_hash_threshold: imageHashThreshold,
        suspicious_hours_start: suspiciousHoursStart,
        suspicious_hours_end: suspiciousHoursEnd,
      });
      toast.success("Settings Saved", "Weights and parameters updated successfully.");
      // Reload settings to get normalized weights if total was not 100
      const settingsData = await fetchSettings();
      setGpsWeight(settingsData.gps_weight);
      setImageWeight(settingsData.image_weight);
      setFrequencyWeight(settingsData.frequency_weight);
    } catch (err: any) {
      console.error("Failed to save settings:", err);
      toast.error("Save Failed", err.message || "Could not save system settings.");
    } finally {
      setIsSavingSystem(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="animate-spin text-emerald-500" size={32} />
      </div>
    );
  }

  const systemTotalWeight = gpsWeight + imageWeight + frequencyWeight;

  return (
    <div className="space-y-6 max-w-4xl pb-12">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 animate-fade-in-up">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-text-primary)] tracking-tight">Administration & Profile</h1>
          <p className="text-[var(--color-text-secondary)] text-sm mt-1">
            Manage your personal settings, password, and global carbon engine weights
          </p>
        </div>
      </div>

      {/* Tabs Selector */}
      <div className="flex border-b border-[var(--color-border)] gap-2">
        <button
          onClick={() => setActiveTab("profile")}
          className={`px-5 py-3 text-sm font-semibold border-b-2 transition-all flex items-center gap-2 ${
            activeTab === "profile"
              ? "border-emerald-500 text-emerald-400"
              : "border-transparent text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:border-[var(--color-border)]"
          }`}
        >
          <UserIcon size={16} />
          My Profile & Password
        </button>
        <button
          onClick={() => setActiveTab("system")}
          className={`px-5 py-3 text-sm font-semibold border-b-2 transition-all flex items-center gap-2 ${
            activeTab === "system"
              ? "border-emerald-500 text-emerald-400"
              : "border-transparent text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:border-[var(--color-border)]"
          }`}
        >
          <SettingsIcon size={16} />
          System Trust Parameters
        </button>
      </div>

      {/* =======================================================================
          TAB 1: PROFILE & PASSWORD SETTINGS
          ======================================================================= */}
      {activeTab === "profile" && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 animate-fade-in">
          {/* Left / Mid Column: Profile Information Form */}
          <div className="md:col-span-2 space-y-6">
            <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl p-6 shadow-sm">
              <div className="flex items-center gap-3 mb-6 border-b border-[var(--color-border)] pb-4">
                <UserIcon className="text-emerald-500" size={20} />
                <h2 className="text-sm font-bold uppercase tracking-wider text-[var(--color-text-primary)]">
                  Personal Details
                </h2>
              </div>

              <form onSubmit={handleSaveProfile} className="space-y-6">
                {/* Avatar Preview and Selector */}
                <div className="space-y-4">
                  <label className="block text-xs font-semibold text-[var(--color-text-secondary)]">
                    Profile Picture
                  </label>
                  <div className="flex flex-col sm:flex-row gap-4 items-center sm:items-start">
                    <div 
                      onClick={() => fileInputRef.current?.click()}
                      className="relative group shrink-0 cursor-pointer"
                      title="Click to upload custom picture"
                    >
                      <div className="w-20 h-20 rounded-full border-2 border-emerald-500/20 overflow-hidden bg-emerald-500/5 flex items-center justify-center">
                        {isUploading ? (
                          <Loader2 className="animate-spin text-emerald-500" size={24} />
                        ) : avatarUrl ? (
                          <img src={avatarUrl} alt="Avatar Preview" className="w-full h-full object-cover" />
                        ) : (
                          <UserIcon size={36} className="text-emerald-500/40" />
                        )}
                      </div>
                      <div className="absolute inset-0 bg-black/60 rounded-full opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                        <Camera size={18} className="text-white" />
                      </div>
                    </div>

                    <input
                      type="file"
                      ref={fileInputRef}
                      onChange={handleAvatarFileChange}
                      accept="image/*"
                      className="hidden"
                    />

                    <div className="space-y-3 flex-1 w-full">
                      <div className="flex flex-wrap gap-2 items-center">
                        <button
                          type="button"
                          disabled={isUploading}
                          onClick={() => fileInputRef.current?.click()}
                          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-emerald-500/30 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 hover:text-emerald-300 font-semibold text-[10px] transition-all disabled:opacity-50 cursor-pointer"
                        >
                          {isUploading ? <Loader2 className="animate-spin" size={12} /> : <Camera size={12} />}
                          <span>Upload Custom Photo</span>
                        </button>
                      </div>

                      {/* Custom URL switch */}
                      <div className="pt-1">
                        <button
                          type="button"
                          onClick={() => setCustomAvatarInput(!customAvatarInput)}
                          className="text-[10px] text-emerald-400 hover:text-emerald-300 transition-colors font-medium flex items-center gap-1"
                        >
                          {customAvatarInput ? "Hide custom URL field" : "Provide custom picture URL..."}
                        </button>
                        {customAvatarInput && (
                          <input
                            type="url"
                            value={avatarUrl}
                            onChange={(e) => setAvatarUrl(e.target.value)}
                            placeholder="https://example.com/avatar.jpg"
                            className="mt-2 w-full text-xs bg-[var(--color-background)] border border-[var(--color-border)] rounded-xl p-2.5 text-[var(--color-text-primary)] focus:outline-none focus:border-emerald-500"
                          />
                        )}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Form fields */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-[var(--color-text-secondary)] mb-2">
                      Full Name
                    </label>
                    <input
                      type="text"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      placeholder="e.g. Segun Oluwole"
                      className="w-full text-xs bg-[var(--color-background)] border border-[var(--color-border)] rounded-xl p-3 text-[var(--color-text-primary)] focus:outline-none focus:border-emerald-500"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-[var(--color-text-secondary)] mb-2">
                      Email Address
                    </label>
                    <div className="relative">
                      <Mail className="absolute left-3 top-3 text-[var(--color-text-muted)]" size={16} />
                      <input
                        type="text"
                        disabled
                        value={user?.email || ""}
                        className="w-full pl-10 text-xs bg-slate-900/40 border border-[var(--color-border)] rounded-xl p-3 text-[var(--color-text-muted)] cursor-not-allowed opacity-80"
                      />
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-[var(--color-text-secondary)] mb-2">
                      Role Privilege
                    </label>
                    <div className="relative">
                      <ShieldCheck className="absolute left-3 top-3 text-[var(--color-text-muted)]" size={16} />
                      <input
                        type="text"
                        disabled
                        value={user?.role === "admin" ? "Organization Admin" : "Field Agent"}
                        className="w-full pl-10 text-xs bg-slate-900/40 border border-[var(--color-border)] rounded-xl p-3 text-[var(--color-text-muted)] cursor-not-allowed opacity-80 uppercase tracking-wider"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-[var(--color-text-secondary)] mb-2">
                      Organization Tenant
                    </label>
                    <div className="relative">
                      <Building className="absolute left-3 top-3 text-[var(--color-text-muted)]" size={16} />
                      <input
                        type="text"
                        disabled
                        value={user?.organization || "VeriField"}
                        className="w-full pl-10 text-xs bg-slate-900/40 border border-[var(--color-border)] rounded-xl p-3 text-[var(--color-text-muted)] cursor-not-allowed opacity-80 font-bold"
                      />
                    </div>
                  </div>
                </div>

                {/* Save button */}
                <div className="flex justify-end pt-2">
                  <button
                    type="submit"
                    disabled={isSavingProfile}
                    className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-emerald-500 text-white font-medium hover:bg-emerald-600 transition-colors shadow-lg shadow-emerald-500/20 disabled:opacity-50"
                  >
                    {isSavingProfile ? <Loader2 className="animate-spin" size={18} /> : <Save size={18} />}
                    {isSavingProfile ? "Saving Profile..." : "Save Profile Details"}
                  </button>
                </div>
              </form>
            </div>

            {/* Change Password Card */}
            <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl p-6 shadow-sm">
              <div className="flex items-center gap-3 mb-6 border-b border-[var(--color-border)] pb-4">
                <Lock className="text-emerald-500" size={20} />
                <h2 className="text-sm font-bold uppercase tracking-wider text-[var(--color-text-primary)]">
                  Change Password
                </h2>
              </div>

              <form onSubmit={handleChangePassword} className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-[var(--color-text-secondary)] mb-2">
                      New Password
                    </label>
                    <div className="relative">
                      <Key className="absolute left-3 top-3 text-[var(--color-text-muted)]" size={16} />
                      <input
                        type={showPassword ? "text" : "password"}
                        value={newPassword}
                        onChange={(e) => setNewPassword(e.target.value)}
                        placeholder="At least 8 characters"
                        className="w-full pl-10 pr-10 text-xs bg-[var(--color-background)] border border-[var(--color-border)] rounded-xl p-3 text-[var(--color-text-primary)] focus:outline-none focus:border-emerald-500"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute right-3 top-3 text-[var(--color-text-muted)] hover:text-slate-200 transition-colors"
                      >
                        {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                      </button>
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-[var(--color-text-secondary)] mb-2">
                      Confirm New Password
                    </label>
                    <div className="relative">
                      <Key className="absolute left-3 top-3 text-[var(--color-text-muted)]" size={16} />
                      <input
                        type={showPassword ? "text" : "password"}
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        placeholder="Repeat new password"
                        className="w-full pl-10 pr-10 text-xs bg-[var(--color-background)] border border-[var(--color-border)] rounded-xl p-3 text-[var(--color-text-primary)] focus:outline-none focus:border-emerald-500"
                      />
                    </div>
                  </div>
                </div>

                {/* Password Strength Indicator */}
                {newPassword && (
                  <div className="p-3 rounded-xl bg-slate-900/30 border border-[var(--color-border)] space-y-2">
                    <div className="flex justify-between items-center text-[10px]">
                      <span className="text-[var(--color-text-secondary)]">Security strength:</span>
                      <span className={`font-extrabold ${
                        newPassword.length >= 12 ? "text-emerald-400" : newPassword.length >= 8 ? "text-amber-400" : "text-red-400"
                      }`}>
                        {newPassword.length >= 12 ? "Strong" : newPassword.length >= 8 ? "Medium" : "Too Short"}
                      </span>
                    </div>
                    <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                      <div 
                        className={`h-full transition-all duration-300 ${
                          newPassword.length >= 12 ? "bg-emerald-500 w-full" : newPassword.length >= 8 ? "bg-amber-500 w-2/3" : "bg-red-500 w-1/3"
                        }`}
                      />
                    </div>
                  </div>
                )}

                <div className="flex justify-end pt-2">
                  <button
                    type="submit"
                    disabled={isChangingPassword || !newPassword || newPassword !== confirmPassword}
                    className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-emerald-500 text-white font-medium hover:bg-emerald-600 transition-colors shadow-lg shadow-emerald-500/20 disabled:opacity-50"
                  >
                    {isChangingPassword ? <Loader2 className="animate-spin" size={18} /> : <Lock size={18} />}
                    {isChangingPassword ? "Saving Credentials..." : "Update Security Password"}
                  </button>
                </div>
              </form>
            </div>
          </div>

          {/* Right Column: Settings & Configuration Guide */}
          <div className="space-y-6">
            <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl p-5 shadow-sm space-y-4 animate-fade-in">
              <div className="flex items-center gap-2 border-b border-[var(--color-border)] pb-3">
                <SettingsIcon className="text-emerald-500" size={18} />
                <h3 className="text-xs font-extrabold uppercase tracking-wider text-[var(--color-text-primary)]">
                  Settings Guide
                </h3>
              </div>
              <p className="text-[10px] text-[var(--color-text-secondary)] leading-relaxed">
                Quick reference guide to managing your personal profile and adjusting global system trust engines:
              </p>
              
              <div className="p-3 bg-emerald-500/5 rounded-xl border border-emerald-500/10 space-y-1 text-[10px]">
                <div className="flex gap-2 items-center text-emerald-400 font-bold mb-1">
                  <UserIcon size={12} className="shrink-0" />
                  <span>Profile Customization</span>
                </div>
                <p className="text-[var(--color-text-secondary)] leading-relaxed">
                  Upload a custom avatar file or paste a URL. Click <strong>Save Profile Details</strong> to persist your name and image globally.
                </p>
              </div>

              <div className="p-3 bg-emerald-500/5 rounded-xl border border-emerald-500/10 space-y-1 text-[10px]">
                <div className="flex gap-2 items-center text-emerald-400 font-bold mb-1">
                  <Lock size={12} className="shrink-0" />
                  <span>Password Upgrades</span>
                </div>
                <p className="text-[var(--color-text-secondary)] leading-relaxed">
                  Protect your account by inputting an 8+ character password. Strong indicators will turn green once optimal complexity thresholds are satisfied.
                </p>
              </div>

              <div className="p-3 bg-emerald-500/5 rounded-xl border border-emerald-500/10 space-y-1 text-[10px]">
                <div className="flex gap-2 items-center text-emerald-400 font-bold mb-1">
                  <SettingsIcon size={12} className="shrink-0 animate-spin-slow" />
                  <span>Trust Calibration</span>
                </div>
                <p className="text-[var(--color-text-secondary)] leading-relaxed">
                  Org Admins can fine-tune verification dimension weights. Weights will be automatically normalized to 100% on saving to preserve proportional scoring.
                </p>
              </div>
            </div>

            {/* Session Control / Sign Out */}
            <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl p-5 shadow-sm space-y-4 animate-fade-in">
              <div className="flex items-center gap-2 border-b border-[var(--color-border)] pb-3">
                <LogOut className="text-red-500" size={18} />
                <h3 className="text-xs font-extrabold uppercase tracking-wider text-[var(--color-text-primary)]">
                  Session Control
                </h3>
              </div>
              <p className="text-[10px] text-[var(--color-text-secondary)] leading-relaxed">
                Log out of your current session. You will need to enter your credentials to log back in.
              </p>
              <button
                type="button"
                onClick={() => {
                  localStorage.removeItem("vf_token");
                  window.location.href = "/login";
                }}
                className="w-full flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-red-500/10 hover:bg-red-500 text-red-400 hover:text-white font-medium transition-all shadow-xs border border-red-500/20"
              >
                <LogOut size={16} />
                <span>Sign Out Account</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* =======================================================================
          TAB 2: SYSTEM trust weights (EXISTING LOGIC)
          ======================================================================= */}
      {activeTab === "system" && (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-3 animate-fade-in">
          {/* Left Side: Sliders */}
          <div className="md:col-span-2 space-y-6">
            
            {/* Section 1: Trust Weights */}
            <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl p-6 shadow-sm">
              <div className="flex items-center gap-3 mb-6 border-b border-[var(--color-border)] pb-4">
                <SettingsIcon className="text-emerald-500" size={20} />
                <h2 className="text-sm font-bold uppercase tracking-wider text-[var(--color-text-primary)]">Dimension Weights</h2>
              </div>
              
              <div className="space-y-6">
                <div>
                  <label className="block text-xs font-semibold text-[var(--color-text-secondary)] mb-2 flex justify-between">
                    <span>GPS Verification Weight</span>
                    <span className="text-emerald-500 font-extrabold">{gpsWeight}%</span>
                  </label>
                  <input 
                    type="range" 
                    min="0" max="100" 
                    value={gpsWeight} 
                    onChange={(e) => setGpsWeight(Number(e.target.value))}
                    className="w-full accent-emerald-500" 
                  />
                  <div className="flex justify-between text-[10px] text-[var(--color-text-muted)] mt-1">
                    <span>0%</span><span>100%</span>
                  </div>
                </div>
                
                <div>
                  <label className="block text-xs font-semibold text-[var(--color-text-secondary)] mb-2 flex justify-between">
                    <span>Image Anomaly Detection Weight</span>
                    <span className="text-emerald-500 font-extrabold">{imageWeight}%</span>
                  </label>
                  <input 
                    type="range" 
                    min="0" max="100" 
                    value={imageWeight} 
                    onChange={(e) => setImageWeight(Number(e.target.value))}
                    className="w-full accent-emerald-500" 
                  />
                  <div className="flex justify-between text-[10px] text-[var(--color-text-muted)] mt-1">
                    <span>0%</span><span>100%</span>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-[var(--color-text-secondary)] mb-2 flex justify-between">
                    <span>Frequency Heuristic Weight</span>
                    <span className="text-emerald-500 font-extrabold">{frequencyWeight}%</span>
                  </label>
                  <input 
                    type="range" 
                    min="0" max="100" 
                    value={frequencyWeight} 
                    onChange={(e) => setFrequencyWeight(Number(e.target.value))}
                    className="w-full accent-emerald-500" 
                  />
                  <div className="flex justify-between text-[10px] text-[var(--color-text-muted)] mt-1">
                    <span>0%</span><span>100%</span>
                  </div>
                </div>
                
                <div className={`p-4 rounded-xl border transition-colors ${systemTotalWeight === 100 ? 'bg-emerald-500/5 border-emerald-500/10 text-emerald-400' : 'bg-amber-500/5 border-amber-500/10 text-amber-400'}`}>
                  <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${systemTotalWeight === 100 ? 'bg-emerald-500' : 'bg-amber-500'}`} />
                    <p className="text-xs font-bold uppercase tracking-wider">Total Weight: {systemTotalWeight}%</p>
                  </div>
                  {systemTotalWeight !== 100 && (
                    <p className="text-[10px] text-[var(--color-text-secondary)] mt-1.5 leading-normal">
                      Note: Weights will be automatically normalized to equal exactly 100% when saved to preserve proportional scoring.
                    </p>
                  )}
                </div>
              </div>
            </div>

            {/* Section 2: Platform Threshold Parameters */}
            <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl p-6 shadow-sm">
              <div className="flex items-center gap-3 mb-6 border-b border-[var(--color-border)] pb-4">
                <ShieldCheck className="text-emerald-500" size={20} />
                <h2 className="text-sm font-bold uppercase tracking-wider text-[var(--color-text-primary)]">Validation & Anomaly Thresholds</h2>
              </div>
              
              <div className="space-y-6">
                {/* GPS max distance */}
                <div>
                  <label className="block text-xs font-semibold text-[var(--color-text-secondary)] mb-1 flex justify-between">
                    <span className="flex items-center gap-1.5"><MapPin size={12} className="text-emerald-500" /> Max Property Distance Radius</span>
                    <span className="text-emerald-500 font-extrabold">{gpsMaxDistance} km</span>
                  </label>
                  <p className="text-[10px] text-[var(--color-text-muted)] mb-2.5 leading-relaxed">
                    Allowed boundary between submissions and property center before applying distance penalties.
                  </p>
                  <input 
                    type="range" 
                    min="0.5" max="25" step="0.5"
                    value={gpsMaxDistance} 
                    onChange={(e) => setGpsMaxDistance(Number(e.target.value))}
                    className="w-full accent-emerald-500" 
                  />
                  <div className="flex justify-between text-[10px] text-[var(--color-text-muted)] mt-1">
                    <span>0.5 km</span><span>25.0 km</span>
                  </div>
                </div>

                {/* Max Hourly submissions */}
                <div>
                  <label className="block text-xs font-semibold text-[var(--color-text-secondary)] mb-1 flex justify-between">
                    <span className="flex items-center gap-1.5"><Clock size={12} className="text-emerald-500" /> Max Submissions per Hour</span>
                    <span className="text-emerald-500 font-extrabold">{maxSubmissions} / hr</span>
                  </label>
                  <p className="text-[10px] text-[var(--color-text-muted)] mb-2.5 leading-relaxed">
                    Hourly limit per agent. Exceeding this flags automated bot patterns & frequency alerts.
                  </p>
                  <input 
                    type="range" 
                    min="2" max="50" step="1"
                    value={maxSubmissions} 
                    onChange={(e) => setMaxSubmissions(Number(e.target.value))}
                    className="w-full accent-emerald-500" 
                  />
                  <div className="flex justify-between text-[10px] text-[var(--color-text-muted)] mt-1">
                    <span>2 / hr</span><span>50 / hr</span>
                  </div>
                </div>

                {/* Image similarity threshold */}
                <div>
                  <label className="block text-xs font-semibold text-[var(--color-text-secondary)] mb-1 flex justify-between">
                    <span className="flex items-center gap-1.5"><ImageIcon size={12} className="text-emerald-500" /> Image Similarity Threshold (Hamming)</span>
                    <span className="text-emerald-500 font-extrabold">{imageHashThreshold} bits</span>
                  </label>
                  <p className="text-[10px] text-[var(--color-text-muted)] mb-2.5 leading-relaxed">
                    Maximum bit differences in perceptual hashes to flag duplicate/similar images. Lower value is stricter.
                  </p>
                  <input 
                    type="range" 
                    min="4" max="32" step="1"
                    value={imageHashThreshold} 
                    onChange={(e) => setImageHashThreshold(Number(e.target.value))}
                    className="w-full accent-emerald-500" 
                  />
                  <div className="flex justify-between text-[10px] text-[var(--color-text-muted)] mt-1">
                    <span>4 bits (Strictest)</span><span>32 bits (Lenient)</span>
                  </div>
                </div>

                {/* Suspicious Hours */}
                <div className="pt-2">
                  <label className="block text-xs font-semibold text-[var(--color-text-secondary)] mb-1">
                    Suspicious Hours Window
                  </label>
                  <p className="text-[10px] text-[var(--color-text-muted)] mb-3 leading-relaxed">
                    Activities captured within this overnight window receive low-severity time outlier flags.
                  </p>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-[10px] text-[var(--color-text-secondary)] mb-1 font-semibold">Start Hour</label>
                      <select
                        value={suspiciousHoursStart}
                        onChange={(e) => setSuspiciousHoursStart(Number(e.target.value))}
                        className="w-full text-xs bg-[var(--color-background)] border border-[var(--color-border)] rounded-xl p-2 text-[var(--color-text-primary)] focus:outline-none focus:border-emerald-500"
                      >
                        {Array.from({ length: 24 }).map((_, i) => (
                          <option key={i} value={i}>{String(i).padStart(2, "0")}:00 ({i < 12 ? "AM" : "PM"})</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-[10px] text-[var(--color-text-secondary)] mb-1 font-semibold">End Hour</label>
                      <select
                        value={suspiciousHoursEnd}
                        onChange={(e) => setSuspiciousHoursEnd(Number(e.target.value))}
                        className="w-full text-xs bg-[var(--color-background)] border border-[var(--color-border)] rounded-xl p-2 text-[var(--color-text-primary)] focus:outline-none focus:border-emerald-500"
                      >
                        {Array.from({ length: 24 }).map((_, i) => (
                          <option key={i} value={i}>{String(i).padStart(2, "0")}:00 ({i < 12 ? "AM" : "PM"})</option>
                        ))}
                      </select>
                    </div>
                  </div>
                </div>

              </div>
            </div>
          </div>

          {/* Right Side: Informative Card */}
          <div className="space-y-6">
            <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl p-5 shadow-sm space-y-4">
              <h3 className="text-xs font-extrabold uppercase tracking-wider text-[var(--color-text-primary)] mb-3">Audit Trail Policy</h3>
              <ul className="space-y-3">
                <li className="flex gap-2.5 items-start text-[10px] text-[var(--color-text-secondary)] leading-relaxed">
                  <Check size={14} className="text-emerald-500 shrink-0 mt-0.5" />
                  <span>Modifying weight percentages recalculates the trust indices of pending or future calculations dynamically.</span>
                </li>
                <li className="flex gap-2.5 items-start text-[10px] text-[var(--color-text-secondary)] leading-relaxed">
                  <Check size={14} className="text-emerald-500 shrink-0 mt-0.5" />
                  <span>Adjusting parameters immediately calibrates the real-time submission ingestion pipeline.</span>
                </li>
              </ul>
              
              {/* Save Button for system tab */}
              <div className="pt-2">
                <button 
                  onClick={handleSaveSystem}
                  disabled={isSavingSystem}
                  className="w-full flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-emerald-500 text-white font-medium hover:bg-emerald-600 transition-colors shadow-lg shadow-emerald-500/20 disabled:opacity-50"
                >
                  {isSavingSystem ? <Loader2 className="animate-spin" size={18} /> : <Save size={18} />}
                  {isSavingSystem ? "Saving weights..." : "Save Weight Settings"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// VeriField Nexus — Super Admin Governance Portal
// =============================================================================
// Platform-owner governance panel to manage multi-tenant access, approve/reject
// requests, enable/disable users, and audit platform activities globally.
// =============================================================================

"use client";

import { useState, useEffect } from "react";
import { useToast } from "@/components/Toast";
import { useRouter } from "next/navigation";
import { 
  ShieldCheck, 
  Users, 
  Building2, 
  FileCheck2, 
  Activity, 
  History, 
  Power, 
  CheckCircle2, 
  XCircle, 
  Loader2, 
  Globe, 
  Mail, 
  Phone, 
  MapPin, 
  Sparkles, 
  Copy, 
  Check,
  TrendingUp,
  Cpu,
  Database,
  Trash2,
  Eye,
  Settings,
  Key,
  User as UserIcon
} from "lucide-react";
import { WorkspaceProvider, useWorkspace } from "@/context/WorkspaceContext";
import { safeStorage } from "@/lib/storage";
import { 
  fetchAccessRequests, 
  approveAccessRequest, 
  rejectAccessRequest, 
  deleteAccessRequest,
  fetchAllOrganizations, 
  fetchAllUsersGlobal, 
  toggleUserSuspension, 
  fetchAuditLogs,
  deleteOrganization,
  fetchOrganizationAnalytics,
  changePassword,
  forceResetUserPassword,
  fetchGlobalAnalytics
} from "@/lib/api";

type Tab = "leads" | "organizations" | "users" | "analytics" | "audit";

function SuperAdminDashboard() {
  const { user, isLoading } = useWorkspace();
  const router = useRouter();
  
  // Navigation
  const [activeTab, setActiveTab] = useState<Tab>("leads");
  
  // Data States
  const [requests, setRequests] = useState<any[]>([]);
  const [orgs, setOrgs] = useState<any[]>([]);
  const [users, setUsers] = useState<any[]>([]);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [mrvStats, setMrvStats] = useState<any>({
    installations: 0,
    avgTrust: 0.0,
    tCO2: 0.0,
    activeOrgs: 0,
    methodologies: {}
  });

  // Action states
  const [loadingData, setLoadingData] = useState(false);
  const [processingId, setProcessingId] = useState<string | null>(null);
  const [copiedText, setCopiedText] = useState(false);
  
  // Approval Credentials Popup State
  const [approvedCredentials, setApprovedCredentials] = useState<{
    orgName: string;
    email: string;
    tempPw: string;
  } | null>(null);

  // New features states
  const [selectedUserForDetails, setSelectedUserForDetails] = useState<any | null>(null);
  const [selectedOrgForAnalytics, setSelectedOrgForAnalytics] = useState<any | null>(null);
  const [loadingOrgAnalytics, setLoadingOrgAnalytics] = useState(false);
  const [orgAnalyticsData, setOrgAnalyticsData] = useState<any | null>(null);
  
  const [isPasswordModalOpen, setIsPasswordModalOpen] = useState(false);

  // Password reset for tenant users
  const [selectedOrgForPasswordReset, setSelectedOrgForPasswordReset] = useState<any | null>(null);
  const [resetPasswordUserId, setResetPasswordUserId] = useState<string>("");
  const [resetNewPassword, setResetNewPassword] = useState<string>("");
  const [isResettingPassword, setIsResettingPassword] = useState(false);
  const [resetPasswordError, setResetPasswordError] = useState("");
  const [resetPasswordSuccess, setResetPasswordSuccess] = useState("");
  const [passwordForm, setPasswordForm] = useState({ currentPassword: "", newPassword: "", confirmPassword: "" });
  const [passwordError, setPasswordError] = useState("");
  const [passwordSuccess, setPasswordSuccess] = useState("");
  const [isChangingPassword, setIsChangingPassword] = useState(false);

  // Authenticate user is SUPER_ADMIN
  useEffect(() => {
    if (isLoading) return;
    if (!user || user.role !== "SUPER_ADMIN") {
      router.push("/login?error=unauthorized");
    }
  }, [user, isLoading, router]);

  // Load Data based on active tab
  const loadData = async () => {
    setLoadingData(true);
    try {
      if (activeTab === "leads") {
        const res = await fetchAccessRequests();
        setRequests(res);
      } else if (activeTab === "organizations") {
        const res = await fetchAllOrganizations();
        setOrgs(res);
      } else if (activeTab === "users") {
        const res = await fetchAllUsersGlobal();
        setUsers(res);
      } else if (activeTab === "analytics") {
        // Fetch all data to compile global stats dynamically
        const [o, u, globalStats] = await Promise.all([
          fetchAllOrganizations(),
          fetchAllUsersGlobal(),
          fetchGlobalAnalytics()
        ]);
        setMrvStats(globalStats);
        setOrgs(o);
        setUsers(u);
      } else if (activeTab === "audit") {
        const res = await fetchAuditLogs();
        setAuditLogs(res);
      }
    } catch (err) {
      console.error("Error loading admin data:", err);
    } finally {
      setLoadingData(false);
    }
  };

  useEffect(() => {
    if (user && user.role === "SUPER_ADMIN") {
      loadData();
    }
  }, [activeTab, user]);

  const handleApprove = async (id: string) => {
    setProcessingId(id);
    try {
      const res = await approveAccessRequest(id);
      // Open credentials view modal
      setApprovedCredentials({
        orgName: res.organization_name,
        email: res.org_admin_email,
        tempPw: res.temporary_password
      });
      // Reload active queue
      await loadData();
    } catch (err: any) {
      toast.error('Operation Failed', err.message || "Failed to approve access request.");
    } finally {
      setProcessingId(null);
    }
  };

  const handleReject = async (id: string) => {
    if (!confirm("Are you sure you want to reject this request?")) return;
    setProcessingId(id);
    try {
      await rejectAccessRequest(id);
      await loadData();
    } catch (err: any) {
      toast.error('Operation Failed', err.message || "Failed to reject request.");
    } finally {
      setProcessingId(null);
    }
  };

  const handleDeleteAccessRequest = async (id: string) => {
    if (!confirm("Are you sure you want to permanently delete this access request?")) return;
    setProcessingId(id);
    try {
      await deleteAccessRequest(id);
      await loadData();
    } catch (err: any) {
      toast.error('Operation Failed', err.message || "Failed to delete request.");
    } finally {
      setProcessingId(null);
    }
  };

  const handleToggleSuspension = async (userId: string, currentActive: boolean) => {
    const actionText = currentActive ? "suspend" : "activate";
    if (!confirm(`Are you sure you want to ${actionText} this user's access?`)) return;
    
    setProcessingId(userId);
    try {
      await toggleUserSuspension(userId, !currentActive);
      await loadData();
    } catch (err: any) {
      toast.error('Operation Failed', err.message || "Failed to update user status.");
    } finally {
      setProcessingId(null);
    }
  };

  const handleDeleteOrg = async (orgId: string, orgName: string) => {
    if (!confirm(`Are you sure you want to delete the organization "${orgName}"? Associated users will be suspended.`)) return;
    
    setProcessingId(orgId);
    try {
      await deleteOrganization(orgId);
      toast.success("Organization Deleted", `Organization "${orgName}" has been successfully deleted.`);
      await loadData();
    } catch (err: any) {
      toast.error('Operation Failed', err.message || `Failed to delete organization "${orgName}".`);
    } finally {
      setProcessingId(null);
    }
  };

  const handleViewOrgAnalytics = async (orgId: string, orgName: string) => {
    setSelectedOrgForAnalytics({ id: orgId, name: orgName });
    setLoadingOrgAnalytics(true);
    setOrgAnalyticsData(null);
    try {
      const data = await fetchOrganizationAnalytics(orgId);
      setOrgAnalyticsData(data);
    } catch (err: any) {
      toast.error('Operation Failed', err.message || `Failed to fetch analytics for "${orgName}".`);
      setSelectedOrgForAnalytics(null);
    } finally {
      setLoadingOrgAnalytics(false);
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordError("");
    setPasswordSuccess("");

    if (passwordForm.newPassword.length < 8) {
      setPasswordError("New password must be at least 8 characters long.");
      return;
    }

    if (passwordForm.newPassword !== passwordForm.confirmPassword) {
      setPasswordError("New passwords do not match.");
      return;
    }

    setIsChangingPassword(true);
    try {
      await changePassword({
        old_password: passwordForm.currentPassword,
        new_password: passwordForm.newPassword
      });
      setPasswordSuccess("Password changed successfully.");
      setPasswordForm({ currentPassword: "", newPassword: "", confirmPassword: "" });
      setTimeout(() => {
        setIsPasswordModalOpen(false);
        setPasswordSuccess("");
      }, 1500);
    } catch (err: any) {
      setPasswordError(err.message || "Failed to change password. Please check your current password.");
    } finally {
      setIsChangingPassword(false);
    }
  };

  const handleResetUserPasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setResetPasswordError("");
    setResetPasswordSuccess("");

    if (!resetPasswordUserId) {
      setResetPasswordError("Please select a user.");
      return;
    }

    if (resetNewPassword.length < 8) {
      setResetPasswordError("New password must be at least 8 characters long.");
      return;
    }

    setIsResettingPassword(true);
    try {
      await forceResetUserPassword(resetPasswordUserId, resetNewPassword);
      setResetPasswordSuccess("Password successfully updated!");
      setResetNewPassword("");
      setTimeout(() => {
        setSelectedOrgForPasswordReset(null);
        setResetPasswordUserId("");
        setResetPasswordSuccess("");
      }, 1500);
    } catch (err: any) {
      setResetPasswordError(err.message || "Failed to reset password.");
    } finally {
      setIsResettingPassword(false);
    }
  };

  const handleCopyCredentials = () => {
    if (!approvedCredentials) return;
    const credText = `Email: ${approvedCredentials.email}\nTemporary Password: ${approvedCredentials.tempPw}\nOrganization: ${approvedCredentials.orgName}`;
    navigator.clipboard.writeText(credText);
    setCopiedText(true);
    setTimeout(() => setCopiedText(false), 2000);
  };

  const handleSignOut = () => {
    safeStorage.removeItem("vf_token");
    safeStorage.removeItem("vf_user");
    router.push("/login");
  };

  if (isLoading || !user || user.role !== "SUPER_ADMIN") {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-[#090F10] space-y-3">
        <div className="w-8 h-8 border-2 border-[#00B47A] border-t-transparent rounded-full animate-spin" />
        <p className="text-zinc-500 text-xs font-semibold tracking-tight animate-pulse">
          Resolving Super Admin Authority...
        </p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#090F10] text-[#F8FAF9] flex flex-col font-sans select-none selection:bg-[#00B47A]/30 selection:text-white">
      
      {/* Dynamic glow decoration */}
      <div className="absolute top-0 right-1/4 w-96 h-96 bg-[#00B47A]/5 rounded-full blur-[140px] pointer-events-none" />

      {/* SUPER ADMIN NAVBAR */}
      <header className="sticky top-0 w-full bg-[#0E1617]/90 border-b border-[#213233]/80 z-40 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-md bg-[#00B47A] flex items-center justify-center">
              <ShieldCheck size={16} className="text-black" />
            </div>
            <span className="font-extrabold text-sm tracking-tight">
              VeriField Nexus <span className="text-[#00B47A]">Governance</span>
            </span>
          </div>

          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 bg-[#141F20] px-3 py-1 rounded-full border border-[#213233]">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-400">
                Super Admin Account
              </span>
            </div>
            <button
              onClick={() => {
                setPasswordForm({ currentPassword: "", newPassword: "", confirmPassword: "" });
                setPasswordError("");
                setPasswordSuccess("");
                setIsPasswordModalOpen(true);
              }}
              className="p-2 bg-[#141F20] hover:bg-[#213233] rounded-lg border border-[#213233] text-zinc-400 hover:text-white transition-colors"
              title="Change Password"
            >
              <Settings size={14} />
            </button>
            <button 
              onClick={handleSignOut}
              className="text-[10px] uppercase font-bold tracking-wider py-1.5 px-3.5 rounded bg-red-950/20 hover:bg-red-950/40 border border-red-900/30 hover:border-red-500/50 text-red-400 transition-colors"
            >
              Sign Out
            </button>
          </div>
        </div>
      </header>

      {/* DASHBOARD WRAPPER */}
      <div className="flex-1 max-w-7xl w-full mx-auto p-6 flex flex-col md:flex-row gap-6">
        
        {/* SIDEBAR NAVIGATION TABS */}
        <aside className="w-full md:w-64 space-y-1 bg-[#0E1617] p-3 rounded-2xl border border-[#213233] self-start">
          <div className="px-3 py-2 text-[10px] uppercase tracking-wider font-extrabold text-zinc-500">
            Governance Dashboard
          </div>
          
          {[
            { id: "leads", label: "Access Requests", icon: FileCheck2 },
            { id: "organizations", label: "Organizations", icon: Building2 },
            { id: "users", label: "Global Users", icon: Users },
            { id: "analytics", label: "System Analytics", icon: Activity },
            { id: "audit", label: "Platform Audit Logs", icon: History }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as Tab)}
              className={`w-full flex items-center justify-between px-3.5 py-3 rounded-xl text-xs font-semibold tracking-wide transition-all ${
                activeTab === tab.id 
                  ? "bg-[#00B47A] text-black" 
                  : "text-zinc-400 hover:text-white hover:bg-[#141F20]"
              }`}
            >
              <div className="flex items-center gap-2.5">
                <tab.icon size={15} />
                <span>{tab.label}</span>
              </div>
              {tab.id === "leads" && requests.filter(r => r.status === "PENDING").length > 0 && (
                <span className={`px-1.5 py-0.5 rounded-full text-[9px] font-bold font-mono ${
                  activeTab === "leads" ? "bg-black text-[#00B47A]" : "bg-red-500/10 text-red-400 border border-red-500/20"
                }`}>
                  {requests.filter(r => r.status === "PENDING").length}
                </span>
              )}
            </button>
          ))}
        </aside>

        {/* MAIN PANEL */}
        <main className="flex-1 bg-[#0E1617] rounded-2xl border border-[#213233] p-6 min-h-[500px] flex flex-col relative overflow-hidden">
          
          {/* Section title & loading spinner */}
          <div className="flex items-center justify-between border-b border-[#213233] pb-4 mb-6">
            <div>
              <h2 className="text-base font-extrabold uppercase tracking-wider text-white">
                {activeTab === "leads" && "Access Requests Queue"}
                {activeTab === "organizations" && "Registered Tenants"}
                {activeTab === "users" && "Global Users Directory"}
                {activeTab === "analytics" && "Global MRV Telemetry"}
                {activeTab === "audit" && "Platform Governance Audit Logs"}
              </h2>
              <p className="text-[10px] text-zinc-500 mt-1">
                {activeTab === "leads" && "Review and approve/reject carbon developer and mini-grid operator applications."}
                {activeTab === "organizations" && "Manage provisioned tenants and coordinate workspace isolation."}
                {activeTab === "users" && "Manage operational permissions, roles, and status of users across tenants."}
                {activeTab === "analytics" && "Aggregated measurement data and submission telemetry across all organizations."}
                {activeTab === "audit" && "Security logs tracking Super Admin actions and administrative updates."}
              </p>
            </div>
            
            <button 
              onClick={loadData}
              disabled={loadingData}
              className="p-2 bg-[#141F20] hover:bg-[#213233] rounded-lg border border-[#213233] text-zinc-400 hover:text-white transition-colors"
            >
              {loadingData ? (
                <Loader2 size={14} className="animate-spin text-[#00B47A]" />
              ) : (
                <span className="text-[10px] uppercase font-bold px-1 select-none">Sync Logs</span>
              )}
            </button>
          </div>

          {/* TAB CONTENT 1: ACCESS REQUESTS QUEUE */}
          {activeTab === "leads" && (
            <div className="flex-1 space-y-4">
              {requests.length === 0 ? (
                <div className="py-20 text-center text-zinc-600 text-xs">
                  No access requests submitted.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-[#213233] text-zinc-500 uppercase text-[9px] font-bold">
                        <th className="pb-3">Applicant / Organization</th>
                        <th className="pb-3">Contact</th>
                        <th className="pb-3">Region</th>
                        <th className="pb-3">Methodology Sector</th>
                        <th className="pb-3">Status</th>
                        <th className="pb-3 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#213233]/40">
                      {requests.map(req => (
                        <tr key={req.id} className="hover:bg-[#141F20]/30 transition-colors">
                          <td className="py-4 font-semibold text-white">
                            <div>{req.full_name}</div>
                            <div className="text-[10px] text-zinc-500">{req.organization_name}</div>
                          </td>
                          <td className="py-4 text-zinc-400">
                            <div className="flex items-center gap-1"><Mail size={12} className="text-zinc-600" />{req.email}</div>
                            {req.phone && <div className="flex items-center gap-1 mt-0.5"><Phone size={12} className="text-zinc-600" />{req.phone}</div>}
                          </td>
                          <td className="py-4 text-zinc-400">
                            <span className="inline-flex items-center gap-1">
                              <MapPin size={11} className="text-[#00B47A]" />
                              {req.country || "Unspecified"}
                            </span>
                          </td>
                          <td className="py-4">
                            <span className="text-[10px] font-bold uppercase bg-zinc-900 border border-zinc-800 px-2 py-0.5 rounded text-zinc-400">
                              {req.use_case?.split(" - ")[0] || "Energy"}
                            </span>
                          </td>
                          <td className="py-4">
                            <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold border uppercase ${
                              req.status === "PENDING" ? "bg-amber-500/10 border-amber-500/20 text-amber-400" :
                              req.status === "APPROVED" ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400" :
                              "bg-red-500/10 border-red-500/20 text-red-400"
                            }`}>
                              {req.status}
                            </span>
                          </td>
                          <td className="py-4 text-right">
                            <div className="flex justify-end gap-2 items-center">
                              {req.status === "PENDING" ? (
                                <>
                                  <button
                                    onClick={() => handleReject(req.id)}
                                    disabled={processingId !== null}
                                    className="py-1 px-3 bg-red-950/20 hover:bg-red-950/40 border border-red-900/30 hover:border-red-500/50 text-red-400 rounded text-[10px] font-bold uppercase transition-colors"
                                  >
                                    Reject
                                  </button>
                                  <button
                                    onClick={() => handleApprove(req.id)}
                                    disabled={processingId !== null}
                                    className="py-1 px-3 bg-[#00B47A]/15 hover:bg-[#00B47A]/35 border border-[#00B47A]/30 hover:border-[#00B47A]/80 text-[#00B47A] rounded text-[10px] font-bold uppercase transition-colors"
                                  >
                                    {processingId === req.id ? "Working..." : "Approve"}
                                  </button>
                                </>
                              ) : (
                                <span className="text-[10px] text-zinc-600 font-mono">Reviewed</span>
                              )}
                              <button
                                onClick={() => handleDeleteAccessRequest(req.id)}
                                disabled={processingId !== null}
                                className="py-1 px-2 hover:bg-red-900/20 hover:text-red-400 text-zinc-600 rounded transition-colors"
                                title="Delete Request Permanently"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* TAB CONTENT 2: ORGANIZATIONS LIST */}
          {activeTab === "organizations" && (
            <div className="flex-1 space-y-4">
              {orgs.length === 0 ? (
                <div className="py-20 text-center text-zinc-600 text-xs">
                  No registered SaaS tenant organizations.
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {orgs.map(org => (
                    <div 
                      key={org.id} 
                      onClick={() => handleViewOrgAnalytics(org.id, org.name)}
                      className="p-5 rounded-2xl bg-[#141F20]/30 border border-[#213233] hover:border-[#00B47A]/40 transition-all cursor-pointer space-y-4 group relative"
                    >
                      <div className="flex items-center justify-between" onClick={(e) => e.stopPropagation()}>
                        <span className="px-2 py-0.5 bg-emerald-500/10 border border-emerald-500/20 text-[#00B47A] text-[9px] font-bold rounded">
                          {org.status}
                        </span>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedOrgForPasswordReset(org);
                            }}
                            className="p-1 hover:bg-[#213233] rounded border border-transparent hover:border-[#213233] text-zinc-500 hover:text-white transition-colors"
                            title="Change User Passwords"
                          >
                            <Key size={13} />
                          </button>
                          <button
                            onClick={() => handleDeleteOrg(org.id, org.name)}
                            disabled={processingId !== null}
                            className="p-1 hover:bg-red-950/40 rounded border border-transparent hover:border-red-900/30 text-zinc-500 hover:text-red-400 transition-colors"
                            title="Delete Organization"
                          >
                            <Trash2 size={13} />
                          </button>
                          <span className="text-[9px] font-mono text-zinc-600">ID: {org.id.substring(0, 8)}...</span>
                        </div>
                      </div>
                      
                      <div className="space-y-1">
                        <h4 className="font-extrabold text-white text-base leading-snug group-hover:text-[#00B47A] transition-colors">{org.name}</h4>
                        <p className="text-[10px] text-zinc-500">
                          Workspace Created: {new Date(org.created_at).toLocaleDateString()}
                        </p>
                      </div>

                      {/* Agents List inside Org Card */}
                      <div className="space-y-1.5 pt-1 border-t border-[#213233]/20" onClick={(e) => e.stopPropagation()}>
                        <span className="text-[9px] uppercase tracking-wider text-zinc-500 font-extrabold block">Assigned Agents</span>
                        {users.filter(u => u.organization === org.name && u.role === "field_agent").length === 0 ? (
                          <span className="text-[10px] text-zinc-600 font-medium block">No agents created yet</span>
                        ) : (
                          <div className="flex flex-wrap gap-1 pt-0.5 max-h-[60px] overflow-y-auto scrollbar">
                            {users.filter(u => u.organization === org.name && u.role === "field_agent").map(agent => (
                              <span key={agent.id} className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-zinc-900 border border-zinc-800 text-[9px] text-zinc-400" title={agent.email}>
                                <span className="w-1 h-1 rounded-full bg-[#00B47A]" />
                                {agent.full_name}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>

                      <div className="pt-2 border-t border-[#213233]/40 flex justify-between items-center text-[10px] text-zinc-400">
                        <span>Associated Users: {users.filter(u => u.organization === org.name).length}</span>
                        <span className="text-zinc-600 font-bold uppercase group-hover:text-[#00B47A]/80 transition-colors">View Analytics</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB CONTENT 3: GLOBAL USERS TABLE */}
          {activeTab === "users" && (
            <div className="flex-1 space-y-4">
              {users.length === 0 ? (
                <div className="py-20 text-center text-zinc-600 text-xs">
                  No users registered.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-[#213233] text-zinc-500 uppercase text-[9px] font-bold">
                        <th className="pb-3">User</th>
                        <th className="pb-3">Email</th>
                        <th className="pb-3">Role</th>
                        <th className="pb-3">Organization Workspace</th>
                        <th className="pb-3">Status</th>
                        <th className="pb-3 text-right">Access Controls</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#213233]/40">
                      {users.map(u => (
                        <tr key={u.id} className="hover:bg-[#141F20]/30 transition-colors">
                          <td className="py-4 font-semibold text-white">
                            <div>{u.full_name}</div>
                            <div className="text-[9px] font-mono text-zinc-600">ID: {u.id}</div>
                          </td>
                          <td className="py-4 text-zinc-400">{u.email}</td>
                          <td className="py-4">
                            <span className={`text-[10px] font-mono font-bold uppercase px-2 py-0.5 rounded border ${
                              u.role === "SUPER_ADMIN" ? "bg-purple-500/10 border-purple-500/20 text-purple-400" :
                              u.role === "ORG_ADMIN" ? "bg-blue-500/10 border-blue-500/20 text-blue-400" :
                              u.role === "admin" ? "bg-blue-500/10 border-blue-500/20 text-blue-400" :
                              "bg-zinc-800 border-zinc-700 text-zinc-400"
                            }`}>
                              {u.role === "admin" ? "ORG_ADMIN" : u.role}
                            </span>
                          </td>
                          <td className="py-4 text-zinc-400 font-semibold">{u.organization || "System Default"}</td>
                          <td className="py-4">
                            <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold border uppercase ${
                              u.is_active ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400" : "bg-red-500/10 border-red-500/20 text-red-400"
                            }`}>
                              {u.is_active ? "Active" : "Suspended"}
                            </span>
                          </td>
                          <td className="py-4 text-right">
                            <div className="flex justify-end items-center gap-2">
                              <button
                                onClick={() => setSelectedUserForDetails(u)}
                                className="p-1 hover:bg-[#141F20] rounded border border-transparent hover:border-[#213233] text-zinc-400 hover:text-white transition-colors"
                                title="Inspect User Profile"
                              >
                                <Eye size={14} />
                              </button>
                              {u.role !== "SUPER_ADMIN" && (
                                <button
                                  onClick={() => {
                                    const userOrg = orgs.find(o => o.name === u.organization) || { name: u.organization || "System Default" };
                                    setSelectedOrgForPasswordReset(userOrg);
                                    setResetPasswordUserId(u.id);
                                  }}
                                  className="p-1 hover:bg-[#141F20] rounded border border-transparent hover:border-[#213233] text-zinc-400 hover:text-white transition-colors"
                                  title="Reset Password"
                                >
                                  <Key size={14} />
                                </button>
                              )}
                              {u.role === "SUPER_ADMIN" ? (
                                <span className="text-[10px] text-zinc-600 font-mono pr-2">Immutable</span>
                              ) : (
                                <button
                                  onClick={() => handleToggleSuspension(u.id, u.is_active)}
                                  disabled={processingId !== null}
                                  className={`py-1 px-3 rounded text-[10px] font-bold uppercase transition-colors border ${
                                    u.is_active 
                                      ? "bg-red-950/20 hover:bg-red-950/40 border-red-900/30 text-red-400" 
                                      : "bg-[#00B47A]/15 hover:bg-[#00B47A]/35 border-[#00B47A]/30 text-[#00B47A]"
                                  }`}
                                >
                                  {processingId === u.id ? "Working..." : u.is_active ? "Suspend" : "Activate"}
                                </button>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* TAB CONTENT 4: GLOBAL ANALYTICS */}
          {activeTab === "analytics" && (
            <div className="flex-1 space-y-6">
              
              {/* Core metrics counts cards grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-[#141F20]/30 p-5 rounded-2xl border border-[#213233] space-y-2">
                  <span className="text-[10px] text-zinc-500 uppercase font-extrabold tracking-wider">Installations</span>
                  <div className="flex items-center gap-2">
                    <Database className="text-[#00B47A]" size={20} />
                    <span className="text-2xl font-black text-white">{mrvStats.installations}</span>
                  </div>
                  <p className="text-[9px] text-zinc-600 font-semibold">Across all SaaS tenants</p>
                </div>

                <div className="bg-[#141F20]/30 p-5 rounded-2xl border border-[#213233] space-y-2">
                  <span className="text-[10px] text-zinc-500 uppercase font-extrabold tracking-wider">Avg Trust Score</span>
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="text-[#00B47A]" size={20} />
                    <span className="text-2xl font-black text-[#00B47A]">{mrvStats.avgTrust}%</span>
                  </div>
                  <p className="text-[9px] text-zinc-600 font-semibold">High-fidelity metrics lock</p>
                </div>

                <div className="bg-[#141F20]/30 p-5 rounded-2xl border border-[#213233] space-y-2">
                  <span className="text-[10px] text-zinc-500 uppercase font-extrabold tracking-wider">CO₂ Impact</span>
                  <div className="flex items-center gap-2">
                    <Globe className="text-sky-400" size={20} />
                    <span className="text-2xl font-black text-white">{mrvStats.tCO2} t</span>
                  </div>
                  <p className="text-[9px] text-zinc-600 font-semibold">tCO2e Estimated</p>
                </div>

                <div className="bg-[#141F20]/30 p-5 rounded-2xl border border-[#213233] space-y-2">
                  <span className="text-[10px] text-zinc-500 uppercase font-extrabold tracking-wider">Active Tenants</span>
                  <div className="flex items-center gap-2">
                    <Building2 className="text-[#00B47A]" size={20} />
                    <span className="text-2xl font-black text-white">{mrvStats.activeOrgs}</span>
                  </div>
                  <p className="text-[9px] text-zinc-600 font-semibold">Approved workspaces</p>
                </div>
              </div>

              {/* Layout splits */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-4">
                
                {/* Sector deployment distribution */}
                <div className="bg-[#141F20]/30 p-6 rounded-2xl border border-[#213233] space-y-4">
                  <h4 className="font-extrabold text-white text-sm">Tenant Methodology Coverage</h4>
                  <div className="space-y-3 pt-2">
                    {(() => {
                      const methodologies = mrvStats.methodologies || {};
                      const totalMethodologies = Object.values(methodologies).reduce((a: any, b: any) => a + b, 0) as number;
                      
                      if (totalMethodologies === 0) {
                        return <span className="text-[11px] text-zinc-500">No methodology data available.</span>;
                      }

                      return Object.entries(methodologies).map(([name, count]: [string, any], idx) => {
                        const pct = Math.round((count / totalMethodologies) * 100);
                        return (
                          <div key={idx} className="space-y-1 font-mono text-[11px]">
                            <div className="flex justify-between text-zinc-400">
                              <span>{name.replace(/_/g, ' ').toUpperCase()}</span>
                              <span className="text-[#00B47A] font-bold">{count} Orgs ({pct}%)</span>
                            </div>
                            <div className="w-full bg-[#141F20] h-2 rounded-full overflow-hidden border border-[#213233]/60">
                              <div 
                                className="bg-[#00B47A] h-full rounded-full" 
                                style={{ width: `${pct}%` }} 
                              />
                            </div>
                          </div>
                        );
                      });
                    })()}
                  </div>
                </div>

                {/* Platform Users distribution */}
                <div className="bg-[#141F20]/30 p-6 rounded-2xl border border-[#213233] space-y-4">
                  <h4 className="font-extrabold text-white text-sm">Global User Role Breakdown</h4>
                  <div className="grid grid-cols-3 gap-2 pt-2 text-center font-mono">
                    <div className="bg-[#141F20] p-3 rounded-xl border border-[#213233]">
                      <span className="text-[8px] text-zinc-500 uppercase block font-bold">SUPER_ADMIN</span>
                      <p className="text-lg font-bold text-purple-400 mt-1">1</p>
                    </div>
                    <div className="bg-[#141F20] p-3 rounded-xl border border-[#213233]">
                      <span className="text-[8px] text-zinc-500 uppercase block font-bold">ORG_ADMIN</span>
                      <p className="text-lg font-bold text-blue-400 mt-1">
                        {users.filter(u => u.role === "ORG_ADMIN" || u.role === "admin").length}
                      </p>
                    </div>
                    <div className="bg-[#141F20] p-3 rounded-xl border border-[#213233]">
                      <span className="text-[8px] text-zinc-500 uppercase block font-bold">FIELD_AGENT</span>
                      <p className="text-lg font-bold text-emerald-400 mt-1">
                        {users.filter(u => u.role === "field_agent").length}
                      </p>
                    </div>
                  </div>
                </div>

              </div>

            </div>
          )}

          {/* TAB CONTENT 5: PLATFORM AUDIT LOGS */}
          {activeTab === "audit" && (
            <div className="flex-1 space-y-4 font-mono text-[11px]">
              {auditLogs.length === 0 ? (
                <div className="py-20 text-center text-zinc-600 text-xs">
                  No governance logs indexed yet.
                </div>
              ) : (
                <div className="bg-[#090F10] border border-[#213233] rounded-xl p-4 max-h-[420px] overflow-y-auto space-y-3 scrollbar">
                  {auditLogs.map((log, index) => (
                    <div key={index} className="flex gap-4 items-start border-b border-[#141F20] pb-2 last:border-b-0 last:pb-0">
                      <span className="text-zinc-500 shrink-0">[{log.timestamp}]</span>
                      <div className="space-y-0.5">
                        <div className="flex items-center gap-2">
                          <span className={`font-bold px-1.5 py-0.2 rounded text-[9px] ${
                            (log.action || "").includes("APPROVED") || (log.action || "").includes("USER_PROVISIONED")
                              ? "bg-emerald-950/40 text-emerald-400 border border-emerald-900/30" :
                            (log.action || "").includes("REJECTED")
                              ? "bg-red-950/40 text-red-400 border border-red-900/30" :
                            "bg-purple-950/40 text-purple-400 border border-purple-900/30"
                          }`}>
                            {log.action || "SYSTEM_EVENT"}
                          </span>
                          <span className="text-zinc-400 text-[10px]">Actor: {log.user}</span>
                        </div>
                        <p className="text-zinc-300 pt-0.5">{log.details}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

        </main>
      </div>

      {/* RENDER SYSTEM APPROVED CREDENTIALS MODAL ON APPROVAL */}
      {approvedCredentials && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md">
          <div className="relative w-full max-w-md bg-[#0E1617] border border-[#00B47A]/30 rounded-2xl shadow-2xl overflow-hidden animate-fade-in-up p-8 space-y-6">
            
            <div className="text-center space-y-2">
              <div className="w-14 h-14 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-[#00B47A] flex items-center justify-center mx-auto animate-pulse">
                <Sparkles size={28} />
              </div>
              <h3 className="text-lg font-bold text-white">Tenant Credentials Generated</h3>
              <p className="text-xs text-zinc-400">
                Organization workspace successfully provisioned. Share these credentials with the tenant administrator.
              </p>
            </div>

            <div className="bg-[#090F10] border border-[#213233] p-4 rounded-xl space-y-3.5 text-xs font-mono">
              <div className="space-y-0.5">
                <span className="text-[9px] uppercase tracking-wider text-zinc-500 block font-bold">Organization Name</span>
                <p className="text-white font-bold">{approvedCredentials.orgName}</p>
              </div>

              <div className="space-y-0.5">
                <span className="text-[9px] uppercase tracking-wider text-zinc-500 block font-bold">Admin Login Email</span>
                <p className="text-white font-bold">{approvedCredentials.email}</p>
              </div>

              <div className="space-y-0.5">
                <span className="text-[9px] uppercase tracking-wider text-zinc-500 block font-bold">Temporary Password</span>
                <p className="text-emerald-400 font-bold text-sm tracking-wide bg-black/50 p-2 rounded border border-emerald-950">
                  {approvedCredentials.tempPw}
                </p>
              </div>
            </div>

            <div className="bg-amber-500/5 border border-amber-500/10 p-3 rounded-lg text-[10px] text-amber-300 leading-normal">
              ⚠️ **Log In Security**: The new Org Admin will be forced to change this temporary password on their very first sign-in session.
            </div>

            <div className="flex gap-3">
              <button
                onClick={handleCopyCredentials}
                className="flex-1 py-3 bg-[#141F20] hover:bg-[#213233] border border-[#213233] text-white rounded-xl text-xs font-bold uppercase transition-all flex items-center justify-center gap-1.5"
              >
                {copiedText ? (
                  <>
                    <Check size={14} className="text-[#00B47A]" />
                    Copied!
                  </>
                ) : (
                  <>
                    <Copy size={14} />
                    Copy Info
                  </>
                )}
              </button>
              <button
                onClick={() => setApprovedCredentials(null)}
                className="flex-1 py-3 bg-[#00B47A] hover:bg-emerald-400 text-black rounded-xl text-xs font-bold uppercase transition-all"
              >
                Close Queue
              </button>
            </div>

          </div>
        </div>
      )}

      {/* USER PROFILE INSPECTOR MODAL */}
      {selectedUserForDetails && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md">
          <div className="relative w-full max-w-md bg-[#0E1617] border border-[#213233] rounded-2xl shadow-2xl overflow-hidden p-8 space-y-6 animate-fade-in-up">
            <div className="text-center space-y-2">
              <div className="w-12 h-12 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-[#00B47A] flex items-center justify-center mx-auto">
                <Users size={22} />
              </div>
              <h3 className="text-lg font-bold text-white">User Profile Inspector</h3>
              <p className="text-xs text-zinc-400">
                Detailed metadata for {selectedUserForDetails.full_name}
              </p>
            </div>

            <div className="bg-[#090F10] border border-[#213233] p-4 rounded-xl space-y-3.5 text-xs font-mono">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-0.5">
                  <span className="text-[9px] uppercase tracking-wider text-zinc-500 block font-bold">Full Name</span>
                  <p className="text-white font-bold">{selectedUserForDetails.full_name}</p>
                </div>
                <div className="space-y-0.5">
                  <span className="text-[9px] uppercase tracking-wider text-zinc-500 block font-bold">Email Address</span>
                  <p className="text-white font-bold break-all">{selectedUserForDetails.email}</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-0.5">
                  <span className="text-[9px] uppercase tracking-wider text-zinc-500 block font-bold">User Role</span>
                  <span className={`inline-block text-[10px] font-mono font-bold uppercase px-1.5 py-0.5 rounded border mt-1 ${
                    selectedUserForDetails.role === "SUPER_ADMIN" ? "bg-purple-500/10 border-purple-500/20 text-purple-400" :
                    selectedUserForDetails.role === "ORG_ADMIN" || selectedUserForDetails.role === "admin" ? "bg-blue-500/10 border-blue-500/20 text-blue-400" :
                    "bg-zinc-800 border-zinc-700 text-zinc-400"
                  }`}>
                    {selectedUserForDetails.role === "admin" ? "ORG_ADMIN" : selectedUserForDetails.role}
                  </span>
                </div>
                <div className="space-y-0.5">
                  <span className="text-[9px] uppercase tracking-wider text-zinc-500 block font-bold">Organization</span>
                  <p className="text-white font-bold">{selectedUserForDetails.organization || "System / None"}</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-0.5">
                  <span className="text-[9px] uppercase tracking-wider text-zinc-500 block font-bold">Sector</span>
                  <p className="text-white font-bold capitalize">{selectedUserForDetails.sector || "Unassigned"}</p>
                </div>
                <div className="space-y-0.5">
                  <span className="text-[9px] uppercase tracking-wider text-zinc-500 block font-bold">Country</span>
                  <p className="text-white font-bold">{selectedUserForDetails.country || "Unspecified"}</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-0.5 col-span-2">
                  <span className="text-[9px] uppercase tracking-wider text-zinc-500 block font-bold">Unique User ID</span>
                  <p className="text-zinc-400 font-mono text-[10px] select-text break-all">{selectedUserForDetails.id}</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-0.5">
                  <span className="text-[9px] uppercase tracking-wider text-zinc-500 block font-bold">Account Status</span>
                  <span className={`inline-block px-2 py-0.5 rounded-full text-[9px] font-bold border uppercase mt-1 ${
                    selectedUserForDetails.is_active ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400" : "bg-red-500/10 border-red-500/20 text-red-400"
                  }`}>
                    {selectedUserForDetails.is_active ? "Active" : "Suspended"}
                  </span>
                </div>
                <div className="space-y-0.5">
                  <span className="text-[9px] uppercase tracking-wider text-zinc-500 block font-bold">Created At</span>
                  <p className="text-zinc-400 font-mono mt-1">
                    {selectedUserForDetails.created_at ? new Date(selectedUserForDetails.created_at).toLocaleString() : "Unknown"}
                  </p>
                </div>
              </div>
            </div>

            <div className="flex pt-2">
              <button
                onClick={() => setSelectedUserForDetails(null)}
                className="w-full py-2.5 bg-[#141F20] hover:bg-[#213233] border border-[#213233] text-white rounded-xl text-xs font-bold uppercase transition-all"
              >
                Close Profile
              </button>
            </div>
          </div>
        </div>
      )}

      {/* USER PASSWORD RESET MODAL FOR SAAS ORG */}
      {selectedOrgForPasswordReset && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md">
          <div className="relative w-full max-w-md bg-[#0E1617] border border-[#213233] rounded-2xl shadow-2xl overflow-hidden p-8 space-y-6 animate-fade-in-up">
            <div className="text-center space-y-2">
              <div className="w-12 h-12 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-[#00B47A] flex items-center justify-center mx-auto">
                <Key size={22} />
              </div>
              <h3 className="text-lg font-bold text-white">Reset User Credentials</h3>
              <p className="text-xs text-zinc-400">
                Force update the password of a user under {selectedOrgForPasswordReset.name}
              </p>
            </div>

            <form onSubmit={handleResetUserPasswordSubmit} className="space-y-4">
              <div className="space-y-1.5 text-left">
                <label className="text-[10px] uppercase tracking-wider text-zinc-400 font-bold">Select User</label>
                <select
                  required
                  value={resetPasswordUserId}
                  onChange={(e) => setResetPasswordUserId(e.target.value)}
                  className="w-full bg-[#090F10] border border-[#213233] focus:border-[#00B47A] rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none transition-colors"
                >
                  <option value="">-- Choose User --</option>
                  {users
                    .filter(u => u.organization_id === selectedOrgForPasswordReset.id)
                    .map(u => (
                      <option key={u.id} value={u.id}>
                        {u.full_name} ({u.role === "admin" ? "ORG_ADMIN" : u.role}) — {u.email}
                      </option>
                    ))}
                </select>
              </div>

              <div className="space-y-1.5 text-left">
                <label className="text-[10px] uppercase tracking-wider text-zinc-400 font-bold">New Password</label>
                <input
                  type="password"
                  required
                  placeholder="Minimum 8 characters"
                  value={resetNewPassword}
                  onChange={(e) => setResetNewPassword(e.target.value)}
                  className="w-full bg-[#090F10] border border-[#213233] focus:border-[#00B47A] rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none transition-colors"
                />
              </div>

              {resetPasswordError && (
                <p className="text-red-400 text-[10px] font-semibold">{resetPasswordError}</p>
              )}
              {resetPasswordSuccess && (
                <p className="text-emerald-400 text-[10px] font-semibold">{resetPasswordSuccess}</p>
              )}

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setSelectedOrgForPasswordReset(null);
                    setResetPasswordUserId("");
                    setResetNewPassword("");
                    setResetPasswordError("");
                    setResetPasswordSuccess("");
                  }}
                  className="flex-1 py-2.5 bg-[#141F20] hover:bg-[#213233] border border-[#213233] text-white rounded-xl text-xs font-bold uppercase transition-all"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isResettingPassword}
                  className="flex-1 py-2.5 bg-[#00B47A] hover:bg-emerald-400 text-black rounded-xl text-xs font-bold uppercase transition-all disabled:opacity-50"
                >
                  {isResettingPassword ? "Updating..." : "Reset Password"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ORGANIZATION ANALYTICS MODAL */}
      {selectedOrgForAnalytics && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md">
          <div className="relative w-full max-w-2xl bg-[#0E1617] border border-[#213233] rounded-2xl shadow-2xl overflow-hidden p-8 space-y-6 animate-fade-in-up">
            
            <div className="flex items-start justify-between border-b border-[#213233] pb-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg bg-[#00B47A]/10 border border-[#00B47A]/20 flex items-center justify-center text-[#00B47A]">
                    <Building2 size={18} />
                  </div>
                  <h3 className="text-lg font-bold text-white">{selectedOrgForAnalytics.name}</h3>
                </div>
                <p className="text-xs text-zinc-500">
                  Tenant Analytics & Methodology Metrics
                </p>
              </div>
              <button
                onClick={() => {
                  setSelectedOrgForAnalytics(null);
                  setOrgAnalyticsData(null);
                }}
                className="text-zinc-500 hover:text-white transition-colors text-xs font-bold uppercase"
              >
                Close
              </button>
            </div>

            {loadingOrgAnalytics ? (
              <div className="py-20 flex flex-col items-center justify-center space-y-3">
                <Loader2 size={24} className="animate-spin text-[#00B47A]" />
                <p className="text-zinc-500 text-xs font-semibold tracking-tight">
                  Calculating real-time database metrics...
                </p>
              </div>
            ) : orgAnalyticsData ? (
              <div className="space-y-6">
                
                {/* Metrics Grid */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="bg-[#090F10] p-4 rounded-xl border border-[#213233] space-y-1">
                    <span className="text-[9px] text-zinc-500 uppercase font-bold tracking-wider">Installations</span>
                    <div className="text-xl font-black text-white">
                      {orgAnalyticsData.metrics.installations_count}
                    </div>
                  </div>

                  <div className="bg-[#090F10] p-4 rounded-xl border border-[#213233] space-y-1">
                    <span className="text-[9px] text-zinc-500 uppercase font-bold tracking-wider">Activities</span>
                    <div className="text-xl font-black text-white">
                      {orgAnalyticsData.metrics.activities_count}
                    </div>
                  </div>

                  <div className="bg-[#090F10] p-4 rounded-xl border border-[#213233] space-y-1">
                    <span className="text-[9px] text-zinc-500 uppercase font-bold tracking-wider">Avg Trust Score</span>
                    <div className="text-xl font-black text-[#00B47A]">
                      {orgAnalyticsData.metrics.average_trust_score}%
                    </div>
                  </div>

                  <div className="bg-[#090F10] p-4 rounded-xl border border-[#213233] space-y-1">
                    <span className="text-[9px] text-zinc-500 uppercase font-bold tracking-wider">Carbon Offset</span>
                    <div className="text-xl font-black text-white">
                      {orgAnalyticsData.metrics.total_co2_offset} t
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
                  {/* Sector Mix */}
                  <div className="bg-[#090F10] p-5 rounded-xl border border-[#213233] space-y-4">
                    <h4 className="font-extrabold text-white text-xs uppercase tracking-wider text-zinc-400">Sector Mix</h4>
                    <div className="space-y-3 font-mono text-[11px]">
                      {Object.keys(orgAnalyticsData.metrics.sector_mix || {}).length === 0 ? (
                        <p className="text-zinc-600 text-xs py-2">No sector distribution data available.</p>
                      ) : (
                        Object.entries(orgAnalyticsData.metrics.sector_mix || {}).map(([sector, count]) => {
                          const typedCount = count as number;
                          const total = Object.values(orgAnalyticsData.metrics.sector_mix).reduce((a: any, b: any) => a + b, 0) as number;
                          const pct = total > 0 ? Math.round((typedCount / total) * 100) : 0;
                          return (
                            <div key={sector} className="space-y-1">
                              <div className="flex justify-between text-zinc-400">
                                <span className="capitalize">{sector}</span>
                                <span className="text-[#00B47A] font-bold">{typedCount} Users ({pct}%)</span>
                              </div>
                              <div className="w-full bg-[#141F20] h-1.5 rounded-full overflow-hidden border border-[#213233]/60">
                                <div 
                                  className="bg-[#00B47A] h-full rounded-full" 
                                  style={{ width: `${pct}%` }} 
                                />
                              </div>
                            </div>
                          );
                        })
                      )}
                    </div>
                  </div>

                  {/* Users / Roles breakdown */}
                  <div className="bg-[#090F10] p-5 rounded-xl border border-[#213233] space-y-4">
                    <h4 className="font-extrabold text-white text-xs uppercase tracking-wider text-zinc-400">Team Structure</h4>
                    <div className="space-y-2 text-xs font-mono">
                      <div className="flex justify-between border-b border-[#213233]/40 pb-2">
                        <span className="text-zinc-500">Total Users</span>
                        <span className="text-white font-bold">{orgAnalyticsData.metrics.users_count}</span>
                      </div>
                      
                      <div className="space-y-1.5 pt-1 text-[11px]">
                        {Object.entries(orgAnalyticsData.metrics.roles || {}).map(([role, count]) => (
                          <div key={role} className="flex justify-between text-zinc-400 font-semibold">
                            <span className="uppercase">{role === "admin" ? "ORG_ADMIN" : role}</span>
                            <span className="text-white font-mono">{count as number}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="text-[10px] text-zinc-600 font-mono text-center pt-2">
                  Organization Status: <span className="text-[#00B47A] uppercase">{orgAnalyticsData.status}</span> • Workspace Provisioned: {new Date(orgAnalyticsData.created_at).toLocaleString()}
                </div>

              </div>
            ) : (
              <div className="py-20 text-center text-zinc-600 text-xs">
                Failed to load analytics data.
              </div>
            )}

            <div className="flex pt-2 justify-end">
              <button
                onClick={() => {
                  setSelectedOrgForAnalytics(null);
                  setOrgAnalyticsData(null);
                }}
                className="py-2.5 px-6 bg-[#141F20] hover:bg-[#213233] border border-[#213233] text-white rounded-xl text-xs font-bold uppercase transition-all"
              >
                Close Metrics
              </button>
            </div>
          </div>
        </div>
      )}

      {/* RENDER CHANGE PASSWORD MODAL */}
      {isPasswordModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md">
          <div className="relative w-full max-w-md bg-[#0E1617] border border-[#213233] rounded-2xl shadow-2xl overflow-hidden p-8 space-y-6">
            <div className="text-center space-y-2">
              <div className="w-12 h-12 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-[#00B47A] flex items-center justify-center mx-auto">
                <Settings size={22} />
              </div>
              <h3 className="text-lg font-bold text-white">Change Credentials</h3>
              <p className="text-xs text-zinc-400">
                Update your Super Admin password.
              </p>
            </div>

            <form onSubmit={handleChangePassword} className="space-y-4">
              <div className="space-y-1.5 text-left">
                <label className="text-[10px] uppercase tracking-wider text-zinc-400 font-bold">Current Password</label>
                <input
                  type="password"
                  required
                  placeholder="••••••••"
                  value={passwordForm.currentPassword}
                  onChange={(e) => setPasswordForm({ ...passwordForm, currentPassword: e.target.value })}
                  className="w-full bg-[#090F10] border border-[#213233] focus:border-[#00B47A] rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none transition-colors"
                />
              </div>

              <div className="space-y-1.5 text-left">
                <label className="text-[10px] uppercase tracking-wider text-zinc-400 font-bold">New Password</label>
                <input
                  type="password"
                  required
                  placeholder="••••••••"
                  value={passwordForm.newPassword}
                  onChange={(e) => setPasswordForm({ ...passwordForm, newPassword: e.target.value })}
                  className="w-full bg-[#090F10] border border-[#213233] focus:border-[#00B47A] rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none transition-colors"
                />
              </div>

              <div className="space-y-1.5 text-left">
                <label className="text-[10px] uppercase tracking-wider text-zinc-400 font-bold">Confirm New Password</label>
                <input
                  type="password"
                  required
                  placeholder="••••••••"
                  value={passwordForm.confirmPassword}
                  onChange={(e) => setPasswordForm({ ...passwordForm, confirmPassword: e.target.value })}
                  className="w-full bg-[#090F10] border border-[#213233] focus:border-[#00B47A] rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none transition-colors"
                />
              </div>

              {passwordError && (
                <p className="text-red-400 text-[10px] font-semibold">{passwordError}</p>
              )}
              {passwordSuccess && (
                <p className="text-emerald-400 text-[10px] font-semibold">{passwordSuccess}</p>
              )}

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsPasswordModalOpen(false)}
                  className="flex-1 py-2.5 bg-[#141F20] hover:bg-[#213233] border border-[#213233] text-white rounded-xl text-xs font-bold uppercase transition-all"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isChangingPassword}
                  className="flex-1 py-2.5 bg-[#00B47A] hover:bg-emerald-400 text-black rounded-xl text-xs font-bold uppercase transition-all disabled:opacity-50"
                >
                  {isChangingPassword ? "Updating..." : "Save Password"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}

export default function SuperAdminPage() {
  return (
    <WorkspaceProvider>
      <SuperAdminDashboard />
    </WorkspaceProvider>
  );
}

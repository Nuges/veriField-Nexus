// =============================================================================

// VeriField Nexus — Super Admin Governance Portal

// =============================================================================

// Platform-owner governance panel to manage multi-tenant access, approve/reject

// requests, enable/disable users, and audit platform activities globally.

// =============================================================================



"use client";



import { useState, useEffect } from "react";
import { useToast } from "@/components/Toast";
import { RolePermissionConsole } from "@/components/access-control/RolePermissionConsole";
import { ThemeLogo } from "@/components/common/ThemeLogo";
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

  RotateCw,

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

  fetchGlobalAnalytics,

  fetchAdminUsers,

  fetchAdminUserDetail,

  adminResetUserPassword,

  adminSuspendUser,

  adminReactivateUser,

  adminDeleteUser,

  fetchProjectUsers,

  fetchAdminRoles,

  fetchAdminPermissions,

  fetchProjectMemberships,

  assignProjectMembership,

  revokeProjectMembership,

  adminRevokeUserSessions,

  fetchGovernanceAuditLogs,

  createAdminUserAccount,

  fetchOrganizationProjects

} from "@/lib/api";



type Tab = "leads" | "organizations" | "users" | "roles" | "projects" | "analytics" | "audit";



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

    methodologies: {

      "AMS-II.G": 0,

      "AMS-I.F": 0,

      "BIOCHAR-V1": 0,

      "EV-MOBILITY": 0

    }

  });



  const toast = useToast();



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



  // Authenticate user is SUPER_ADMIN or Admin

  useEffect(() => {

    if (isLoading) return;

    const userRoleStr = (user?.role || "").toUpperCase().replace(" ", "_");

    const allowed = ["SUPER_ADMIN", "ADMIN", "ORG_ADMIN"];

    if (!user || !allowed.includes(userRoleStr)) {

      router.push("/login?error=unauthorized");

    }

  }, [user, isLoading, router]);



  // Governance State

  const [rolesList, setRolesList] = useState<any[]>([]);

  const [permissionsList, setPermissionsList] = useState<any[]>([]);

  const [govAuditLogs, setGovAuditLogs] = useState<any[]>([]);

  const [account360Data, setAccount360Data] = useState<any | null>(null);

  const [loadingAccount360, setLoadingAccount360] = useState(false);



  // Enterprise Account Provisioning Wizard State

  const [isCreateUserModalOpen, setIsCreateUserModalOpen] = useState(false);

  const [createStep, setCreateStep] = useState<1 | 2 | 3 | 4 | 5>(1);

  const [createForm, setCreateForm] = useState<{
    fullName: string;
    email: string;
    phone: string;
    jobTitle: string;
    role: string;
    organizationId: string;
    password: string;
    orgMode: "existing" | "new";
    newOrgName: string;
  }>({
    fullName: "",
    email: "",
    phone: "",
    jobTitle: "",
    role: "FIELD_AGENT",
    organizationId: "",
    password: "",
    orgMode: "existing",
    newOrgName: "",
  });

  const [createProjectMemberships, setCreateProjectMemberships] = useState<Array<{ project_id: string; role: string }>>([]);

  const [orgProjects, setOrgProjects] = useState<any[]>([]);

  const [loadingOrgProjects, setLoadingOrgProjects] = useState(false);

  const [isProvisioning, setIsProvisioning] = useState(false);

  const [provisionError, setProvisionError] = useState("");

  const [provisionResult, setProvisionResult] = useState<any | null>(null);



  const handleOpenCreateUserModal = async () => {

    setIsCreateUserModalOpen(true);

    setCreateStep(1);

    setCreateForm({
      fullName: "",
      email: "",
      phone: "",
      jobTitle: "",
      role: "FIELD_AGENT",
      organizationId: "",
      password: "",
      orgMode: "existing",
      newOrgName: "",
    });

    setCreateProjectMemberships([]);

    setProvisionError("");

    setProvisionResult(null);



    // Always fetch fresh organizations for the wizard
    try {
      const o = await fetchAllOrganizations();
      setOrgs(o);
      const valid = (o || []).filter((item: any) => !item.name.startsWith("Test ") && !item.name.startsWith("Hardening ") && !item.name.startsWith("Attack "));
      if (valid.length > 0) {
        setCreateForm(prev => ({ ...prev, organizationId: valid[0].id }));
        try {
          const projs = await fetchOrganizationProjects(valid[0].id);
          setOrgProjects(projs || []);
        } catch (e) {}
      }
    } catch (e) {
      console.error("Failed to load organizations for wizard:", e);
    }

    if (rolesList.length === 0) {
      try {
        const r = await fetchAdminRoles();
        setRolesList(r);
      } catch (e) {
        console.error("Failed to load roles for wizard:", e);
      }
    }
  };



  const handleOrgChangeInWizard = async (orgId: string) => {

    setCreateForm(prev => ({ ...prev, organizationId: orgId }));

    setCreateProjectMemberships([]);

    if (!orgId) {

      setOrgProjects([]);

      return;

    }

    setLoadingOrgProjects(true);

    try {

      const projs = await fetchOrganizationProjects(orgId);

      setOrgProjects(projs || []);

    } catch (e) {

      setOrgProjects([]);

    } finally {

      setLoadingOrgProjects(false);

    }

  };



  const handleToggleProjectMembership = (projectId: string, projRole = "FIELD_AGENT") => {

    setCreateProjectMemberships(prev => {

      const exists = prev.find(pm => pm.project_id === projectId);

      if (exists) {

        return prev.filter(pm => pm.project_id !== projectId);

      } else {

        return [...prev, { project_id: projectId, role: projRole }];

      }

    });

  };



  const handleUpdateProjectMembershipRole = (projectId: string, newRole: string) => {

    setCreateProjectMemberships(prev =>

      prev.map(pm => pm.project_id === projectId ? { ...pm, role: newRole } : pm)

    );

  };



  const handleProvisionAccountSubmit = async () => {

    setProvisionError("");

    setIsProvisioning(true);

    try {

      const res = await createAdminUserAccount({

        full_name: createForm.fullName,

        email: createForm.email,

        phone: createForm.phone || undefined,

        job_title: createForm.jobTitle || undefined,

        role: createForm.role,

        organization_id: createForm.orgMode === "new" ? undefined : (createForm.organizationId || undefined),

        password: createForm.password || undefined,

        project_memberships: createProjectMemberships,

        meta_data: createForm.orgMode === "new" && createForm.newOrgName.trim() ? { organization: createForm.newOrgName.trim(), organization_name: createForm.newOrgName.trim() } : undefined,

      });



      setProvisionResult(res);

      toast.success("Account Provisioned", res.message || "User account created successfully.");

      await loadData();

    } catch (err: any) {

      setProvisionError(err.message || "Failed to provision user account.");

    } finally {

      setIsProvisioning(false);

    }

  };



  // Load Data based on active tab

  const loadData = async () => {

    setLoadingData(true);

    try {

      if (activeTab === "leads") {

        const [res, o] = await Promise.all([fetchAccessRequests(), fetchAllOrganizations()]);

        setRequests(res);

        setOrgs(o);

      } else if (activeTab === "organizations") {

        const res = await fetchAllOrganizations();

        setOrgs(res);

      } else if (activeTab === "users") {

        const [res, o] = await Promise.all([fetchAllUsersGlobal(), fetchAllOrganizations()]);

        setUsers(res);

        setOrgs(o);

      } else if (activeTab === "roles") {

        const [r, p] = await Promise.all([fetchAdminRoles(), fetchAdminPermissions()]);

        setRolesList(r);

        setPermissionsList(p);

      } else if (activeTab === "projects") {

        const o = await fetchAllOrganizations();

        setOrgs(o);

      } else if (activeTab === "analytics") {

        const [o, u, globalStats] = await Promise.all([

          fetchAllOrganizations(),

          fetchAllUsersGlobal(),

          fetchGlobalAnalytics()

        ]);

        setMrvStats(globalStats);

        setOrgs(o);

        setUsers(u);

      } else if (activeTab === "audit") {

        const logs = await fetchGovernanceAuditLogs();

        setGovAuditLogs(logs);

      }

    } catch (err) {

      console.error("Error loading admin data:", err);

    } finally {

      setLoadingData(false);

    }

  };



  const openAccount360 = async (userId: string) => {

    setLoadingAccount360(true);

    try {

      const data = await fetchAdminUserDetail(userId);

      setAccount360Data(data);

    } catch (err: any) {

      toast.error("Account 360 Error", err.message || "Failed to inspect user account.");

    } finally {

      setLoadingAccount360(false);

    }

  };



  useEffect(() => {

    const userRoleStr = (user?.role || "").toUpperCase().replace(" ", "_");

    const isAllowed = ["SUPER_ADMIN", "ADMIN", "ORG_ADMIN"].includes(userRoleStr);

    if (user && isAllowed) {

      loadData();

      const interval = setInterval(() => {

        loadData();

      }, 10000);

      return () => clearInterval(interval);

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



  const isUserActive = (u: any) => {

    if (!u) return false;

    if (u.status) {

      return u.status.toLowerCase() === "active";

    }

    return u.is_active === true || u.is_active === 1 || u.is_active === "true";

  };



  const handleToggleSuspension = async (userObj: any) => {

    const activeState = isUserActive(userObj);

    const actionText = activeState ? "suspend" : "activate";

    if (!confirm(`Are you sure you want to ${actionText} this user's access?`)) return;



    setProcessingId(userObj.id);

    try {

      if (activeState) {

        await adminSuspendUser(userObj.id);

        toast.success("Account Suspended", "User account access has been suspended.");

      } else {

        await adminReactivateUser(userObj.id);

        toast.success("Account Reactivated", "User account access has been restored.");

      }

      await loadData();

    } catch (err: any) {

      toast.error('Operation Failed', err.message || "Failed to update user status.");

    } finally {

      setProcessingId(null);

    }

  };



  const handleDeleteUserAccount = async (userId: string, userEmail: string) => {

    if (!confirm(`Are you sure you want to permanently delete/deactivate user account "${userEmail}"? Operational records will be safely archived.`)) return;



    setProcessingId(userId);

    try {

      await adminDeleteUser(userId);

      toast.success("Account Deleted", `User account "${userEmail}" has been deactivated.`);

      await loadData();

    } catch (err: any) {

      toast.error('Operation Failed', err.message || "Failed to delete user account.");

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

      await adminResetUserPassword(resetPasswordUserId, resetNewPassword);

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
      <div className="flex flex-col items-center justify-center min-h-screen bg-[var(--color-background)] space-y-3">
        <div className="w-8 h-8 border-2 border-[#008A5E] border-t-transparent rounded-full animate-spin" />
        <p className="text-[var(--color-text-secondary)] text-xs font-medium">
          Resolving Super Admin Authority...
        </p>
      </div>
    );
  }  return (
    <div className="min-h-screen bg-[var(--color-background)] text-[var(--color-text-primary)] flex flex-col font-sans select-none">
      {/* SUPER ADMIN NAVBAR */}
      <header className="sticky top-0 w-full bg-[var(--color-surface)] border-b border-[var(--color-border)] z-40 shadow-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex items-center">
              <ThemeLogo className="h-8 w-auto object-contain" />
            </div>
            <span className="text-[10px] font-mono font-bold uppercase px-2.5 py-1 rounded-md bg-purple-100 dark:bg-purple-950/60 text-purple-800 dark:text-purple-200 border border-purple-300 dark:border-purple-700">
              Super Admin Governance
            </span>
          </div>

          <div className="flex items-center gap-2.5">
            <div className="flex items-center gap-2 bg-emerald-50 dark:bg-emerald-950/50 px-3 py-1.5 rounded-lg border border-emerald-300 dark:border-emerald-700">
              <span className="w-2 h-2 rounded-full bg-[#008A5E]" />
              <span className="text-xs font-bold text-emerald-800 dark:text-emerald-300">
                Super Admin
              </span>
            </div>

            <button
              onClick={loadData}
              disabled={loadingData}
              className="p-2 bg-[var(--color-surface)] hover:bg-[var(--color-surface-subtle)] rounded-lg border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-all shadow-xs cursor-pointer"
              title="Refresh Real-time Data"
            >
              <RotateCw size={15} className={loadingData ? "animate-spin text-[#008A5E]" : ""} />
            </button>

            <button
              onClick={() => {
                setPasswordForm({ currentPassword: "", newPassword: "", confirmPassword: "" });
                setPasswordError("");
                setPasswordSuccess("");
                setIsPasswordModalOpen(true);
              }}
              className="p-2 bg-[var(--color-surface)] hover:bg-[var(--color-surface-subtle)] rounded-lg border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-all shadow-xs cursor-pointer"
              title="Change Password"
            >
              <Settings size={15} />
            </button>

            <button
              onClick={handleSignOut}
              className="text-xs font-bold py-1.5 px-3.5 rounded-lg bg-red-50 hover:bg-red-600 hover:text-white border border-red-300 dark:border-red-700 text-red-700 dark:text-red-300 transition-all shadow-xs cursor-pointer"
            >
              Sign Out
            </button>
          </div>
        </div>
      </header>

      {/* DASHBOARD WRAPPER */}
      <div className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 flex flex-col md:flex-row gap-6">
        {/* SIDEBAR NAVIGATION TABS */}
        <aside className="w-full md:w-60 space-y-1.5 bg-[var(--color-surface)] p-3.5 rounded-xl border border-[var(--color-border)] self-start shadow-xs">
          <div className="px-3 py-2 text-[10px] uppercase tracking-wider font-extrabold text-[var(--color-text-muted)]">
            Governance Console
          </div>

          {[
            { id: "leads", label: "Access Requests", icon: FileCheck2 },
            { id: "organizations", label: "Organizations", icon: Building2 },
            { id: "users", label: "Users & Accounts", icon: Users },
            { id: "roles", label: "Roles & Permissions", icon: ShieldCheck },
            { id: "projects", label: "Projects & Access", icon: Database },
            { id: "audit", label: "Audit Ledger", icon: History },
            { id: "analytics", label: "System Analytics", icon: Activity }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as Tab)}
              className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg text-xs transition-all cursor-pointer ${
                activeTab === tab.id
                  ? "bg-[#008A5E] text-white font-bold shadow-sm"
                  : "text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-subtle)] hover:text-[var(--color-text-primary)] font-semibold"
              }`}
            >
              <div className="flex items-center gap-2.5">
                <tab.icon size={16} className={activeTab === tab.id ? "text-white" : "text-[var(--color-text-muted)]"} />
                <span>{tab.label}</span>
              </div>
              {tab.id === "leads" && requests.filter(r => r.status === "PENDING").length > 0 && (
                <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                  activeTab === tab.id
                    ? "bg-white text-[#008A5E]"
                    : "bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-700"
                }`}>
                  {requests.filter(r => r.status === "PENDING").length}
                </span>
              )}
            </button>
          ))}
        </aside>

        {/* MAIN PANEL */}
        <main className="flex-1 bg-[var(--color-surface)] rounded-xl border border-[var(--color-border)] p-6 min-h-[520px] flex flex-col relative shadow-xs">

          {/* Section title & sync button */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between border-b border-[var(--color-border)] pb-4 mb-6 gap-3">
            <div>
              <h2 className="text-base font-bold tracking-tight text-[var(--color-text-primary)]">
                {activeTab === "leads" && "Access Requests Queue"}
                {activeTab === "organizations" && "Registered Tenants"}
                {activeTab === "users" && "Users & Account 360 Workspace"}
                {activeTab === "roles" && "Platform Roles & Permission Catalogue"}
                {activeTab === "projects" && "Projects & Scoped Role Access"}
                {activeTab === "audit" && "Security Governance Audit Stream"}
                {activeTab === "analytics" && "Global MRV Telemetry"}
              </h2>
              <p className="text-xs text-[var(--color-text-secondary)] mt-0.5 font-normal">
                {activeTab === "leads" && "Review and approve/reject carbon developer and mini-grid operator applications."}
                {activeTab === "organizations" && "Manage provisioned tenants and coordinate workspace isolation."}
                {activeTab === "users" && "Inspect comprehensive user profiles, multi-project roles, and security actions."}
                {activeTab === "roles" && "Inspect metadata-driven roles, permissions, scopes, and user counts."}
                {activeTab === "projects" && "Manage project memberships and assign project-specific role privileges."}
                {activeTab === "audit" && "Immutable security audit logs tracking user creation, role changes, and admin actions."}
                {activeTab === "analytics" && "Aggregated measurement data and submission telemetry across all organizations."}
              </p>
            </div>

            <button
              onClick={loadData}
              disabled={loadingData}
              className="flex items-center gap-2 px-3.5 py-2 bg-[var(--color-surface)] hover:bg-[var(--color-surface-subtle)] rounded-lg border border-[var(--color-border)] text-xs font-bold text-[var(--color-text-primary)] transition-all shadow-xs cursor-pointer"
            >
              {loadingData ? (
                <Loader2 size={14} className="animate-spin text-[#008A5E]" />
              ) : (
                <RotateCw size={14} className="text-[var(--color-text-secondary)]" />
              )}
              <span>Sync Logs</span>
            </button>
          </div>

          {/* TAB CONTENT 1: ACCESS REQUESTS QUEUE */}
          {activeTab === "leads" && (
            <div className="flex-1 space-y-4">
              {requests.length === 0 ? (
                <div className="py-20 text-center text-[var(--color-text-muted)] text-xs">
                  No access requests submitted.
                </div>
              ) : (
                <div className="overflow-x-auto rounded-xl border border-[var(--color-border)]">
                  <table className="w-full text-left text-xs min-w-[840px]">
                    <thead>
                      <tr className="bg-[var(--color-surface-subtle)] border-b border-[var(--color-border)] text-[var(--color-text-secondary)] uppercase text-[10px] font-bold">
                        <th className="py-3 px-4 w-[24%]">Applicant / Organization</th>
                        <th className="py-3 px-4 w-[22%]">Contact</th>
                        <th className="py-3 px-4 w-[14%]">Region</th>
                        <th className="py-3 px-4 w-[16%]">Methodology Sector</th>
                        <th className="py-3 px-4 w-[10%]">Status</th>
                        <th className="py-3 px-4 w-[14%] text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[var(--color-border)]">
                      {requests.map(req => (
                        <tr key={req.id} className="hover:bg-[var(--color-surface-subtle)] transition-colors">
                          <td className="py-3.5 px-4 font-semibold text-[var(--color-text-primary)]">
                            <div>{req.full_name}</div>
                            <div className="text-[11px] text-[var(--color-text-muted)] font-normal truncate max-w-[180px]">{req.organization_name}</div>
                          </td>
                          <td className="py-3.5 px-4 text-[var(--color-text-secondary)]">
                            <div className="flex items-center gap-1.5 truncate max-w-[180px]" title={req.email}><Mail size={12} className="text-[var(--color-text-muted)] shrink-0" /><span className="truncate">{req.email}</span></div>
                            {req.phone && <div className="flex items-center gap-1.5 mt-0.5 text-[11px]"><Phone size={12} className="text-[var(--color-text-muted)] shrink-0" /><span>{req.phone}</span></div>}
                          </td>
                          <td className="py-3.5 px-4 text-[var(--color-text-secondary)]">
                            <span className="inline-flex items-center gap-1">
                              <MapPin size={12} className="text-[#008A5E]" />
                              {req.country || "Unspecified"}
                            </span>
                          </td>
                          <td className="py-3.5 px-4">
                            <span className="inline-block text-[10px] font-bold uppercase bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-300 dark:border-slate-700 px-2 py-0.5 rounded">
                              {(() => {
                                if (req.sector_name) return req.sector_name;
                                if (req.sector_code) return req.sector_code;
                                if (!req.use_case) return "Clean Cookstoves";
                                if (typeof req.use_case === "string" && req.use_case.startsWith("{")) {
                                  try {
                                    const parsed = JSON.parse(req.use_case);
                                    if (parsed && typeof parsed === "object") {
                                      const sid = parsed.sector_id || parsed.SECTOR_ID;
                                      if (sid === "dff43d66-631b-4f08-8763-aaab12d0d5ee" || sid === "dff43d66631b4f088763aaab12d0d5ee") return "Clean Cookstoves";
                                      if (sid === "7f12bfe9-b81c-442d-ad52-3e9318adafaa" || sid === "7f12bfe9b81c442dad523e9318adafaa") return "Hybrid Energy";
                                      if (sid === "e6db7fbe-9430-4ff5-9904-6caed0b94cce" || sid === "e6db7fbe94304ff599046caed0b94cce") return "Biochar Removal";
                                      if (sid === "867f684f-722c-4d2f-8734-113f4976840e" || sid === "867f684f722c4d2f8734113f4976840e") return "EV Mobility";
                                    }
                                  } catch (e) {}
                                }
                                return req.use_case?.split(" - ")[0] || "Clean Cookstoves";
                              })()}
                            </span>
                          </td>
                          <td className="py-3.5 px-4">
                            <span className={`inline-block whitespace-nowrap px-2.5 py-0.5 rounded-full text-[10px] font-bold border uppercase ${
                              req.status === "PENDING" ? "bg-amber-100 dark:bg-amber-950/60 border-amber-300 dark:border-amber-700 text-amber-800 dark:text-amber-200" :
                              req.status === "APPROVED" ? "bg-emerald-100 dark:bg-emerald-950/60 border-emerald-300 dark:border-emerald-700 text-emerald-800 dark:text-emerald-200" :
                              "bg-red-100 dark:bg-red-950/60 border-red-300 dark:border-red-700 text-red-800 dark:text-red-200"
                            }`}>
                              {req.status}
                            </span>
                          </td>
                          <td className="py-3.5 px-4 text-right">
                            <div className="flex justify-end gap-1.5 items-center whitespace-nowrap">
                              {req.status === "PENDING" ? (
                                <>
                                  <button
                                    onClick={() => handleReject(req.id)}
                                    disabled={processingId !== null}
                                    className="p-1.5 bg-red-50 hover:bg-red-600 hover:text-white border border-red-300 rounded-md text-red-600 transition-all cursor-pointer"
                                    title="Reject Lead"
                                  >
                                    <XCircle size={15} />
                                  </button>
                                  <button
                                    onClick={() => handleApprove(req.id)}
                                    disabled={processingId !== null}
                                    className="py-1.5 px-3 bg-[#008A5E] hover:bg-[#00734E] text-white border border-[#008A5E] text-[10px] font-bold uppercase rounded-md transition-all shadow-xs cursor-pointer"
                                  >
                                    {processingId === req.id ? <Loader2 size={12} className="animate-spin" /> : "Approve"}
                                  </button>
                                </>
                              ) : (
                                <button
                                  onClick={() => handleDeleteAccessRequest(req.id)}
                                  disabled={processingId !== null}
                                  className="p-1.5 bg-red-50 hover:bg-red-100 border border-red-300 rounded-md text-red-600 transition-all cursor-pointer"
                                  title="Delete Lead Record"
                                >
                                  <Trash2 size={14} />
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

          {/* TAB CONTENT 2: REGISTERED ORGANIZATIONS */}
          {activeTab === "organizations" && (
            <div className="flex-1 space-y-4">
              {orgs.length === 0 ? (
                <div className="py-20 text-center text-[var(--color-text-muted)] text-xs">
                  No registered tenants on the platform yet.
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {orgs.map(org => (
                    <div
                      key={org.id}
                      onClick={() => handleViewOrgAnalytics(org.id, org.name)}
                      className="p-5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] hover:border-[#008A5E] transition-all shadow-xs cursor-pointer space-y-4 group relative"
                    >
                      <div className="flex items-center justify-between" onClick={(e) => e.stopPropagation()}>
                        <span className="px-2.5 py-0.5 bg-emerald-100 dark:bg-emerald-950/60 border border-emerald-300 dark:border-emerald-700 text-emerald-800 dark:text-emerald-200 text-[10px] font-bold rounded-full">
                          {org.status || "ACTIVE"}
                        </span>
                        <div className="flex items-center gap-1.5">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedOrgForPasswordReset(org);
                            }}
                            className="p-1.5 bg-amber-50 dark:bg-amber-950/50 hover:bg-amber-100 rounded-md border border-amber-300 dark:border-amber-700 text-amber-700 dark:text-amber-300 transition-all shadow-xs cursor-pointer"
                            title="Change User Passwords"
                          >
                            <Key size={13} />
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDeleteOrg(org.id, org.name);
                            }}
                            disabled={processingId !== null}
                            className="p-1.5 bg-red-50 dark:bg-red-950/50 hover:bg-red-100 rounded-md border border-red-300 dark:border-red-700 text-red-600 dark:text-red-300 transition-all shadow-xs cursor-pointer"
                            title="Delete Organization"
                          >
                            <Trash2 size={13} />
                          </button>
                          <span className="text-[9px] font-mono text-[var(--color-text-muted)]">ID: {org.id.substring(0, 8)}...</span>
                        </div>
                      </div>

                      <div className="space-y-1">
                        <h4 className="font-bold text-[var(--color-text-primary)] text-sm leading-snug group-hover:text-[#008A5E] transition-colors">{org.name}</h4>
                        <p className="text-[11px] text-[var(--color-text-muted)]">
                          Workspace Created: {new Date(org.created_at).toLocaleDateString()}
                        </p>
                      </div>

                      {/* Agents List inside Org Card */}
                      <div className="space-y-1.5 pt-2 border-t border-[var(--color-border)]" onClick={(e) => e.stopPropagation()}>
                        <span className="text-[10px] uppercase tracking-wider text-[var(--color-text-muted)] font-bold block">Assigned Agents</span>
                        {users.filter(u => u.organization === org.name && u.role === "field_agent").length === 0 ? (
                          <span className="text-[11px] text-[var(--color-text-muted)] font-normal block">No agents created yet</span>
                        ) : (
                          <div className="flex flex-wrap gap-1 pt-0.5 max-h-[60px] overflow-y-auto scrollbar">
                            {users.filter(u => u.organization === org.name && u.role === "field_agent").map(agent => (
                              <span key={agent.id} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-[10px] font-medium text-slate-700 dark:text-slate-300" title={agent.email}>
                                <span className="w-1.5 h-1.5 rounded-full bg-[#008A5E]" />
                                {agent.full_name}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>

                      <div className="pt-2 border-t border-[var(--color-border)] flex justify-between items-center text-[11px] text-[var(--color-text-secondary)]">
                        <span>Associated Users: {users.filter(u => u.organization === org.name).length}</span>
                        <span className="text-[#008A5E] font-bold uppercase group-hover:underline transition-colors">View Analytics →</span>
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
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 bg-[var(--color-surface-subtle)] p-4 rounded-xl border border-[var(--color-border)] shadow-xs">
                <div>
                  <h3 className="text-sm font-bold text-[var(--color-text-primary)] flex items-center gap-2">
                    <Users size={16} className="text-[#008A5E]" />
                    <span>Platform Accounts Roster ({users.length})</span>
                  </h3>
                  <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">Governed user accounts across all tenant organizations</p>
                </div>
                <button
                  onClick={() => handleOpenCreateUserModal()}
                  className="px-4 py-2 bg-[#008A5E] hover:bg-[#00734E] text-white text-xs font-bold rounded-lg flex items-center gap-2 transition-all shadow-sm cursor-pointer"
                >
                  <UserIcon size={14} />
                  <span>+ Create Account</span>
                </button>
              </div>

              {users.length === 0 ? (
                <div className="py-20 text-center text-[var(--color-text-muted)] text-xs">
                  No users registered.
                </div>
              ) : (
                <div className="overflow-x-auto rounded-xl border border-[var(--color-border)]">
                  <table className="w-full text-left text-xs min-w-[840px]">
                    <thead>
                      <tr className="bg-[var(--color-surface-subtle)] border-b border-[var(--color-border)] text-[var(--color-text-secondary)] uppercase text-[10px] font-bold">
                        <th className="py-3 px-4 w-[22%]">User</th>
                        <th className="py-3 px-4 w-[20%]">Email</th>
                        <th className="py-3 px-4 w-[12%]">Role</th>
                        <th className="py-3 px-4 w-[22%]">Organization Workspace</th>
                        <th className="py-3 px-4 w-[10%]">Status</th>
                        <th className="py-3 px-4 w-[14%] text-right">Access Controls</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[var(--color-border)]">
                      {users.map(u => (
                        <tr key={u.id} className="hover:bg-[var(--color-surface-subtle)] transition-colors">
                          <td className="py-3.5 px-4 font-semibold text-[var(--color-text-primary)]">
                            <div>{u.full_name}</div>
                            <div className="text-[10px] font-mono text-[var(--color-text-muted)] font-normal truncate max-w-[150px]" title={u.id}>
                              ID: {u.id.substring(0, 10)}...
                            </div>
                          </td>
                          <td className="py-3.5 px-4 text-[var(--color-text-secondary)]">
                            <div className="truncate max-w-[170px]" title={u.email}>{u.email}</div>
                          </td>
                          <td className="py-3.5 px-4">
                            <span className={`inline-block whitespace-nowrap text-[10px] font-mono font-bold uppercase px-2.5 py-0.5 rounded-md border ${
                              u.role === "SUPER_ADMIN" ? "bg-purple-100 dark:bg-purple-950/60 border-purple-300 dark:border-purple-700 text-purple-800 dark:text-purple-200" :
                              (u.role === "ORG_ADMIN" || u.role === "ADMIN" || u.role === "admin") ? "bg-blue-100 dark:bg-blue-950/60 border-blue-300 dark:border-blue-700 text-blue-800 dark:text-blue-200" :
                              (u.role === "AUDITOR" || u.role === "VVB" || u.role === "VERIFIER") ? "bg-amber-100 dark:bg-amber-950/60 border-amber-300 dark:border-amber-700 text-amber-800 dark:text-amber-200" :
                              (u.role === "FIELD_AGENT" || u.role === "FIELD_SUPERVISOR") ? "bg-emerald-100 dark:bg-emerald-950/60 border-emerald-300 dark:border-emerald-700 text-emerald-800 dark:text-emerald-200" :
                              "bg-slate-100 dark:bg-slate-800 border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300"
                            }`}>
                              {u.role === "admin" ? "ORG_ADMIN" : u.role}
                            </span>
                          </td>
                          <td className="py-3.5 px-4 text-xs">
                            {(() => {
                              const userOrg = orgs.find(o => o.id === u.organization_id || o.name === u.organization);
                              const orgName = u.organization || userOrg?.name;
                              const sectors = (u.licensed_sectors && u.licensed_sectors.length > 0)
                                ? u.licensed_sectors
                                : (userOrg?.licensed_sectors || []);

                              if (u.role === "SUPER_ADMIN" && !orgName) {
                                return (
                                  <div className="flex flex-col">
                                    <span className="text-[var(--color-text-primary)] font-bold text-xs">Platform Global</span>
                                    <span className="text-[10px] text-[var(--color-text-muted)] font-mono">System Default</span>
                                  </div>
                                );
                              }

                              return (
                                <div className="flex flex-col items-start gap-1">
                                  <span className="text-[var(--color-text-primary)] font-bold text-xs truncate max-w-[170px] block" title={orgName || "System Default"}>
                                    {orgName || "System Default"}
                                  </span>
                                  {sectors.length > 0 && (
                                    <div className="flex flex-wrap gap-1">
                                      {sectors.map((sec: string) => (
                                        <span
                                          key={sec}
                                          className="px-2 py-0.5 rounded-md text-[9px] font-mono font-bold uppercase bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-300 dark:border-slate-700 whitespace-nowrap"
                                        >
                                          {sec}
                                        </span>
                                      ))}
                                    </div>
                                  )}
                                </div>
                              );
                            })()}
                          </td>
                          <td className="py-3.5 px-4">
                            <span className={`inline-block whitespace-nowrap px-2.5 py-0.5 rounded-full text-[10px] font-bold border uppercase ${
                              isUserActive(u)
                                ? "bg-emerald-100 dark:bg-emerald-950/60 border-emerald-300 dark:border-emerald-700 text-emerald-800 dark:text-emerald-200"
                                : "bg-red-100 dark:bg-red-950/60 border-red-300 dark:border-red-700 text-red-800 dark:text-red-200"
                            }`}>
                              {isUserActive(u) ? "Active" : "Suspended"}
                            </span>
                          </td>
                          <td className="py-3.5 px-4 text-right">
                            <div className="flex justify-end items-center gap-1.5 whitespace-nowrap">
                              <button
                                onClick={() => {
                                  setSelectedUserForDetails(u);
                                  openAccount360(u.id);
                                }}
                                className="p-1.5 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-md border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-200 transition-all shadow-xs cursor-pointer"
                                title="Inspect Account 360 & Activity Log"
                              >
                                <Eye size={14} />
                              </button>
                              {u.role !== "SUPER_ADMIN" && (
                                <>
                                  <button
                                    onClick={() => {
                                      const userOrg = orgs.find(o => o.name === u.organization || o.id === u.organization_id) || { id: u.organization_id, name: u.organization || "System Default" };
                                      setSelectedOrgForPasswordReset(userOrg);
                                      setResetPasswordUserId(u.id);
                                    }}
                                    className="p-1.5 bg-amber-50 dark:bg-amber-950/50 hover:bg-amber-100 rounded-md border border-amber-300 dark:border-amber-700 text-amber-700 dark:text-amber-300 transition-all shadow-xs cursor-pointer"
                                    title="Reset Password"
                                  >
                                    <Key size={14} />
                                  </button>
                                  <button
                                    onClick={() => handleDeleteUserAccount(u.id, u.email)}
                                    disabled={processingId === u.id}
                                    className="p-1.5 bg-red-50 dark:bg-red-950/50 hover:bg-red-100 rounded-md border border-red-300 dark:border-red-700 text-red-600 dark:text-red-300 transition-all shadow-xs cursor-pointer"
                                    title="Delete / Deactivate User Account"
                                  >
                                    <Trash2 size={14} />
                                  </button>
                                  <button
                                    onClick={() => handleToggleSuspension(u)}
                                    disabled={processingId !== null}
                                    className={`py-1 px-3 rounded-md border text-[10px] font-bold uppercase transition-all shadow-xs cursor-pointer ${
                                      isUserActive(u)
                                        ? "bg-red-50 hover:bg-red-600 hover:text-white dark:bg-red-950/50 border-red-300 dark:border-red-700 text-red-700 dark:text-red-300"
                                        : "bg-emerald-50 hover:bg-[#008A5E] hover:text-white dark:bg-emerald-950/50 border-emerald-300 dark:border-emerald-700 text-emerald-800 dark:text-emerald-300"
                                    }`}
                                  >
                                    {processingId === u.id ? <Loader2 size={11} className="animate-spin" /> : isUserActive(u) ? "Suspend" : "Activate"}
                                  </button>
                                </>
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
                <div className="bg-[var(--color-surface)] p-5 rounded-xl border border-[var(--color-border)] shadow-xs hover:border-[var(--color-border-hover)] transition-all">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider">Installations</span>
                    <div className="w-8 h-8 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 flex items-center justify-center text-[#008A5E] dark:text-emerald-400">
                      <Database size={16} />
                    </div>
                  </div>
                  <div className="mt-3">
                    <div className="text-2xl font-bold text-[var(--color-text-primary)]">{mrvStats.installations}</div>
                    <p className="text-xs text-[var(--color-text-muted)] mt-1 font-medium">Across all SaaS tenants</p>
                  </div>
                </div>

                <div className="bg-[var(--color-surface)] p-5 rounded-xl border border-[var(--color-border)] shadow-xs hover:border-[var(--color-border-hover)] transition-all">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider">Avg Trust Score</span>
                    <div className="w-8 h-8 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 flex items-center justify-center text-[#008A5E] dark:text-emerald-400">
                      <ShieldCheck size={16} />
                    </div>
                  </div>
                  <div className="mt-3">
                    <div className="text-2xl font-bold text-[#008A5E] dark:text-emerald-400">{mrvStats.avgTrust}%</div>
                    <p className="text-xs text-[var(--color-text-muted)] mt-1 font-medium">High-fidelity metrics lock</p>
                  </div>
                </div>

                <div className="bg-[var(--color-surface)] p-5 rounded-xl border border-[var(--color-border)] shadow-xs hover:border-[var(--color-border-hover)] transition-all">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider">CO₂ Impact</span>
                    <div className="w-8 h-8 rounded-lg bg-sky-50 dark:bg-sky-950/40 border border-sky-200 dark:border-sky-800 flex items-center justify-center text-sky-600 dark:text-sky-400">
                      <Globe size={16} />
                    </div>
                  </div>
                  <div className="mt-3">
                    <div className="text-2xl font-bold text-[var(--color-text-primary)]">{mrvStats.tCO2} t</div>
                    <p className="text-xs text-[var(--color-text-muted)] mt-1 font-medium">tCO2e Estimated</p>
                  </div>
                </div>

                <div className="bg-[var(--color-surface)] p-5 rounded-xl border border-[var(--color-border)] shadow-xs hover:border-[var(--color-border-hover)] transition-all">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider">Active Tenants</span>
                    <div className="w-8 h-8 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 flex items-center justify-center text-[#008A5E] dark:text-emerald-400">
                      <Building2 size={16} />
                    </div>
                  </div>
                  <div className="mt-3">
                    <div className="text-2xl font-bold text-[var(--color-text-primary)]">{mrvStats.activeOrgs}</div>
                    <p className="text-xs text-[var(--color-text-muted)] mt-1 font-medium">Approved workspaces</p>
                  </div>
                </div>
              </div>

              {/* Layout splits */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
                {/* Sector deployment distribution */}
                <div className="bg-[var(--color-surface)] p-6 rounded-xl border border-[var(--color-border)] shadow-xs space-y-4">
                  <div className="flex items-center justify-between">
                    <h4 className="font-bold text-sm text-[var(--color-text-primary)]">Tenant Methodology Coverage</h4>
                    <span className="text-xs text-[var(--color-text-muted)] font-medium">Active Distribution</span>
                  </div>

                  <div className="space-y-4 pt-1">
                    {(() => {
                      const methodologies = mrvStats.methodologies || {};
                      const sectorLabels: Record<string, string> = {
                        "AMS-II.G": "Clean Cookstoves Orgs",
                        "AMS-I.F": "Renewable Energy Orgs",
                        "BIOCHAR-V1": "Biochar Removal Orgs",
                        "EV-MOBILITY": "EV Mobility Orgs"
                      };
                      const totalOrgs = orgs.length;

                      // Ensure all 4 sectors are present
                      const allSectors: Record<string, number> = {
                        "AMS-II.G": methodologies["AMS-II.G"] || 0,
                        "AMS-I.F": methodologies["AMS-I.F"] || 0,
                        "BIOCHAR-V1": methodologies["BIOCHAR-V1"] || 0,
                        "EV-MOBILITY": methodologies["EV-MOBILITY"] || 0,
                        ...methodologies
                      };

                      return Object.entries(allSectors).map(([code, count]: [string, any], idx) => {
                        const label = sectorLabels[code] || `${code.replace(/_/g, ' ')} Orgs`;
                        const numCount = typeof count === "number" ? count : 0;
                        const pct = totalOrgs > 0 ? Math.round((numCount / totalOrgs) * 100) : 0;

                        return (
                          <div key={idx} className="space-y-1.5 text-xs">
                            <div className="flex justify-between items-center text-[var(--color-text-secondary)]">
                              <span className="font-semibold font-mono text-[var(--color-text-primary)]">{code}</span>
                              <span className="text-[#008A5E] dark:text-emerald-400 font-semibold">{label} ({pct}%)</span>
                            </div>
                            <div className="w-full bg-[var(--color-background)] h-2 rounded-full overflow-hidden border border-[var(--color-border)]">
                              <div
                                className="bg-[#008A5E] dark:bg-emerald-500 h-full rounded-full transition-all duration-300"
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
                <div className="bg-[var(--color-surface)] p-6 rounded-xl border border-[var(--color-border)] shadow-xs space-y-4">
                  <div className="flex items-center justify-between">
                    <h4 className="font-bold text-sm text-[var(--color-text-primary)]">Global User Role Breakdown</h4>
                    <span className="text-xs text-[var(--color-text-muted)] font-medium">RBAC Security Profiles</span>
                  </div>

                  <div className="grid grid-cols-3 gap-3 pt-1 text-center">
                    <div className="bg-[var(--color-background)] p-3.5 rounded-xl border border-[var(--color-border)]">
                      <span className="text-[10px] text-[var(--color-text-muted)] uppercase block font-semibold tracking-wider">Super Admin</span>
                      <p className="text-xl font-bold text-purple-600 dark:text-purple-400 mt-1">1</p>
                    </div>

                    <div className="bg-[var(--color-background)] p-3.5 rounded-xl border border-[var(--color-border)]">
                      <span className="text-[10px] text-[var(--color-text-muted)] uppercase block font-semibold tracking-wider">Org Admin</span>
                      <p className="text-xl font-bold text-blue-600 dark:text-blue-400 mt-1">
                        {users.filter(u => u.role === "ORG_ADMIN" || u.role === "admin").length}
                      </p>
                    </div>

                    <div className="bg-[var(--color-background)] p-3.5 rounded-xl border border-[var(--color-border)]">
                      <span className="text-[10px] text-[var(--color-text-muted)] uppercase block font-semibold tracking-wider">Field Agent</span>
                      <p className="text-xl font-bold text-[#008A5E] dark:text-emerald-400 mt-1">
                        {users.filter(u => u.role === "field_agent").length}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}



          {/* TAB CONTENT: ROLES & PERMISSIONS CATALOGUE */}

          {activeTab === "roles" && (

            <div className="flex-1">

              <RolePermissionConsole
                roles={rolesList}
                permissionsList={permissionsList}
                users={users}
                organizations={orgs}
                onRefresh={async () => {
                  try {
                    const r = await fetchAdminRoles();
                    setRolesList(r);
                    const u = await fetchAdminUsers();
                    setUsers(u);
                  } catch (e) {}
                }}
              />

            </div>

          )}



          {/* TAB CONTENT: PROJECTS & ACCESS GOVERNANCE */}
          {activeTab === "projects" && (
            <div className="flex-1 space-y-4">
              <div className="grid grid-cols-1 gap-4">
                {orgs.map((org) => (
                  <div key={org.id} className="bg-[var(--color-surface-subtle)] border border-[var(--color-border)] rounded-xl p-4 space-y-3 shadow-xs">
                    <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-2">
                      <div className="flex items-center gap-2">
                        <Building2 size={16} className="text-[#008A5E]" />
                        <span className="font-bold text-[var(--color-text-primary)] text-xs uppercase tracking-wider">{org.name}</span>
                      </div>
                      <span className="text-[10px] font-mono text-[var(--color-text-muted)]">Status: {org.status || "ACTIVE"}</span>
                    </div>

                    <div className="p-3 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] text-xs space-y-1">
                      <p className="font-bold text-[var(--color-text-primary)]">Organization Access Scope Active</p>
                      <p className="text-xs text-[var(--color-text-secondary)]">
                        Multi-project role membership enabled. Users can hold project-specific permissions across organization projects.
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB CONTENT 5: IMMUTABLE SECURITY AUDIT LOGS */}
          {activeTab === "audit" && (
            <div className="flex-1 space-y-4 font-mono text-xs">
              {govAuditLogs.length === 0 ? (
                <div className="py-20 text-center text-[var(--color-text-muted)] text-xs">
                  No governance audit logs indexed yet.
                </div>
              ) : (
                <div className="bg-[var(--color-surface-subtle)] border border-[var(--color-border)] rounded-xl p-4 max-h-[460px] overflow-y-auto space-y-3 scrollbar">
                  {govAuditLogs.map((log) => (
                    <div key={log.id} className="flex gap-4 items-start border-b border-[var(--color-border)] pb-2.5 last:border-b-0 last:pb-0">
                      <span className="text-[var(--color-text-muted)] shrink-0 text-[10px]">[{new Date(log.created_at).toLocaleTimeString()}]</span>
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className={`font-bold px-1.5 py-0.5 rounded text-[9px] uppercase ${
                            log.action.includes("GRANTED") || log.action.includes("CREATED") || log.action.includes("REACTIVATED")
                              ? "bg-emerald-50 dark:bg-emerald-950/40 text-[#008A5E] dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800" :
                            log.action.includes("SUSPENDED") || log.action.includes("REVOKED") || log.action.includes("DELETED")
                              ? "bg-red-50 dark:bg-red-950/40 text-red-700 dark:text-red-300 border border-red-200 dark:border-red-800" :
                            "bg-purple-50 dark:bg-purple-950/40 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800"
                          }`}>
                            {log.action}
                          </span>
                          <span className="text-[var(--color-text-secondary)] text-[10px]">Result: {log.result}</span>
                        </div>
                        <p className="text-[var(--color-text-primary)] text-[11px]">
                          Target User: {log.target_user_id || "N/A"} • Actor: {log.actor_user_id || "System"}
                        </p>
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
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs">
          <div className="relative w-full max-w-md bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl shadow-2xl overflow-hidden animate-fade-in-up p-8 space-y-6">
            <div className="text-center space-y-2">
              <div className="w-12 h-12 rounded-full bg-emerald-100 dark:bg-emerald-950/60 border border-emerald-300 dark:border-emerald-700 text-emerald-800 dark:text-emerald-300 flex items-center justify-center mx-auto">
                <Sparkles size={24} />
              </div>
              <h3 className="text-lg font-bold text-[var(--color-text-primary)]">Tenant Credentials Generated</h3>
              <p className="text-xs text-[var(--color-text-secondary)]">
                Organization workspace successfully provisioned. Share these credentials with the tenant administrator.
              </p>
            </div>

            <div className="bg-[var(--color-surface-subtle)] border border-[var(--color-border)] p-4 rounded-xl space-y-3.5 text-xs font-mono">
              <div className="space-y-0.5">
                <span className="text-[10px] uppercase tracking-wider text-[var(--color-text-muted)] block font-bold">Organization Name</span>
                <p className="text-[var(--color-text-primary)] font-bold">{approvedCredentials.orgName}</p>
              </div>

              <div className="space-y-0.5">
                <span className="text-[10px] uppercase tracking-wider text-[var(--color-text-muted)] block font-bold">Admin Login Email</span>
                <p className="text-[var(--color-text-primary)] font-bold">{approvedCredentials.email}</p>
              </div>

              <div className="space-y-0.5">
                <span className="text-[10px] uppercase tracking-wider text-[var(--color-text-muted)] block font-bold">Temporary Password</span>
                <p className="text-emerald-800 dark:text-emerald-300 font-bold text-sm tracking-wide bg-[var(--color-surface)] p-2.5 rounded-lg border border-emerald-300 dark:border-emerald-700">
                  {approvedCredentials.tempPw}
                </p>
              </div>
            </div>

            <div className="bg-amber-50 dark:bg-amber-950/30 border border-amber-300 dark:border-amber-700 p-3 rounded-lg text-xs text-amber-900 dark:text-amber-200 leading-normal">
              ⚠️ <strong>First Login Security</strong>: The new Org Admin will be forced to change this temporary password on their first login.
            </div>

            <div className="flex gap-3">
              <button
                onClick={handleCopyCredentials}
                className="flex-1 py-2.5 bg-[var(--color-surface)] hover:bg-[var(--color-surface-subtle)] border border-[var(--color-border)] text-[var(--color-text-primary)] rounded-xl text-xs font-bold uppercase transition-all flex items-center justify-center gap-1.5 shadow-xs cursor-pointer"
              >
                {copiedText ? (
                  <>
                    <Check size={14} className="text-[#008A5E]" />
                    <span>Copied!</span>
                  </>
                ) : (
                  <>
                    <Copy size={14} />
                    <span>Copy Info</span>
                  </>
                )}
              </button>
              <button
                onClick={() => setApprovedCredentials(null)}
                className="flex-1 py-2.5 bg-[#008A5E] hover:bg-[#00734E] text-white rounded-xl text-xs font-bold uppercase transition-all shadow-xs cursor-pointer"
              >
                Close Queue
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ACCOUNT 360 INSPECTION MODAL */}
      {selectedUserForDetails && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs">
          <div className="relative w-full max-w-2xl bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl shadow-2xl overflow-hidden p-6 sm:p-8 space-y-6 animate-fade-in-up max-h-[90vh] overflow-y-auto">
            {/* Header */}
            <div className="flex items-start justify-between border-b border-[var(--color-border)] pb-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2.5">
                  <div className="w-10 h-10 rounded-xl bg-emerald-100 dark:bg-emerald-950/60 border border-emerald-300 dark:border-emerald-700 text-emerald-800 dark:text-emerald-300 flex items-center justify-center font-bold text-sm">
                    {selectedUserForDetails.full_name ? selectedUserForDetails.full_name.slice(0, 2).toUpperCase() : "US"}
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-[var(--color-text-primary)] leading-tight">{selectedUserForDetails.full_name}</h3>
                    <p className="text-xs text-[var(--color-text-secondary)]">{selectedUserForDetails.email}</p>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className={`text-[10px] font-mono font-bold uppercase px-2.5 py-1 rounded-md border ${
                  selectedUserForDetails.role === "SUPER_ADMIN" ? "bg-purple-100 dark:bg-purple-950/60 border-purple-300 dark:border-purple-700 text-purple-800 dark:text-purple-200" :
                  selectedUserForDetails.role === "ORG_ADMIN" || selectedUserForDetails.role === "admin" ? "bg-blue-100 dark:bg-blue-950/60 border-blue-300 dark:border-blue-700 text-blue-800 dark:text-blue-200" :
                  "bg-emerald-100 dark:bg-emerald-950/60 border-emerald-300 dark:border-emerald-700 text-emerald-800 dark:text-emerald-200"
                }`}>
                  {selectedUserForDetails.role === "admin" ? "ORG_ADMIN" : selectedUserForDetails.role}
                </span>
                <button
                  onClick={() => {
                    setSelectedUserForDetails(null);
                    setAccount360Data(null);
                  }}
                  className="p-1 hover:bg-[var(--color-surface-subtle)] rounded-lg text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors text-xs font-bold uppercase cursor-pointer"
                >
                  ✕
                </button>
              </div>
            </div>

            {loadingAccount360 ? (
              <div className="py-16 flex flex-col items-center justify-center space-y-3">
                <Loader2 size={24} className="animate-spin text-[#008A5E]" />
                <p className="text-[var(--color-text-secondary)] text-xs font-medium">Loading Account 360 activity log...</p>
              </div>
            ) : (
              <div className="space-y-6">
                {/* 4 Summary KPI Cards */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="bg-[var(--color-surface-subtle)] p-3.5 rounded-xl border border-[var(--color-border)] space-y-1">
                    <span className="text-[10px] text-[var(--color-text-muted)] uppercase font-bold tracking-wider">Projects</span>
                    <div className="text-lg font-bold text-[var(--color-text-primary)]">
                      {account360Data?.assigned_projects?.length ?? (selectedUserForDetails.projects_count || 0)}
                    </div>
                  </div>

                  <div className="bg-[var(--color-surface-subtle)] p-3.5 rounded-xl border border-[var(--color-border)] space-y-1">
                    <span className="text-[10px] text-[var(--color-text-muted)] uppercase font-bold tracking-wider">Activities</span>
                    <div className="text-lg font-bold text-emerald-700 dark:text-emerald-400">
                      {account360Data?.activity_summary?.total ?? (selectedUserForDetails.activities_count || 0)}
                    </div>
                  </div>

                  <div className="bg-[var(--color-surface-subtle)] p-3.5 rounded-xl border border-[var(--color-border)] space-y-1">
                    <span className="text-[10px] text-[var(--color-text-muted)] uppercase font-bold tracking-wider">Assets</span>
                    <div className="text-lg font-bold text-[var(--color-text-primary)]">
                      {account360Data?.asset_summary?.total ?? (selectedUserForDetails.assets_count || 0)}
                    </div>
                  </div>

                  <div className="bg-[var(--color-surface-subtle)] p-3.5 rounded-xl border border-[var(--color-border)] space-y-1">
                    <span className="text-[10px] text-[var(--color-text-muted)] uppercase font-bold tracking-wider">Evidence Packages</span>
                    <div className="text-lg font-bold text-purple-700 dark:text-purple-400">
                      {account360Data?.evidence_summary?.total ?? (selectedUserForDetails.evidence_count || 0)}
                    </div>
                  </div>
                </div>

                {/* Account Details Summary */}
                <div className="bg-[var(--color-surface-subtle)] border border-[var(--color-border)] p-4 rounded-xl space-y-3 text-xs">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <span className="text-[10px] uppercase text-[var(--color-text-muted)] font-bold block">Organization Workspace</span>
                      <p className="text-[var(--color-text-primary)] font-bold">{selectedUserForDetails.organization || "System Default"}</p>
                    </div>
                    <div>
                      <span className="text-[10px] uppercase text-[var(--color-text-muted)] font-bold block">Phone Number</span>
                      <p className="text-[var(--color-text-secondary)] font-medium">{selectedUserForDetails.phone || "Not specified"}</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <span className="text-[10px] uppercase text-[var(--color-text-muted)] font-bold block">Account Status</span>
                      <span className={`inline-block px-2.5 py-0.5 rounded-full text-[10px] font-bold border uppercase mt-0.5 ${
                        isUserActive(selectedUserForDetails) ? "bg-emerald-100 dark:bg-emerald-950/60 border-emerald-300 dark:border-emerald-700 text-emerald-800 dark:text-emerald-200" : "bg-red-100 dark:bg-red-950/60 border-red-300 dark:border-red-700 text-red-800 dark:text-red-200"
                      }`}>
                        {isUserActive(selectedUserForDetails) ? "Active" : "Suspended"}
                      </span>
                    </div>
                    <div>
                      <span className="text-[10px] uppercase text-[var(--color-text-muted)] font-bold block">Created At</span>
                      <p className="text-[var(--color-text-secondary)] font-mono text-[11px]">
                        {selectedUserForDetails.created_at ? new Date(selectedUserForDetails.created_at).toLocaleString() : "N/A"}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Assigned Projects Roster */}
                {account360Data?.assigned_projects && account360Data.assigned_projects.length > 0 && (
                  <div className="space-y-2">
                    <h4 className="font-bold text-xs text-[var(--color-text-secondary)] uppercase tracking-wider">Assigned Projects Roster</h4>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {account360Data.assigned_projects.map((p: any) => (
                        <div key={p.id} className="p-3 rounded-xl bg-[var(--color-surface-subtle)] border border-[var(--color-border)] space-y-1">
                          <div className="flex justify-between items-center text-xs">
                            <span className="font-bold text-[var(--color-text-primary)] truncate">{p.name}</span>
                            <span className="text-[10px] font-mono text-emerald-800 dark:text-emerald-300 font-bold px-2 py-0.5 rounded-md bg-emerald-100 dark:bg-emerald-950/60 border border-emerald-300 dark:border-emerald-700">{p.role}</span>
                          </div>
                          <p className="text-[11px] text-[var(--color-text-muted)] font-mono">Code: {p.project_code} • {p.country || "Global"}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Activities Log & Field Submissions Feed */}
                <div className="space-y-2">
                  <h4 className="font-bold text-xs text-[var(--color-text-secondary)] uppercase tracking-wider flex items-center justify-between">
                    <span>User Activities Log & Field Telemetry</span>
                    <span className="text-[10px] font-mono text-emerald-700 dark:text-emerald-400 font-bold">
                      {account360Data?.activity_summary?.verified ?? 0} Verified • {account360Data?.activity_summary?.pending ?? 0} Pending
                    </span>
                  </h4>

                  {!account360Data?.activity_summary?.recent || account360Data.activity_summary.recent.length === 0 ? (
                    <div className="p-4 text-center text-[var(--color-text-muted)] text-xs rounded-xl bg-[var(--color-surface-subtle)] border border-[var(--color-border)]">
                      0 field activities submitted by this user account yet.
                    </div>
                  ) : (
                    <div className="overflow-x-auto rounded-xl border border-[var(--color-border)]">
                      <table className="w-full text-left text-xs">
                        <thead>
                          <tr className="bg-[var(--color-surface-subtle)] text-[var(--color-text-secondary)] uppercase text-[10px] font-bold border-b border-[var(--color-border)]">
                            <th className="p-2.5">Activity Type</th>
                            <th className="p-2.5">Captured At</th>
                            <th className="p-2.5">Trust Score</th>
                            <th className="p-2.5">Status</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-[var(--color-border)]">
                          {account360Data.activity_summary.recent.map((act: any) => (
                            <tr key={act.id} className="hover:bg-[var(--color-surface-subtle)]">
                              <td className="p-2.5 text-[var(--color-text-primary)] font-semibold capitalize">{act.activity_type.replace(/_/g, " ")}</td>
                              <td className="p-2.5 text-[var(--color-text-secondary)] text-[11px] font-mono">{new Date(act.captured_at).toLocaleString()}</td>
                              <td className="p-2.5 font-bold text-emerald-700 dark:text-emerald-400">{act.trust_score}%</td>
                              <td className="p-2.5">
                                <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold border uppercase ${
                                  act.status === "verified" ? "bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700" :
                                  act.status === "flagged" ? "bg-red-100 dark:bg-red-950/60 text-red-800 dark:text-red-300 border border-red-300 dark:border-red-700" :
                                  "bg-amber-100 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-700"
                                }`}>
                                  {act.status}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>

                {/* Account Action Controls Bar */}
                <div className="pt-3 border-t border-[var(--color-border)] flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    {selectedUserForDetails.role !== "SUPER_ADMIN" && (
                      <>
                        <button
                          onClick={() => {
                            const userOrg = orgs.find(o => o.name === selectedUserForDetails.organization || o.id === selectedUserForDetails.organization_id) || { id: selectedUserForDetails.organization_id, name: selectedUserForDetails.organization || "System Default" };
                            setSelectedUserForDetails(null);
                            setSelectedOrgForPasswordReset(userOrg);
                            setResetPasswordUserId(selectedUserForDetails.id);
                          }}
                          className="px-3.5 py-2 bg-amber-50 dark:bg-amber-950/50 hover:bg-amber-100 border border-amber-300 dark:border-amber-700 text-amber-800 dark:text-amber-300 text-xs font-bold rounded-lg flex items-center gap-1.5 transition-all cursor-pointer shadow-xs"
                        >
                          <Key size={13} />
                          <span>Reset Password</span>
                        </button>

                        <button
                          onClick={() => handleToggleSuspension(selectedUserForDetails)}
                          disabled={processingId !== null}
                          className={`px-3.5 py-2 text-xs font-bold uppercase rounded-lg border transition-all cursor-pointer shadow-xs ${
                            isUserActive(selectedUserForDetails)
                              ? "bg-red-50 hover:bg-red-600 hover:text-white dark:bg-red-950/50 border-red-300 dark:border-red-700 text-red-700 dark:text-red-300"
                              : "bg-emerald-50 hover:bg-[#008A5E] hover:text-white dark:bg-emerald-950/50 border-emerald-300 dark:border-emerald-700 text-emerald-800 dark:text-emerald-300"
                          }`}
                        >
                          {isUserActive(selectedUserForDetails) ? "Suspend Account" : "Activate Account"}
                        </button>

                        <button
                          onClick={() => handleDeleteUserAccount(selectedUserForDetails.id, selectedUserForDetails.email)}
                          disabled={processingId !== null}
                          className="px-3.5 py-2 bg-red-50 hover:bg-red-600 hover:text-white dark:bg-red-950/50 border border-red-300 dark:border-red-700 text-red-700 dark:text-red-300 text-xs font-bold rounded-lg flex items-center gap-1.5 transition-all cursor-pointer shadow-xs"
                        >
                          <Trash2 size={13} />
                          <span>Delete Account</span>
                        </button>
                      </>
                    )}
                  </div>

                  <button
                    onClick={() => {
                      setSelectedUserForDetails(null);
                      setAccount360Data(null);
                    }}
                    className="py-2 px-4 bg-[var(--color-surface)] hover:bg-[var(--color-surface-subtle)] border border-[var(--color-border)] text-[var(--color-text-primary)] rounded-lg text-xs font-bold transition-all cursor-pointer shadow-xs"
                  >
                    Close 360 View
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* USER PASSWORD RESET MODAL FOR SAAS ORG */}
      {selectedOrgForPasswordReset && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs">
          <div className="relative w-full max-w-md bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl shadow-2xl overflow-hidden p-8 space-y-6 animate-fade-in-up">
            <div className="text-center space-y-2">
              <div className="w-12 h-12 rounded-full bg-emerald-100 dark:bg-emerald-950/60 border border-emerald-300 dark:border-emerald-700 text-emerald-800 dark:text-emerald-300 flex items-center justify-center mx-auto">
                <Key size={22} />
              </div>
              <h3 className="text-base font-bold text-[var(--color-text-primary)]">Reset User Credentials</h3>
              <p className="text-xs text-[var(--color-text-secondary)]">
                Force update the password of a user under {selectedOrgForPasswordReset.name}
              </p>
            </div>

            <form onSubmit={handleResetUserPasswordSubmit} className="space-y-4">
              <div className="space-y-1.5 text-left">
                <label className="text-[10px] uppercase tracking-wider text-[var(--color-text-secondary)] font-bold">Select User</label>
                <select
                  required
                  value={resetPasswordUserId}
                  onChange={(e) => setResetPasswordUserId(e.target.value)}
                  className="w-full bg-[var(--color-surface)] border border-[var(--color-border)] focus:border-[#008A5E] rounded-lg px-3 py-2 text-xs text-[var(--color-text-primary)] focus:outline-none transition-colors shadow-xs"
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
                <label className="text-[10px] uppercase tracking-wider text-[var(--color-text-secondary)] font-bold">New Password</label>
                <input
                  type="password"
                  required
                  placeholder="Minimum 8 characters"
                  value={resetNewPassword}
                  onChange={(e) => setResetNewPassword(e.target.value)}
                  className="w-full bg-[var(--color-surface)] border border-[var(--color-border)] focus:border-[#008A5E] rounded-lg px-3 py-2 text-xs text-[var(--color-text-primary)] focus:outline-none transition-colors shadow-xs"
                />
              </div>

              {resetPasswordError && (
                <p className="text-red-600 text-xs font-bold">{resetPasswordError}</p>
              )}

              {resetPasswordSuccess && (
                <p className="text-emerald-700 font-bold text-xs">{resetPasswordSuccess}</p>
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
                  className="flex-1 py-2.5 bg-[var(--color-surface)] hover:bg-[var(--color-surface-subtle)] border border-[var(--color-border)] text-[var(--color-text-primary)] rounded-lg text-xs font-bold uppercase transition-all shadow-xs cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isResettingPassword}
                  className="flex-1 py-2.5 bg-[#008A5E] hover:bg-[#00734E] text-white rounded-lg text-xs font-bold uppercase transition-all disabled:opacity-50 shadow-xs cursor-pointer"
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
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs">
          <div className="relative w-full max-w-2xl bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl shadow-2xl overflow-hidden p-8 space-y-6 animate-fade-in-up">
            <div className="flex items-start justify-between border-b border-[var(--color-border)] pb-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg bg-emerald-100 dark:bg-emerald-950/60 border border-emerald-300 dark:border-emerald-700 flex items-center justify-center text-emerald-800 dark:text-emerald-300">
                    <Building2 size={18} />
                  </div>
                  <h3 className="text-base font-bold text-[var(--color-text-primary)]">{selectedOrgForAnalytics.name}</h3>
                </div>
                <p className="text-xs text-[var(--color-text-secondary)]">
                  Tenant Analytics & Methodology Metrics
                </p>
              </div>

              <button
                onClick={() => {
                  setSelectedOrgForAnalytics(null);
                  setOrgAnalyticsData(null);
                }}
                className="p-1 hover:bg-[var(--color-surface-subtle)] rounded-lg text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors text-xs font-bold uppercase cursor-pointer"
              >
                ✕
              </button>
            </div>

            {loadingOrgAnalytics ? (
              <div className="py-20 flex flex-col items-center justify-center space-y-3">
                <Loader2 size={24} className="animate-spin text-[#008A5E]" />
                <p className="text-[var(--color-text-secondary)] text-xs font-medium tracking-tight">
                  Calculating real-time database metrics...
                </p>
              </div>
            ) : orgAnalyticsData ? (
              <div className="space-y-6">
                {(() => {
                  const metrics = orgAnalyticsData?.metrics || {};
                  const sectorMix = metrics.sector_mix || {};
                  const rolesMap = metrics.roles || {};
                  const sectorMixEntries = Object.entries(sectorMix);
                  const sectorTotal = Object.values(sectorMix).reduce((a: any, b: any) => Number(a) + Number(b), 0) as number;

                  return (
                    <>
                      {/* Metrics Grid */}
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div className="bg-[var(--color-surface-subtle)] p-4 rounded-xl border border-[var(--color-border)] space-y-1">
                          <span className="text-[10px] text-[var(--color-text-muted)] uppercase font-bold tracking-wider">Installations</span>
                          <div className="text-xl font-bold text-[var(--color-text-primary)]">
                            {metrics.installations_count ?? 0}
                          </div>
                        </div>

                        <div className="bg-[var(--color-surface-subtle)] p-4 rounded-xl border border-[var(--color-border)] space-y-1">
                          <span className="text-[10px] text-[var(--color-text-muted)] uppercase font-bold tracking-wider">Activities</span>
                          <div className="text-xl font-bold text-[var(--color-text-primary)]">
                            {metrics.activities_count ?? 0}
                          </div>
                        </div>

                        <div className="bg-[var(--color-surface-subtle)] p-4 rounded-xl border border-[var(--color-border)] space-y-1">
                          <span className="text-[10px] text-[var(--color-text-muted)] uppercase font-bold tracking-wider">Avg Trust Score</span>
                          <div className="text-xl font-bold text-emerald-700 dark:text-emerald-400">
                            {metrics.average_trust_score ?? 0}%
                          </div>
                        </div>

                        <div className="bg-[var(--color-surface-subtle)] p-4 rounded-xl border border-[var(--color-border)] space-y-1">
                          <span className="text-[10px] text-[var(--color-text-muted)] uppercase font-bold tracking-wider">Carbon Offset</span>
                          <div className="text-xl font-bold text-[var(--color-text-primary)]">
                            {metrics.total_co2_offset ?? 0} t
                          </div>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
                        {/* Sector Mix */}
                        <div className="bg-[var(--color-surface-subtle)] p-5 rounded-xl border border-[var(--color-border)] space-y-4">
                          <h4 className="font-bold text-xs uppercase tracking-wider text-[var(--color-text-secondary)]">Sector Mix</h4>
                          <div className="space-y-3 text-xs">
                            {sectorMixEntries.length === 0 ? (
                              <p className="text-[var(--color-text-muted)] text-xs py-2">No sector distribution data available.</p>
                            ) : (
                              sectorMixEntries.map(([sector, count]) => {
                                const typedCount = Number(count);
                                const pct = sectorTotal > 0 ? Math.round((typedCount / sectorTotal) * 100) : 0;
                                return (
                                  <div key={sector} className="space-y-1">
                                    <div className="flex justify-between text-[var(--color-text-secondary)]">
                                      <span className="capitalize font-semibold">{sector}</span>
                                      <span className="text-emerald-700 dark:text-emerald-400 font-bold">{typedCount} Users ({pct}%)</span>
                                    </div>
                                    <div className="w-full bg-[var(--color-background)] h-2 rounded-full overflow-hidden border border-[var(--color-border)]">
                                      <div
                                        className="bg-[#008A5E] dark:bg-emerald-500 h-full rounded-full"
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
                        <div className="bg-[var(--color-surface-subtle)] p-5 rounded-xl border border-[var(--color-border)] space-y-4">
                          <h4 className="font-bold text-xs uppercase tracking-wider text-[var(--color-text-secondary)]">Team Structure</h4>
                          <div className="space-y-2 text-xs">
                            <div className="flex justify-between border-b border-[var(--color-border)] pb-2">
                              <span className="text-[var(--color-text-muted)] font-bold">Total Users</span>
                              <span className="text-[var(--color-text-primary)] font-bold">{metrics.users_count ?? 0}</span>
                            </div>

                            <div className="space-y-1.5 pt-1 text-xs">
                              {Object.entries(rolesMap).map(([role, count]) => (
                                <div key={role} className="flex justify-between text-[var(--color-text-secondary)] font-medium">
                                  <span className="uppercase font-semibold">{role === "admin" ? "ORG_ADMIN" : role}</span>
                                  <span className="text-[var(--color-text-primary)] font-bold">{Number(count)}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        </div>
                      </div>

                      <div className="text-xs text-[var(--color-text-muted)] text-center pt-2">
                        Organization Status: <span className="text-[#008A5E] font-bold uppercase">{orgAnalyticsData.status || "ACTIVE"}</span> • Workspace Provisioned: {orgAnalyticsData.created_at ? new Date(orgAnalyticsData.created_at).toLocaleString() : "N/A"}
                      </div>
                    </>
                  );
                })()}
              </div>
            ) : (
              <div className="py-20 text-center text-[var(--color-text-muted)] text-xs">
                Failed to load analytics data.
              </div>
            )}

            <div className="flex pt-2 justify-end">
              <button
                onClick={() => {
                  setSelectedOrgForAnalytics(null);
                  setOrgAnalyticsData(null);
                }}
                className="py-2 px-5 bg-[var(--color-surface)] hover:bg-[var(--color-surface-subtle)] border border-[var(--color-border)] text-[var(--color-text-primary)] rounded-lg text-xs font-bold uppercase transition-all shadow-xs cursor-pointer"
              >
                Close Metrics
              </button>
            </div>
          </div>
        </div>
      )}

      {/* RENDER CHANGE PASSWORD MODAL */}
      {isPasswordModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs">
          <div className="relative w-full max-w-md bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl shadow-2xl overflow-hidden p-8 space-y-6">
            <div className="text-center space-y-2">
              <div className="w-12 h-12 rounded-full bg-emerald-100 dark:bg-emerald-950/60 border border-emerald-300 dark:border-emerald-700 text-emerald-800 dark:text-emerald-300 flex items-center justify-center mx-auto">
                <Settings size={22} />
              </div>
              <h3 className="text-base font-bold text-[var(--color-text-primary)]">Change Credentials</h3>
              <p className="text-xs text-[var(--color-text-secondary)]">
                Update your Super Admin password.
              </p>
            </div>

            <form onSubmit={handleChangePassword} className="space-y-4">
              <div className="space-y-1.5 text-left">
                <label className="text-[10px] uppercase tracking-wider text-[var(--color-text-secondary)] font-bold">Current Password</label>
                <input
                  type="password"
                  required
                  placeholder="••••••••"
                  value={passwordForm.currentPassword}
                  onChange={(e) => setPasswordForm({ ...passwordForm, currentPassword: e.target.value })}
                  className="w-full bg-[var(--color-surface)] border border-[var(--color-border)] focus:border-[#008A5E] rounded-lg px-3 py-2 text-xs text-[var(--color-text-primary)] focus:outline-none transition-colors shadow-xs"
                />
              </div>

              <div className="space-y-1.5 text-left">
                <label className="text-[10px] uppercase tracking-wider text-[var(--color-text-secondary)] font-bold">New Password</label>
                <input
                  type="password"
                  required
                  placeholder="••••••••"
                  value={passwordForm.newPassword}
                  onChange={(e) => setPasswordForm({ ...passwordForm, newPassword: e.target.value })}
                  className="w-full bg-[var(--color-surface)] border border-[var(--color-border)] focus:border-[#008A5E] rounded-lg px-3 py-2 text-xs text-[var(--color-text-primary)] focus:outline-none transition-colors shadow-xs"
                />
              </div>

              <div className="space-y-1.5 text-left">
                <label className="text-[10px] uppercase tracking-wider text-[var(--color-text-secondary)] font-bold">Confirm New Password</label>
                <input
                  type="password"
                  required
                  placeholder="••••••••"
                  value={passwordForm.confirmPassword}
                  onChange={(e) => setPasswordForm({ ...passwordForm, confirmPassword: e.target.value })}
                  className="w-full bg-[var(--color-surface)] border border-[var(--color-border)] focus:border-[#008A5E] rounded-lg px-3 py-2 text-xs text-[var(--color-text-primary)] focus:outline-none transition-colors shadow-xs"
                />
              </div>

              {passwordError && (
                <p className="text-red-600 text-xs font-bold">{passwordError}</p>
              )}

              {passwordSuccess && (
                <p className="text-emerald-700 text-xs font-bold">{passwordSuccess}</p>
              )}

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsPasswordModalOpen(false)}
                  className="flex-1 py-2.5 bg-[var(--color-surface)] hover:bg-[var(--color-surface-subtle)] border border-[var(--color-border)] text-[var(--color-text-primary)] rounded-lg text-xs font-bold uppercase transition-all shadow-xs cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isChangingPassword}
                  className="flex-1 py-2.5 bg-[#008A5E] hover:bg-[#00734E] text-white rounded-lg text-xs font-bold uppercase transition-all disabled:opacity-50 shadow-xs cursor-pointer"
                >
                  {isChangingPassword ? "Updating..." : "Save Password"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 5-STEP ENTERPRISE ACCOUNT CREATION WIZARD MODAL */}
      {isCreateUserModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs">
          <div className="relative w-full max-w-2xl bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl shadow-2xl overflow-hidden p-6 sm:p-8 space-y-6 animate-fade-in-up max-h-[90vh] overflow-y-auto scrollbar">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-emerald-100 dark:bg-emerald-950/60 border border-emerald-300 dark:border-emerald-700 flex items-center justify-center text-emerald-800 dark:text-emerald-300">
                  <UserIcon size={20} />
                </div>
                <div>
                  <h3 className="text-base font-bold text-[var(--color-text-primary)]">Enterprise User Provisioning</h3>
                  <p className="text-xs text-[var(--color-text-secondary)]">Step {createStep} of 5 — {
                    createStep === 1 ? "Identity Details" :
                    createStep === 2 ? "Role & Scope Privilege" :
                    createStep === 3 ? "Tenant Organization Binding" :
                    createStep === 4 ? "Optional Project Access Roster" :
                    "Review & Provision Account"
                  }</p>
                </div>
              </div>

              <button
                onClick={() => setIsCreateUserModalOpen(false)}
                className="p-1 hover:bg-[var(--color-surface-subtle)] rounded-lg text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors text-xs font-bold uppercase cursor-pointer"
              >
                ✕
              </button>
            </div>

            {/* Stepper Progress Bar */}
            {!provisionResult && (
              <div className="flex items-center justify-between gap-1.5 font-mono text-[10px] uppercase font-bold text-[var(--color-text-muted)]">
                {[1, 2, 3, 4, 5].map((s) => (
                  <div
                    key={s}
                    onClick={() => {
                      if (s < createStep) setCreateStep(s as any);
                    }}
                    className={`flex-1 py-1.5 rounded-md text-center transition-all cursor-pointer border ${
                      createStep === s ? "bg-[#008A5E] text-white border-[#008A5E] font-bold shadow-xs" :
                      createStep > s ? "bg-emerald-50 dark:bg-emerald-950/50 border-emerald-300 dark:border-emerald-700 text-emerald-800 dark:text-emerald-300" :
                      "bg-[var(--color-surface-subtle)] border-[var(--color-border)] text-[var(--color-text-muted)]"
                    }`}
                  >
                    {s}. {s === 1 ? "Identity" : s === 2 ? "Role" : s === 3 ? "Org" : s === 4 ? "Projects" : "Review"}
                  </div>
                ))}
              </div>
            )}

            {/* ERROR ALERT */}
            {provisionError && (
              <div className="p-3 bg-red-50 dark:bg-red-950/40 border border-red-300 dark:border-red-700 rounded-xl text-red-700 dark:text-red-300 text-xs font-bold">
                {provisionError}
              </div>
            )}

            {/* PROVISION SUCCESS CONFIRMATION VIEW */}
            {provisionResult ? (
              <div className="space-y-6 animate-fade-in">
                <div className="p-5 rounded-2xl bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-300 dark:border-emerald-700 text-center space-y-3">
                  <div className="w-12 h-12 rounded-full bg-emerald-100 dark:bg-emerald-900/50 border border-emerald-300 dark:border-emerald-700 text-emerald-800 dark:text-emerald-300 flex items-center justify-center mx-auto">
                    <CheckCircle2 size={26} />
                  </div>
                  <h4 className="text-base font-bold text-[var(--color-text-primary)]">Account Provisioned Successfully!</h4>
                  <p className="text-xs text-[var(--color-text-secondary)]">
                    Account <strong>{provisionResult.user?.email}</strong> is active with forced first-login password change (<code className="text-emerald-700 dark:text-emerald-400 font-mono font-bold">requires_password_change = true</code>).
                  </p>
                </div>

                <div className="bg-[var(--color-surface-subtle)] p-4 rounded-xl border border-[var(--color-border)] space-y-3 font-mono text-xs">
                  <div className="flex justify-between items-center text-[var(--color-text-secondary)] border-b border-[var(--color-border)] pb-2">
                    <span className="text-[10px] uppercase font-bold text-[var(--color-text-muted)]">Account Email</span>
                    <span className="text-[var(--color-text-primary)] font-bold">{provisionResult.user?.email}</span>
                  </div>

                  <div className="flex justify-between items-center text-[var(--color-text-secondary)] border-b border-[var(--color-border)] pb-2">
                    <span className="text-[10px] uppercase font-bold text-[var(--color-text-muted)]">Global Role</span>
                    <span className="text-emerald-800 dark:text-emerald-300 font-bold">{provisionResult.user?.role}</span>
                  </div>

                  <div className="flex justify-between items-center text-[var(--color-text-secondary)] border-b border-[var(--color-border)] pb-2">
                    <span className="text-[10px] uppercase font-bold text-[var(--color-text-muted)]">Organization</span>
                    <span className="text-[var(--color-text-primary)] font-bold">{provisionResult.user?.organization || "System Platform"}</span>
                  </div>

                  <div className="flex justify-between items-center text-[var(--color-text-secondary)] border-b border-[var(--color-border)] pb-2">
                    <span className="text-[10px] uppercase font-bold text-[var(--color-text-muted)]">Project Memberships</span>
                    <span className="text-emerald-800 dark:text-emerald-300 font-bold">{provisionResult.assigned_memberships_count} Project(s)</span>
                  </div>

                  <div className="pt-2 space-y-1.5">
                    <label className="text-[10px] uppercase font-bold text-[var(--color-text-secondary)] block">One-Time Temporary Credential</label>
                    <div className="flex gap-2 items-center">
                      <input
                        type="text"
                        readOnly
                        value={provisionResult.temporary_password || ""}
                        className="flex-1 bg-[var(--color-surface)] border border-emerald-300 dark:border-emerald-700 rounded-lg px-3 py-2 text-xs font-mono text-emerald-800 dark:text-emerald-300 font-bold select-all shadow-xs"
                      />
                      <button
                        type="button"
                        onClick={() => {
                          if (provisionResult.temporary_password) {
                            navigator.clipboard.writeText(provisionResult.temporary_password);
                            toast.success("Copied", "Temporary password copied to clipboard.");
                          }
                        }}
                        className="px-3.5 py-2 bg-[var(--color-surface)] hover:bg-[var(--color-surface-subtle)] border border-[var(--color-border)] text-[var(--color-text-primary)] rounded-lg text-xs font-bold flex items-center gap-1.5 cursor-pointer shadow-xs"
                      >
                        <Copy size={14} />
                        <span>Copy</span>
                      </button>
                    </div>
                    <p className="text-xs text-[var(--color-text-muted)]">
                      Send this temporary password securely to the user. Plaintext credentials are not stored in logs or database.
                    </p>
                  </div>
                </div>

                <div className="flex gap-3 pt-2">
                  <button
                    onClick={() => {
                      setSelectedUserForDetails(provisionResult.user);
                      setIsCreateUserModalOpen(false);
                    }}
                    className="flex-1 py-2.5 bg-[var(--color-surface)] hover:bg-[var(--color-surface-subtle)] border border-[var(--color-border)] text-[var(--color-text-primary)] rounded-lg text-xs font-bold uppercase transition-all shadow-xs cursor-pointer"
                  >
                    View Account 360
                  </button>
                  <button
                    onClick={() => setIsCreateUserModalOpen(false)}
                    className="flex-1 py-2.5 bg-[#008A5E] hover:bg-[#00734E] text-white rounded-lg text-xs font-bold uppercase transition-all shadow-xs cursor-pointer"
                  >
                    Done
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-5">
                {/* STEP 1: IDENTITY */}
                {createStep === 1 && (
                  <div className="space-y-4 animate-fade-in">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-secondary)] border-b border-[var(--color-border)] pb-2">
                      Step 1: User Identity Information
                    </h4>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div className="space-y-1 text-left">
                        <label className="text-[10px] uppercase tracking-wider text-[var(--color-text-secondary)] font-bold">Full Name *</label>
                        <input
                          type="text"
                          required
                          placeholder="e.g. Dr. Jane Doe"
                          value={createForm.fullName}
                          onChange={(e) => setCreateForm({ ...createForm, fullName: e.target.value })}
                          className="w-full bg-[var(--color-surface)] border border-[var(--color-border)] focus:border-[#008A5E] rounded-lg px-3 py-2 text-xs text-[var(--color-text-primary)] focus:outline-none transition-colors shadow-xs"
                        />
                      </div>
                      <div className="space-y-1 text-left">
                        <label className="text-[10px] uppercase tracking-wider text-[var(--color-text-secondary)] font-bold">Email Address *</label>
                        <input
                          type="email"
                          required
                          placeholder="e.g. jane.doe@verifier.org"
                          value={createForm.email}
                          onChange={(e) => setCreateForm({ ...createForm, email: e.target.value })}
                          className="w-full bg-[var(--color-surface)] border border-[var(--color-border)] focus:border-[#008A5E] rounded-lg px-3 py-2 text-xs text-[var(--color-text-primary)] focus:outline-none transition-colors shadow-xs"
                        />
                      </div>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div className="space-y-1 text-left">
                        <label className="text-[10px] uppercase tracking-wider text-[var(--color-text-secondary)] font-bold">Phone Number</label>
                        <input
                          type="text"
                          placeholder="e.g. +1 555 019 2831"
                          value={createForm.phone}
                          onChange={(e) => setCreateForm({ ...createForm, phone: e.target.value })}
                          className="w-full bg-[var(--color-surface)] border border-[var(--color-border)] focus:border-[#008A5E] rounded-lg px-3 py-2 text-xs text-[var(--color-text-primary)] focus:outline-none transition-colors shadow-xs"
                        />
                      </div>
                      <div className="space-y-1 text-left">
                        <label className="text-[10px] uppercase tracking-wider text-[var(--color-text-secondary)] font-bold">Job Title / Position</label>
                        <input
                          type="text"
                          placeholder="e.g. Senior Climate Auditor"
                          value={createForm.jobTitle}
                          onChange={(e) => setCreateForm({ ...createForm, jobTitle: e.target.value })}
                          className="w-full bg-[var(--color-surface)] border border-[var(--color-border)] focus:border-[#008A5E] rounded-lg px-3 py-2 text-xs text-[var(--color-text-primary)] focus:outline-none transition-colors shadow-xs"
                        />
                      </div>
                    </div>

                    <div className="space-y-1 text-left">
                      <label className="text-[10px] uppercase tracking-wider text-[var(--color-text-secondary)] font-bold">Custom Initial Password (Optional)</label>
                      <input
                        type="password"
                        placeholder="Leave blank for secure auto-generated temporary password"
                        value={createForm.password}
                        onChange={(e) => setCreateForm({ ...createForm, password: e.target.value })}
                        className="w-full bg-[var(--color-surface)] border border-[var(--color-border)] focus:border-[#008A5E] rounded-lg px-3 py-2 text-xs text-[var(--color-text-primary)] focus:outline-none transition-colors shadow-xs"
                      />
                    </div>
                  </div>
                )}

                {/* STEP 2: ROLE & SCOPE */}
                {createStep === 2 && (
                  <div className="space-y-4 animate-fade-in">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-secondary)] border-b border-[var(--color-border)] pb-2">
                      Step 2: Account Role & Privilege Scope
                    </h4>
                    <p className="text-xs text-[var(--color-text-secondary)]">
                      Select the global/organization privilege level for this account. Dynamically loaded from backend metadata:
                    </p>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 max-h-[300px] overflow-y-auto scrollbar">
                      {[
                        { code: "SUPER_ADMIN", name: "Super Admin", scope: "PLATFORM", desc: "Platform-wide owner with full administrative authority across all tenants" },
                        { code: "ORG_ADMIN", name: "Organization Admin", scope: "ORGANIZATION", desc: "Tenant organization manager with workspace administration authority" },
                        { code: "AUDITOR", name: "Auditor", scope: "PROJECT / ORG", desc: "Independent VVBA Auditor with read and validation audit access" },
                        { code: "THIRD_PARTY_AUDITOR", name: "3rd-Party Auditor", scope: "PROJECT / ORG", desc: "External independent verification auditor" },
                        { code: "COMPLIANCE_OFFICER", name: "Compliance Officer", scope: "PROJECT / ORG", desc: "Carbon standard compliance and registry alignment manager" },
                        { code: "PROJECT_MANAGER", name: "Project Manager", scope: "PROJECT / ORG", desc: "Operational lead for climate project execution" },
                        { code: "FIELD_AGENT", name: "Field Agent", scope: "PROJECT", desc: "Field MRV data collector submitting evidence and IoT telemetry" },
                        { code: "REGULATOR", name: "Regulator", scope: "PLATFORM / ORG", desc: "Government / Designated National Authority oversight observer" },
                      ].map((r) => {
                        const isSelected = createForm.role === r.code;
                        return (
                          <div
                            key={r.code}
                            onClick={() => setCreateForm({ ...createForm, role: r.code })}
                            className={`p-3.5 rounded-xl border text-left cursor-pointer transition-all space-y-1.5 shadow-xs ${
                              isSelected
                                ? "bg-emerald-50 dark:bg-emerald-950/60 border-emerald-500 ring-1 ring-emerald-500"
                                : "bg-[var(--color-surface)] border-[var(--color-border)] hover:border-[var(--color-border-hover)]"
                            }`}
                          >
                            <div className="flex items-center justify-between">
                              <span className={`text-xs font-bold uppercase ${isSelected ? "text-emerald-800 dark:text-emerald-300" : "text-[var(--color-text-primary)]"}`}>
                                {r.name}
                              </span>
                              <span className={`text-[9px] font-mono font-bold px-2 py-0.5 rounded-md uppercase ${
                                r.scope === "PLATFORM" ? "bg-purple-100 dark:bg-purple-950/60 text-purple-800 dark:text-purple-200 border border-purple-300 dark:border-purple-700" :
                                r.scope === "ORGANIZATION" ? "bg-blue-100 dark:bg-blue-950/60 text-blue-800 dark:text-blue-200 border border-blue-300 dark:border-blue-700" :
                                "bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-200 border border-emerald-300 dark:border-emerald-700"
                              }`}>
                                {r.scope}
                              </span>
                            </div>
                            <p className="text-xs text-[var(--color-text-secondary)] leading-tight">{r.desc}</p>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* STEP 3: ORGANIZATION SELECTION */}
                {createStep === 3 && (
                  <div className="space-y-4 animate-fade-in">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-secondary)] border-b border-[var(--color-border)] pb-2">
                      Step 3: Tenant Organization Binding
                    </h4>
                    <p className="text-xs text-[var(--color-text-secondary)]">
                      Bind this account to an approved SaaS Tenant Organization (Required for non-Super Admin roles):
                    </p>

                    {createForm.role === "SUPER_ADMIN" && (
                      <div className="p-3 bg-purple-50 dark:bg-purple-950/30 border border-purple-300 dark:border-purple-700 rounded-xl text-purple-800 dark:text-purple-200 text-xs font-bold">
                        <strong>Platform Scope Notice:</strong> SUPER_ADMIN operates platform-wide. Organization assignment is optional.
                      </div>
                    )}

                    {createForm.role !== "SUPER_ADMIN" && (
                      <div className="flex items-center gap-2 p-1 bg-[var(--color-surface-subtle)] border border-[var(--color-border)] rounded-xl mb-3">
                        <button
                          type="button"
                          onClick={() => setCreateForm(prev => ({ ...prev, orgMode: "existing" }))}
                          className={`flex-1 py-1.5 px-3 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                            createForm.orgMode === "existing"
                              ? "bg-[#008A5E] text-white shadow-xs"
                              : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
                          }`}
                        >
                          Select Existing Organization
                        </button>
                        <button
                          type="button"
                          onClick={() => setCreateForm(prev => ({ ...prev, orgMode: "new" }))}
                          className={`flex-1 py-1.5 px-3 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                            createForm.orgMode === "new"
                              ? "bg-[#008A5E] text-white shadow-xs"
                              : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
                          }`}
                        >
                          + Create New Organization
                        </button>
                      </div>
                    )}

                    {createForm.orgMode === "new" && createForm.role !== "SUPER_ADMIN" ? (
                      <div className="space-y-2">
                        <label className="text-[10px] uppercase tracking-wider text-[var(--color-text-secondary)] font-bold block">
                          New SaaS Tenant Organization Name *
                        </label>
                        <input
                          type="text"
                          value={createForm.newOrgName || ""}
                          onChange={(e) => setCreateForm(prev => ({ ...prev, newOrgName: e.target.value }))}
                          placeholder="e.g. Acme Climate Tech Ltd, Solaria West Africa"
                          className="w-full bg-[var(--color-surface)] border border-[var(--color-border)] focus:border-[#008A5E] rounded-lg px-3 py-2 text-xs text-[var(--color-text-primary)] focus:outline-none transition-colors shadow-xs"
                        />
                        <p className="text-xs text-[#008A5E] font-bold">
                          A new SaaS Tenant Organization will be automatically created and bound to this {createForm.role} account upon submission.
                        </p>
                      </div>
                    ) : (
                      <div className="space-y-2">
                        <label className="text-[10px] uppercase tracking-wider text-[var(--color-text-secondary)] font-bold block">
                          Select SaaS Tenant Organization {createForm.role !== "SUPER_ADMIN" && "*"}
                        </label>
                        <select
                          value={createForm.organizationId}
                          onChange={(e) => handleOrgChangeInWizard(e.target.value)}
                          className="w-full bg-[var(--color-surface)] border border-[var(--color-border)] focus:border-[#008A5E] rounded-lg px-3 py-2 text-xs text-[var(--color-text-primary)] focus:outline-none transition-colors shadow-xs"
                        >
                          {createForm.role === "SUPER_ADMIN" || createForm.role === "REGULATOR" ? (
                            <option value="">-- System Platform Scope (No Organization) --</option>
                          ) : (
                            <option value="">-- Choose an Organization --</option>
                          )}
                          {orgs
                            .filter((o) => !o.name.startsWith("Test ") && !o.name.startsWith("Hardening ") && !o.name.startsWith("Attack "))
                            .map((o) => (
                              <option key={o.id} value={o.id}>
                                {o.name} ({o.status || "ACTIVE"})
                              </option>
                            ))}
                        </select>
                      </div>
                    )}

                    {createForm.orgMode === "existing" && createForm.organizationId && (
                      <div className="p-3 rounded-xl bg-[var(--color-surface-subtle)] border border-[var(--color-border)] space-y-1 text-xs">
                        <span className="text-[10px] text-[var(--color-text-muted)] font-bold uppercase block">Selected Tenant</span>
                        <p className="text-[var(--color-text-primary)] font-bold">
                          {orgs.find(o => o.id === createForm.organizationId)?.name}
                        </p>
                      </div>
                    )}
                  </div>
                )}

                {/* STEP 4: OPTIONAL PROJECT ACCESS */}
                {createStep === 4 && (
                  <div className="space-y-4 animate-fade-in">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-secondary)] border-b border-[var(--color-border)] pb-2">
                      Step 4: Optional Project Access Roster
                    </h4>
                    <p className="text-xs text-[var(--color-text-secondary)]">
                      Optionally assign this user to specific climate projects within the selected organization.
                    </p>

                    {!createForm.organizationId ? (
                      <div className="p-4 bg-[var(--color-surface-subtle)] border border-[var(--color-border)] rounded-xl text-center text-[var(--color-text-muted)] text-xs">
                        No organization selected. Skip or return to Step 3 to select an organization.
                      </div>
                    ) : loadingOrgProjects ? (
                      <div className="py-8 flex flex-col items-center justify-center space-y-2">
                        <Loader2 size={20} className="animate-spin text-[#008A5E]" />
                        <p className="text-[var(--color-text-muted)] text-xs">Loading organization projects...</p>
                      </div>
                    ) : orgProjects.length === 0 ? (
                      <div className="p-4 bg-[var(--color-surface-subtle)] border border-[var(--color-border)] rounded-xl text-center text-[var(--color-text-muted)] text-xs">
                        No projects exist under this organization tenant yet. Click Next to proceed.
                      </div>
                    ) : (
                      <div className="space-y-2.5 max-h-[260px] overflow-y-auto scrollbar">
                        {orgProjects.map((p) => {
                          const assigned = createProjectMemberships.find(pm => pm.project_id === p.id);
                          return (
                            <div
                              key={p.id}
                              className={`p-3 rounded-xl border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-left transition-all shadow-xs ${
                                assigned ? "bg-emerald-50 dark:bg-emerald-950/30 border-emerald-300 dark:border-emerald-700" : "bg-[var(--color-surface)] border-[var(--color-border)]"
                              }`}
                            >
                              <div className="flex items-center gap-3">
                                <input
                                  type="checkbox"
                                  checked={!!assigned}
                                  onChange={() => handleToggleProjectMembership(p.id, createForm.role)}
                                  className="w-4 h-4 accent-[#008A5E] cursor-pointer"
                                />
                                <div>
                                  <span className="text-xs font-bold text-[var(--color-text-primary)] block">{p.name}</span>
                                  <span className="text-[10px] font-mono text-[var(--color-text-muted)]">Code: {p.project_code} • Status: {p.status}</span>
                                </div>
                              </div>

                              {assigned && (
                                <div className="flex items-center gap-2 text-xs">
                                  <span className="text-[10px] font-bold text-[var(--color-text-secondary)] uppercase">Project Role:</span>
                                  <select
                                    value={assigned.role}
                                    onChange={(e) => handleUpdateProjectMembershipRole(p.id, e.target.value)}
                                    className="bg-[var(--color-surface)] border border-[var(--color-border)] focus:border-[#008A5E] rounded-md px-2.5 py-1 text-xs font-mono text-emerald-800 dark:text-emerald-300 font-bold focus:outline-none"
                                  >
                                    <option value="FIELD_AGENT">FIELD_AGENT</option>
                                    <option value="AUDITOR">AUDITOR</option>
                                    <option value="THIRD_PARTY_AUDITOR">THIRD_PARTY_AUDITOR</option>
                                    <option value="COMPLIANCE_OFFICER">COMPLIANCE_OFFICER</option>
                                    <option value="PROJECT_MANAGER">PROJECT_MANAGER</option>
                                  </select>
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                )}

                {/* STEP 5: REVIEW & PROVISION */}
                {createStep === 5 && (
                  <div className="space-y-4 animate-fade-in">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-secondary)] border-b border-[var(--color-border)] pb-2">
                      Step 5: Review & Provision Account
                    </h4>

                    <div className="bg-[var(--color-surface-subtle)] p-4 rounded-xl border border-[var(--color-border)] space-y-3 text-xs font-mono">
                      <div className="flex justify-between items-center border-b border-[var(--color-border)] pb-2">
                        <span className="text-[10px] text-[var(--color-text-muted)] uppercase font-bold">Full Name</span>
                        <span className="text-[var(--color-text-primary)] font-bold">{createForm.fullName || "N/A"}</span>
                      </div>

                      <div className="flex justify-between items-center border-b border-[var(--color-border)] pb-2">
                        <span className="text-[10px] text-[var(--color-text-muted)] uppercase font-bold">Email Address</span>
                        <span className="text-[var(--color-text-primary)] font-bold">{createForm.email || "N/A"}</span>
                      </div>

                      <div className="flex justify-between items-center border-b border-[var(--color-border)] pb-2">
                        <span className="text-[10px] text-[var(--color-text-muted)] uppercase font-bold">Global Privilege Role</span>
                        <span className="text-emerald-800 dark:text-emerald-300 font-bold">{createForm.role}</span>
                      </div>

                      <div className="flex justify-between items-center border-b border-[var(--color-border)] pb-2">
                        <span className="text-[10px] text-[var(--color-text-muted)] uppercase font-bold">Organization Tenant</span>
                        <span className="text-[var(--color-text-primary)] font-bold">
                          {orgs.find(o => o.id === createForm.organizationId)?.name || (createForm.role === "SUPER_ADMIN" ? "Platform-Wide" : "N/A")}
                        </span>
                      </div>

                      <div className="space-y-1 border-b border-[var(--color-border)] pb-2">
                        <span className="text-[10px] text-[var(--color-text-muted)] uppercase font-bold block">Assigned Project Memberships</span>
                        {createProjectMemberships.length === 0 ? (
                          <span className="text-[var(--color-text-muted)] text-[11px]">None selected</span>
                        ) : (
                          <div className="space-y-1 pt-1">
                            {createProjectMemberships.map((pm) => {
                              const proj = orgProjects.find(p => p.id === pm.project_id);
                              return (
                                <div key={pm.project_id} className="flex justify-between text-[11px]">
                                  <span className="text-[var(--color-text-secondary)]">{proj?.name || pm.project_id}</span>
                                  <span className="text-emerald-800 dark:text-emerald-300 font-bold">{pm.role}</span>
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </div>

                      <div className="flex justify-between items-center pt-1">
                        <span className="text-[10px] text-[var(--color-text-muted)] uppercase font-bold">Security Policy</span>
                        <span className="text-purple-700 dark:text-purple-300 font-bold text-xs">Temporary Credentials (Forced Change)</span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Wizard Action Buttons */}
                <div className="flex items-center justify-between pt-2 border-t border-[var(--color-border)]">
                  <button
                    type="button"
                    disabled={createStep === 1 || isProvisioning}
                    onClick={() => setCreateStep((s) => Math.max(1, s - 1) as any)}
                    className="px-4 py-2 bg-[var(--color-surface)] hover:bg-[var(--color-surface-subtle)] border border-[var(--color-border)] text-[var(--color-text-primary)] text-xs font-bold rounded-lg disabled:opacity-30 cursor-pointer shadow-xs"
                  >
                    Back
                  </button>

                  {createStep < 5 ? (
                    <button
                      type="button"
                      onClick={() => {
                        if (createStep === 1) {
                          if (!createForm.fullName.trim() || !createForm.email.includes("@")) {
                            setProvisionError("Please provide a valid Full Name and Email Address.");
                            return;
                          }
                        }

                        if (createStep === 3) {
                          if (createForm.role !== "SUPER_ADMIN" && createForm.role !== "REGULATOR") {
                            if (createForm.orgMode === "new") {
                              if (!createForm.newOrgName || !createForm.newOrgName.trim()) {
                                setProvisionError("Please enter a name for the new Organization.");
                                return;
                              }
                            } else if (!createForm.organizationId) {
                              const valid = (orgs || []).filter((item: any) => !item.name.startsWith("Test ") && !item.name.startsWith("Hardening ") && !item.name.startsWith("Attack "));
                              if (valid.length > 0) {
                                handleOrgChangeInWizard(valid[0].id);
                              } else {
                                setProvisionError("Please select an organization or click '+ Create New Organization'.");
                                return;
                              }
                            }
                          }
                        }

                        setProvisionError("");
                        setCreateStep((s) => Math.min(5, s + 1) as any);
                      }}
                      className="px-4 py-2 bg-[#008A5E] hover:bg-[#00734E] text-white text-xs font-bold rounded-lg flex items-center gap-1.5 cursor-pointer shadow-xs"
                    >
                      <span>Next</span>
                    </button>
                  ) : (
                    <button
                      type="button"
                      disabled={isProvisioning}
                      onClick={handleProvisionAccountSubmit}
                      className="px-5 py-2 bg-[#008A5E] hover:bg-[#00734E] text-white text-xs font-bold rounded-lg flex items-center gap-2 transition-all shadow-xs disabled:opacity-50 cursor-pointer"
                    >
                      {isProvisioning ? <Loader2 size={15} className="animate-spin" /> : <UserIcon size={15} />}
                      <span>{isProvisioning ? "Provisioning..." : "Provision Account"}</span>
                    </button>
                  )}
                </div>
              </div>
            )}
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

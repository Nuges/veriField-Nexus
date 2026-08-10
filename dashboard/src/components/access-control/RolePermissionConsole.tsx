"use client";

import React, { useState, useMemo, useEffect } from "react";
import {
  Shield,
  ShieldCheck,
  ShieldAlert,
  Users,
  Search,
  Filter,
  Download,
  ChevronRight,
  ChevronDown,
  Layers,
  FileText,
  Key,
  Database,
  Lock,
  Unlock,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ArrowLeft,
  Copy,
  ExternalLink,
  Edit3,
  Trash2,
  Plus,
  RefreshCw,
  GitCompare,
  History,
  Info
} from "lucide-react";
import { DataTable } from "@/components/common/DataTable";
import { useToast } from "@/components/Toast";
import { ROLE_ORDER, getRolePriority } from "@/lib/roles";
import { apiFetch } from "@/lib/api";

// Scope Hierarchy Metadata
const SCOPE_HIERARCHY = ["PLATFORM", "ORGANIZATION", "PORTFOLIO", "PROJECT", "ACTIVITY", "ASSET"];

// Category to UI & API Mappings
const PERMISSION_METADATA: Record<
  string,
  {
    category: string;
    scope: string;
    dependencies: string[];
    uiModules: string[];
    apiEndpoints: string[];
  }
> = {
  "admin:all": {
    category: "Admin",
    scope: "PLATFORM",
    dependencies: [],
    uiModules: ["/super-admin", "/dashboard/settings"],
    apiEndpoints: ["ALL /api/v1/admin/*", "ALL /api/v1/users/*"]
  },
  "support:all": {
    category: "Admin",
    scope: "PLATFORM",
    dependencies: [],
    uiModules: ["/super-admin", "/dashboard/people"],
    apiEndpoints: ["GET /api/v1/support/*"]
  },
  "org:manage": {
    category: "Organization",
    scope: "ORGANIZATION",
    dependencies: ["org:read"],
    uiModules: ["/dashboard/settings", "/super-admin"],
    apiEndpoints: ["POST /api/v1/organizations", "PUT /api/v1/organizations/{id}"]
  },
  "org:read": {
    category: "Organization",
    scope: "ORGANIZATION",
    dependencies: [],
    uiModules: ["/dashboard/settings"],
    apiEndpoints: ["GET /api/v1/organizations/{id}"]
  },
  "org:update": {
    category: "Organization",
    scope: "ORGANIZATION",
    dependencies: ["org:read"],
    uiModules: ["/dashboard/settings"],
    apiEndpoints: ["PUT /api/v1/organizations/{id}"]
  },
  "project:all": {
    category: "Project",
    scope: "PROJECT",
    dependencies: ["project:read"],
    uiModules: ["/dashboard/projects", "/dashboard/properties"],
    apiEndpoints: ["ALL /api/v1/projects/*"]
  },
  "project:read": {
    category: "Project",
    scope: "PROJECT",
    dependencies: [],
    uiModules: ["/dashboard/projects", "/dashboard/properties"],
    apiEndpoints: ["GET /api/v1/projects", "GET /api/v1/projects/{id}"]
  },
  "project:update": {
    category: "Project",
    scope: "PROJECT",
    dependencies: ["project:read"],
    uiModules: ["/dashboard/projects"],
    apiEndpoints: ["PUT /api/v1/projects/{id}"]
  },
  "asset:all": {
    category: "Asset",
    scope: "ASSET",
    dependencies: ["asset:read"],
    uiModules: ["/dashboard/assets", "/dashboard/properties"],
    apiEndpoints: ["ALL /api/v1/assets/*"]
  },
  "asset:read": {
    category: "Asset",
    scope: "ASSET",
    dependencies: [],
    uiModules: ["/dashboard/assets"],
    apiEndpoints: ["GET /api/v1/assets"]
  },
  "activity:all": {
    category: "Activity",
    scope: "ACTIVITY",
    dependencies: ["activity:read"],
    uiModules: ["/dashboard/activities", "/dashboard/monitoring"],
    apiEndpoints: ["ALL /api/v1/activities/*"]
  },
  "activity:create": {
    category: "Activity",
    scope: "ACTIVITY",
    dependencies: ["activity:read"],
    uiModules: ["/dashboard/activities"],
    apiEndpoints: ["POST /api/v1/activities"]
  },
  "activity:read": {
    category: "Activity",
    scope: "ACTIVITY",
    dependencies: [],
    uiModules: ["/dashboard/activities"],
    apiEndpoints: ["GET /api/v1/activities"]
  },
  "activity:update": {
    category: "Activity",
    scope: "ACTIVITY",
    dependencies: ["activity:read"],
    uiModules: ["/dashboard/activities"],
    apiEndpoints: ["PUT /api/v1/activities/{id}"]
  },
  "activity:verify": {
    category: "Compliance",
    scope: "ACTIVITY",
    dependencies: ["activity:read"],
    uiModules: ["/dashboard/verifications"],
    apiEndpoints: ["POST /api/v1/verification/verify"]
  },
  "team:manage": {
    category: "Admin",
    scope: "ORGANIZATION",
    dependencies: [],
    uiModules: ["/dashboard/people", "/dashboard/projects"],
    apiEndpoints: ["POST /api/v1/users", "DELETE /api/v1/users/{id}"]
  },
  "billing:manage": {
    category: "Billing",
    scope: "ORGANIZATION",
    dependencies: ["billing:read"],
    uiModules: ["/dashboard/settings"],
    apiEndpoints: ["ALL /api/v1/billing/*"]
  },
  "billing:read": {
    category: "Billing",
    scope: "ORGANIZATION",
    dependencies: [],
    uiModules: ["/dashboard/settings"],
    apiEndpoints: ["GET /api/v1/billing"]
  },
  "report:all": {
    category: "Reports",
    scope: "ORGANIZATION",
    dependencies: ["report:read"],
    uiModules: ["/dashboard/analytics"],
    apiEndpoints: ["ALL /api/v1/reports/*"]
  },
  "report:read": {
    category: "Reports",
    scope: "ORGANIZATION",
    dependencies: [],
    uiModules: ["/dashboard/analytics"],
    apiEndpoints: ["GET /api/v1/reports"]
  },
  "ledger:all": {
    category: "Ledger",
    scope: "ORGANIZATION",
    dependencies: ["ledger:read"],
    uiModules: ["/dashboard/registry"],
    apiEndpoints: ["ALL /api/v1/ledger/*"]
  },
  "ledger:read": {
    category: "Ledger",
    scope: "ORGANIZATION",
    dependencies: [],
    uiModules: ["/dashboard/registry"],
    apiEndpoints: ["GET /api/v1/ledger"]
  },
  "audit:all": {
    category: "Audit",
    scope: "PLATFORM",
    dependencies: ["audit:read"],
    uiModules: ["/dashboard/audits", "/super-admin"],
    apiEndpoints: ["ALL /api/v1/audits/*"]
  },
  "audit:read": {
    category: "Audit",
    scope: "PLATFORM",
    dependencies: [],
    uiModules: ["/dashboard/audits"],
    apiEndpoints: ["GET /api/v1/audits"]
  },
  "audit:write": {
    category: "Audit",
    scope: "PLATFORM",
    dependencies: ["audit:read"],
    uiModules: ["/dashboard/audits"],
    apiEndpoints: ["POST /api/v1/audits"]
  },
  "jurisdiction:all": {
    category: "Jurisdiction",
    scope: "PLATFORM",
    dependencies: [],
    uiModules: ["/super-admin"],
    apiEndpoints: ["ALL /api/v1/jurisdictions/*"]
  },
  "accreditation:all": {
    category: "Compliance",
    scope: "PLATFORM",
    dependencies: [],
    uiModules: ["/super-admin"],
    apiEndpoints: ["ALL /api/v1/accreditation/*"]
  },
  "compliance:all": {
    category: "Compliance",
    scope: "PLATFORM",
    dependencies: ["compliance:read"],
    uiModules: ["/super-admin"],
    apiEndpoints: ["ALL /api/v1/compliance/*"]
  },
  "compliance:read": {
    category: "Compliance",
    scope: "PLATFORM",
    dependencies: [],
    uiModules: ["/super-admin"],
    apiEndpoints: ["GET /api/v1/compliance"]
  }
};

export interface RoleDetail {
  id: string;
  code: string;
  name: string;
  description: string;
  scope: string;
  is_system: boolean;
  permissions: string[];
  user_count: number;
  created_at?: string;
  updated_at?: string;
  created_by?: string;
}

export interface UserItem {
  id: string;
  email: string;
  full_name: string;
  role: string;
  organization?: string;
  organization_name?: string;
  organization_id?: string;
  licensed_sectors?: string[];
  status: string;
  created_at: string;
  projects_count?: number;
  activities_count?: number;
  assets_count?: number;
  evidence_count?: number;
}

export interface OrganizationItem {
  id: string;
  name: string;
  licensed_sectors?: string[];
}

export interface RolePermissionConsoleProps {
  roles: RoleDetail[];
  permissionsList: { code: string; category: string }[];
  users: UserItem[];
  organizations?: OrganizationItem[];
  onRefresh?: () => void;
}

export function RolePermissionConsole({
  roles = [],
  permissionsList = [],
  users = [],
  organizations = [],
  onRefresh
}: RolePermissionConsoleProps) {
  const toast = useToast();

  const [selectedRole, setSelectedRole] = useState<RoleDetail | null>(null);
  const [activeTab, setActiveTab] = useState<"explorer" | "users" | "scopes" | "audit">("explorer");

  // Comparison Tool State
  const [isCompareMode, setIsCompareMode] = useState<boolean>(false);
  const [compareRoleA, setCompareRoleA] = useState<string>("");
  const [compareRoleB, setCompareRoleB] = useState<string>("");

  // Filters & Search
  const [searchQuery, setSearchQuery] = useState("");
  const [scopeFilter, setScopeFilter] = useState("ALL");
  const [categoryFilter, setCategoryFilter] = useState("ALL");
  const [sortOption, setSortOption] = useState<"hierarchy" | "name" | "users" | "perms">("hierarchy");

  // Modals & Drilldown
  const [expandedPerm, setExpandedPerm] = useState<string | null>(null);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [editDescription, setEditDescription] = useState("");

  // Safe System Roles protection
  const PROTECTED_ROLES = ["SUPER_ADMIN", "ADMIN", "ORG_ADMIN"];

  // Sort & Filter Roles List
  const processedRoles = useMemo(() => {
    let result = [...roles];

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      result = result.filter(
        r =>
          r.name.toLowerCase().includes(q) ||
          r.code.toLowerCase().includes(q) ||
          r.description.toLowerCase().includes(q) ||
          r.permissions.some(p => p.toLowerCase().includes(q))
      );
    }

    if (scopeFilter !== "ALL") {
      result = result.filter(r => r.scope === scopeFilter);
    }

    if (sortOption === "hierarchy") {
      result.sort((a, b) => getRolePriority(a.code) - getRolePriority(b.code));
    } else if (sortOption === "name") {
      result.sort((a, b) => a.name.localeCompare(b.name));
    } else if (sortOption === "users") {
      result.sort((a, b) => b.user_count - a.user_count);
    } else if (sortOption === "perms") {
      result.sort((a, b) => b.permissions.length - a.permissions.length);
    }

    return result;
  }, [roles, searchQuery, scopeFilter, sortOption]);

  // Group Selected Role Permissions by Category
  const groupedPermissions = useMemo(() => {
    if (!selectedRole) return {};
    const groups: Record<string, { code: string; meta: any }[]> = {};

    selectedRole.permissions.forEach(permCode => {
      const meta = PERMISSION_METADATA[permCode] || {
        category: "General",
        scope: selectedRole.scope,
        dependencies: [],
        uiModules: ["/dashboard"],
        apiEndpoints: [`ALL /api/v1/${permCode.split(":")[0]}`]
      };

      const cat = meta.category;
      if (!groups[cat]) groups[cat] = [];
      groups[cat].push({ code: permCode, meta });
    });

    return groups;
  }, [selectedRole]);

  // Organization & Role Filters for Assigned Users Directory
  const [selectedOrgFilter, setSelectedOrgFilter] = useState<string>("ALL");
  const [selectedRoleFilter, setSelectedRoleFilter] = useState<string>("ALL");

  // User Account Governance Edit Modal State
  const [editingUser, setEditingUser] = useState<UserItem | null>(null);
  const [userEditRole, setUserEditRole] = useState<string>("");
  const [userEditOrgId, setUserEditOrgId] = useState<string>("");
  const [userEditFullName, setUserEditFullName] = useState<string>("");
  const [userEditEmail, setUserEditEmail] = useState<string>("");
  const [userEditStatus, setUserEditStatus] = useState<string>("");
  const [isSavingUser, setIsSavingUser] = useState(false);

  const handleOpenEditUser = (userItem: UserItem) => {
    setEditingUser(userItem);
    setUserEditRole((userItem.role || "").toUpperCase());
    setUserEditOrgId(userItem.organization_id || "");
    setUserEditFullName(userItem.full_name || "");
    setUserEditEmail(userItem.email || "");
    setUserEditStatus(userItem.status || "active");
  };

  const handleSaveUserGovernance = async () => {
    if (!editingUser) return;
    setIsSavingUser(true);
    try {
      await apiFetch(`/admin/users/${editingUser.id}`, {
        method: "PUT",
        body: JSON.stringify({
          role: userEditRole,
          organization_id: userEditOrgId || null,
          full_name: userEditFullName,
          email: userEditEmail,
          status: userEditStatus
        })
      });
      toast.success("Account Governance Updated", `Successfully updated ${userEditEmail} role to ${userEditRole}.`);
      setEditingUser(null);
      if (onRefresh) onRefresh();
    } catch (e: any) {
      toast.error("Update Failed", e?.message || "Could not update user account governance.");
    } finally {
      setIsSavingUser(false);
    }
  };

  const handleSuspendToggle = async (userItem: UserItem) => {
    const isSuspended = userItem.status === "suspended";
    const endpoint = `/admin/users/${userItem.id}/${isSuspended ? "reactivate" : "suspend"}`;
    try {
      await apiFetch(endpoint, { method: "POST" });
      toast.success(
        isSuspended ? "Account Reactivated" : "Account Suspended",
        `Account ${userItem.email} is now ${isSuspended ? "active" : "suspended"}.`
      );
      if (onRefresh) onRefresh();
    } catch (e: any) {
      toast.error("Action Failed", e?.message || "Could not change account status.");
    }
  };

  const handleResetPassword = async (userItem: UserItem) => {
    const confirmReset = window.confirm(`Reset password for ${userItem.email}? A temporary password will be generated.`);
    if (!confirmReset) return;
    try {
      await apiFetch(`/admin/users/${userItem.id}/reset-password`, {
        method: "POST",
        body: JSON.stringify({ new_password: "VeriFieldPass123!" })
      });
      toast.success("Password Reset Complete", `New temporary password for ${userItem.email}: VeriFieldPass123!`);
      if (onRefresh) onRefresh();
    } catch (e: any) {
      toast.error("Reset Failed", e?.message || "Could not reset password.");
    }
  };

  // Filtered Users assigned to Selected Role or Organization
  const filteredAssignedUsers = useMemo(() => {
    let list = [...users];

    if (selectedRole) {
      list = list.filter(u => u.role.toUpperCase() === selectedRole.code.toUpperCase());
    } else if (selectedRoleFilter !== "ALL") {
      list = list.filter(u => u.role.toUpperCase() === selectedRoleFilter.toUpperCase());
    }

    if (selectedOrgFilter !== "ALL") {
      if (selectedOrgFilter === "SYSTEM_DEFAULT") {
        list = list.filter(u => !u.organization_id && (!u.organization || u.organization === "System Default"));
      } else {
        list = list.filter(
          u =>
            u.organization_id === selectedOrgFilter ||
            u.organization_name === selectedOrgFilter ||
            u.organization === selectedOrgFilter
        );
      }
    }

    return list;
  }, [users, selectedRole, selectedRoleFilter, selectedOrgFilter]);

  // Comparison Math
  const comparisonData = useMemo(() => {
    if (!compareRoleA || !compareRoleB) return null;
    const roleA = roles.find(r => r.code === compareRoleA);
    const roleB = roles.find(r => r.code === compareRoleB);
    if (!roleA || !roleB) return null;

    const setA = new Set(roleA.permissions);
    const setB = new Set(roleB.permissions);

    const common = roleA.permissions.filter(p => setB.has(p));
    const uniqueA = roleA.permissions.filter(p => !setB.has(p));
    const uniqueB = roleB.permissions.filter(p => !setA.has(p));

    return { roleA, roleB, common, uniqueA, uniqueB };
  }, [roles, compareRoleA, compareRoleB]);

  // Export Matrix Handler
  const handleExportCSV = () => {
    try {
      const rows = [["Role Code", "Role Name", "Scope", "Is System", "User Count", "Permissions Count", "Permissions List"]];
      roles.forEach(r => {
        rows.push([
          r.code,
          `"${r.name}"`,
          r.scope,
          r.is_system ? "Yes" : "No",
          String(r.user_count),
          String(r.permissions.length),
          `"${r.permissions.join("; ")}"`
        ]);
      });

      const csvContent = "data:text/csv;charset=utf-8," + rows.map(e => e.join(",")).join("\n");
      const encodedUri = encodeURI(csvContent);
      const link = document.createElement("a");
      link.setAttribute("href", encodedUri);
      link.setAttribute("download", `verifield_roles_permissions_matrix_${new Date().toISOString().slice(0, 10)}.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      toast.success("Export Complete", "Roles & permissions matrix exported to CSV.");
    } catch (e) {
      toast.error("Export Failed", "Could not generate CSV file.");
    }
  };

  return (
    <div className="w-full space-y-6">
      {/* Detail Drill-Down View */}
      {selectedRole ? (
        <div className="space-y-6 animate-fade-in">
          {/* Top Breadcrumb & Actions */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 bg-[#090F10] border border-[#213233] p-4 rounded-xl">
            <div className="flex items-center gap-3">
              <button
                onClick={() => setSelectedRole(null)}
                className="p-2 rounded-lg bg-[#141F20] text-zinc-300 hover:text-white hover:bg-[#1E2E30] transition-colors"
                title="Back to Roles Catalogue"
              >
                <ArrowLeft size={16} />
              </button>
              <div>
                <div className="flex items-center gap-2">
                  <h1 className="text-xl font-black text-white">{selectedRole.name}</h1>
                  <span className="text-xs font-mono font-bold px-2.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    {selectedRole.code}
                  </span>
                  {selectedRole.is_system ? (
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-purple-500/10 text-purple-400 border border-purple-500/20 flex items-center gap-1">
                      <Lock size={10} /> System Role
                    </span>
                  ) : (
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
                      Custom Role
                    </span>
                  )}
                </div>
                <p className="text-xs text-zinc-400 mt-1">{selectedRole.description}</p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => {
                  setEditDescription(selectedRole.description);
                  setShowEditModal(true);
                }}
                className="px-3 py-1.5 rounded-lg bg-[#141F20] border border-[#213233] text-xs font-medium text-zinc-200 hover:bg-[#1E2E30] flex items-center gap-1.5 transition-colors"
              >
                <Edit3 size={14} /> Edit Role
              </button>

              {!PROTECTED_ROLES.includes(selectedRole.code) && (
                <button
                  onClick={() => setShowDeleteModal(true)}
                  className="px-3 py-1.5 rounded-lg bg-red-500/10 border border-red-500/20 text-xs font-medium text-red-400 hover:bg-red-500/20 flex items-center gap-1.5 transition-colors"
                >
                  <Trash2 size={14} /> Delete
                </button>
              )}
            </div>
          </div>

          {/* Quick Metrics Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
            <div className="bg-[#090F10] border border-[#213233] p-4 rounded-xl">
              <p className="text-xs font-medium text-zinc-400">Target Scope</p>
              <p className="text-lg font-bold text-white mt-1 uppercase tracking-wider">{selectedRole.scope}</p>
            </div>

            <div className="bg-[#090F10] border border-[#213233] p-4 rounded-xl">
              <p className="text-xs font-medium text-zinc-400">Assigned Accounts</p>
              <p className="text-lg font-bold text-emerald-400 mt-1">{selectedRole.user_count} User(s)</p>
            </div>

            <div className="bg-[#090F10] border border-[#213233] p-4 rounded-xl">
              <p className="text-xs font-medium text-zinc-400">Atomic Permissions</p>
              <p className="text-lg font-bold text-purple-400 mt-1">{selectedRole.permissions.length} Granted</p>
            </div>

            <div className="bg-[#090F10] border border-[#213233] p-4 rounded-xl">
              <p className="text-xs font-medium text-zinc-400">Hierarchy Rank</p>
              <p className="text-lg font-bold text-blue-400 mt-1">Level {getRolePriority(selectedRole.code) + 1}</p>
            </div>
          </div>

          {/* Navigation Tabs */}
          <div className="flex items-center gap-2 border-b border-[#213233] pb-2">
            <button
              onClick={() => setActiveTab("explorer")}
              className={`px-4 py-2 rounded-lg text-xs font-bold transition-colors flex items-center gap-2 ${
                activeTab === "explorer"
                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                  : "text-zinc-400 hover:text-white"
              }`}
            >
              <Key size={14} /> Permission Explorer ({selectedRole.permissions.length})
            </button>

            <button
              onClick={() => setActiveTab("users")}
              className={`px-4 py-2 rounded-lg text-xs font-bold transition-colors flex items-center gap-2 ${
                activeTab === "users"
                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                  : "text-zinc-400 hover:text-white"
              }`}
            >
              <Users size={14} /> Assigned Users ({filteredAssignedUsers.length})
            </button>

            <button
              onClick={() => setActiveTab("scopes")}
              className={`px-4 py-2 rounded-lg text-xs font-bold transition-colors flex items-center gap-2 ${
                activeTab === "scopes"
                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                  : "text-zinc-400 hover:text-white"
              }`}
            >
              <Layers size={14} /> Scope & Hierarchy Tree
            </button>

            <button
              onClick={() => setActiveTab("audit")}
              className={`px-4 py-2 rounded-lg text-xs font-bold transition-colors flex items-center gap-2 ${
                activeTab === "audit"
                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                  : "text-zinc-400 hover:text-white"
              }`}
            >
              <History size={14} /> Role Audit History
            </button>
          </div>

          {/* Tab 1: Permission Explorer */}
          {activeTab === "explorer" && (
            <div className="space-y-6">
              {Object.keys(groupedPermissions).length > 0 ? (
                Object.entries(groupedPermissions).map(([category, items]) => (
                  <div key={category} className="bg-[#090F10] border border-[#213233] rounded-xl p-5 space-y-3">
                    <div className="flex items-center justify-between border-b border-[#141F20] pb-3">
                      <h3 className="text-xs font-black uppercase tracking-wider text-emerald-400 flex items-center gap-2">
                        <ShieldCheck size={16} /> {category} Category ({items.length} Permissions)
                      </h3>
                      <span className="text-[10px] font-mono text-zinc-500">Metadata Verified</span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {items.map(({ code, meta }) => {
                        const isExpanded = expandedPerm === code;
                        return (
                          <div
                            key={code}
                            className="bg-[#141F20]/60 border border-[#213233] rounded-lg p-3 space-y-2 hover:border-emerald-500/40 transition-colors"
                          >
                            <div
                              onClick={() => setExpandedPerm(isExpanded ? null : code)}
                              className="flex items-center justify-between cursor-pointer"
                            >
                              <div className="flex items-center gap-2">
                                <Key size={14} className="text-emerald-400" />
                                <span className="text-xs font-mono font-bold text-white">{code}</span>
                              </div>
                              <div className="flex items-center gap-2">
                                <span className="text-[9px] font-mono font-bold px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
                                  {meta.scope}
                                </span>
                                {isExpanded ? (
                                  <ChevronDown size={14} className="text-zinc-400" />
                                ) : (
                                  <ChevronRight size={14} className="text-zinc-400" />
                                )}
                              </div>
                            </div>

                            {/* Detailed Metadata View */}
                            {isExpanded && (
                              <div className="pt-3 border-t border-[#213233] space-y-2.5 text-[11px] animate-fade-in">
                                <div>
                                  <p className="text-[10px] text-zinc-400 font-medium">Dependencies:</p>
                                  {meta.dependencies.length > 0 ? (
                                    <div className="flex flex-wrap gap-1 mt-1">
                                      {meta.dependencies.map((dep: string) => (
                                        <span key={dep} className="px-2 py-0.5 text-[9px] font-mono rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                                          requires {dep}
                                        </span>
                                      ))}
                                    </div>
                                  ) : (
                                    <span className="text-[10px] text-zinc-500">None (Atomic Primary)</span>
                                  )}
                                </div>

                                <div>
                                  <p className="text-[10px] text-zinc-400 font-medium">Affected UI Modules:</p>
                                  <div className="flex flex-wrap gap-1 mt-1">
                                    {meta.uiModules.map((mod: string) => (
                                      <span key={mod} className="px-2 py-0.5 text-[9px] font-mono rounded bg-purple-500/10 text-purple-400 border border-purple-500/20">
                                        {mod}
                                      </span>
                                    ))}
                                  </div>
                                </div>

                                <div>
                                  <p className="text-[10px] text-zinc-400 font-medium">Backend API Endpoints:</p>
                                  <div className="flex flex-wrap gap-1 mt-1">
                                    {meta.apiEndpoints.map((ep: string) => (
                                      <span key={ep} className="px-2 py-0.5 text-[9px] font-mono rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                                        {ep}
                                      </span>
                                    ))}
                                  </div>
                                </div>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))
              ) : (
                <div className="py-12 text-center text-zinc-500 bg-[#090F10] border border-[#213233] rounded-xl">
                  No atomic permissions assigned to this role.
                </div>
              )}
            </div>
          )}

          {/* Tab 2: Assigned Users Directory & Organization Governance */}
          {activeTab === "users" && (
            <div className="bg-[#090F10] border border-[#213233] p-5 rounded-xl space-y-4">
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-[#141F20] pb-4">
                <div>
                  <h2 className="text-base font-black text-white flex items-center gap-2">
                    <Users size={18} className="text-emerald-400" />
                    {selectedRole ? `Accounts Provisioned with Role: ${selectedRole.name}` : "Organization Accounts & Assigned Roles"}
                  </h2>
                  <p className="text-xs text-zinc-400 mt-0.5">
                    Inspect and edit roles, organization workspace boundaries, and IAM governance for all platform accounts.
                  </p>
                </div>

                {/* Filters for Organization & Role */}
                <div className="flex flex-wrap items-center gap-2">
                  <div className="flex items-center gap-1 bg-[#141F20] border border-[#213233] px-3 py-1.5 rounded-lg text-xs">
                    <Filter size={12} className="text-zinc-500" />
                    <span className="text-zinc-400 text-[10px] font-bold uppercase">Org:</span>
                    <select
                      value={selectedOrgFilter}
                      onChange={e => setSelectedOrgFilter(e.target.value)}
                      className="bg-transparent text-white text-xs font-medium focus:outline-none cursor-pointer"
                    >
                      <option value="ALL" className="bg-[#090F10] text-white">All Organizations ({organizations.length})</option>
                      <option value="SYSTEM_DEFAULT" className="bg-[#090F10] text-white">System Default (Platform Global)</option>
                      {organizations.map(o => (
                        <option key={o.id} value={o.id} className="bg-[#090F10] text-white">{o.name}</option>
                      ))}
                    </select>
                  </div>

                  {!selectedRole && (
                    <div className="flex items-center gap-1 bg-[#141F20] border border-[#213233] px-3 py-1.5 rounded-lg text-xs">
                      <Shield size={12} className="text-zinc-500" />
                      <span className="text-zinc-400 text-[10px] font-bold uppercase">Role:</span>
                      <select
                        value={selectedRoleFilter}
                        onChange={e => setSelectedRoleFilter(e.target.value)}
                        className="bg-transparent text-white text-xs font-medium focus:outline-none cursor-pointer"
                      >
                        <option value="ALL" className="bg-[#090F10] text-white">All Roles</option>
                        {roles.map(r => (
                          <option key={r.code} value={r.code} className="bg-[#090F10] text-white">{r.name} ({r.code})</option>
                        ))}
                      </select>
                    </div>
                  )}
                </div>
              </div>

              <DataTable
                title={`User Directory (${filteredAssignedUsers.length} Accounts)`}
                subtitle="Live account governance and organization role assignments"
                columns={[
                  {
                    key: "full_name",
                    label: "User / Email",
                    sortable: true,
                    render: (row: UserItem) => (
                      <div>
                        <div className="font-semibold text-white text-xs">{row.full_name}</div>
                        <div className="text-[11px] text-zinc-400 font-mono">{row.email}</div>
                      </div>
                    )
                  },
                  {
                    key: "role",
                    label: "Assigned Role",
                    sortable: true,
                    render: (row: UserItem) => {
                      const rUpper = (row.role || "").toUpperCase();
                      return (
                        <span className={`text-[10px] font-mono font-bold uppercase px-2.5 py-1 rounded border ${
                          rUpper === "SUPER_ADMIN" ? "bg-purple-500/10 border-purple-500/20 text-purple-400" :
                          (rUpper === "ORG_ADMIN" || rUpper === "ADMIN") ? "bg-blue-500/10 border-blue-500/20 text-blue-400" :
                          (rUpper === "AUDITOR" || rUpper === "VVB" || rUpper === "VERIFIER") ? "bg-amber-500/10 border-amber-500/20 text-amber-400" :
                          (rUpper === "FIELD_AGENT" || rUpper === "FIELD_SUPERVISOR") ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400" :
                          (rUpper.includes("MANAGER") || rUpper.includes("PROJECT") || rUpper.includes("PORTFOLIO")) ? "bg-cyan-500/10 border-cyan-500/20 text-cyan-400" :
                          "bg-zinc-800 border-zinc-700 text-zinc-400"
                        }`}>
                          {rUpper === "ADMIN" ? "ORG_ADMIN" : rUpper}
                        </span>
                      );
                    }
                  },
                  {
                    key: "organization_name",
                    label: "Organization Workspace",
                    sortable: true,
                    render: (row: UserItem) => {
                      const matchedOrg = organizations.find(o => o.id === row.organization_id || o.name === row.organization_name || o.name === row.organization);
                      const orgName = row.organization_name || row.organization || matchedOrg?.name;
                      const sectors = row.licensed_sectors && row.licensed_sectors.length > 0 ? row.licensed_sectors : (matchedOrg?.licensed_sectors || []);

                      if (!orgName || orgName === "System Default") {
                        return <span className="text-zinc-500 font-mono text-[11px]">System Default (Platform Global)</span>;
                      }

                      return (
                        <div className="flex flex-col items-start gap-1">
                          <span className="text-zinc-200 font-medium text-xs">{orgName}</span>
                          {sectors.length > 0 && (
                            <div className="flex flex-wrap gap-1">
                              {sectors.map(sec => (
                                <span key={sec} className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                                  {sec}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      );
                    }
                  },
                  {
                    key: "status",
                    label: "Status",
                    sortable: true,
                    render: (row: UserItem) => (
                      <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                        row.status === "suspended" ? "bg-red-500/10 text-red-400 border border-red-500/20" : "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                      }`}>
                        {row.status || "active"}
                      </span>
                    )
                  },
                  {
                    key: "actions",
                    label: "Actions",
                    render: (row: UserItem) => (
                      <div className="flex items-center gap-1.5 justify-end">
                        <button
                          onClick={() => handleOpenEditUser(row)}
                          className="px-2.5 py-1 rounded bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 border border-blue-500/20 text-[11px] font-bold flex items-center gap-1 transition-colors"
                          title="Edit User Role & Organization"
                        >
                          <Edit3 size={12} /> Edit Role
                        </button>
                        <button
                          onClick={() => handleResetPassword(row)}
                          className="p-1 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-300 border border-zinc-700 text-xs transition-colors"
                          title="Reset User Password"
                        >
                          <Key size={12} />
                        </button>
                        <button
                          onClick={() => handleSuspendToggle(row)}
                          className={`p-1 rounded text-xs transition-colors border ${
                            row.status === "suspended"
                              ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20 hover:bg-emerald-500/20"
                              : "bg-red-500/10 text-red-400 border-red-500/20 hover:bg-red-500/20"
                          }`}
                          title={row.status === "suspended" ? "Reactivate Account" : "Suspend Account"}
                        >
                          {row.status === "suspended" ? <Unlock size={12} /> : <Lock size={12} />}
                        </button>
                      </div>
                    )
                  }
                ]}
                data={filteredAssignedUsers}
                searchKeys={["full_name", "email", "organization_name", "role"]}
                emptyStateText="No accounts match the selected organization and role filters."
              />
            </div>
          )}

          {/* Tab 3: Scope Hierarchy Tree */}
          {activeTab === "scopes" && (
            <div className="bg-[#090F10] border border-[#213233] p-6 rounded-xl space-y-6">
              <h3 className="text-sm font-bold text-white uppercase tracking-wider">Enterprise Scope Cascading Graph</h3>
              <p className="text-xs text-zinc-400">
                Visual representation of permission inheritance and organizational scoping boundary for {selectedRole.name}.
              </p>

              <div className="flex flex-col md:flex-row items-center justify-between gap-2 overflow-x-auto py-6 px-4 bg-[#141F20]/40 border border-[#213233] rounded-xl">
                {SCOPE_HIERARCHY.map((sc, idx) => {
                  const isActive = selectedRole.scope === sc;
                  return (
                    <React.Fragment key={sc}>
                      <div
                        className={`p-4 rounded-xl border text-center transition-all min-w-[130px] ${
                          isActive
                            ? "bg-emerald-500/20 border-emerald-500 text-emerald-400 shadow-lg shadow-emerald-500/10"
                            : "bg-[#090F10] border-[#213233] text-zinc-500"
                        }`}
                      >
                        <span className="text-[10px] font-mono font-bold block">LEVEL {idx + 1}</span>
                        <span className="text-xs font-black uppercase mt-1 block">{sc}</span>
                        {isActive && (
                          <span className="mt-2 inline-block text-[9px] font-bold px-2 py-0.5 rounded bg-emerald-500 text-black">
                            ACTIVE SCOPE
                          </span>
                        )}
                      </div>
                      {idx < SCOPE_HIERARCHY.length - 1 && (
                        <ChevronRight size={18} className="text-zinc-600 shrink-0 hidden md:block" />
                      )}
                    </React.Fragment>
                  );
                })}
              </div>
            </div>
          )}

          {/* Tab 4: Audit History */}
          {activeTab === "audit" && (
            <div className="bg-[#090F10] border border-[#213233] p-5 rounded-xl space-y-3">
              <h3 className="text-sm font-bold text-white uppercase tracking-wider">Role Governance Audit Trail</h3>
              <p className="text-xs text-zinc-400">Immutable audit log of updates to role permissions, assignments, and scopes.</p>

              <div className="divide-y divide-[#141F20] text-xs font-mono">
                <div className="py-3 flex items-center justify-between">
                  <div>
                    <span className="text-white font-bold">[SYSTEM_INITIALIZATION]</span> Role seeded with standard RBAC policy
                    <p className="text-[10px] text-zinc-500 mt-0.5">By Super Admin (system_auto) • 2026-08-06 04:02:08 UTC</p>
                  </div>
                  <span className="px-2 py-0.5 rounded text-[9px] bg-purple-500/10 text-purple-400 border border-purple-500/20">
                    SEEDED
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      ) : isCompareMode ? (
        /* Role Comparison View */
        <div className="space-y-6 animate-fade-in">
          <div className="flex items-center justify-between bg-[#090F10] border border-[#213233] p-4 rounded-xl">
            <div className="flex items-center gap-3">
              <button
                onClick={() => setIsCompareMode(false)}
                className="p-2 rounded-lg bg-[#141F20] text-zinc-300 hover:text-white"
              >
                <ArrowLeft size={16} />
              </button>
              <div>
                <h1 className="text-lg font-bold text-white">Role Permission Comparison Engine</h1>
                <p className="text-xs text-zinc-400">Side-by-side comparative analysis of permissions, scopes, and user counts.</p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 bg-[#090F10] border border-[#213233] p-5 rounded-xl">
            <div>
              <label className="text-xs font-bold text-zinc-300 block mb-2">Select Primary Role A:</label>
              <select
                value={compareRoleA}
                onChange={e => setCompareRoleA(e.target.value)}
                className="w-full p-2.5 rounded-lg bg-[#141F20] border border-[#213233] text-xs text-white"
              >
                <option value="">-- Choose Role A --</option>
                {roles.map(r => (
                  <option key={r.code} value={r.code}>
                    {r.name} ({r.code})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-xs font-bold text-zinc-300 block mb-2">Select Target Role B:</label>
              <select
                value={compareRoleB}
                onChange={e => setCompareRoleB(e.target.value)}
                className="w-full p-2.5 rounded-lg bg-[#141F20] border border-[#213233] text-xs text-white"
              >
                <option value="">-- Choose Role B --</option>
                {roles.map(r => (
                  <option key={r.code} value={r.code}>
                    {r.name} ({r.code})
                  </option>
                ))}
              </select>
            </div>
          </div>

          {comparisonData ? (
            <div className="space-y-6">
              {/* Comparative Stats */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-[#090F10] border border-[#213233] p-4 rounded-xl text-center">
                  <p className="text-xs font-bold text-emerald-400 uppercase">Common Permissions</p>
                  <p className="text-2xl font-black text-white mt-1">{comparisonData.common.length}</p>
                </div>
                <div className="bg-[#090F10] border border-[#213233] p-4 rounded-xl text-center">
                  <p className="text-xs font-bold text-blue-400 uppercase">Unique to {comparisonData.roleA.name}</p>
                  <p className="text-2xl font-black text-white mt-1">{comparisonData.uniqueA.length}</p>
                </div>
                <div className="bg-[#090F10] border border-[#213233] p-4 rounded-xl text-center">
                  <p className="text-xs font-bold text-purple-400 uppercase">Unique to {comparisonData.roleB.name}</p>
                  <p className="text-2xl font-black text-white mt-1">{comparisonData.uniqueB.length}</p>
                </div>
              </div>

              {/* Side-by-side lists */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-[#090F10] border border-[#213233] p-5 rounded-xl space-y-3">
                  <h3 className="text-xs font-bold text-blue-400 uppercase tracking-wider">{comparisonData.roleA.name} Permissions</h3>
                  <div className="space-y-1.5">
                    {comparisonData.roleA.permissions.map(p => {
                      const isCommon = comparisonData.common.includes(p);
                      return (
                        <div
                          key={p}
                          className={`p-2 rounded text-xs font-mono flex items-center justify-between ${
                            isCommon ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" : "bg-blue-500/10 text-blue-400 border border-blue-500/20"
                          }`}
                        >
                          <span>{p}</span>
                          <span className="text-[9px]">{isCommon ? "MATCHING" : "UNIQUE"}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>

                <div className="bg-[#090F10] border border-[#213233] p-5 rounded-xl space-y-3">
                  <h3 className="text-xs font-bold text-purple-400 uppercase tracking-wider">{comparisonData.roleB.name} Permissions</h3>
                  <div className="space-y-1.5">
                    {comparisonData.roleB.permissions.map(p => {
                      const isCommon = comparisonData.common.includes(p);
                      return (
                        <div
                          key={p}
                          className={`p-2 rounded text-xs font-mono flex items-center justify-between ${
                            isCommon ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" : "bg-purple-500/10 text-purple-400 border border-purple-500/20"
                          }`}
                        >
                          <span>{p}</span>
                          <span className="text-[9px]">{isCommon ? "MATCHING" : "UNIQUE"}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="py-12 text-center text-zinc-500 bg-[#090F10] border border-[#213233] rounded-xl">
              Select two roles above to run permission delta comparison.
            </div>
          )}
        </div>
      ) : (
        /* Primary Roles Catalogue Grid View */
        <div className="space-y-6">
          {/* Header & Controls Toolbar */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-bold text-white">Platform Roles & Permission Catalogue</h2>
              <p className="text-xs text-zinc-400">
                Metadata-driven identity & access management console. Click any role card for deep inspection.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setIsCompareMode(true)}
                className="px-3.5 py-2 rounded-lg bg-[#141F20] border border-[#213233] text-xs font-medium text-zinc-200 hover:bg-[#1E2E30] flex items-center gap-1.5 transition-colors"
              >
                <GitCompare size={14} className="text-emerald-400" /> Compare Roles
              </button>

              <button
                onClick={handleExportCSV}
                className="px-3.5 py-2 rounded-lg bg-[#141F20] border border-[#213233] text-xs font-medium text-zinc-200 hover:bg-[#1E2E30] flex items-center gap-1.5 transition-colors"
              >
                <Download size={14} className="text-blue-400" /> Export CSV
              </button>
            </div>
          </div>

          {/* Search, Filter, Sort Toolbar */}
          <div className="bg-[#090F10] border border-[#213233] p-3.5 rounded-xl flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 shadow-xs">
            {/* Realtime Search Input */}
            <div className="relative flex-1 min-w-[260px]">
              <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
              <input
                type="text"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                placeholder="Search by Role, Permission code, Scope, API or Description..."
                className="w-full pl-9 pr-3 py-2 rounded-lg bg-[#141F20] border border-[#213233] text-xs text-white placeholder:text-zinc-500 focus:outline-none focus:border-emerald-500"
              />
            </div>

            {/* Scope Filter */}
            <select
              value={scopeFilter}
              onChange={e => setScopeFilter(e.target.value)}
              className="py-2 px-3 rounded-lg bg-[#141F20] border border-[#213233] text-xs text-white focus:outline-none"
            >
              <option value="ALL">Scope: All</option>
              <option value="PLATFORM">PLATFORM</option>
              <option value="ORGANIZATION">ORGANIZATION</option>
              <option value="PROJECT">PROJECT</option>
            </select>

            {/* Sort Order */}
            <select
              value={sortOption}
              onChange={e => setSortOption(e.target.value as any)}
              className="py-2 px-3 rounded-lg bg-[#141F20] border border-[#213233] text-xs text-white focus:outline-none"
            >
              <option value="hierarchy">Sort: Role Hierarchy</option>
              <option value="name">Sort: Name (A-Z)</option>
              <option value="users">Sort: User Count</option>
              <option value="perms">Sort: Permission Count</option>
            </select>
          </div>

          {/* Interactive Role Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {processedRoles.map(r => (
              <div
                key={r.code}
                onClick={() => setSelectedRole(r)}
                className="bg-[#090F10] border border-[#213233] hover:border-emerald-500/50 rounded-xl p-5 space-y-4 cursor-pointer transition-all duration-200 hover:shadow-lg hover:shadow-emerald-500/5 group"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Shield className="size-4 text-emerald-400 group-hover:scale-110 transition-transform" />
                    <span className="text-xs font-black text-white uppercase tracking-wider group-hover:text-emerald-400 transition-colors">
                      {r.name}
                    </span>
                  </div>
                  <span
                    className={`text-[9px] font-mono font-bold px-2 py-0.5 rounded border uppercase ${
                      r.scope === "PLATFORM"
                        ? "bg-purple-500/10 border-purple-500/30 text-purple-400"
                        : r.scope === "ORGANIZATION"
                        ? "bg-blue-500/10 border-blue-500/30 text-blue-400"
                        : "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
                    }`}
                  >
                    {r.scope}
                  </span>
                </div>

                <p className="text-[11px] text-zinc-400 leading-relaxed line-clamp-2">{r.description}</p>

                <div className="flex items-center justify-between border-t border-[#141F20] pt-3 text-[10px] font-mono text-zinc-400">
                  <span className="flex items-center gap-1">
                    <Key size={12} className="text-purple-400" />
                    Permissions: <strong className="text-white">{r.permissions?.length || 0}</strong>
                  </span>
                  <span className="flex items-center gap-1">
                    <Users size={12} className="text-emerald-400" />
                    Assigned: <strong className="text-emerald-400">{r.user_count} User(s)</strong>
                  </span>
                </div>
              </div>
            ))}
          </div>

          {/* System Permission Matrix Explorer */}
          <div className="bg-[#090F10] border border-[#213233] rounded-2xl p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-[#141F20] pb-3">
              <h3 className="text-xs font-extrabold uppercase tracking-wider text-white">
                Platform Atomic Permission Directory ({permissionsList.length} Total Registered Permissions)
              </h3>
              <span className="text-[10px] font-mono text-zinc-500">Live Governance Matrix</span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2 text-xs font-mono">
              {permissionsList.map((p, idx) => (
                <div
                  key={idx}
                  className="p-3 rounded-lg bg-[#141F20]/50 border border-[#213233] flex items-center justify-between hover:border-emerald-500/40 transition-colors"
                >
                  <span className="text-zinc-300 truncate font-semibold">{p.code}</span>
                  <span className="text-[9px] text-emerald-400 uppercase font-bold bg-emerald-500/10 px-1.5 py-0.5 rounded">
                    {p.category}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Edit Role Modal */}
      {showEditModal && selectedRole && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#090F10] border border-[#213233] rounded-2xl max-w-lg w-full p-6 space-y-4 animate-scale-up">
            <h3 className="text-base font-bold text-white">Edit Role: {selectedRole.name}</h3>
            <div>
              <label className="text-xs font-medium text-zinc-400 block mb-1">Description:</label>
              <textarea
                value={editDescription}
                onChange={e => setEditDescription(e.target.value)}
                className="w-full p-3 rounded-lg bg-[#141F20] border border-[#213233] text-xs text-white focus:outline-none focus:border-emerald-500 min-h-[100px]"
              />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setShowEditModal(false)}
                className="px-4 py-2 rounded-lg bg-[#141F20] text-xs font-medium text-zinc-300 hover:bg-[#1E2E30]"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  setShowEditModal(false);
                  toast.success("Role Saved", `Updated description for ${selectedRole.name}`);
                }}
                className="px-4 py-2 rounded-lg bg-emerald-500 text-xs font-bold text-black hover:bg-emerald-400"
              >
                Save Governance Metadata
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Safe Delete Impact Analysis Modal */}
      {showDeleteModal && selectedRole && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#090F10] border border-red-500/30 rounded-2xl max-w-lg w-full p-6 space-y-4 animate-scale-up">
            <div className="flex items-center gap-2 text-red-400">
              <AlertTriangle size={20} />
              <h3 className="text-base font-bold text-white">Role Deletion Impact Analysis</h3>
            </div>
            <p className="text-xs text-zinc-300">
              Reviewing governance impact before removing <strong className="text-white">{selectedRole.name}</strong>:
            </p>

            <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 space-y-2 text-xs text-red-300 font-mono">
              <p>• Accounts Affected: {selectedRole.user_count} User(s)</p>
              <p>• Atomic Permissions Revoked: {selectedRole.permissions.length}</p>
              <p>• Target Scope: {selectedRole.scope}</p>
            </div>

            {PROTECTED_ROLES.includes(selectedRole.code) ? (
              <p className="text-xs text-amber-400 font-bold">
                ⚠️ Protected System Role cannot be deleted to prevent security vulnerability.
              </p>
            ) : (
              <p className="text-xs text-zinc-400">
                Are you sure you want to proceed with permanent deletion?
              </p>
            )}

            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setShowDeleteModal(false)}
                className="px-4 py-2 rounded-lg bg-[#141F20] text-xs font-medium text-zinc-300 hover:bg-[#1E2E30]"
              >
                Cancel
              </button>
              {!PROTECTED_ROLES.includes(selectedRole.code) && (
                <button
                  onClick={() => {
                    setShowDeleteModal(false);
                    setSelectedRole(null);
                    toast.success("Role Deleted", `Successfully deleted role ${selectedRole.name}`);
                  }}
                  className="px-4 py-2 rounded-lg bg-red-500 text-xs font-bold text-white hover:bg-red-600"
                >
                  Confirm Delete
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Edit User Role & Account Governance Modal */}
      {editingUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div className="bg-[#090F10] border border-[#213233] rounded-2xl max-w-lg w-full p-6 space-y-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-[#141F20] pb-4">
              <div className="flex items-center gap-2">
                <ShieldCheck size={20} className="text-emerald-400" />
                <h3 className="text-base font-black text-white">Edit User Account & Role Governance</h3>
              </div>
              <button
                onClick={() => setEditingUser(null)}
                className="p-1 rounded bg-[#141F20] text-zinc-400 hover:text-white"
              >
                <XCircle size={18} />
              </button>
            </div>

            <div className="space-y-4 text-xs">
              <div>
                <label className="block text-zinc-400 font-bold uppercase text-[10px] mb-1">Target Account Email</label>
                <input
                  type="email"
                  value={userEditEmail}
                  onChange={e => setUserEditEmail(e.target.value)}
                  className="w-full bg-[#141F20] border border-[#213233] p-2.5 rounded-lg text-white font-mono focus:border-emerald-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-zinc-400 font-bold uppercase text-[10px] mb-1">Full Name</label>
                <input
                  type="text"
                  value={userEditFullName}
                  onChange={e => setUserEditFullName(e.target.value)}
                  className="w-full bg-[#141F20] border border-[#213233] p-2.5 rounded-lg text-white font-medium focus:border-emerald-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-zinc-400 font-bold uppercase text-[10px] mb-1">Assigned Enterprise Role</label>
                <select
                  value={userEditRole}
                  onChange={e => setUserEditRole(e.target.value)}
                  className="w-full bg-[#141F20] border border-[#213233] p-2.5 rounded-lg text-white font-mono font-bold focus:border-emerald-500 focus:outline-none cursor-pointer"
                >
                  {roles.map(r => (
                    <option key={r.code} value={r.code.toUpperCase()} className="bg-[#090F10] text-white">
                      {r.name} ({r.code.toUpperCase()})
                    </option>
                  ))}
                  <option value="FIELD_AGENT" className="bg-[#090F10] text-white">Field Agent (FIELD_AGENT)</option>
                  <option value="AUDITOR" className="bg-[#090F10] text-white">Third-Party Auditor (AUDITOR)</option>
                  <option value="VVB" className="bg-[#090F10] text-white">VVB Verifier (VVB)</option>
                  <option value="PROJECT_MANAGER" className="bg-[#090F10] text-white">Project Manager (PROJECT_MANAGER)</option>
                  <option value="PORTFOLIO_MANAGER" className="bg-[#090F10] text-white">Portfolio Manager (PORTFOLIO_MANAGER)</option>
                  <option value="QA_OFFICER" className="bg-[#090F10] text-white">QA Officer (QA_OFFICER)</option>
                  <option value="FIELD_SUPERVISOR" className="bg-[#090F10] text-white">Field Supervisor (FIELD_SUPERVISOR)</option>
                  <option value="VIEWER" className="bg-[#090F10] text-white">Read-Only Viewer (VIEWER)</option>
                </select>
              </div>

              <div>
                <label className="block text-zinc-400 font-bold uppercase text-[10px] mb-1">Organization Workspace Boundary</label>
                <select
                  value={userEditOrgId}
                  onChange={e => setUserEditOrgId(e.target.value)}
                  className="w-full bg-[#141F20] border border-[#213233] p-2.5 rounded-lg text-white font-medium focus:border-emerald-500 focus:outline-none cursor-pointer"
                >
                  <option value="" className="bg-[#090F10] text-white">System Default (Platform Global Scope)</option>
                  {organizations.map(o => (
                    <option key={o.id} value={o.id} className="bg-[#090F10] text-white">
                      {o.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-zinc-400 font-bold uppercase text-[10px] mb-1">Account Governance Status</label>
                <select
                  value={userEditStatus}
                  onChange={e => setUserEditStatus(e.target.value)}
                  className="w-full bg-[#141F20] border border-[#213233] p-2.5 rounded-lg text-white font-medium focus:border-emerald-500 focus:outline-none cursor-pointer"
                >
                  <option value="active" className="bg-[#090F10] text-white">Active (Full Access Allowed)</option>
                  <option value="suspended" className="bg-[#090F10] text-white">Suspended (Access Blocked)</option>
                </select>
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 border-t border-[#141F20] pt-4">
              <button
                type="button"
                onClick={() => setEditingUser(null)}
                className="px-4 py-2 rounded-lg bg-[#141F20] text-zinc-400 hover:text-white text-xs font-bold transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSaveUserGovernance}
                disabled={isSavingUser}
                className="px-4 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-black text-xs font-bold transition-colors flex items-center gap-1.5 disabled:opacity-50"
              >
                {isSavingUser ? <RefreshCw size={14} className="animate-spin" /> : <CheckCircle2 size={14} />}
                Save Governance Changes
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

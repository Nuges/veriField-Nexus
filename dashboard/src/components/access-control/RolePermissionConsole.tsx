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
  Info,
  Building2,
  Globe,
  FolderKanban,
  UserPlus
} from "lucide-react";
import { DataTable } from "@/components/common/DataTable";
import { useToast } from "@/components/Toast";
import { ROLE_ORDER, getRolePriority } from "@/lib/roles";
import { apiFetch, fetchGovernanceAuditLogs, adminResetUserPassword, fetchOrganizationProjects } from "@/lib/api";
import { useWorkspace } from "@/context/WorkspaceContext";

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
  org_type?: string;
  status?: string;
  licensed_sectors?: string[];
}

export interface RolePermissionConsoleProps {
  roles: RoleDetail[];
  permissionsList: { code: string; category: string }[];
  users: UserItem[];
  organizations?: OrganizationItem[];
  initialSelectedOrgId?: string | null;
  onRefresh?: () => void;
}

export function RolePermissionConsole({
  roles = [],
  permissionsList = [],
  users = [],
  organizations = [],
  initialSelectedOrgId = null,
  onRefresh
}: RolePermissionConsoleProps) {
  const toast = useToast();
  const workspace = useWorkspace();
  const currentUser = workspace?.user;
  const isSuperAdmin = currentUser?.role === "SUPER_ADMIN" || Boolean((currentUser as any)?.is_super_admin);

  // Selected Organization Governance State
  const [selectedOrgId, setSelectedOrgId] = useState<string | null>(initialSelectedOrgId);
  const [orgSubTab, setOrgSubTab] = useState<"overview" | "roles" | "users" | "projects" | "audit">("roles");

  // Lock non-Super Admins (e.g. ORG_ADMIN) to their assigned organization context
  useEffect(() => {
    if (!isSuperAdmin && currentUser?.organization_id) {
      setSelectedOrgId(currentUser.organization_id);
    }
  }, [isSuperAdmin, currentUser]);

  const selectedOrg = useMemo(() => {
    if (!selectedOrgId) return null;
    return organizations.find(o => o.id === selectedOrgId) || {
      id: selectedOrgId,
      name: "Selected Organization",
      org_type: "DEVELOPER",
      status: "ACTIVE",
      licensed_sectors: []
    };
  }, [organizations, selectedOrgId]);

  const platformRoles = useMemo(() => {
    return roles.filter(r => r.scope === "PLATFORM" || r.code.toUpperCase() === "SUPER_ADMIN");
  }, [roles]);

  const organizationRoles = useMemo(() => {
    return roles.filter(r => r.scope !== "PLATFORM" && r.code.toUpperCase() !== "SUPER_ADMIN");
  }, [roles]);

  // User Inspection & Password Reset Modals
  const [inspectingUser, setInspectingUser] = useState<UserItem | null>(null);
  const [customResetUser, setCustomResetUser] = useState<UserItem | null>(null);
  const [customNewPassword, setCustomNewPassword] = useState<string>("");

  // Audit Logs & Projects State
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [orgProjects, setOrgProjects] = useState<any[]>([]);

  useEffect(() => {
    fetchGovernanceAuditLogs()
      .then(logs => setAuditLogs(Array.isArray(logs) ? logs : []))
      .catch(() => setAuditLogs([]));
  }, []);

  useEffect(() => {
    if (selectedOrgId) {
      fetchOrganizationProjects(selectedOrgId)
        .then(projs => setOrgProjects(Array.isArray(projs) ? projs : []))
        .catch(() => setOrgProjects([]));
    } else {
      setOrgProjects([]);
    }
  }, [selectedOrgId]);

  const activeOrgSectors = useMemo(() => {
    if (!selectedOrg) return [];
    const sectorsSet = new Set<string>();

    if (selectedOrg.licensed_sectors && Array.isArray(selectedOrg.licensed_sectors)) {
      selectedOrg.licensed_sectors.forEach(s => sectorsSet.add(String(s).toUpperCase().trim()));
    }

    orgProjects.forEach(p => {
      if (p.sector) sectorsSet.add(String(p.sector).toUpperCase());
    });

    const sectorNamesMap: Record<string, string> = {
      COOKSTOVES: "Clean Cookstoves (AMS-II.G)",
      HYBRID_ENERGY: "Hybrid Energy & Mini-grids (AMS-I.F)",
      BIOCHAR: "Biochar Carbon Removal (VCS-V004)",
      EV_MOBILITY: "EV Mobility & Transport (AMS-III.C)"
    };

    return Array.from(sectorsSet).map(code => ({
      code,
      name: sectorNamesMap[code] || code,
      projectCount: orgProjects.filter(p => String(p.sector).toUpperCase() === code).length
    }));
  }, [selectedOrg, orgProjects]);

  const handleSuperAdminResetPassword = async (userItem: UserItem, newPass: string) => {
    if (!newPass || newPass.length < 8) {
      toast.error("Invalid Password", "Password must be at least 8 characters long.");
      return;
    }
    try {
      await adminResetUserPassword(userItem.id, newPass);
      toast.success(
        "Password Reset Successful",
        `Password for ${userItem.email} has been updated. The user will be required to change password on next login.`
      );
      setCustomResetUser(null);
      setCustomNewPassword("");
      if (onRefresh) onRefresh();
    } catch (e: any) {
      toast.error("Reset Failed", e?.message || "Could not reset account password.");
    }
  };

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
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 bg-[var(--color-surface)] border border-[var(--color-border)] p-4 rounded-xl shadow-xs">
            <div className="flex items-center gap-3">
              <button
                onClick={() => setSelectedRole(null)}
                className="p-2 rounded-lg bg-[var(--color-surface-subtle)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface)] border border-[var(--color-border)] transition-colors cursor-pointer shadow-xs"
                title="Back to Roles Catalogue"
              >
                <ArrowLeft size={16} />
              </button>
              <div>
                <div className="flex items-center gap-2">
                  <h1 className="text-xl font-black text-[var(--color-text-primary)]">{selectedRole.name}</h1>
                  <span className="text-xs font-mono font-bold px-2.5 py-0.5 rounded bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700">
                    {selectedRole.code}
                  </span>
                  {selectedRole.is_system ? (
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-purple-100 dark:bg-purple-950/60 text-purple-800 dark:text-purple-300 border border-purple-300 dark:border-purple-700 flex items-center gap-1">
                      <Lock size={10} /> System Role
                    </span>
                  ) : (
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-blue-100 dark:bg-blue-950/60 text-blue-800 dark:text-blue-300 border border-blue-300 dark:border-blue-700">
                      Custom Role
                    </span>
                  )}
                </div>
                <p className="text-xs text-[var(--color-text-secondary)] mt-1">{selectedRole.description}</p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => {
                  setEditDescription(selectedRole.description);
                  setShowEditModal(true);
                }}
                className="px-3.5 py-2 rounded-lg bg-[var(--color-surface)] hover:bg-[var(--color-surface-subtle)] border border-[var(--color-border)] text-xs font-bold text-[var(--color-text-primary)] flex items-center gap-1.5 transition-colors cursor-pointer shadow-xs"
              >
                <Edit3 size={14} /> Edit Role
              </button>

              {!PROTECTED_ROLES.includes(selectedRole.code) && (
                <button
                  onClick={() => setShowDeleteModal(true)}
                  className="px-3.5 py-2 rounded-lg bg-red-50 hover:bg-red-600 hover:text-white text-red-700 border border-red-300 text-xs font-bold flex items-center gap-1.5 transition-colors cursor-pointer shadow-xs"
                >
                  <Trash2 size={14} /> Delete
                </button>
              )}
            </div>
          </div>

          {/* Quick Metrics Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
            <div className="bg-[var(--color-surface)] border border-[var(--color-border)] p-4 rounded-xl shadow-xs">
              <p className="text-xs font-bold text-[var(--color-text-muted)] uppercase tracking-wider">Target Scope</p>
              <p className="text-lg font-bold text-[var(--color-text-primary)] mt-1 uppercase tracking-wider">{selectedRole.scope}</p>
            </div>

            <div className="bg-[var(--color-surface)] border border-[var(--color-border)] p-4 rounded-xl shadow-xs">
              <p className="text-xs font-bold text-[var(--color-text-muted)] uppercase tracking-wider">Assigned Accounts</p>
              <p className="text-lg font-bold text-emerald-700 dark:text-emerald-400 mt-1">{selectedRole.user_count} User(s)</p>
            </div>

            <div className="bg-[var(--color-surface)] border border-[var(--color-border)] p-4 rounded-xl shadow-xs">
              <p className="text-xs font-bold text-[var(--color-text-muted)] uppercase tracking-wider">Atomic Permissions</p>
              <p className="text-lg font-bold text-purple-700 dark:text-purple-400 mt-1">{selectedRole.permissions.length} Granted</p>
            </div>

            <div className="bg-[var(--color-surface)] border border-[var(--color-border)] p-4 rounded-xl shadow-xs">
              <p className="text-xs font-bold text-[var(--color-text-muted)] uppercase tracking-wider">Hierarchy Rank</p>
              <p className="text-lg font-bold text-blue-700 dark:text-blue-400 mt-1">Level {getRolePriority(selectedRole.code) + 1}</p>
            </div>
          </div>

          {/* Navigation Tabs */}
          <div className="flex items-center gap-2 border-b border-[var(--color-border)] pb-2 overflow-x-auto">
            <button
              onClick={() => setActiveTab("explorer")}
              className={`px-4 py-2 rounded-lg text-xs font-bold transition-all flex items-center gap-2 cursor-pointer ${
                activeTab === "explorer"
                  ? "bg-[#008A5E] text-white shadow-xs"
                  : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-subtle)]"
              }`}
            >
              <Key size={14} /> Permission Explorer ({selectedRole.permissions.length})
            </button>

            <button
              onClick={() => setActiveTab("users")}
              className={`px-4 py-2 rounded-lg text-xs font-bold transition-all flex items-center gap-2 cursor-pointer ${
                activeTab === "users"
                  ? "bg-[#008A5E] text-white shadow-xs"
                  : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-subtle)]"
              }`}
            >
              <Users size={14} /> Assigned Users ({filteredAssignedUsers.length})
            </button>

            <button
              onClick={() => setActiveTab("scopes")}
              className={`px-4 py-2 rounded-lg text-xs font-bold transition-all flex items-center gap-2 cursor-pointer ${
                activeTab === "scopes"
                  ? "bg-[#008A5E] text-white shadow-xs"
                  : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-subtle)]"
              }`}
            >
              <Layers size={14} /> Scope & Hierarchy Tree
            </button>

            <button
              onClick={() => setActiveTab("audit")}
              className={`px-4 py-2 rounded-lg text-xs font-bold transition-all flex items-center gap-2 cursor-pointer ${
                activeTab === "audit"
                  ? "bg-[#008A5E] text-white shadow-xs"
                  : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-subtle)]"
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
                  <div key={category} className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-5 space-y-3 shadow-xs">
                    <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-3">
                      <h3 className="text-xs font-black uppercase tracking-wider text-emerald-800 dark:text-emerald-300 flex items-center gap-2">
                        <ShieldCheck size={16} /> {category} Category ({items.length} Permissions)
                      </h3>
                      <span className="text-[10px] font-mono text-[var(--color-text-muted)] font-bold">Metadata Verified</span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {items.map(({ code, meta }) => {
                        const isExpanded = expandedPerm === code;
                        return (
                          <div
                            key={code}
                            className="bg-[var(--color-surface-subtle)] border border-[var(--color-border)] rounded-lg p-3 space-y-2 hover:border-[var(--color-border-hover)] transition-colors shadow-xs"
                          >
                            <div
                              onClick={() => setExpandedPerm(isExpanded ? null : code)}
                              className="flex items-center justify-between cursor-pointer"
                            >
                              <div className="flex items-center gap-2">
                                <Key size={14} className="text-[#008A5E]" />
                                <span className="text-xs font-mono font-bold text-[var(--color-text-primary)]">{code}</span>
                              </div>
                              <div className="flex items-center gap-2">
                                <span className="text-[9px] font-mono font-bold px-2 py-0.5 rounded bg-blue-100 dark:bg-blue-950/60 text-blue-800 dark:text-blue-300 border border-blue-300 dark:border-blue-700">
                                  {meta.scope}
                                </span>
                                {isExpanded ? (
                                  <ChevronDown size={14} className="text-[var(--color-text-secondary)]" />
                                ) : (
                                  <ChevronRight size={14} className="text-[var(--color-text-secondary)]" />
                                )}
                              </div>
                            </div>

                            {/* Detailed Metadata View */}
                            {isExpanded && (
                              <div className="pt-3 border-t border-[var(--color-border)] space-y-2.5 text-[11px] animate-fade-in">
                                <div>
                                  <p className="text-[10px] text-[var(--color-text-secondary)] font-bold">Dependencies:</p>
                                  {meta.dependencies.length > 0 ? (
                                    <div className="flex flex-wrap gap-1 mt-1">
                                      {meta.dependencies.map((dep: string) => (
                                        <span key={dep} className="px-2 py-0.5 text-[9px] font-mono rounded bg-amber-100 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-700 font-bold">
                                          requires {dep}
                                        </span>
                                      ))}
                                    </div>
                                  ) : (
                                    <span className="text-[10px] text-[var(--color-text-muted)]">None (Atomic Primary)</span>
                                  )}
                                </div>

                                <div>
                                  <p className="text-[10px] text-[var(--color-text-secondary)] font-bold">Affected UI Modules:</p>
                                  <div className="flex flex-wrap gap-1 mt-1">
                                    {meta.uiModules.map((mod: string) => (
                                      <span key={mod} className="px-2 py-0.5 text-[9px] font-mono rounded bg-purple-100 dark:bg-purple-950/60 text-purple-800 dark:text-purple-300 border border-purple-300 dark:border-purple-700 font-bold">
                                        {mod}
                                      </span>
                                    ))}
                                  </div>
                                </div>

                                <div>
                                  <p className="text-[10px] text-[var(--color-text-secondary)] font-bold">Backend API Endpoints:</p>
                                  <div className="flex flex-wrap gap-1 mt-1">
                                    {meta.apiEndpoints.map((ep: string) => (
                                      <span key={ep} className="px-2 py-0.5 text-[9px] font-mono rounded bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700 font-bold">
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
                <div className="py-12 text-center text-[var(--color-text-muted)] bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl text-xs font-medium">
                  No atomic permissions assigned to this role.
                </div>
              )}
            </div>
          )}

          {/* Tab 2: Assigned Users Directory & Organization Governance */}
          {activeTab === "users" && (
            <div className="bg-[var(--color-surface)] border border-[var(--color-border)] p-5 rounded-xl space-y-4 shadow-xs">
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-[var(--color-border)] pb-4">
                <div>
                  <h2 className="text-base font-black text-[var(--color-text-primary)] flex items-center gap-2">
                    <Users size={18} className="text-[#008A5E]" />
                    {selectedRole ? `Accounts Provisioned with Role: ${selectedRole.name}` : "Organization Accounts & Assigned Roles"}
                  </h2>
                  <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
                    Inspect and edit roles, organization workspace boundaries, and IAM governance for all platform accounts.
                  </p>
                </div>

                {/* Filters for Organization & Role */}
                <div className="flex flex-wrap items-center gap-2">
                  <div className="flex items-center gap-1.5 bg-[var(--color-surface)] border border-[var(--color-border)] px-3 py-1.5 rounded-lg text-xs shadow-xs">
                    <Filter size={12} className="text-[var(--color-text-muted)]" />
                    <span className="text-[var(--color-text-secondary)] text-[10px] font-bold uppercase">Org:</span>
                    <select
                      value={selectedOrgFilter}
                      onChange={e => setSelectedOrgFilter(e.target.value)}
                      className="bg-transparent text-[var(--color-text-primary)] text-xs font-semibold focus:outline-none cursor-pointer"
                    >
                      <option value="ALL" className="bg-[var(--color-surface)] text-[var(--color-text-primary)]">All Organizations ({organizations.length})</option>
                      <option value="SYSTEM_DEFAULT" className="bg-[var(--color-surface)] text-[var(--color-text-primary)]">System Default (Platform Global)</option>
                      {organizations.map(o => (
                        <option key={o.id} value={o.id} className="bg-[var(--color-surface)] text-[var(--color-text-primary)]">{o.name}</option>
                      ))}
                    </select>
                  </div>

                  {!selectedRole && (
                    <div className="flex items-center gap-1.5 bg-[var(--color-surface)] border border-[var(--color-border)] px-3 py-1.5 rounded-lg text-xs shadow-xs">
                      <Shield size={12} className="text-[var(--color-text-muted)]" />
                      <span className="text-[var(--color-text-secondary)] text-[10px] font-bold uppercase">Role:</span>
                      <select
                        value={selectedRoleFilter}
                        onChange={e => setSelectedRoleFilter(e.target.value)}
                        className="bg-transparent text-[var(--color-text-primary)] text-xs font-semibold focus:outline-none cursor-pointer"
                      >
                        <option value="ALL" className="bg-[var(--color-surface)] text-[var(--color-text-primary)]">All Roles</option>
                        {roles.map(r => (
                          <option key={r.code} value={r.code} className="bg-[var(--color-surface)] text-[var(--color-text-primary)]">{r.name} ({r.code})</option>
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
                        <div className="font-bold text-[var(--color-text-primary)] text-xs">{row.full_name}</div>
                        <div className="text-[11px] text-[var(--color-text-secondary)] font-mono">{row.email}</div>
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
                          rUpper === "SUPER_ADMIN" ? "bg-purple-100 dark:bg-purple-950/60 border-purple-300 dark:border-purple-700 text-purple-800 dark:text-purple-300" :
                          (rUpper === "ORG_ADMIN" || rUpper === "ADMIN") ? "bg-blue-100 dark:bg-blue-950/60 border-blue-300 dark:border-blue-700 text-blue-800 dark:text-blue-300" :
                          (rUpper === "AUDITOR" || rUpper === "VVB" || rUpper === "VERIFIER") ? "bg-amber-100 dark:bg-amber-950/60 border-amber-300 dark:border-amber-700 text-amber-800 dark:text-amber-300" :
                          (rUpper === "FIELD_AGENT" || rUpper === "FIELD_SUPERVISOR") ? "bg-emerald-100 dark:bg-emerald-950/60 border-emerald-300 dark:border-emerald-700 text-emerald-800 dark:text-emerald-300" :
                          (rUpper.includes("MANAGER") || rUpper.includes("PROJECT") || rUpper.includes("PORTFOLIO")) ? "bg-cyan-100 dark:bg-cyan-950/60 border-cyan-300 dark:border-cyan-700 text-cyan-800 dark:text-cyan-300" :
                          "bg-[var(--color-surface-subtle)] border-[var(--color-border)] text-[var(--color-text-secondary)]"
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
                        return <span className="text-[var(--color-text-muted)] font-mono text-[11px] font-semibold">System Default (Platform Global)</span>;
                      }

                      return (
                        <div className="flex flex-col items-start gap-1">
                          <span className="text-[var(--color-text-primary)] font-semibold text-xs">{orgName}</span>
                          {sectors.length > 0 && (
                            <div className="flex flex-wrap gap-1">
                              {sectors.map(sec => (
                                <span key={sec} className="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700">
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
                        row.status === "suspended" ? "bg-red-100 dark:bg-red-950/60 text-red-800 dark:text-red-300 border border-red-300 dark:border-red-700" : "bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700"
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
                          className="px-2.5 py-1 rounded bg-blue-50 hover:bg-blue-600 hover:text-white text-blue-700 border border-blue-300 text-[11px] font-bold flex items-center gap-1 transition-colors cursor-pointer shadow-xs"
                          title="Edit User Role & Organization"
                        >
                          <Edit3 size={12} /> Edit Role
                        </button>
                        <button
                          onClick={() => handleResetPassword(row)}
                          className="p-1.5 rounded bg-[var(--color-surface)] hover:bg-[var(--color-surface-subtle)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] border border-[var(--color-border)] text-xs transition-colors cursor-pointer shadow-xs"
                          title="Reset User Password"
                        >
                          <Key size={12} />
                        </button>
                        <button
                          onClick={() => handleSuspendToggle(row)}
                          className={`p-1.5 rounded text-xs transition-colors border font-bold cursor-pointer shadow-xs ${
                            row.status === "suspended"
                              ? "bg-emerald-50 hover:bg-emerald-600 hover:text-white text-emerald-800 border-emerald-300"
                              : "bg-red-50 hover:bg-red-600 hover:text-white text-red-700 border-red-300"
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
            <div className="bg-[var(--color-surface)] border border-[var(--color-border)] p-6 rounded-xl space-y-6 shadow-xs">
              <h3 className="text-sm font-bold text-[var(--color-text-primary)] uppercase tracking-wider">Enterprise Scope Cascading Graph</h3>
              <p className="text-xs text-[var(--color-text-secondary)]">
                Visual representation of permission inheritance and organizational scoping boundary for {selectedRole.name}.
              </p>

              <div className="flex flex-col md:flex-row items-center justify-between gap-2 overflow-x-auto py-6 px-4 bg-[var(--color-surface-subtle)] border border-[var(--color-border)] rounded-xl">
                {SCOPE_HIERARCHY.map((sc, idx) => {
                  const isActive = selectedRole.scope === sc;
                  return (
                    <React.Fragment key={sc}>
                      <div
                        className={`p-4 rounded-xl border text-center transition-all min-w-[130px] shadow-xs ${
                          isActive
                            ? "bg-[#008A5E] border-[#008A5E] text-white font-bold"
                            : "bg-[var(--color-surface)] border-[var(--color-border)] text-[var(--color-text-muted)]"
                        }`}
                      >
                        <span className="text-[10px] font-mono font-bold block opacity-90">LEVEL {idx + 1}</span>
                        <span className="text-xs font-black uppercase mt-1 block">{sc}</span>
                        {isActive && (
                          <span className="mt-2 inline-block text-[9px] font-bold px-2 py-0.5 rounded bg-white text-[#008A5E]">
                            ACTIVE SCOPE
                          </span>
                        )}
                      </div>
                      {idx < SCOPE_HIERARCHY.length - 1 && (
                        <ChevronRight size={18} className="text-[var(--color-text-muted)] shrink-0 hidden md:block" />
                      )}
                    </React.Fragment>
                  );
                })}
              </div>
            </div>
          )}

          {/* Tab 4: Audit History */}
          {activeTab === "audit" && (
            <div className="bg-[var(--color-surface)] border border-[var(--color-border)] p-5 rounded-xl space-y-3 shadow-xs">
              <h3 className="text-sm font-bold text-[var(--color-text-primary)] uppercase tracking-wider">Role Governance Audit Trail</h3>
              <p className="text-xs text-[var(--color-text-secondary)]">Immutable audit log of updates to role permissions, assignments, and scopes.</p>

              <div className="divide-y divide-[var(--color-border)] text-xs font-mono">
                <div className="py-3 flex items-center justify-between">
                  <div>
                    <span className="text-[var(--color-text-primary)] font-bold">[SYSTEM_INITIALIZATION]</span> Role seeded with standard RBAC policy
                    <p className="text-[10px] text-[var(--color-text-muted)] mt-0.5">By Super Admin (system_auto) • 2026-08-06 04:02:08 UTC</p>
                  </div>
                  <span className="px-2 py-0.5 rounded text-[9px] bg-purple-100 dark:bg-purple-950/60 text-purple-800 dark:text-purple-300 border border-purple-300 dark:border-purple-700 font-bold">
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
          <div className="flex items-center justify-between bg-[var(--color-surface)] border border-[var(--color-border)] p-4 rounded-xl shadow-xs">
            <div className="flex items-center gap-3">
              <button
                onClick={() => setIsCompareMode(false)}
                className="p-2 rounded-lg bg-[var(--color-surface-subtle)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface)] border border-[var(--color-border)] transition-colors cursor-pointer shadow-xs"
              >
                <ArrowLeft size={16} />
              </button>
              <div>
                <h1 className="text-lg font-bold text-[var(--color-text-primary)]">Role Permission Comparison Engine</h1>
                <p className="text-xs text-[var(--color-text-secondary)]">Side-by-side comparative analysis of permissions, scopes, and user counts.</p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 bg-[var(--color-surface)] border border-[var(--color-border)] p-5 rounded-xl shadow-xs">
            <div>
              <label className="text-xs font-bold text-[var(--color-text-secondary)] block mb-2">Select Primary Role A:</label>
              <select
                value={compareRoleA}
                onChange={e => setCompareRoleA(e.target.value)}
                className="w-full p-2.5 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] focus:border-[#008A5E] text-xs text-[var(--color-text-primary)] font-semibold cursor-pointer shadow-xs"
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
              <label className="text-xs font-bold text-[var(--color-text-secondary)] block mb-2">Select Target Role B:</label>
              <select
                value={compareRoleB}
                onChange={e => setCompareRoleB(e.target.value)}
                className="w-full p-2.5 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] focus:border-[#008A5E] text-xs text-[var(--color-text-primary)] font-semibold cursor-pointer shadow-xs"
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
                <div className="bg-[var(--color-surface)] border border-[var(--color-border)] p-4 rounded-xl text-center shadow-xs">
                  <p className="text-xs font-bold text-emerald-800 dark:text-emerald-300 uppercase">Common Permissions</p>
                  <p className="text-2xl font-black text-[var(--color-text-primary)] mt-1">{comparisonData.common.length}</p>
                </div>
                <div className="bg-[var(--color-surface)] border border-[var(--color-border)] p-4 rounded-xl text-center shadow-xs">
                  <p className="text-xs font-bold text-blue-800 dark:text-blue-300 uppercase">Unique to {comparisonData.roleA.name}</p>
                  <p className="text-2xl font-black text-[var(--color-text-primary)] mt-1">{comparisonData.uniqueA.length}</p>
                </div>
                <div className="bg-[var(--color-surface)] border border-[var(--color-border)] p-4 rounded-xl text-center shadow-xs">
                  <p className="text-xs font-bold text-purple-800 dark:text-purple-300 uppercase">Unique to {comparisonData.roleB.name}</p>
                  <p className="text-2xl font-black text-[var(--color-text-primary)] mt-1">{comparisonData.uniqueB.length}</p>
                </div>
              </div>

              {/* Side-by-side lists */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-[var(--color-surface)] border border-[var(--color-border)] p-5 rounded-xl space-y-3 shadow-xs">
                  <h3 className="text-xs font-bold text-blue-800 dark:text-blue-300 uppercase tracking-wider">{comparisonData.roleA.name} Permissions</h3>
                  <div className="space-y-1.5">
                    {comparisonData.roleA.permissions.map(p => {
                      const isCommon = comparisonData.common.includes(p);
                      return (
                        <div
                          key={p}
                          className={`p-2 rounded text-xs font-mono flex items-center justify-between ${
                            isCommon ? "bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700" : "bg-blue-100 dark:bg-blue-950/60 text-blue-800 dark:text-blue-300 border border-blue-300 dark:border-blue-700"
                          }`}
                        >
                          <span className="font-semibold">{p}</span>
                          <span className="text-[9px] font-bold">{isCommon ? "MATCHING" : "UNIQUE"}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>

                <div className="bg-[var(--color-surface)] border border-[var(--color-border)] p-5 rounded-xl space-y-3 shadow-xs">
                  <h3 className="text-xs font-bold text-purple-800 dark:text-purple-300 uppercase tracking-wider">{comparisonData.roleB.name} Permissions</h3>
                  <div className="space-y-1.5">
                    {comparisonData.roleB.permissions.map(p => {
                      const isCommon = comparisonData.common.includes(p);
                      return (
                        <div
                          key={p}
                          className={`p-2 rounded text-xs font-mono flex items-center justify-between ${
                            isCommon ? "bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700" : "bg-purple-100 dark:bg-purple-950/60 text-purple-800 dark:text-purple-300 border border-purple-300 dark:border-purple-700"
                          }`}
                        >
                          <span className="font-semibold">{p}</span>
                          <span className="text-[9px] font-bold">{isCommon ? "MATCHING" : "UNIQUE"}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="py-12 text-center text-[var(--color-text-muted)] bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl text-xs font-medium">
              Select two roles above to run permission delta comparison.
            </div>
          )}
        </div>
      ) : selectedOrgId && selectedOrg ? (
        /* ORGANISATION-SCOPED GOVERNANCE VIEW */
        <div className="space-y-6 animate-fade-in">
          {/* Header Banner */}
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] p-5 rounded-xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-xs">
            <div>
              <div className="flex flex-wrap items-center gap-3">
                {isSuperAdmin && (
                  <button
                    onClick={() => setSelectedOrgId(null)}
                    className="p-2 rounded-lg bg-[var(--color-surface-subtle)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface)] border border-[var(--color-border)] transition-colors flex items-center gap-1.5 text-xs font-bold cursor-pointer shadow-xs"
                    title="Return to Platform Governance"
                  >
                    <ArrowLeft size={16} /> Platform Governance
                  </button>
                )}
                <div className="flex items-center gap-2">
                  <Building2 size={20} className="text-[#008A5E]" />
                  <h1 className="text-xl font-black text-[var(--color-text-primary)]">{selectedOrg.name}</h1>
                  <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700">
                    {selectedOrg.status || "ACTIVE"}
                  </span>
                  <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-blue-100 dark:bg-blue-950/60 text-blue-800 dark:text-blue-300 border border-blue-300 dark:border-blue-700">
                    {selectedOrg.org_type || "DEVELOPER"}
                  </span>
                </div>
              </div>
              <p className="text-xs text-[var(--color-text-secondary)] mt-1">
                Organisation-scoped role & account governance context for {selectedOrg.name}.
              </p>
            </div>

            {/* Quick Metrics */}
            <div className="flex items-center gap-3">
              <div className="bg-[var(--color-surface-subtle)] border border-[var(--color-border)] px-3.5 py-2 rounded-lg text-center shadow-xs">
                <span className="text-[10px] font-mono text-[var(--color-text-muted)] font-bold block uppercase">Accounts</span>
                <span className="text-sm font-black text-[var(--color-text-primary)]">
                  {users.filter(u => u.organization_id === selectedOrg.id || u.organization === selectedOrg.name || u.organization_name === selectedOrg.name).length}
                </span>
              </div>
              <div className="bg-[var(--color-surface-subtle)] border border-[var(--color-border)] px-3.5 py-2 rounded-lg text-center shadow-xs">
                <span className="text-[10px] font-mono text-[var(--color-text-muted)] font-bold block uppercase">Org Roles</span>
                <span className="text-sm font-black text-emerald-800 dark:text-emerald-300">{organizationRoles.length}</span>
              </div>
            </div>
          </div>

          {/* Sub-Navigation Tabs */}
          <div className="flex items-center gap-2 border-b border-[var(--color-border)] pb-2 text-xs font-bold overflow-x-auto">
            <button
              onClick={() => setOrgSubTab("overview")}
              className={`px-4 py-2 rounded-lg flex items-center gap-2 transition-all cursor-pointer ${
                orgSubTab === "overview"
                  ? "bg-[#008A5E] text-white shadow-xs"
                  : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-subtle)]"
              }`}
            >
              <Info size={14} /> Overview
            </button>
            <button
              onClick={() => setOrgSubTab("roles")}
              className={`px-4 py-2 rounded-lg flex items-center gap-2 transition-all cursor-pointer ${
                orgSubTab === "roles"
                  ? "bg-[#008A5E] text-white shadow-xs"
                  : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-subtle)]"
              }`}
            >
              <Shield size={14} /> Roles & Permissions ({organizationRoles.length})
            </button>
            <button
              onClick={() => setOrgSubTab("users")}
              className={`px-4 py-2 rounded-lg flex items-center gap-2 transition-all cursor-pointer ${
                orgSubTab === "users"
                  ? "bg-[#008A5E] text-white shadow-xs"
                  : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-subtle)]"
              }`}
            >
              <Users size={14} /> Users & Accounts (
              {users.filter(u => u.organization_id === selectedOrg.id || u.organization === selectedOrg.name || u.organization_name === selectedOrg.name).length}
              )
            </button>
            <button
              onClick={() => setOrgSubTab("projects")}
              className={`px-4 py-2 rounded-lg flex items-center gap-2 transition-all cursor-pointer ${
                orgSubTab === "projects"
                  ? "bg-[#008A5E] text-white shadow-xs"
                  : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-subtle)]"
              }`}
            >
              <FolderKanban size={14} /> Projects ({orgProjects.length})
            </button>
            <button
              onClick={() => setOrgSubTab("audit")}
              className={`px-4 py-2 rounded-lg flex items-center gap-2 transition-all cursor-pointer ${
                orgSubTab === "audit"
                  ? "bg-[#008A5E] text-white shadow-xs"
                  : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-subtle)]"
              }`}
            >
              <History size={14} /> Security Audit Trail
            </button>
          </div>

          {/* Sub-Tab 0: Organisation Overview */}
          {orgSubTab === "overview" && (
            <div className="space-y-6">
              {/* Summary Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="bg-[var(--color-surface)] border border-[var(--color-border)] p-4 rounded-xl shadow-xs">
                  <p className="text-xs text-[var(--color-text-muted)] font-bold uppercase tracking-wider">Organisation Administrator</p>
                  <p className="text-sm font-black text-[var(--color-text-primary)] mt-1">
                    {users.find(u => (u.organization_id === selectedOrg.id || u.organization === selectedOrg.name) && (u.role === "ORG_ADMIN" || u.role === "admin" || u.role === "ORG_OWNER"))?.full_name || "Unassigned"}
                  </p>
                  <p className="text-[11px] text-[var(--color-text-secondary)] font-mono">
                    {users.find(u => (u.organization_id === selectedOrg.id || u.organization === selectedOrg.name) && (u.role === "ORG_ADMIN" || u.role === "admin" || u.role === "ORG_OWNER"))?.email || "N/A"}
                  </p>
                </div>
                <div className="bg-[var(--color-surface)] border border-[var(--color-border)] p-4 rounded-xl shadow-xs">
                  <p className="text-xs text-[var(--color-text-muted)] font-bold uppercase tracking-wider">Active Accounts</p>
                  <p className="text-xl font-black text-emerald-800 dark:text-emerald-300 mt-1">
                    {users.filter(u => u.organization_id === selectedOrg.id || u.organization === selectedOrg.name || u.organization_name === selectedOrg.name).length} Users
                  </p>
                </div>
                <div className="bg-[var(--color-surface)] border border-[var(--color-border)] p-4 rounded-xl shadow-xs">
                  <p className="text-xs text-[var(--color-text-muted)] font-bold uppercase tracking-wider">Registered Projects</p>
                  <p className="text-xl font-black text-blue-800 dark:text-blue-300 mt-1">{orgProjects.length} Projects</p>
                </div>
                <div className="bg-[var(--color-surface)] border border-[var(--color-border)] p-4 rounded-xl shadow-xs">
                  <p className="text-xs text-[var(--color-text-muted)] font-bold uppercase tracking-wider">Active Sectors</p>
                  <p className="text-xl font-black text-purple-800 dark:text-purple-300 mt-1">{activeOrgSectors.length} Sectors</p>
                </div>
              </div>

              {/* Dynamic Active Sectors Breakdown */}
              <div className="bg-[var(--color-surface)] border border-[var(--color-border)] p-5 rounded-xl space-y-4 shadow-xs">
                <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-3">
                  <div>
                    <h3 className="text-sm font-bold text-[var(--color-text-primary)] uppercase tracking-wider flex items-center gap-2">
                      <Globe size={16} className="text-[#008A5E]" /> Active Sectors & Climate Portfolios
                    </h3>
                    <p className="text-xs text-[var(--color-text-secondary)]">
                      Sectors dynamically derived from {selectedOrg.name}'s project licensing and operational assets.
                    </p>
                  </div>
                </div>

                {activeOrgSectors.length > 0 ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {activeOrgSectors.map(sec => (
                      <div key={sec.code} className="bg-[var(--color-surface-subtle)] border border-[var(--color-border)] p-4 rounded-xl space-y-2 shadow-xs">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-[var(--color-text-primary)] text-xs">{sec.name}</span>
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700 font-bold">
                            {sec.projectCount} Project(s)
                          </span>
                        </div>
                        <p className="text-[11px] text-[var(--color-text-secondary)]">
                          Operates active MRV and quantification protocols under sector code <code className="text-[#008A5E] font-bold">{sec.code}</code>.
                        </p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="py-8 text-center text-[var(--color-text-muted)] text-xs bg-[var(--color-surface-subtle)] rounded-lg">
                    No active sectors currently configured for this organisation.
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Sub-Tab 1: Roles & Permissions for this Organization */}
          {orgSubTab === "roles" && (
            <div className="space-y-4">
              <div className="bg-[var(--color-surface)] border border-[var(--color-border)] p-4 rounded-xl flex items-center justify-between shadow-xs">
                <div>
                  <h3 className="text-sm font-bold text-[var(--color-text-primary)] uppercase tracking-wider">
                    {selectedOrg.name} — Organisation Roles
                  </h3>
                  <p className="text-xs text-[var(--color-text-secondary)]">
                    Roles available for assignment to accounts belonging to {selectedOrg.name}.
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {organizationRoles.map(r => {
                  const countInOrg = users.filter(
                    u =>
                      (u.organization_id === selectedOrg.id || u.organization === selectedOrg.name || u.organization_name === selectedOrg.name) &&
                      u.role.toUpperCase() === r.code.toUpperCase()
                  ).length;

                  return (
                    <div
                      key={r.code}
                      onClick={() => setSelectedRole(r)}
                      className="bg-[var(--color-surface)] border border-[var(--color-border)] hover:border-[var(--color-border-hover)] rounded-xl p-5 space-y-4 cursor-pointer transition-all duration-200 hover:shadow-md group shadow-xs"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Shield className="size-4 text-[#008A5E] group-hover:scale-110 transition-transform" />
                          <span className="text-xs font-black text-[var(--color-text-primary)] uppercase tracking-wider group-hover:text-[#008A5E] transition-colors">
                            {r.name}
                          </span>
                        </div>
                        <span className="text-[9px] font-mono font-bold px-2 py-0.5 rounded bg-blue-100 dark:bg-blue-950/60 border border-blue-300 dark:border-blue-700 text-blue-800 dark:text-blue-300 uppercase">
                          {r.scope}
                        </span>
                      </div>

                      <p className="text-[11px] text-[var(--color-text-secondary)] leading-relaxed line-clamp-2">{r.description}</p>

                      <div className="flex items-center justify-between border-t border-[var(--color-border)] pt-3 text-[10px] font-mono text-[var(--color-text-secondary)]">
                        <span className="flex items-center gap-1">
                          <Key size={12} className="text-purple-700 dark:text-purple-400" />
                          Permissions: <strong className="text-[var(--color-text-primary)]">{r.permissions?.length || 0}</strong>
                        </span>
                        <span className="flex items-center gap-1">
                          <Users size={12} className="text-emerald-700 dark:text-emerald-400" />
                          In {selectedOrg.name}: <strong className="text-emerald-800 dark:text-emerald-300">{countInOrg} Account(s)</strong>
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Sub-Tab 2: Users & Accounts for this Organization */}
          {orgSubTab === "users" && (
            <div className="bg-[var(--color-surface)] border border-[var(--color-border)] p-5 rounded-xl space-y-4 shadow-xs">
              <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-4">
                <div>
                  <h2 className="text-base font-black text-[var(--color-text-primary)] flex items-center gap-2">
                    <Users size={18} className="text-[#008A5E]" />
                    {selectedOrg.name} — Accounts Directory
                  </h2>
                  <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
                    Accounts linked to {selectedOrg.name}. Roles and status permissions are isolated to this tenant.
                  </p>
                </div>
              </div>

              <DataTable
                title={`Accounts (${users.filter(u => u.organization_id === selectedOrg.id || u.organization === selectedOrg.name || u.organization_name === selectedOrg.name).length})`}
                subtitle={`Accounts belonging to ${selectedOrg.name}`}
                columns={[
                  {
                    key: "full_name",
                    label: "User / Email",
                    sortable: true,
                    render: (row: UserItem) => (
                      <div>
                        <div className="font-bold text-[var(--color-text-primary)] text-xs">{row.full_name}</div>
                        <div className="text-[11px] text-[var(--color-text-secondary)] font-mono">{row.email}</div>
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
                        <span className="text-[10px] font-mono font-bold uppercase px-2.5 py-1 rounded border bg-blue-100 dark:bg-blue-950/60 border-blue-300 dark:border-blue-700 text-blue-800 dark:text-blue-300">
                          {rUpper === "ADMIN" ? "ORG_ADMIN" : rUpper}
                        </span>
                      );
                    }
                  },
                  {
                    key: "status",
                    label: "Status",
                    sortable: true,
                    render: (row: UserItem) => (
                      <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                        row.status === "suspended" ? "bg-red-100 dark:bg-red-950/60 text-red-800 dark:text-red-300 border border-red-300 dark:border-red-700" : "bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700"
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
                          onClick={() => setInspectingUser(row)}
                          className="px-2.5 py-1 rounded bg-[var(--color-surface)] hover:bg-[var(--color-surface-subtle)] text-[var(--color-text-primary)] border border-[var(--color-border)] text-[11px] font-bold flex items-center gap-1 transition-colors cursor-pointer shadow-xs"
                          title="Inspect Account Hierarchy & Traceability"
                        >
                          <Info size={12} className="text-[#008A5E]" /> Inspect
                        </button>
                        <button
                          onClick={() => handleOpenEditUser(row)}
                          className="px-2.5 py-1 rounded bg-blue-50 hover:bg-blue-600 hover:text-white text-blue-700 border border-blue-300 text-[11px] font-bold flex items-center gap-1 transition-colors cursor-pointer shadow-xs"
                        >
                          <Edit3 size={12} /> Edit Role
                        </button>
                        {isSuperAdmin && (
                          <button
                            onClick={() => {
                              setCustomResetUser(row);
                              setCustomNewPassword("");
                            }}
                            className="px-2.5 py-1 rounded bg-purple-50 hover:bg-purple-600 hover:text-white text-purple-700 border border-purple-300 text-[11px] font-bold flex items-center gap-1 transition-colors cursor-pointer shadow-xs"
                            title="Super Admin Secure Password Reset"
                          >
                            <Key size={12} /> Reset Password
                          </button>
                        )}
                        <button
                          onClick={() => handleSuspendToggle(row)}
                          className={`px-2.5 py-1 rounded text-[11px] font-bold border transition-colors cursor-pointer shadow-xs ${
                            row.status === "suspended"
                              ? "bg-emerald-50 hover:bg-emerald-600 hover:text-white text-emerald-800 border-emerald-300"
                              : "bg-amber-50 hover:bg-amber-600 hover:text-white text-amber-800 border-amber-300"
                          }`}
                        >
                          {row.status === "suspended" ? "Reactivate" : "Suspend"}
                        </button>
                      </div>
                    )
                  }
                ]}
                data={users.filter(u => u.organization_id === selectedOrg.id || u.organization === selectedOrg.name || u.organization_name === selectedOrg.name)}
                searchKeys={["email", "full_name"]}
                searchPlaceholder="Filter account email or name..."
              />
            </div>
          )}

          {/* Sub-Tab 3: Projects & Access */}
          {orgSubTab === "projects" && (
            <div className="bg-[var(--color-surface)] border border-[var(--color-border)] p-5 rounded-xl space-y-4 shadow-xs">
              <h3 className="text-sm font-bold text-[var(--color-text-primary)] uppercase tracking-wider flex items-center gap-2">
                <FolderKanban size={16} className="text-blue-700 dark:text-blue-400" />
                Projects Registered under {selectedOrg.name}
              </h3>
              {orgProjects.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {orgProjects.map(p => (
                    <div key={p.id} className="p-4 rounded-lg bg-[var(--color-surface-subtle)] border border-[var(--color-border)] space-y-1 shadow-xs">
                      <p className="font-bold text-[var(--color-text-primary)] text-xs">{p.name}</p>
                      <p className="text-[11px] text-[var(--color-text-secondary)] font-mono">Sector: {p.sector || "GENERAL"}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="py-8 text-center text-[var(--color-text-muted)] text-xs bg-[var(--color-surface-subtle)] rounded-lg">
                  No projects currently registered under this organisation.
                </div>
              )}
            </div>
          )}

          {/* Sub-Tab 4: Security Audit Trail */}
          {orgSubTab === "audit" && (
            <div className="bg-[var(--color-surface)] border border-[var(--color-border)] p-5 rounded-xl space-y-3 shadow-xs">
              <h3 className="text-sm font-bold text-[var(--color-text-primary)] uppercase tracking-wider flex items-center gap-2">
                <History size={16} className="text-purple-700 dark:text-purple-400" />
                Security Audit Trail for {selectedOrg.name}
              </h3>
              <p className="text-xs text-[var(--color-text-secondary)]">Actual audit log events recorded for this organisation's accounts and roles.</p>

              {auditLogs.filter(l => l.organization_id === selectedOrg.id || !l.organization_id).length > 0 ? (
                <div className="divide-y divide-[var(--color-border)] text-xs font-mono">
                  {auditLogs
                    .filter(l => l.organization_id === selectedOrg.id || !l.organization_id)
                    .map((log, idx) => (
                      <div key={log.id || idx} className="py-3 flex items-center justify-between">
                        <div>
                          <span className="text-[var(--color-text-primary)] font-bold">[{log.action}]</span> {log.result || "SUCCESS"}
                          <p className="text-[10px] text-[var(--color-text-muted)] mt-0.5">
                            Actor: {log.actor_user_id || "System"} • {log.created_at || "Recent"}
                          </p>
                        </div>
                        <span className="px-2 py-0.5 rounded text-[9px] bg-purple-100 dark:bg-purple-950/60 text-purple-800 dark:text-purple-300 border border-purple-300 dark:border-purple-700 font-bold">
                          {log.action}
                        </span>
                      </div>
                    ))}
                </div>
              ) : (
                <div className="py-8 text-center text-[var(--color-text-muted)] text-xs bg-[var(--color-surface-subtle)] rounded-lg">
                  No audit activity recorded for this organisation.
                </div>
              )}
            </div>
          )}
        </div>
      ) : (
        /* Primary Platform Governance & Organisations Hierarchy View */
        <div className="space-y-6">
          {/* Header & Controls Toolbar */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-bold text-[var(--color-text-primary)]">Platform Governance & Organisations Hierarchy</h2>
              <p className="text-xs text-[var(--color-text-secondary)]">
                Hierarchical governance separating Platform-level roles from Organisation-scoped roles and user accounts.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setIsCompareMode(true)}
                className="px-3.5 py-2 rounded-lg bg-[var(--color-surface)] hover:bg-[var(--color-surface-subtle)] border border-[var(--color-border)] text-xs font-bold text-[var(--color-text-primary)] flex items-center gap-1.5 transition-colors cursor-pointer shadow-xs"
              >
                <GitCompare size={14} className="text-[#008A5E]" /> Compare Roles
              </button>

              <button
                onClick={handleExportCSV}
                className="px-3.5 py-2 rounded-lg bg-[var(--color-surface)] hover:bg-[var(--color-surface-subtle)] border border-[var(--color-border)] text-xs font-bold text-[var(--color-text-primary)] flex items-center gap-1.5 transition-colors cursor-pointer shadow-xs"
              >
                <Download size={14} className="text-blue-700 dark:text-blue-400" /> Export CSV
              </button>
            </div>
          </div>

          {/* Platform Core Roles Section */}
          <div className="bg-[var(--color-surface)] border border-purple-300 dark:border-purple-700/60 rounded-xl p-5 space-y-3 shadow-xs">
            <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-2">
              <div className="flex items-center gap-2">
                <ShieldCheck size={18} className="text-purple-700 dark:text-purple-400" />
                <h3 className="text-xs font-bold text-[var(--color-text-primary)] uppercase tracking-wider">Platform-Level Core Roles</h3>
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-purple-100 dark:bg-purple-950/60 text-purple-800 dark:text-purple-300 border border-purple-300 dark:border-purple-700 uppercase font-bold">
                Scope: PLATFORM
              </span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {platformRoles.map(pr => (
                <div
                  key={pr.code}
                  onClick={() => setSelectedRole(pr)}
                  className="bg-[var(--color-surface-subtle)] border border-[var(--color-border)] hover:border-purple-400 rounded-lg p-3.5 flex items-center justify-between cursor-pointer transition-colors shadow-xs"
                >
                  <div>
                    <span className="font-bold text-[var(--color-text-primary)] text-xs">{pr.name}</span>
                    <p className="text-[11px] text-[var(--color-text-secondary)] mt-0.5">{pr.description}</p>
                  </div>
                  <span className="text-[10px] font-mono text-purple-800 dark:text-purple-300 font-bold bg-purple-100 dark:bg-purple-950/60 px-2 py-1 rounded border border-purple-300 dark:border-purple-700">
                    {pr.user_count} Global Users
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Organisations Hierarchy Section */}
          {organizations.length > 0 && (
            <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-5 space-y-4 shadow-xs">
              <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-2">
                <div>
                  <h3 className="text-xs font-bold text-[var(--color-text-primary)] uppercase tracking-wider flex items-center gap-2">
                    <Building2 size={16} className="text-[#008A5E]" />
                    Organisations & Tenant Governance Hierarchy ({organizations.length})
                  </h3>
                  <p className="text-[11px] text-[var(--color-text-secondary)]">
                    Select an organisation to enter its isolated roles, accounts, and access governance context.
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {organizations.map(org => {
                  const orgUserCount = users.filter(
                    u => u.organization_id === org.id || u.organization === org.name || u.organization_name === org.name
                  ).length;

                  return (
                    <div
                      key={org.id}
                      onClick={() => {
                        setSelectedOrgId(org.id);
                        setOrgSubTab("roles");
                      }}
                      className="bg-[var(--color-surface-subtle)] border border-[var(--color-border)] hover:border-[var(--color-border-hover)] rounded-xl p-4 space-y-3 cursor-pointer transition-all hover:shadow-md group shadow-xs"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Building2 size={16} className="text-[#008A5E] group-hover:scale-110 transition-transform" />
                          <span className="font-bold text-[var(--color-text-primary)] text-xs uppercase tracking-wider group-hover:text-[#008A5E] transition-colors">
                            {org.name}
                          </span>
                        </div>
                        <span className="text-[9px] font-mono font-bold px-2 py-0.5 rounded bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700">
                          {org.status || "ACTIVE"}
                        </span>
                      </div>

                      <div className="flex items-center justify-between text-[10px] font-mono text-[var(--color-text-secondary)] border-t border-[var(--color-border)] pt-2">
                        <span>Accounts: <strong className="text-[var(--color-text-primary)]">{orgUserCount}</strong></span>
                        <span>Org Roles: <strong className="text-emerald-800 dark:text-emerald-300">{organizationRoles.length}</strong></span>
                      </div>

                      <div className="text-[10px] font-bold text-[#008A5E] group-hover:underline flex items-center justify-end gap-1 pt-1">
                        Enter Governance Context →
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Search, Filter, Sort Toolbar for Global Matrix */}
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] p-3.5 rounded-xl flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 shadow-xs">
            <div className="relative flex-1 min-w-[260px]">
              <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
              <input
                type="text"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                placeholder="Search by Role, Permission code, Scope, API or Description..."
                className="w-full pl-9 pr-3 py-2 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] text-xs text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[#008A5E] shadow-xs"
              />
            </div>

            <select
              value={scopeFilter}
              onChange={e => setScopeFilter(e.target.value)}
              className="py-2 px-3 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] text-xs text-[var(--color-text-primary)] font-semibold focus:outline-none cursor-pointer shadow-xs"
            >
              <option value="ALL">Scope: All</option>
              <option value="PLATFORM">PLATFORM</option>
              <option value="ORGANIZATION">ORGANIZATION</option>
              <option value="PROJECT">PROJECT</option>
            </select>

            <select
              value={sortOption}
              onChange={e => setSortOption(e.target.value as any)}
              className="py-2 px-3 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] text-xs text-[var(--color-text-primary)] font-semibold focus:outline-none cursor-pointer shadow-xs"
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
                className="bg-[var(--color-surface)] border border-[var(--color-border)] hover:border-[var(--color-border-hover)] rounded-xl p-5 space-y-4 cursor-pointer transition-all duration-200 hover:shadow-md group shadow-xs"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Shield className="size-4 text-[#008A5E] group-hover:scale-110 transition-transform" />
                    <span className="text-xs font-black text-[var(--color-text-primary)] uppercase tracking-wider group-hover:text-[#008A5E] transition-colors">
                      {r.name}
                    </span>
                  </div>
                  <span
                    className={`text-[9px] font-mono font-bold px-2 py-0.5 rounded border uppercase ${
                      r.scope === "PLATFORM"
                        ? "bg-purple-100 dark:bg-purple-950/60 border-purple-300 dark:border-purple-700 text-purple-800 dark:text-purple-300"
                        : r.scope === "ORGANIZATION"
                        ? "bg-blue-100 dark:bg-blue-950/60 border-blue-300 dark:border-blue-700 text-blue-800 dark:text-blue-300"
                        : "bg-emerald-100 dark:bg-emerald-950/60 border-emerald-300 dark:border-emerald-700 text-emerald-800 dark:text-emerald-300"
                    }`}
                  >
                    {r.scope}
                  </span>
                </div>

                <p className="text-[11px] text-[var(--color-text-secondary)] leading-relaxed line-clamp-2">{r.description}</p>

                <div className="flex items-center justify-between border-t border-[var(--color-border)] pt-3 text-[10px] font-mono text-[var(--color-text-secondary)]">
                  <span className="flex items-center gap-1">
                    <Key size={12} className="text-purple-700 dark:text-purple-400" />
                    Permissions: <strong className="text-[var(--color-text-primary)]">{r.permissions?.length || 0}</strong>
                  </span>
                  <span className="flex items-center gap-1">
                    <Users size={12} className="text-emerald-700 dark:text-emerald-400" />
                    Assigned: <strong className="text-emerald-800 dark:text-emerald-300">{r.user_count} User(s)</strong>
                  </span>
                </div>
              </div>
            ))}
          </div>

          {/* System Permission Matrix Explorer */}
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-5 space-y-4 shadow-xs">
            <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-3">
              <h3 className="text-xs font-black uppercase tracking-wider text-[var(--color-text-primary)]">
                Platform Atomic Permission Directory ({permissionsList.length} Total Registered Permissions)
              </h3>
              <span className="text-[10px] font-mono text-[var(--color-text-muted)] font-bold">Live Governance Matrix</span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2 text-xs font-mono">
              {permissionsList.map((p, idx) => (
                <div
                  key={idx}
                  className="p-3 rounded-lg bg-[var(--color-surface-subtle)] border border-[var(--color-border)] flex items-center justify-between hover:border-[var(--color-border-hover)] transition-colors shadow-xs"
                >
                  <span className="text-[var(--color-text-primary)] truncate font-bold">{p.code}</span>
                  <span className="text-[9px] text-emerald-800 dark:text-emerald-300 uppercase font-bold bg-emerald-100 dark:bg-emerald-950/60 border border-emerald-300 dark:border-emerald-700 px-1.5 py-0.5 rounded">
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
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl max-w-lg w-full p-6 space-y-4 animate-scale-up shadow-2xl">
            <h3 className="text-base font-black text-[var(--color-text-primary)]">Edit Role: {selectedRole.name}</h3>
            <div>
              <label className="text-xs font-bold text-[var(--color-text-secondary)] block mb-1">Description:</label>
              <textarea
                value={editDescription}
                onChange={e => setEditDescription(e.target.value)}
                className="w-full p-3 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] text-xs text-[var(--color-text-primary)] focus:outline-none focus:border-[#008A5E] min-h-[100px] shadow-xs"
              />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setShowEditModal(false)}
                className="px-4 py-2 rounded-lg bg-[var(--color-surface)] hover:bg-[var(--color-surface-subtle)] text-xs font-bold text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] border border-[var(--color-border)] cursor-pointer shadow-xs"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  setShowEditModal(false);
                  toast.success("Role Saved", `Updated description for ${selectedRole.name}`);
                }}
                className="px-4 py-2 rounded-lg bg-[#008A5E] hover:bg-[#00734E] text-xs font-bold text-white cursor-pointer shadow-xs"
              >
                Save Governance Metadata
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Safe Delete Impact Analysis Modal */}
      {showDeleteModal && selectedRole && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-[var(--color-surface)] border border-red-300 dark:border-red-700/60 rounded-2xl max-w-lg w-full p-6 space-y-4 animate-scale-up shadow-2xl">
            <div className="flex items-center gap-2 text-red-600 dark:text-red-400">
              <AlertTriangle size={20} />
              <h3 className="text-base font-black text-[var(--color-text-primary)]">Role Deletion Impact Analysis</h3>
            </div>
            <p className="text-xs text-[var(--color-text-secondary)]">
              Reviewing governance impact before removing <strong className="text-[var(--color-text-primary)]">{selectedRole.name}</strong>:
            </p>

            <div className="bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 rounded-xl p-4 space-y-2 text-xs text-red-800 dark:text-red-300 font-mono font-semibold">
              <p>• Accounts Affected: {selectedRole.user_count} User(s)</p>
              <p>• Atomic Permissions Revoked: {selectedRole.permissions.length}</p>
              <p>• Target Scope: {selectedRole.scope}</p>
            </div>

            {PROTECTED_ROLES.includes(selectedRole.code) ? (
              <p className="text-xs text-amber-700 dark:text-amber-400 font-bold">
                ⚠️ Protected System Role cannot be deleted to prevent security vulnerability.
              </p>
            ) : (
              <p className="text-xs text-[var(--color-text-secondary)]">
                Are you sure you want to proceed with permanent deletion?
              </p>
            )}

            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setShowDeleteModal(false)}
                className="px-4 py-2 rounded-lg bg-[var(--color-surface)] hover:bg-[var(--color-surface-subtle)] text-xs font-bold text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] border border-[var(--color-border)] cursor-pointer shadow-xs"
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
                  className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-xs font-bold text-white cursor-pointer shadow-xs"
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
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-fade-in">
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl max-w-lg w-full p-6 space-y-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-4">
              <div className="flex items-center gap-2">
                <ShieldCheck size={20} className="text-[#008A5E]" />
                <h3 className="text-base font-black text-[var(--color-text-primary)]">Edit User Account & Role Governance</h3>
              </div>
              <button
                onClick={() => setEditingUser(null)}
                className="p-1.5 rounded-lg bg-[var(--color-surface-subtle)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] border border-[var(--color-border)] cursor-pointer"
              >
                <XCircle size={18} />
              </button>
            </div>

            <div className="space-y-4 text-xs">
              <div>
                <label className="block text-[var(--color-text-secondary)] font-bold uppercase text-[10px] mb-1">Target Account Email</label>
                <input
                  type="email"
                  value={userEditEmail}
                  onChange={e => setUserEditEmail(e.target.value)}
                  className="w-full bg-[var(--color-surface)] border border-[var(--color-border)] p-2.5 rounded-lg text-[var(--color-text-primary)] font-mono focus:border-[#008A5E] focus:outline-none shadow-xs"
                />
              </div>

              <div>
                <label className="block text-[var(--color-text-secondary)] font-bold uppercase text-[10px] mb-1">Full Name</label>
                <input
                  type="text"
                  value={userEditFullName}
                  onChange={e => setUserEditFullName(e.target.value)}
                  className="w-full bg-[var(--color-surface)] border border-[var(--color-border)] p-2.5 rounded-lg text-[var(--color-text-primary)] font-semibold focus:border-[#008A5E] focus:outline-none shadow-xs"
                />
              </div>

              <div>
                <label className="block text-[var(--color-text-secondary)] font-bold uppercase text-[10px] mb-1">Assigned Enterprise Role</label>
                <select
                  value={userEditRole}
                  onChange={e => setUserEditRole(e.target.value)}
                  className="w-full bg-[var(--color-surface)] border border-[var(--color-border)] p-2.5 rounded-lg text-[var(--color-text-primary)] font-mono font-bold focus:border-[#008A5E] focus:outline-none cursor-pointer shadow-xs"
                >
                  {roles.map(r => (
                    <option key={r.code} value={r.code.toUpperCase()} className="bg-[var(--color-surface)] text-[var(--color-text-primary)]">
                      {r.name} ({r.code.toUpperCase()})
                    </option>
                  ))}
                  <option value="FIELD_AGENT" className="bg-[var(--color-surface)] text-[var(--color-text-primary)]">Field Agent (FIELD_AGENT)</option>
                  <option value="AUDITOR" className="bg-[var(--color-surface)] text-[var(--color-text-primary)]">Third-Party Auditor (AUDITOR)</option>
                  <option value="VVB" className="bg-[var(--color-surface)] text-[var(--color-text-primary)]">VVB Verifier (VVB)</option>
                  <option value="PROJECT_MANAGER" className="bg-[var(--color-surface)] text-[var(--color-text-primary)]">Project Manager (PROJECT_MANAGER)</option>
                  <option value="PORTFOLIO_MANAGER" className="bg-[var(--color-surface)] text-[var(--color-text-primary)]">Portfolio Manager (PORTFOLIO_MANAGER)</option>
                  <option value="QA_OFFICER" className="bg-[var(--color-surface)] text-[var(--color-text-primary)]">QA Officer (QA_OFFICER)</option>
                  <option value="FIELD_SUPERVISOR" className="bg-[var(--color-surface)] text-[var(--color-text-primary)]">Field Supervisor (FIELD_SUPERVISOR)</option>
                  <option value="VIEWER" className="bg-[var(--color-surface)] text-[var(--color-text-primary)]">Read-Only Viewer (VIEWER)</option>
                </select>
              </div>

              <div>
                <label className="block text-[var(--color-text-secondary)] font-bold uppercase text-[10px] mb-1">Organization Workspace Boundary</label>
                <select
                  value={userEditOrgId}
                  onChange={e => setUserEditOrgId(e.target.value)}
                  className="w-full bg-[var(--color-surface)] border border-[var(--color-border)] p-2.5 rounded-lg text-[var(--color-text-primary)] font-semibold focus:border-[#008A5E] focus:outline-none cursor-pointer shadow-xs"
                >
                  <option value="" className="bg-[var(--color-surface)] text-[var(--color-text-primary)]">System Default (Platform Global Scope)</option>
                  {organizations.map(o => (
                    <option key={o.id} value={o.id} className="bg-[var(--color-surface)] text-[var(--color-text-primary)]">
                      {o.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-[var(--color-text-secondary)] font-bold uppercase text-[10px] mb-1">Account Governance Status</label>
                <select
                  value={userEditStatus}
                  onChange={e => setUserEditStatus(e.target.value)}
                  className="w-full bg-[var(--color-surface)] border border-[var(--color-border)] p-2.5 rounded-lg text-[var(--color-text-primary)] font-semibold focus:border-[#008A5E] focus:outline-none cursor-pointer shadow-xs"
                >
                  <option value="active" className="bg-[var(--color-surface)] text-[var(--color-text-primary)]">Active (Full Access Allowed)</option>
                  <option value="suspended" className="bg-[var(--color-surface)] text-[var(--color-text-primary)]">Suspended (Access Blocked)</option>
                </select>
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 border-t border-[var(--color-border)] pt-4">
              <button
                type="button"
                onClick={() => setEditingUser(null)}
                className="px-4 py-2 rounded-lg bg-[var(--color-surface)] hover:bg-[var(--color-surface-subtle)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] border border-[var(--color-border)] text-xs font-bold transition-colors cursor-pointer shadow-xs"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSaveUserGovernance}
                disabled={isSavingUser}
                className="px-4 py-2 rounded-lg bg-[#008A5E] hover:bg-[#00734E] text-white text-xs font-bold transition-colors flex items-center gap-1.5 disabled:opacity-50 cursor-pointer shadow-xs"
              >
                {isSavingUser ? <RefreshCw size={14} className="animate-spin" /> : <CheckCircle2 size={14} />}
                Save Governance Changes
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Account Inspection Modal */}
      {inspectingUser && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl max-w-2xl w-full p-6 space-y-5 animate-scale-up max-h-[90vh] overflow-y-auto shadow-2xl">
            <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-emerald-100 dark:bg-emerald-950/60 border border-emerald-300 dark:border-emerald-700 text-emerald-800 dark:text-emerald-300">
                  <Shield size={20} />
                </div>
                <div>
                  <h3 className="text-base font-black text-[var(--color-text-primary)]">{inspectingUser.full_name}</h3>
                  <p className="text-xs text-[var(--color-text-secondary)] font-mono">{inspectingUser.email}</p>
                </div>
              </div>
              <button
                onClick={() => setInspectingUser(null)}
                className="p-1.5 rounded-lg bg-[var(--color-surface-subtle)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] border border-[var(--color-border)] transition-colors cursor-pointer"
              >
                ✕
              </button>
            </div>

            {/* Account Details & Status Grid */}
            <div className="grid grid-cols-2 gap-3 text-xs font-mono">
              <div className="p-3 rounded-lg bg-[var(--color-surface-subtle)] border border-[var(--color-border)] shadow-xs">
                <span className="text-[10px] text-[var(--color-text-muted)] block uppercase font-bold">Organisation</span>
                <span className="text-[var(--color-text-primary)] font-bold">{inspectingUser.organization_name || inspectingUser.organization || "Platform Global"}</span>
              </div>
              <div className="p-3 rounded-lg bg-[var(--color-surface-subtle)] border border-[var(--color-border)] shadow-xs">
                <span className="text-[10px] text-[var(--color-text-muted)] block uppercase font-bold">Assigned Role</span>
                <span className="text-blue-800 dark:text-blue-300 font-bold uppercase">{inspectingUser.role}</span>
              </div>
              <div className="p-3 rounded-lg bg-[var(--color-surface-subtle)] border border-[var(--color-border)] shadow-xs">
                <span className="text-[10px] text-[var(--color-text-muted)] block uppercase font-bold">Account Status</span>
                <span className={`font-bold uppercase ${inspectingUser.status === "suspended" ? "text-red-700 dark:text-red-400" : "text-emerald-800 dark:text-emerald-300"}`}>
                  {inspectingUser.status || "active"}
                </span>
              </div>
              <div className="p-3 rounded-lg bg-[var(--color-surface-subtle)] border border-[var(--color-border)] shadow-xs">
                <span className="text-[10px] text-[var(--color-text-muted)] block uppercase font-bold">Account Creation / Activity</span>
                <span className="text-[var(--color-text-primary)] font-bold">{inspectingUser.created_at || "Not tracked"}</span>
              </div>
            </div>

            {/* Account -> Role -> Project -> Sector Traceability Chain */}
            <div className="p-4 rounded-xl bg-[var(--color-surface-subtle)] border border-[var(--color-border)] space-y-2 shadow-xs">
              <span className="text-[10px] font-bold uppercase tracking-wider text-purple-800 dark:text-purple-300 block">
                Account → Role → Project → Sector Traceability Chain
              </span>
              <div className="flex flex-wrap items-center gap-2 text-[11px] font-mono">
                <span className="px-2.5 py-1 rounded bg-blue-100 dark:bg-blue-950/60 text-blue-800 dark:text-blue-300 border border-blue-300 dark:border-blue-700 font-bold">
                  Org: {inspectingUser.organization_name || inspectingUser.organization || "Global"}
                </span>
                <span className="text-[var(--color-text-muted)]">→</span>
                <span className="px-2.5 py-1 rounded bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700 font-bold">
                  User: {inspectingUser.full_name}
                </span>
                <span className="text-[var(--color-text-muted)]">→</span>
                <span className="px-2.5 py-1 rounded bg-purple-100 dark:bg-purple-950/60 text-purple-800 dark:text-purple-300 border border-purple-300 dark:border-purple-700 font-bold">
                  Role: {inspectingUser.role}
                </span>
                <span className="text-[var(--color-text-muted)]">→</span>
                <span className="px-2.5 py-1 rounded bg-amber-100 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-700 font-bold">
                  Sector Access: {inspectingUser.licensed_sectors?.join(", ") || "All Licensed"}
                </span>
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center justify-between border-t border-[var(--color-border)] pt-4">
              {isSuperAdmin && (
                <button
                  onClick={() => {
                    setCustomResetUser(inspectingUser);
                    setCustomNewPassword("");
                    setInspectingUser(null);
                  }}
                  className="px-3.5 py-2 rounded-lg bg-purple-50 hover:bg-purple-600 hover:text-white text-purple-700 border border-purple-300 text-xs font-bold flex items-center gap-1.5 transition-colors cursor-pointer shadow-xs"
                >
                  <Key size={14} /> Initiate Password Reset
                </button>
              )}
              <button
                onClick={() => setInspectingUser(null)}
                className="px-4 py-2 rounded-lg bg-[var(--color-surface)] hover:bg-[var(--color-surface-subtle)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] border border-[var(--color-border)] text-xs font-bold transition-colors ml-auto cursor-pointer shadow-xs"
              >
                Close Inspection
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Super Admin Secure Password Reset Modal */}
      {customResetUser && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl max-w-md w-full p-6 space-y-4 animate-scale-up shadow-2xl">
            <div className="flex items-center gap-3 border-b border-[var(--color-border)] pb-3">
              <div className="p-2 rounded-lg bg-purple-100 dark:bg-purple-950/60 text-purple-800 dark:text-purple-300 border border-purple-300 dark:border-purple-700">
                <Key size={20} />
              </div>
              <div>
                <h3 className="text-sm font-bold text-[var(--color-text-primary)] uppercase tracking-wider">Super Admin Password Reset</h3>
                <p className="text-xs text-[var(--color-text-secondary)] font-mono">{customResetUser.email}</p>
              </div>
            </div>

            <div className="space-y-3">
              <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">
                Set a new password for account <strong className="text-[var(--color-text-primary)]">{customResetUser.full_name}</strong>. Password will be hashed using bcrypt, requiring password change on next login. Plaintext passwords or hashes are never returned or logged.
              </p>

              <div>
                <label className="text-[10px] font-bold text-[var(--color-text-secondary)] uppercase block mb-1">New Temporary Password:</label>
                <input
                  type="password"
                  value={customNewPassword}
                  onChange={e => setCustomNewPassword(e.target.value)}
                  placeholder="Enter strong temporary password (min 8 chars)..."
                  className="w-full p-3 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] text-xs text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[#008A5E] font-mono shadow-xs"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 border-t border-[var(--color-border)] pt-4">
              <button
                onClick={() => setCustomResetUser(null)}
                className="px-4 py-2 rounded-lg bg-[var(--color-surface)] hover:bg-[var(--color-surface-subtle)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] border border-[var(--color-border)] text-xs font-bold transition-colors cursor-pointer shadow-xs"
              >
                Cancel
              </button>
              <button
                onClick={() => handleSuperAdminResetPassword(customResetUser, customNewPassword)}
                className="px-4 py-2 rounded-lg bg-[#008A5E] hover:bg-[#00734E] text-white text-xs font-bold transition-colors cursor-pointer shadow-xs"
              >
                Confirm Secure Reset
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}


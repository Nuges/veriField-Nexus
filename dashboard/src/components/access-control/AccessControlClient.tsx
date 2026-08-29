"use client";

import { useState, useEffect, useMemo } from "react";
import { useToast } from "@/components/Toast";
import {
  Search,
  Shield,
  UserPlus,
  Filter,
  Download,
  UserCheck,
  UserX,
  MoreVertical,
  Building,
  Key,
  Lock,
  Unlock,
  RefreshCw,
  Edit3,
  CheckCircle2,
  Trash2,
  X
} from "lucide-react";
import { apiFetch, createUserAccount, resetAgentPassword, updateAgentStatus } from "@/lib/api";
import { DataTable } from "@/components/common/DataTable";

export interface EnterpriseUser {
  id: string;
  email: string;
  full_name: string;
  role: string;
  organization?: string;
  organization_name?: string;
  organization_id?: string;
  status?: string;
  is_suspended?: boolean;
  created_at?: string;
  licensed_sectors?: string[];
}

export default function AccessControlClient() {
  const toast = useToast();

  const [users, setUsers] = useState<EnterpriseUser[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isProvisionModalOpen, setIsProvisionModalOpen] = useState(false);
  const [isResetModalOpen, setIsResetModalOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<EnterpriseUser | null>(null);

  // Provision state
  const [provisionData, setProvisionData] = useState({
    email: "",
    full_name: "",
    role: "FIELD_AGENT",
    password: "",
  });
  const [isProvisioning, setIsProvisioning] = useState(false);

  // Password reset state
  const [resetPasswordValue, setResetPasswordValue] = useState("");
  const [isResetting, setIsResetting] = useState(false);

  const loadUsers = async () => {
    setIsLoading(true);
    try {
      const data = await apiFetch<EnterpriseUser[]>("/auth/users?limit=100");
      setUsers(Array.isArray(data) ? data : []);
    } catch (error: any) {
      console.error("Failed to load users", error);
      toast.error("Load Failed", error.message || "Failed to load enterprise user directory.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadUsers();
  }, []);

  const handleProvision = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!provisionData.email || !provisionData.full_name) {
      toast.error("Validation Error", "Full Name and Email Address are required.");
      return;
    }

    setIsProvisioning(true);
    try {
      await createUserAccount({
        email: provisionData.email.trim(),
        full_name: provisionData.full_name.trim(),
        role: provisionData.role,
        password: provisionData.password.trim() || undefined,
      });

      toast.success("Account Provisioned", `User account for ${provisionData.full_name} (${provisionData.role}) created successfully.`);
      setIsProvisionModalOpen(false);
      setProvisionData({
        email: "",
        full_name: "",
        role: "FIELD_AGENT",
        password: "",
      });
      await loadUsers();
    } catch (error: any) {
      console.error("Provision failed", error);
      toast.error("Provisioning Failed", error.message || "Could not provision user account.");
    } finally {
      setIsProvisioning(false);
    }
  };

  const handleStatusToggle = async (user: EnterpriseUser) => {
    const newStatus = user.status === "suspended" || user.is_suspended ? "active" : "suspended";
    try {
      await updateAgentStatus(user.id, newStatus);
      toast.success("Status Updated", `Account ${user.full_name || user.email} status changed to ${newStatus}.`);
      await loadUsers();
    } catch (error: any) {
      console.error("Status update failed", error);
      toast.error("Action Failed", error.message || "Failed to update account status.");
    }
  };

  const handlePasswordReset = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedUser) return;
    if (resetPasswordValue.length < 8) {
      toast.error("Validation Error", "Temporary password must be at least 8 characters.");
      return;
    }

    setIsResetting(true);
    try {
      await resetAgentPassword(selectedUser.id, resetPasswordValue);
      toast.success("Password Reset", `Password for ${selectedUser.full_name} has been securely reset.`);
      setIsResetModalOpen(false);
      setSelectedUser(null);
      setResetPasswordValue("");
    } catch (error: any) {
      console.error("Password reset failed", error);
      toast.error("Reset Failed", error.message || "Failed to reset password.");
    } finally {
      setIsResetting(false);
    }
  };

  const handleExportCSV = () => {
    if (users.length === 0) {
      toast.error("Export Empty", "No user records to export.");
      return;
    }
    const headers = ["ID", "Full Name", "Email", "Role", "Organization", "Status", "Created At"];
    const rows = users.map(u => [
      u.id,
      `"${u.full_name || ""}"`,
      `"${u.email || ""}"`,
      u.role || "",
      `"${u.organization_name || u.organization || "Global"}"`,
      u.status || "active",
      u.created_at || ""
    ]);
    const csvContent = [headers.join(","), ...rows.map(r => r.join(","))].join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `verifield_users_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    toast.success("Export Complete", "Enterprise user directory exported as CSV.");
  };

  // Metrics
  const activeCount = users.filter(u => u.status !== "suspended" && !u.is_suspended).length;
  const suspendedCount = users.filter(u => u.status === "suspended" || u.is_suspended).length;
  const rolesCount = new Set(users.map(u => (u.role || "").toUpperCase())).size;

  return (
    <div className="space-y-6">
      {/* Top Header & Actions */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-[var(--color-surface)] border border-[var(--color-border)] p-5 rounded-2xl shadow-xs">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700 text-[10px] font-mono font-bold uppercase">
              IAM & RBAC Directory
            </span>
          </div>
          <h1 className="text-xl font-black text-[var(--color-text-primary)] mt-1">Team & Access Governance</h1>
          <p className="text-[var(--color-text-secondary)] text-xs mt-0.5">
            Single point of administration for enterprise user accounts, roles, privileges, and authentication credentials.
          </p>
        </div>
        <div className="flex items-center gap-2.5">
          <button
            onClick={handleExportCSV}
            className="px-3.5 py-2 rounded-xl bg-[var(--color-surface)] hover:bg-[var(--color-surface-subtle)] border border-[var(--color-border)] text-xs font-bold text-[var(--color-text-primary)] flex items-center gap-1.5 transition-colors cursor-pointer shadow-xs"
          >
            <Download size={14} className="text-blue-700 dark:text-blue-400" />
            <span>Export CSV</span>
          </button>
          <button
            onClick={() => setIsProvisionModalOpen(true)}
            className="px-4 py-2 rounded-xl bg-[#008A5E] hover:bg-[#00734E] text-white font-bold text-xs flex items-center gap-1.5 transition-colors cursor-pointer shadow-xs"
          >
            <UserPlus size={14} />
            <span>+ Provision User Account</span>
          </button>
        </div>
      </div>

      {/* Metrics Summary Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] p-4 rounded-xl shadow-xs">
          <p className="text-xs text-[var(--color-text-muted)] font-bold uppercase tracking-wider">Total Registered Accounts</p>
          <p className="text-2xl font-black text-[var(--color-text-primary)] mt-1">{users.length}</p>
        </div>
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] p-4 rounded-xl shadow-xs">
          <p className="text-xs text-[var(--color-text-muted)] font-bold uppercase tracking-wider">Active Accounts</p>
          <p className="text-2xl font-black text-emerald-800 dark:text-emerald-300 mt-1">{activeCount}</p>
        </div>
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] p-4 rounded-xl shadow-xs">
          <p className="text-xs text-[var(--color-text-muted)] font-bold uppercase tracking-wider">Suspended Accounts</p>
          <p className="text-2xl font-black text-amber-800 dark:text-amber-300 mt-1">{suspendedCount}</p>
        </div>
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] p-4 rounded-xl shadow-xs">
          <p className="text-xs text-[var(--color-text-muted)] font-bold uppercase tracking-wider">Distinct Enterprise Roles</p>
          <p className="text-2xl font-black text-purple-800 dark:text-purple-300 mt-1">{rolesCount}</p>
        </div>
      </div>

      {/* Data Table */}
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-5 shadow-xs space-y-4">
        <DataTable
          title="Enterprise Account Directory"
          subtitle="Real-time role-based access control and user status matrix"
          columns={[
            {
              key: "full_name",
              label: "User / Email",
              sortable: true,
              render: (row: EnterpriseUser) => (
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-emerald-100 dark:bg-emerald-950/60 border border-emerald-300 dark:border-emerald-700 text-emerald-800 dark:text-emerald-300 flex items-center justify-center font-black text-xs shrink-0">
                    {(row.full_name || row.email || "U").charAt(0).toUpperCase()}
                  </div>
                  <div>
                    <div className="font-bold text-[var(--color-text-primary)] text-xs">{row.full_name || "Unnamed"}</div>
                    <div className="text-[11px] text-[var(--color-text-secondary)] font-mono">{row.email}</div>
                  </div>
                </div>
              )
            },
            {
              key: "role",
              label: "Role & Privileges",
              sortable: true,
              render: (row: EnterpriseUser) => {
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
              key: "organization",
              label: "Workspace Tenant",
              sortable: true,
              render: (row: EnterpriseUser) => (
                <div className="flex items-center gap-1.5 text-xs text-[var(--color-text-secondary)]">
                  <Building size={14} className="text-[var(--color-text-muted)] shrink-0" />
                  <span className="font-semibold text-[var(--color-text-primary)]">
                    {row.organization_name || row.organization || "Global Tenant"}
                  </span>
                </div>
              )
            },
            {
              key: "status",
              label: "Status",
              sortable: true,
              render: (row: EnterpriseUser) => {
                const isSusp = row.status === "suspended" || row.is_suspended;
                return (
                  <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border ${
                    isSusp
                      ? "bg-red-100 dark:bg-red-950/60 text-red-800 dark:text-red-300 border-red-300 dark:border-red-700"
                      : "bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 border-emerald-300 dark:border-emerald-700"
                  }`}>
                    {isSusp ? <UserX size={10} /> : <UserCheck size={10} />}
                    {isSusp ? "Suspended" : "Active"}
                  </span>
                );
              }
            },
            {
              key: "actions",
              label: "Actions",
              render: (row: EnterpriseUser) => (
                <div className="flex items-center gap-1.5 justify-end">
                  <button
                    onClick={() => {
                      setSelectedUser(row);
                      setResetPasswordValue("");
                      setIsResetModalOpen(true);
                    }}
                    className="p-1.5 rounded-lg bg-[var(--color-surface)] hover:bg-[var(--color-surface-subtle)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] border border-[var(--color-border)] transition-colors cursor-pointer shadow-xs"
                    title="Reset Password"
                  >
                    <Key size={13} />
                  </button>
                  <button
                    onClick={() => handleStatusToggle(row)}
                    className={`p-1.5 rounded-lg border font-bold transition-colors cursor-pointer shadow-xs ${
                      row.status === "suspended" || row.is_suspended
                        ? "bg-emerald-50 hover:bg-emerald-600 hover:text-white text-emerald-800 border-emerald-300"
                        : "bg-amber-50 hover:bg-amber-600 hover:text-white text-amber-800 border-amber-300"
                    }`}
                    title={row.status === "suspended" || row.is_suspended ? "Activate Account" : "Suspend Account"}
                  >
                    {row.status === "suspended" || row.is_suspended ? <Unlock size={13} /> : <Lock size={13} />}
                  </button>
                </div>
              )
            }
          ]}
          data={users}
          isLoading={isLoading}
          searchKeys={["full_name", "email", "role", "organization", "organization_name"]}
          searchPlaceholder="Filter by user name, email, or role..."
          emptyStateText="No enterprise accounts match your search query."
        />
      </div>

      {/* Unified User Provisioning Modal */}
      {isProvisionModalOpen && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl w-full max-w-md shadow-2xl animate-scale-up">
            <div className="p-5 border-b border-[var(--color-border)] flex justify-between items-center">
              <h2 className="font-black text-base text-[var(--color-text-primary)] flex items-center gap-2">
                <UserPlus size={18} className="text-[#008A5E]" />
                Provision User Account
              </h2>
              <button
                onClick={() => setIsProvisionModalOpen(false)}
                className="p-1 rounded-lg bg-[var(--color-surface-subtle)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] border border-[var(--color-border)] cursor-pointer"
              >
                <X size={16} />
              </button>
            </div>

            <form onSubmit={handleProvision} className="p-5 space-y-4 text-xs">
              <div>
                <label className="block text-[10px] font-bold text-[var(--color-text-secondary)] mb-1 uppercase tracking-wider">
                  Full Name *
                </label>
                <input
                  required
                  type="text"
                  value={provisionData.full_name}
                  onChange={(e) => setProvisionData({ ...provisionData, full_name: e.target.value })}
                  className="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3 py-2 text-xs text-[var(--color-text-primary)] font-semibold focus:border-[#008A5E] outline-none shadow-xs"
                  placeholder="e.g. Jane Doe"
                />
              </div>

              <div>
                <label className="block text-[10px] font-bold text-[var(--color-text-secondary)] mb-1 uppercase tracking-wider">
                  Email Address *
                </label>
                <input
                  required
                  type="email"
                  value={provisionData.email}
                  onChange={(e) => setProvisionData({ ...provisionData, email: e.target.value })}
                  className="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3 py-2 text-xs text-[var(--color-text-primary)] font-mono focus:border-[#008A5E] outline-none shadow-xs"
                  placeholder="jane@organization.com"
                />
              </div>

              <div>
                <label className="block text-[10px] font-bold text-[var(--color-text-secondary)] mb-1 uppercase tracking-wider">
                  Assign Enterprise Role *
                </label>
                <select
                  value={provisionData.role}
                  onChange={(e) => setProvisionData({ ...provisionData, role: e.target.value })}
                  className="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3 py-2 text-xs text-[var(--color-text-primary)] font-bold focus:border-[#008A5E] outline-none cursor-pointer shadow-xs"
                >
                  <option value="FIELD_AGENT">Field Agent (Mobile Telemetry Capture)</option>
                  <option value="FIELD_SUPERVISOR">Field Supervisor (Field QA & Routing)</option>
                  <option value="PROJECT_MANAGER">Project Manager (Asset & Methodology Binding)</option>
                  <option value="PORTFOLIO_MANAGER">Portfolio Manager (PoA & Registry Allocation)</option>
                  <option value="QA_OFFICER">QA Officer (Internal MRV Audit)</option>
                  <option value="AUDITOR">Third-Party Auditor (External Verification)</option>
                  <option value="VVB">VVB Verifier (Digital Signature & Attestation)</option>
                  <option value="ORG_ADMIN">Organization Administrator (Tenant IAM)</option>
                  <option value="VIEWER">Read-Only Viewer</option>
                </select>
              </div>

              <div>
                <label className="block text-[10px] font-bold text-[var(--color-text-secondary)] mb-1 uppercase tracking-wider">
                  Temporary Password (Optional)
                </label>
                <input
                  type="password"
                  value={provisionData.password}
                  onChange={(e) => setProvisionData({ ...provisionData, password: e.target.value })}
                  className="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3 py-2 text-xs text-[var(--color-text-primary)] font-mono focus:border-[#008A5E] outline-none shadow-xs"
                  placeholder="Auto-generated if left blank (min 8 chars)"
                />
              </div>

              <div className="pt-3 flex justify-end gap-2 border-t border-[var(--color-border)]">
                <button
                  type="button"
                  onClick={() => setIsProvisionModalOpen(false)}
                  className="px-4 py-2 rounded-lg bg-[var(--color-surface)] hover:bg-[var(--color-surface-subtle)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] border border-[var(--color-border)] text-xs font-bold transition-colors cursor-pointer shadow-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isProvisioning}
                  className="px-4 py-2 rounded-lg bg-[#008A5E] hover:bg-[#00734E] text-white text-xs font-bold transition-colors flex items-center gap-1.5 disabled:opacity-50 cursor-pointer shadow-xs"
                >
                  {isProvisioning ? <RefreshCw size={13} className="animate-spin" /> : <UserPlus size={13} />}
                  <span>Provision Account</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Password Reset Modal */}
      {isResetModalOpen && selectedUser && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl w-full max-w-md shadow-2xl animate-scale-up">
            <div className="p-5 border-b border-[var(--color-border)] flex justify-between items-center">
              <h2 className="font-black text-base text-[var(--color-text-primary)] flex items-center gap-2">
                <Key size={18} className="text-purple-700 dark:text-purple-400" />
                Reset Account Password
              </h2>
              <button
                onClick={() => setIsResetModalOpen(false)}
                className="p-1 rounded-lg bg-[var(--color-surface-subtle)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] border border-[var(--color-border)] cursor-pointer"
              >
                <X size={16} />
              </button>
            </div>

            <form onSubmit={handlePasswordReset} className="p-5 space-y-4 text-xs">
              <p className="text-[var(--color-text-secondary)] leading-relaxed">
                Set a new temporary password for <strong className="text-[var(--color-text-primary)]">{selectedUser.full_name}</strong> ({selectedUser.email}).
              </p>

              <div>
                <label className="block text-[10px] font-bold text-[var(--color-text-secondary)] mb-1 uppercase tracking-wider">
                  New Password *
                </label>
                <input
                  required
                  type="password"
                  value={resetPasswordValue}
                  onChange={(e) => setResetPasswordValue(e.target.value)}
                  className="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3 py-2 text-xs text-[var(--color-text-primary)] font-mono focus:border-[#008A5E] outline-none shadow-xs"
                  placeholder="Enter minimum 8 characters..."
                />
              </div>

              <div className="pt-3 flex justify-end gap-2 border-t border-[var(--color-border)]">
                <button
                  type="button"
                  onClick={() => setIsResetModalOpen(false)}
                  className="px-4 py-2 rounded-lg bg-[var(--color-surface)] hover:bg-[var(--color-surface-subtle)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] border border-[var(--color-border)] text-xs font-bold transition-colors cursor-pointer shadow-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isResetting}
                  className="px-4 py-2 rounded-lg bg-[#008A5E] hover:bg-[#00734E] text-white text-xs font-bold transition-colors flex items-center gap-1.5 disabled:opacity-50 cursor-pointer shadow-xs"
                >
                  {isResetting ? <RefreshCw size={13} className="animate-spin" /> : <Key size={13} />}
                  <span>Update Password</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}


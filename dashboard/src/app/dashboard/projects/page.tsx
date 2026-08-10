// =============================================================================

// VeriField Nexus — Project Team & Account Management Workspace (CIOS Level 5)

// =============================================================================



"use client";



import { useState, useEffect } from "react";

import UniversalEntityHeader from "@/components/UniversalEntityHeader";

import PropertiesPage from "../properties/page";

import {

  Users,

  Shield,

  Building,

  ChevronRight,

  CheckCircle2,

  UserCheck,

  Award,

  Key,

  Edit3,

  Activity,

  Save,

  X,

  Plus,

  RefreshCw,

  Lock,

  UserPlus

} from "lucide-react";

import { useWorkspace } from "@/context/WorkspaceContext";

import { useToast } from "@/components/Toast";

import {

  fetchUsers,

  fetchAllUsersGlobal,

  createUserAccount,

  resetAgentPassword,

  adminResetUserPassword,

  updateAgentStatus,

  updateUserAccount,

  adminSuspendUser,

  adminReactivateUser

} from "@/lib/api";



export default function ProjectsPage() {

  const { user } = useWorkspace();

  const toast = useToast();

  const userRole = (user?.role || "ADMIN").toUpperCase();

  const isSuperAdminOrAdmin = userRole === "SUPER_ADMIN" || userRole === "ADMIN" || userRole === "ORG_ADMIN";



  const [realUsers, setRealUsers] = useState<any[]>([]);

  const [isLoadingUsers, setIsLoadingUsers] = useState(true);



  // Selected member modal state for editing/password reset

  const [selectedUser, setSelectedUser] = useState<any | null>(null);

  const [editName, setEditName] = useState("");

  const [editEmail, setEditEmail] = useState("");

  const [editRole, setEditRole] = useState("");

  const [newPassword, setNewPassword] = useState("");

  const [isUpdating, setIsUpdating] = useState(false);



  // Create User Modal State

  const [isCreateOpen, setIsCreateOpen] = useState(false);

  const [createName, setCreateName] = useState("");

  const [createEmail, setCreateEmail] = useState("");

  const [createRole, setCreateRole] = useState("FIELD_AGENT");

  const [createPassword, setCreatePassword] = useState("");

  const [isCreating, setIsCreating] = useState(false);



  async function loadRealUsers() {

    setIsLoadingUsers(true);

    try {

      let data: any[] = [];

      if (userRole === "SUPER_ADMIN") {

        data = await fetchAllUsersGlobal();

      } else {

        data = await fetchUsers();

      }

      setRealUsers(Array.isArray(data) ? data : []);

    } catch (err: any) {

      console.error("Failed to fetch real project team users:", err);

      toast.error("User Roster Error", err.message || "Failed to load team accounts.");

    } finally {

      setIsLoadingUsers(false);

    }

  }



  useEffect(() => {

    loadRealUsers();

  }, [userRole]);



  const openUserModal = (u: any) => {

    setSelectedUser(u);

    setEditName(u.full_name || u.name || "");

    setEditEmail(u.email || "");

    setEditRole((u.role || "FIELD_AGENT").toUpperCase());

    setNewPassword("");

  };



  const handleSaveUser = async () => {

    if (!selectedUser) return;

    setIsUpdating(true);

    try {

      // 1. Password Reset if provided

      if (newPassword.trim()) {

        try {

          if (userRole === "SUPER_ADMIN") {

            await adminResetUserPassword(selectedUser.id, newPassword.trim());

          } else {

            await resetAgentPassword(selectedUser.id, newPassword.trim());

          }

          toast.success("Security Updated", `Password for ${editName || selectedUser.email} updated.`);

        } catch (pwErr: any) {

          toast.error("Password Reset Failed", pwErr.message || "Failed to reset user password.");

        }

      }



      // 2. Status / Name / Role Update if changed

      const isSuspended = selectedUser.is_suspended || selectedUser.status === "suspended";

      if (

        editName !== selectedUser.full_name ||

        editRole !== (selectedUser.role || "").toUpperCase()

      ) {

        await updateUserAccount(selectedUser.id, {

          full_name: editName,

          role: editRole,

          status: isSuspended ? "suspended" : "active"

        });

        toast.success("Account Updated", `User profile for ${editName} saved.`);

      }



      await loadRealUsers();

      setSelectedUser(null);

    } catch (err: any) {

      toast.error("Update Error", err.message || "Failed to update user account.");

    } finally {

      setIsUpdating(false);

    }

  };



  const handleToggleStatus = async (u: any) => {

    const isCurrentlySuspended = u.is_suspended || u.status === "suspended";

    try {

      if (userRole === "SUPER_ADMIN") {

        if (isCurrentlySuspended) {

          await adminReactivateUser(u.id);

          toast.success("Account Reactivated", `${u.full_name || u.email} is now active.`);

        } else {

          await adminSuspendUser(u.id);

          toast.success("Account Suspended", `${u.full_name || u.email} has been suspended.`);

        }

      } else {

        await updateAgentStatus(u.id, isCurrentlySuspended ? "active" : "suspended");

        toast.success("Status Changed", `${u.full_name || u.email} status updated.`);

      }

      await loadRealUsers();

      if (selectedUser?.id === u.id) {

        setSelectedUser(null);

      }

    } catch (err: any) {

      toast.error("Action Failed", err.message || "Failed to change user status.");

    }

  };



  const handleCreateUser = async (e: React.FormEvent) => {

    e.preventDefault();

    if (!createName || !createEmail) {

      toast.error("Validation Error", "Please provide both Full Name and Email Address.");

      return;

    }

    setIsCreating(true);

    try {

      await createUserAccount({

        full_name: createName,

        email: createEmail,

        role: createRole,

        password: createPassword.trim() || undefined,

      });

      toast.success("Account Created", `User account for ${createName} created successfully.`);

      setCreateName("");

      setCreateEmail("");

      setCreatePassword("");

      setCreateRole("FIELD_AGENT");

      setIsCreateOpen(false);

      await loadRealUsers();

    } catch (err: any) {

      toast.error("Creation Failed", err.message || "Failed to create user account.");

    } finally {

      setIsCreating(false);

    }

  };



  const ownerDisplayName = user?.full_name || "Platform Admin";



  return (

    <div className="space-y-6 animate-fade-in-up">

      <UniversalEntityHeader

        entityType="Project"

        entityId="PRJ-2026-NEXUS"

        entityName="Carbon Project Origination & Binding"

        currentStage={1}

        currentStageName="1. Origination & Setup"

        ownerRole={userRole}

        ownerName={ownerDisplayName}

        slaText=""

        status=""

        aiRecommendation="All project spatial boundaries, baseline emissions, and organization team access controls active."

        primaryNextActionLabel=""

        onPrimaryNextAction={() => {}}

      />



      {/* 🏛️ ORGANIZATION ADMINISTRATORS */}

      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-5 shadow-sm space-y-4">

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[var(--color-border)] pb-4">

          <div className="flex items-center gap-3">

            <div className="p-2.5 rounded-xl bg-purple-500/10 text-purple-400 border border-purple-500/20">

              <Shield size={20} />

            </div>

            <div>

              <h2 className="text-sm font-extrabold uppercase tracking-wider text-[var(--color-text-primary)]">

                Organization Administrators

              </h2>

              <p className="text-xs text-[var(--color-text-secondary)]">

                Manage organization administrators, account privileges, and secure password resets.

              </p>

            </div>

          </div>



          {isSuperAdminOrAdmin && (

            <button

              onClick={() => setIsCreateOpen(true)}

              className="px-4 py-2 rounded-xl bg-[#00B47A] hover:bg-[#009b68] text-white font-bold text-xs transition-all shadow-md active:scale-95 shrink-0 flex items-center gap-1.5 cursor-pointer"

            >

              <UserPlus size={14} />

              <span>+ Create User Account</span>

            </button>

          )}

        </div>



        {/* REAL ADMINS GRID */}

        {isLoadingUsers ? (

          <div className="py-8 text-center space-y-2">

            <RefreshCw size={20} className="animate-spin text-[#00B47A] mx-auto" />

            <p className="text-xs font-mono text-zinc-500">Loading organization administrators...</p>

          </div>

        ) : (

          (() => {

            const orgAdmins = realUsers.filter(u => ["ORG_ADMIN", "SUPER_ADMIN", "ADMIN"].includes((u.role || "").toUpperCase()));

            if (orgAdmins.length === 0) {

              return (

                <div className="p-6 text-center bg-[var(--color-background)] rounded-xl border border-[var(--color-border)]">

                  <p className="text-xs font-bold text-[var(--color-text-primary)]">No Organization Administrators Found</p>

                </div>

              );

            }

            return (

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">

                {orgAdmins.map((u) => {

                  const roleClean = (u.role || "USER").toUpperCase().replace(/_/g, " ");

                  const isSuspended = u.is_suspended || u.status === "suspended";

                  return (

                    <div

                      key={u.id}

                      onClick={() => openUserModal(u)}

                      className={`p-3.5 rounded-xl bg-[var(--color-background)] border transition-all flex items-start justify-between gap-2.5 shadow-xs cursor-pointer group active:scale-[0.98] ${

                        isSuspended ? "border-red-500/30 opacity-70" : "border-[var(--color-border)] hover:border-purple-500/50 hover:shadow-md"

                      }`}

                      title="Click to manage account & password"

                    >

                      <div className="flex items-start gap-2.5 min-w-0">

                        <div className="p-2 rounded-lg bg-purple-500/10 text-purple-400 shrink-0 mt-0.5">

                          <Shield size={16} />

                        </div>

                        <div className="min-w-0">

                          <div className="flex items-center gap-1.5">

                            <span className="text-[9px] font-black text-purple-400 uppercase tracking-wider">

                              {roleClean}

                            </span>

                            {isSuspended && (

                              <span className="text-[8px] font-mono font-bold px-1.5 py-0.2 bg-red-500/20 text-red-400 rounded">

                                SUSPENDED

                              </span>

                            )}

                          </div>

                          <p className="text-xs font-bold text-[var(--color-text-primary)] truncate mt-0.5">

                            {u.full_name || u.name || "Unnamed Account"}

                          </p>

                          <p className="text-[9px] font-mono text-[var(--color-text-muted)] truncate">{u.email}</p>

                        </div>

                      </div>

                      <div className="p-1.5 rounded bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-secondary)] group-hover:text-purple-400 shrink-0">

                        <Edit3 size={12} />

                      </div>

                    </div>

                  );

                })}

              </div>

            );

          })()

        )}

      </div>



      {/* 👷 PROJECT OPERATIONAL TEAM */}

      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-5 shadow-sm space-y-4">

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[var(--color-border)] pb-4">

          <div className="flex items-center gap-3">

            <div className="p-2.5 rounded-xl bg-[#00B47A]/10 text-[#00B47A] border border-[#00B47A]/20">

              <Users size={20} />

            </div>

            <div>

              <h2 className="text-sm font-extrabold uppercase tracking-wider text-[var(--color-text-primary)]">

                Project Operational Team

              </h2>

              <p className="text-xs text-[var(--color-text-secondary)]">

                Field agents, project managers, and auditors assigned to project operations and MRV workflows.

              </p>

            </div>

          </div>

        </div>



        {/* REAL OPERATIONAL USERS GRID */}

        {isLoadingUsers ? (

          <div className="py-8 text-center space-y-2">

            <RefreshCw size={20} className="animate-spin text-[#00B47A] mx-auto" />

            <p className="text-xs font-mono text-zinc-500">Loading project operational team...</p>

          </div>

        ) : (

          (() => {

            const opUsers = realUsers.filter(u => !["ORG_ADMIN", "SUPER_ADMIN", "ADMIN"].includes((u.role || "").toUpperCase()));

            if (opUsers.length === 0) {

              return (

                <div className="p-6 text-center bg-[var(--color-background)] rounded-xl border border-[var(--color-border)] space-y-2">

                  <Users size={24} className="text-zinc-600 mx-auto" />

                  <p className="text-xs font-bold text-[var(--color-text-primary)]">No Project-Specific Operational Members Assigned Yet</p>

                  <p className="text-[11px] text-zinc-500 max-w-md mx-auto">

                    Field agents, project managers, and auditors assigned to specific climate projects will appear here. Click "+ Create User Account" above to add operational team members.

                  </p>

                </div>

              );

            }

            return (

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">

                {opUsers.map((u) => {

                  const roleClean = (u.role || "USER").toUpperCase().replace(/_/g, " ");

                  const isSuspended = u.is_suspended || u.status === "suspended";

                  return (

                    <div

                      key={u.id}

                      onClick={() => openUserModal(u)}

                      className={`p-3.5 rounded-xl bg-[var(--color-background)] border transition-all flex items-start justify-between gap-2.5 shadow-xs cursor-pointer group active:scale-[0.98] ${

                        isSuspended ? "border-red-500/30 opacity-70" : "border-[var(--color-border)] hover:border-[#00B47A]/50 hover:shadow-md"

                      }`}

                      title="Click to manage account & password"

                    >

                      <div className="flex items-start gap-2.5 min-w-0">

                        <div className="p-2 rounded-lg bg-emerald-500/10 text-[#00B47A] shrink-0 mt-0.5">

                          <Users size={16} />

                        </div>

                        <div className="min-w-0">

                          <div className="flex items-center gap-1.5">

                            <span className="text-[9px] font-black text-[var(--color-text-secondary)] uppercase tracking-wider group-hover:text-[#00B47A] transition-colors">

                              {roleClean}

                            </span>

                            {isSuspended && (

                              <span className="text-[8px] font-mono font-bold px-1.5 py-0.2 bg-red-500/20 text-red-400 rounded">

                                SUSPENDED

                              </span>

                            )}

                          </div>

                          <p className="text-xs font-bold text-[var(--color-text-primary)] truncate mt-0.5">

                            {u.full_name || u.name || "Unnamed Account"}

                          </p>

                          <p className="text-[9px] font-mono text-[var(--color-text-muted)] truncate">{u.email}</p>

                        </div>

                      </div>

                      <div className="p-1.5 rounded bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-secondary)] group-hover:text-[#00B47A] shrink-0">

                        <Edit3 size={12} />

                      </div>

                    </div>

                  );

                })}

              </div>

            );

          })()

        )}

      </div>



      {/* MANAGE REAL USER & PASSWORD RESET MODAL */}

      {selectedUser && (

        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">

          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl animate-scale-in">

            <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-3">

              <div className="flex items-center gap-2">

                <Users size={18} className="text-[#00B47A]" />

                <h3 className="text-sm font-extrabold uppercase tracking-wider text-[var(--color-text-primary)]">

                  Manage Account: {selectedUser.full_name || selectedUser.email}

                </h3>

              </div>

              <button onClick={() => setSelectedUser(null)} className="text-[var(--color-text-secondary)] hover:text-white"><X size={16} /></button>

            </div>



            <div className="space-y-3 text-xs">

              <div>

                <label className="text-[10px] font-extrabold uppercase tracking-wider text-[var(--color-text-secondary)]">Full Name</label>

                <input

                  type="text"

                  value={editName}

                  onChange={(e) => setEditName(e.target.value)}

                  className="w-full mt-1 p-2.5 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] text-xs font-bold text-[var(--color-text-primary)] focus:outline-none focus:border-[#00B47A]"

                />

              </div>



              <div>

                <label className="text-[10px] font-extrabold uppercase tracking-wider text-[var(--color-text-secondary)]">Email Address</label>

                <input

                  type="email"

                  disabled

                  value={editEmail}

                  className="w-full mt-1 p-2.5 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] text-xs font-mono text-zinc-500 cursor-not-allowed opacity-80"

                />

              </div>



              <div>

                <label className="text-[10px] font-extrabold uppercase tracking-wider text-[var(--color-text-secondary)]">Role Privilege</label>

                <select

                  value={editRole}

                  onChange={(e) => setEditRole(e.target.value)}

                  className="w-full mt-1 p-2.5 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] text-xs font-bold text-[var(--color-text-primary)] focus:outline-none focus:border-[#00B47A]"

                >

                  <option value="ORG_ADMIN">Organization Admin</option>

                  <option value="PROJECT_MANAGER">Project Manager</option>

                  <option value="FIELD_AGENT">Field Agent</option>

                  <option value="AUDITOR">VVB Auditor</option>

                  <option value="QA_OFFICER">QA Officer</option>

                </select>

              </div>



              <div>

                <label className="text-[10px] font-extrabold uppercase tracking-wider text-amber-400 flex items-center gap-1">

                  <Key size={12} /> Change / Reset Password

                </label>

                <input

                  type="password"

                  placeholder="Enter new password (min 8 characters)"

                  value={newPassword}

                  onChange={(e) => setNewPassword(e.target.value)}

                  className="w-full mt-1 p-2.5 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] text-xs text-[var(--color-text-primary)] focus:outline-none focus:border-amber-500"

                />

              </div>



              <div className="pt-2">

                <button

                  type="button"

                  onClick={() => handleToggleStatus(selectedUser)}

                  className={`w-full py-2 px-3 rounded-xl font-bold text-xs border transition-all cursor-pointer ${

                    selectedUser.is_suspended || selectedUser.status === "suspended"

                      ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/20"

                      : "bg-red-500/10 border-red-500/30 text-red-400 hover:bg-red-500/20"

                  }`}

                >

                  {selectedUser.is_suspended || selectedUser.status === "suspended" ? "Reactivate User Account" : "Suspend User Account"}

                </button>

              </div>

            </div>



            <div className="flex items-center justify-end gap-2 pt-3 border-t border-[var(--color-border)]">

              <button

                onClick={() => setSelectedUser(null)}

                className="px-4 py-2 rounded-xl bg-[var(--color-background)] text-[var(--color-text-secondary)] font-bold text-xs cursor-pointer"

              >

                Cancel

              </button>

              <button

                onClick={handleSaveUser}

                disabled={isUpdating}

                className="px-4 py-2 rounded-xl bg-[#00B47A] text-white font-bold text-xs hover:bg-[#009b68] flex items-center gap-1.5 cursor-pointer disabled:opacity-50"

              >

                {isUpdating ? <RefreshCw size={13} className="animate-spin" /> : <Save size={13} />}

                <span>Save Changes</span>

              </button>

            </div>

          </div>

        </div>

      )}



      {/* CREATE NEW REAL USER ACCOUNT MODAL */}

      {isCreateOpen && (

        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">

          <form onSubmit={handleCreateUser} className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl animate-scale-in">

            <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-3">

              <div className="flex items-center gap-2">

                <UserPlus size={18} className="text-[#00B47A]" />

                <h3 className="text-sm font-extrabold uppercase tracking-wider text-[var(--color-text-primary)]">

                  Create User Account

                </h3>

              </div>

              <button type="button" onClick={() => setIsCreateOpen(false)} className="text-[var(--color-text-secondary)] text-xs font-bold hover:text-white"><X size={16} /></button>

            </div>



            <div className="space-y-3 text-xs">

              <div>

                <label className="text-[10px] font-extrabold uppercase tracking-wider text-[var(--color-text-secondary)]">Full Name *</label>

                <input

                  type="text"

                  required

                  placeholder="e.g. Oluwaseun Adeleke"

                  value={createName}

                  onChange={(e) => setCreateName(e.target.value)}

                  className="w-full mt-1 p-2.5 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] text-xs font-bold text-[var(--color-text-primary)] focus:outline-none focus:border-[#00B47A]"

                />

              </div>



              <div>

                <label className="text-[10px] font-extrabold uppercase tracking-wider text-[var(--color-text-secondary)]">Email Address *</label>

                <input

                  type="email"

                  required

                  placeholder="e.g. user@organization.io"

                  value={createEmail}

                  onChange={(e) => setCreateEmail(e.target.value)}

                  className="w-full mt-1 p-2.5 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] text-xs font-mono text-[var(--color-text-primary)] focus:outline-none focus:border-[#00B47A]"

                />

              </div>



              <div>

                <label className="text-[10px] font-extrabold uppercase tracking-wider text-[var(--color-text-secondary)]">Role Privilege *</label>

                <select

                  value={createRole}

                  onChange={(e) => setCreateRole(e.target.value)}

                  className="w-full mt-1 p-2.5 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] text-xs font-bold text-[var(--color-text-primary)] focus:outline-none focus:border-[#00B47A]"

                >

                  <option value="FIELD_AGENT">Field Agent (Mobile capture)</option>

                  <option value="PROJECT_MANAGER">Project Manager</option>

                  <option value="ORG_ADMIN">Organization Admin</option>

                  <option value="AUDITOR">VVB Auditor</option>

                  <option value="QA_OFFICER">QA Officer</option>

                </select>

              </div>



              <div>

                <label className="text-[10px] font-extrabold uppercase tracking-wider text-[var(--color-text-secondary)]">Password (Optional)</label>

                <input

                  type="password"

                  placeholder="Auto-generated if left blank"

                  value={createPassword}

                  onChange={(e) => setCreatePassword(e.target.value)}

                  className="w-full mt-1 p-2.5 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] text-xs text-[var(--color-text-primary)] focus:outline-none focus:border-[#00B47A]"

                />

              </div>

            </div>



            <div className="flex items-center justify-end gap-2 pt-3 border-t border-[var(--color-border)]">

              <button

                type="button"

                onClick={() => setIsCreateOpen(false)}

                className="px-4 py-2 rounded-xl bg-[var(--color-background)] text-[var(--color-text-secondary)] font-bold text-xs cursor-pointer"

              >

                Cancel

              </button>

              <button

                type="submit"

                disabled={isCreating}

                className="px-4 py-2 rounded-xl bg-[#00B47A] text-white font-bold text-xs hover:bg-[#009b68] flex items-center gap-1.5 cursor-pointer disabled:opacity-50"

              >

                {isCreating ? <RefreshCw size={13} className="animate-spin" /> : <UserPlus size={13} />}

                <span>Create Account</span>

              </button>

            </div>

          </form>

        </div>

      )}



      {/* Render Project Portfolio / Properties Directory */}

      <PropertiesPage />

    </div>

  );

}

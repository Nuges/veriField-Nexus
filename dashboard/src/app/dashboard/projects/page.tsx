// =============================================================================
// VeriField Nexus — Project Team & Account Management Workspace (CIOS Level 5)
// =============================================================================

"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import UniversalEntityHeader from "@/components/UniversalEntityHeader";
import PropertiesPage from "../properties/page";
import {
  Users,
  Shield,
  Building,
  ChevronRight,
  RefreshCw,
} from "lucide-react";
import { useWorkspace } from "@/context/WorkspaceContext";
import { useToast } from "@/components/Toast";
import {
  fetchUsers,
  fetchAllUsersGlobal,
} from "@/lib/api";

export default function ProjectsPage() {
  const { user } = useWorkspace();
  const toast = useToast();
  const userRole = (user?.role || "ADMIN").toUpperCase();
  const isSuperAdminOrAdmin = userRole === "SUPER_ADMIN" || userRole === "ADMIN" || userRole === "ORG_ADMIN";

  const [realUsers, setRealUsers] = useState<any[]>([]);
  const [isLoadingUsers, setIsLoadingUsers] = useState(true);

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
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-5 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[var(--color-border)] pb-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-purple-100 dark:bg-purple-950/60 text-purple-800 dark:text-purple-300 border border-purple-300 dark:border-purple-700">
              <Shield size={20} />
            </div>
            <div>
              <h2 className="text-sm font-extrabold uppercase tracking-wider text-[var(--color-text-primary)]">
                Organization Administrators
              </h2>
              <p className="text-xs text-[var(--color-text-secondary)]">
                Organization administrators, tenant oversight, and access governance.
              </p>
            </div>
          </div>

          {isSuperAdminOrAdmin && (
            <Link
              href="/dashboard/people?tab=access"
              className="px-4 py-2 rounded-xl bg-[#008A5E] hover:bg-[#00734E] text-white font-bold text-xs transition-all shadow-xs shrink-0 flex items-center gap-1.5 cursor-pointer"
            >
              <Users size={14} />
              <span>Manage Team & Privileges →</span>
            </Link>
          )}
        </div>

        {/* REAL ADMINS GRID */}
        {isLoadingUsers ? (
          <div className="py-8 text-center space-y-2">
            <RefreshCw size={20} className="animate-spin text-[#008A5E] mx-auto" />
            <p className="text-xs font-mono text-[var(--color-text-muted)]">Loading organization administrators...</p>
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
                    <Link
                      key={u.id}
                      href="/dashboard/people?tab=access"
                      className={`p-3.5 rounded-xl bg-[var(--color-background)] border transition-all flex items-start justify-between gap-2.5 shadow-xs cursor-pointer group active:scale-[0.98] ${
                        isSuspended ? "border-red-300 dark:border-red-700 opacity-70" : "border-[var(--color-border)] hover:border-purple-500/50 hover:shadow-md"
                      }`}
                      title="Manage account in People & Access"
                    >
                      <div className="flex items-start gap-2.5 min-w-0">
                        <div className="p-2 rounded-lg bg-purple-100 dark:bg-purple-950/60 text-purple-800 dark:text-purple-300 shrink-0 mt-0.5">
                          <Shield size={16} />
                        </div>
                        <div className="min-w-0">
                          <div className="flex items-center gap-1.5">
                            <span className="text-[9px] font-black text-purple-800 dark:text-purple-300 uppercase tracking-wider">
                              {roleClean}
                            </span>
                            {isSuspended && (
                              <span className="text-[8px] font-mono font-bold px-1.5 py-0.2 bg-red-100 dark:bg-red-950/60 text-red-800 dark:text-red-300 rounded">
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
                      <div className="p-1.5 rounded bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-secondary)] group-hover:text-purple-800 dark:group-hover:text-purple-300 shrink-0">
                        <ChevronRight size={12} />
                      </div>
                    </Link>
                  );
                })}
              </div>
            );
          })()
        )}
      </div>

      {/* 👷 PROJECT OPERATIONAL TEAM */}
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-5 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[var(--color-border)] pb-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700">
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
            <RefreshCw size={20} className="animate-spin text-[#008A5E] mx-auto" />
            <p className="text-xs font-mono text-[var(--color-text-muted)]">Loading project operational team...</p>
          </div>
        ) : (
          (() => {
            const opUsers = realUsers.filter(u => !["ORG_ADMIN", "SUPER_ADMIN", "ADMIN"].includes((u.role || "").toUpperCase()));
            if (opUsers.length === 0) {
              return (
                <div className="p-6 text-center bg-[var(--color-background)] rounded-xl border border-[var(--color-border)] space-y-2">
                  <Users size={24} className="text-[var(--color-text-muted)] mx-auto" />
                  <p className="text-xs font-bold text-[var(--color-text-primary)]">No Project-Specific Operational Members Assigned Yet</p>
                  <p className="text-[11px] text-[var(--color-text-secondary)] max-w-md mx-auto">
                    Field agents, project managers, and auditors assigned to specific climate projects will appear here. Manage assignments in the People & Access hub.
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
                    <Link
                      key={u.id}
                      href="/dashboard/people?tab=access"
                      className={`p-3.5 rounded-xl bg-[var(--color-background)] border transition-all flex items-start justify-between gap-2.5 shadow-xs cursor-pointer group active:scale-[0.98] ${
                        isSuspended ? "border-red-300 dark:border-red-700 opacity-70" : "border-[var(--color-border)] hover:border-emerald-500/50 hover:shadow-md"
                      }`}
                      title="Manage account in People & Access"
                    >
                      <div className="flex items-start gap-2.5 min-w-0">
                        <div className="p-2 rounded-lg bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 shrink-0 mt-0.5">
                          <Users size={16} />
                        </div>
                        <div className="min-w-0">
                          <div className="flex items-center gap-1.5">
                            <span className="text-[9px] font-black text-[var(--color-text-secondary)] uppercase tracking-wider group-hover:text-emerald-800 dark:group-hover:text-emerald-300 transition-colors">
                              {roleClean}
                            </span>
                            {isSuspended && (
                              <span className="text-[8px] font-mono font-bold px-1.5 py-0.2 bg-red-100 dark:bg-red-950/60 text-red-800 dark:text-red-300 rounded">
                                SUSPENDED
                              </span>
                            )}
                          </div>
                          <p className="text-xs font-bold text-[var(--color-text-primary)] truncate mt-0.5">
                            {u.full_name || u.name || "Unnamed Member"}
                          </p>
                          <p className="text-[9px] font-mono text-[var(--color-text-muted)] truncate">{u.email}</p>
                        </div>
                      </div>
                      <div className="p-1.5 rounded bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-secondary)] group-hover:text-emerald-800 dark:group-hover:text-emerald-300 shrink-0">
                        <ChevronRight size={12} />
                      </div>
                    </Link>
                  );
                })}
              </div>
            );
          })()
        )}
      </div>

      {/* Render Project Portfolio / Properties Directory */}
      <PropertiesPage />
    </div>
  );
}

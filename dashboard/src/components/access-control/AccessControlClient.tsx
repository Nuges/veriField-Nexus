"use client";
import { useState, useEffect } from "react";
import { Search, Shield, UserPlus, Filter, Download, UserCheck, UserX, MoreVertical, Building } from "lucide-react";
import { apiFetch } from "@/lib/api";

export default function AccessControlClient() {
  const [users, setUsers] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [isInviteModalOpen, setIsInviteModalOpen] = useState(false);
  const [inviteData, setInviteData] = useState({
    email: "",
    full_name: "",
    role: "field_agent",
    password: ""
  });

  const loadUsers = async () => {
    setIsLoading(true);
    try {
      // Hit the correct backend auth/users endpoint
      const data = await apiFetch<any[]>("/auth/users?limit=100");
      setUsers(data);
    } catch (error) {
      console.error("Failed to load users", error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadUsers();
  }, []);

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await apiFetch("/auth/users", {
        method: "POST",
        body: JSON.stringify(inviteData),
      });
      setIsInviteModalOpen(false);
      loadUsers();
    } catch (error) {
      console.error("Invite failed", error);
      alert("Failed to create user. Ensure you have SUPER_ADMIN rights.");
    }
  };

  const handleDelete = async (userId: string) => {
    if (!confirm("Are you sure you want to delete this user?")) return;
    try {
      await apiFetch(`/auth/users/${userId}`, {
        method: "DELETE",
      });
      loadUsers();
    } catch (error) {
      console.error("Delete failed", error);
    }
  };

  const filteredUsers = users.filter((u) => 
    u.email.toLowerCase().includes(searchTerm.toLowerCase()) || 
    u.full_name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">Identity & Access Management</h1>
          <p className="text-[var(--color-text-secondary)] text-sm mt-1">
            Enterprise role-based access control, provisioning, and audit directory.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button className="btn-secondary px-4 py-2 flex items-center gap-2">
            <Download size={16} />
            <span className="text-sm font-medium">Export</span>
          </button>
          <button 
            onClick={() => setIsInviteModalOpen(true)}
            className="btn-primary px-4 py-2 flex items-center gap-2"
          >
            <UserPlus size={16} />
            <span className="text-sm font-medium">Invite User</span>
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="card p-4">
          <p className="text-sm text-[var(--color-text-secondary)] font-medium">Total Users</p>
          <p className="text-2xl font-bold text-[var(--color-text-primary)] mt-1">{users.length}</p>
        </div>
        <div className="card p-4">
          <p className="text-sm text-[var(--color-text-secondary)] font-medium">Active Sessions</p>
          <p className="text-2xl font-bold text-[var(--color-text-primary)] mt-1">{users.filter(u => u.status === 'active').length}</p>
        </div>
        <div className="card p-4">
          <p className="text-sm text-[var(--color-text-secondary)] font-medium">Pending Invites</p>
          <p className="text-2xl font-bold text-[var(--color-text-primary)] mt-1">0</p>
        </div>
        <div className="card p-4">
          <p className="text-sm text-[var(--color-text-secondary)] font-medium">System Roles</p>
          <p className="text-2xl font-bold text-[var(--color-text-primary)] mt-1">8</p>
        </div>
      </div>

      <div className="card">
        <div className="p-4 border-b border-[var(--color-border)] flex flex-col sm:flex-row gap-4 justify-between items-center bg-slate-50 dark:bg-slate-900/50 rounded-t-xl">
          <div className="relative w-full sm:max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" size={18} />
            <input
              type="text"
              placeholder="Search by name or email..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg text-sm focus:border-emerald-500 outline-none"
            />
          </div>
          <button className="btn-secondary px-4 py-2 flex items-center gap-2">
            <Filter size={16} />
            <span className="text-sm font-medium">Filters</span>
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-[var(--color-border)] text-xs uppercase tracking-wider text-[var(--color-text-secondary)] bg-slate-50/50 dark:bg-slate-900/20">
                <th className="px-6 py-4 font-bold">User</th>
                <th className="px-6 py-4 font-bold">Role</th>
                <th className="px-6 py-4 font-bold">Organization</th>
                <th className="px-6 py-4 font-bold">Status</th>
                <th className="px-6 py-4 font-bold text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--color-border)] text-sm">
              {isLoading ? (
                <tr>
                  <td colSpan={5} className="px-6 py-8 text-center text-[var(--color-text-secondary)]">
                    <div className="w-6 h-6 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                    Loading users...
                  </td>
                </tr>
              ) : filteredUsers.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-8 text-center text-[var(--color-text-secondary)]">
                    No users found matching "{searchTerm}"
                  </td>
                </tr>
              ) : (
                filteredUsers.map((user) => (
                  <tr key={user.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-900/20 transition-colors">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400 flex items-center justify-center font-bold text-xs">
                          {user.full_name.charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <p className="font-semibold text-[var(--color-text-primary)]">{user.full_name}</p>
                          <p className="text-xs text-[var(--color-text-secondary)]">{user.email}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-1.5">
                        <Shield size={14} className="text-emerald-500" />
                        <span className="font-medium text-[var(--color-text-primary)] bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded-md text-xs border border-[var(--color-border)]">
                          {user.role}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-1.5 text-[var(--color-text-secondary)]">
                        <Building size={14} />
                        <span>{user.organization || "VeriField Internal"}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      {user.status === "active" ? (
                        <span className="inline-flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400 text-xs font-semibold bg-emerald-50 dark:bg-emerald-500/10 px-2 py-1 rounded-full">
                          <UserCheck size={12} /> Active
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 text-red-600 dark:text-red-400 text-xs font-semibold bg-red-50 dark:bg-red-500/10 px-2 py-1 rounded-full">
                          <UserX size={12} /> Suspended
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex justify-end gap-2">
                        <button 
                          onClick={() => handleDelete(user.id)}
                          className="p-1.5 text-red-500 hover:bg-red-50 dark:hover:bg-red-500/10 rounded-lg transition-colors"
                          title="Delete User"
                        >
                          <UserX size={16} />
                        </button>
                        <button className="p-1.5 text-[var(--color-text-secondary)] hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors">
                          <MoreVertical size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {isInviteModalOpen && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl w-full max-w-md shadow-2xl animate-fade-in-up">
            <div className="p-5 border-b border-[var(--color-border)] flex justify-between items-center">
              <h2 className="font-bold text-lg text-[var(--color-text-primary)] flex items-center gap-2">
                <UserPlus size={20} className="text-emerald-500" />
                Invite New User
              </h2>
              <button 
                onClick={() => setIsInviteModalOpen(false)}
                className="text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
              >
                ✕
              </button>
            </div>
            
            <form onSubmit={handleInvite} className="p-5 space-y-4">
              <div>
                <label className="block text-xs font-bold text-[var(--color-text-secondary)] mb-1 uppercase tracking-wider">Full Name</label>
                <input 
                  required
                  type="text" 
                  value={inviteData.full_name}
                  onChange={(e) => setInviteData({...inviteData, full_name: e.target.value})}
                  className="w-full bg-[var(--color-background)] border border-[var(--color-border)] rounded-lg px-3 py-2 text-sm focus:border-emerald-500 outline-none" 
                  placeholder="e.g. Jane Doe"
                />
              </div>
              
              <div>
                <label className="block text-xs font-bold text-[var(--color-text-secondary)] mb-1 uppercase tracking-wider">Email Address</label>
                <input 
                  required
                  type="email" 
                  value={inviteData.email}
                  onChange={(e) => setInviteData({...inviteData, email: e.target.value})}
                  className="w-full bg-[var(--color-background)] border border-[var(--color-border)] rounded-lg px-3 py-2 text-sm focus:border-emerald-500 outline-none" 
                  placeholder="jane@example.com"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-[var(--color-text-secondary)] mb-1 uppercase tracking-wider">Temporary Password</label>
                <input 
                  type="text" 
                  value={inviteData.password}
                  onChange={(e) => setInviteData({...inviteData, password: e.target.value})}
                  className="w-full bg-[var(--color-background)] border border-[var(--color-border)] rounded-lg px-3 py-2 text-sm focus:border-emerald-500 outline-none" 
                  placeholder="Leave blank to auto-generate"
                />
              </div>
              
              <div>
                <label className="block text-xs font-bold text-[var(--color-text-secondary)] mb-1 uppercase tracking-wider">Assign Role</label>
                <select 
                  value={inviteData.role}
                  onChange={(e) => setInviteData({...inviteData, role: e.target.value})}
                  className="w-full bg-[var(--color-background)] border border-[var(--color-border)] rounded-lg px-3 py-2 text-sm focus:border-emerald-500 outline-none"
                >
                  <option value="field_agent">Field Agent (Data Collection)</option>
                  <option value="PROJECT_MANAGER">Project Manager</option>
                  <option value="QA_OFFICER">QA Officer (Internal Audit)</option>
                  <option value="VERIFIER">VVB Verifier (External Audit)</option>
                  <option value="ORG_ADMIN">Organization Admin</option>
                  <option value="SUPER_ADMIN">System Super Admin</option>
                </select>
              </div>

              <div className="pt-4 flex justify-end gap-3">
                <button 
                  type="button"
                  onClick={() => setIsInviteModalOpen(false)}
                  className="px-4 py-2 text-sm font-medium text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
                >
                  Cancel
                </button>
                <button 
                  type="submit"
                  className="btn-primary px-5 py-2 text-sm font-bold"
                >
                  Send Invitation
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

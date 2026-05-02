"use client";

import { useEffect, useState } from "react";
import { Bluetooth, MessageSquare, ShieldAlert, Plus, Loader2 } from "lucide-react";
import { fetchProperties, fetchMyAuditTasks, createAuditTask, fetchActivities } from "@/lib/api";
import type { AuditTask } from "@/lib/api";

export default function VerificationsPage() {
  const [activeTab, setActiveTab] = useState<'sensors' | 'community' | 'audits'>('audits');
  const [audits, setAudits] = useState<AuditTask[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  // Load audit tasks
  useEffect(() => {
    async function loadData() {
      try {
        const tasks = await fetchMyAuditTasks();
        setAudits(tasks);
      } catch (err) {
        console.error(err);
      } finally {
        setIsLoading(false);
      }
    }
    if (activeTab === 'audits') loadData();
  }, [activeTab]);

  const handleGenerateAudit = async () => {
    try {
      setIsGenerating(true);
      // Fetch properties to pick a random one
      const propsRes = await fetchProperties();
      if (!propsRes.properties.length) {
        alert("No assets available to audit.");
        return;
      }
      
      // Fetch activities to find a valid field agent
      const actsRes = await fetchActivities({ per_page: 1 });
      const agentId = actsRes.activities.length > 0 ? actsRes.activities[0].user_id : "00000000-0000-0000-0000-000000000000";

      // Randomly select a property
      const randomProp = propsRes.properties[Math.floor(Math.random() * propsRes.properties.length)];
      
      // Calculate a deadline 7 days from now
      const deadline = new Date();
      deadline.setDate(deadline.getDate() + 7);

      // Create the audit task
      const newAudit = await createAuditTask({
        asset_id: randomProp.id,
        assigned_agent: agentId,
        deadline: deadline.toISOString(),
      });

      // Update state
      setAudits([newAudit, ...audits]);
    } catch (err: any) {
      alert(`Failed to generate audit: ${err.message}`);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="animate-fade-in-up">
        <h1 className="text-2xl font-bold text-[var(--color-text-primary)] tracking-tight">Cross-Verifications</h1>
        <p className="text-[var(--color-text-secondary)] text-sm mt-1">Multi-layered ground truth validation systems</p>
      </div>

      {/* Tabs */}
      <div className="flex bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-1 gap-1 animate-fade-in-up max-w-fit">
        <button
          onClick={() => setActiveTab('audits')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${activeTab === 'audits' ? 'bg-[var(--color-background)] text-emerald-600 shadow-sm' : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]'}`}
        >
          <ShieldAlert size={16} /> Random Audits
        </button>
        <button
          onClick={() => setActiveTab('community')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${activeTab === 'community' ? 'bg-[var(--color-background)] text-blue-600 shadow-sm' : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]'}`}
        >
          <MessageSquare size={16} /> Community Validation
        </button>
        <button
          onClick={() => setActiveTab('sensors')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${activeTab === 'sensors' ? 'bg-[var(--color-background)] text-purple-600 shadow-sm' : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]'}`}
        >
          <Bluetooth size={16} /> IoT Sensors
        </button>
      </div>

      <div className="animate-fade-in-up animation-delay-100">
        {/* RANDOM AUDITS TAB */}
        {activeTab === 'audits' && (
          <div className="space-y-4">
            <div className="flex justify-between items-center bg-[var(--color-card)] p-4 rounded-xl border border-[var(--color-border)]">
              <div>
                <h3 className="font-semibold text-[var(--color-text-primary)]">Audit Tasks</h3>
                <p className="text-sm text-[var(--color-text-secondary)]">Randomly select assets for secondary agent verification.</p>
              </div>
              <button 
                onClick={handleGenerateAudit}
                disabled={isGenerating}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl text-white font-medium transition-colors shadow-lg shadow-emerald-500/20 ${isGenerating ? 'bg-emerald-400 cursor-not-allowed' : 'bg-emerald-500 hover:bg-emerald-600'}`}
              >
                {isGenerating ? <Loader2 size={18} className="animate-spin" /> : <Plus size={18} />} 
                {isGenerating ? 'Generating...' : 'Generate Audits'}
              </button>
            </div>
            
            {isLoading ? (
              <div className="p-12 text-center text-[var(--color-text-secondary)] flex justify-center">
                <Loader2 size={32} className="animate-spin" />
              </div>
            ) : audits.length === 0 ? (
              <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl p-12 text-center text-[var(--color-text-muted)]">
                <ShieldAlert size={48} className="mx-auto mb-4 opacity-50" />
                <p>No active audits currently in progress.</p>
              </div>
            ) : (
              <div className="grid gap-4">
                {audits.map(audit => (
                  <div key={audit.id} className="bg-[var(--color-card)] border border-[var(--color-border)] p-4 rounded-xl flex items-center justify-between">
                    <div>
                      <p className="font-medium text-[var(--color-text-primary)]">Asset: {audit.asset_id.substring(0, 8)}...</p>
                      <p className="text-xs text-[var(--color-text-secondary)] mt-1">Assigned: {new Date(audit.created_at).toLocaleDateString()}</p>
                    </div>
                    <div className="flex flex-col items-end gap-2">
                      <span className={`px-2.5 py-1 rounded-md text-xs font-semibold uppercase tracking-wider ${audit.status === 'completed' ? 'bg-emerald-500/10 text-emerald-500' : 'bg-amber-500/10 text-amber-500'}`}>
                        {audit.status}
                      </span>
                      {audit.deadline && (
                        <span className="text-xs text-[var(--color-text-muted)]">
                          Due: {new Date(audit.deadline).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* COMMUNITY VALIDATION TAB */}
        {activeTab === 'community' && (
          <div className="space-y-4">
            <div className="flex justify-between items-center bg-[var(--color-card)] p-4 rounded-xl border border-[var(--color-border)]">
              <div>
                <h3 className="font-semibold text-[var(--color-text-primary)]">SMS Verifications</h3>
                <p className="text-sm text-[var(--color-text-secondary)]">Direct feedback from household beneficiaries via WhatsApp/SMS.</p>
              </div>
            </div>
            <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl p-12 text-center text-[var(--color-text-muted)]">
              <MessageSquare size={48} className="mx-auto mb-4 opacity-50" />
              <p>Waiting for community SMS responses...</p>
            </div>
          </div>
        )}

        {/* IOT SENSORS TAB */}
        {activeTab === 'sensors' && (
          <div className="space-y-4">
            <div className="flex justify-between items-center bg-[var(--color-card)] p-4 rounded-xl border border-[var(--color-border)]">
              <div>
                <h3 className="font-semibold text-[var(--color-text-primary)]">Bluetooth Data Logs</h3>
                <p className="text-sm text-[var(--color-text-secondary)]">Temperature readings synced directly from field assets.</p>
              </div>
            </div>
            <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl p-12 text-center text-[var(--color-text-muted)]">
              <Bluetooth size={48} className="mx-auto mb-4 opacity-50" />
              <p>No sensor readings have been synced from the field yet.</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

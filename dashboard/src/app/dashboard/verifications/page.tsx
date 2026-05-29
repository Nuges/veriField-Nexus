// =============================================================================
// VeriField Nexus — Ground Truth Cross-Verification Page
// =============================================================================

"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { 
  Bluetooth, 
  MessageSquare, 
  ShieldAlert, 
  Plus, 
  Loader2,
  CheckCircle,
  Calendar,
  Layers,
  ArrowRight,
  Cpu
} from "lucide-react";
import { 
  fetchProperties, 
  fetchMyAuditTasks, 
  createAuditTask, 
  fetchActivities,
  fetchCommunityFeed,
  fetchSensorDevices,
  fetchAgentPerformance
} from "@/lib/api";
import type { AuditTask } from "@/lib/api";
import { useToast } from "@/components/Toast";

export default function VerificationsPage() {
  const toast = useToast();
  const [activeTab, setActiveTab] = useState<'sensors' | 'community' | 'audits'>('audits');
  const [audits, setAudits] = useState<AuditTask[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  // SMS Validation State
  const [smsLogs, setSmsLogs] = useState<any[]>([]);
  const [isLoadingSms, setIsLoadingSms] = useState(false);

  // IoT Sensors State
  const [sensorDevices, setSensorDevices] = useState<any[]>([]);
  const [isLoadingSensors, setIsLoadingSensors] = useState(false);

  // Load audit tasks
  const loadAuditData = async () => {
    setIsLoading(true);
    try {
      const tasks = await fetchMyAuditTasks();
      setAudits(tasks);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  // Load community sms confirmations
  const loadSmsData = async () => {
    setIsLoadingSms(true);
    try {
      const res = await fetchCommunityFeed(1, 10);
      setSmsLogs(res.posts || []);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoadingSms(false);
    }
  };

  // Load connected sensor devices
  const loadSensorData = async () => {
    setIsLoadingSensors(true);
    try {
      const res = await fetchSensorDevices();
      setSensorDevices(res.devices || []);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoadingSensors(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'audits') {
      loadAuditData();
    } else if (activeTab === 'community') {
      loadSmsData();
    } else if (activeTab === 'sensors') {
      loadSensorData();
    }
  }, [activeTab]);

  const handleGenerateAudit = async () => {
    try {
      setIsGenerating(true);
      // Fetch properties to pick a random one
      const propsRes = await fetchProperties();
      if (!propsRes.properties.length) {
        toast.warning("No Assets", "No assets are available to generate audits.");
        return;
      }
      
      // Randomly select a property
      const randomProp = propsRes.properties[Math.floor(Math.random() * propsRes.properties.length)];
      
      // Fetch active agent performance records and recent activity logs to find closest agent
      const [agentsRes, actsRes] = await Promise.all([
        fetchAgentPerformance(),
        fetchActivities({ per_page: 100 })
      ]);
      
      let agentId = "00000000-0000-0000-0000-000000000000";
      let assignedAgentName = "Unallocated";
      
      if (agentsRes.agents && agentsRes.agents.length > 0) {
        let minDistance = Infinity;
        let closestAgent = agentsRes.agents[0];
        
        const propLat = randomProp.latitude;
        const propLon = randomProp.longitude;
        
        if (propLat !== null && propLon !== null && propLat !== undefined && propLon !== undefined) {
          for (const agent of agentsRes.agents) {
            // Find most recent activity registered by this agent that contains coordinates
            const agentAct = actsRes.activities.find(a => 
              a.user_id === agent.id && 
              a.latitude !== null && a.longitude !== null && 
              a.latitude !== undefined && a.longitude !== undefined
            );
            
            if (agentAct && agentAct.latitude !== null && agentAct.longitude !== null) {
              const dLat = agentAct.latitude - propLat;
              const dLon = agentAct.longitude - propLon;
              const distance = Math.sqrt(dLat * dLat + dLon * dLon);
              
              if (distance < minDistance) {
                minDistance = distance;
                closestAgent = agent;
              }
            }
          }
        }
        
        agentId = closestAgent.id;
        assignedAgentName = closestAgent.full_name;
      } else if (actsRes.activities.length > 0) {
        // Fallback to active activity logger if no roster exists
        agentId = actsRes.activities[0].user_id;
        assignedAgentName = actsRes.activities[0].agent_name || "Active Agent";
      }

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
      toast.success(
        "Optimal Audit Assigned", 
        `Verification routed to closest agent: ${assignedAgentName} (7-day turnaround)`
      );
    } catch (err: any) {
      toast.error("Allocation Failed", err.message || "Failed to commit verification task.");
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="space-y-6 animate-fade-in-up pb-10">
      
      {/* 👑 TITLE SECTION */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[var(--color-border)] pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded bg-[#00B47A]/10 text-[#00B47A] text-[9px] font-extrabold tracking-wider uppercase border border-[#00B47A]/15">
              MRV Cross-Checks
            </span>
          </div>
          <h1 className="text-xl font-bold tracking-tight text-[var(--color-text-primary)] mt-1">
            Ground Truth Cross-Verifications
          </h1>
          <p className="text-[var(--color-text-secondary)] text-xs mt-0.5">
            Verify carbon credit claims using multi-layered SMS verifications, manual audit overrides, and real-time IoT sensors.
          </p>
        </div>
      </div>

      {/* 🧭 TABS TOOLBAR */}
      <div className="flex bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-1 gap-1 max-w-fit shadow-inner">
        <button
          onClick={() => setActiveTab('audits')}
          className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-bold transition-all uppercase tracking-wider ${
            activeTab === 'audits' 
              ? 'bg-[#00B47A] text-white shadow-md' 
              : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-background)]/50'
          }`}
        >
          <ShieldAlert size={14} /> Audit Queries
        </button>
        
        <button
          onClick={() => setActiveTab('community')}
          className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-bold transition-all uppercase tracking-wider ${
            activeTab === 'community' 
              ? 'bg-[#00B47A] text-white shadow-md' 
              : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-background)]/50'
          }`}
        >
          <MessageSquare size={14} /> SMS Verification
        </button>
        
        <button
          onClick={() => setActiveTab('sensors')}
          className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-bold transition-all uppercase tracking-wider ${
            activeTab === 'sensors' 
              ? 'bg-[#00B47A] text-white shadow-md' 
              : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-background)]/50'
          }`}
        >
          <Cpu size={14} /> IoT Telemetry
        </button>
      </div>

      {/* 🧭 CONTENT BLOCKS */}
      <div className="animation-delay-100">
        
        {/* RANDOM AUDITS TAB */}
        {activeTab === 'audits' && (
          <div className="space-y-4">
            
            {/* Generate Action Module */}
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center bg-[var(--color-surface)] p-4.5 rounded-2xl border border-[var(--color-border)] shadow-sm gap-4">
              <div>
                <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-primary)]">Automated Verification Triggers</h3>
                <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
                  Instantiate random ground-truth assignments for double-blind verification checks.
                </p>
              </div>
              
              <button 
                onClick={handleGenerateAudit}
                disabled={isGenerating}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold text-white transition-all shadow-md shadow-[#00B47A]/25 shrink-0 uppercase tracking-wider active:scale-95 ${
                  isGenerating 
                    ? 'bg-emerald-400 cursor-not-allowed' 
                    : 'bg-[#00B47A] hover:bg-[#00B47A]/95'
                }`}
              >
                {isGenerating ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />} 
                {isGenerating ? 'Committing...' : 'Generate Audit Run'}
              </button>
            </div>
            
            {/* Audits Ledger Nodes Grid */}
            {isLoading ? (
              <div className="flex flex-col items-center justify-center py-16 space-y-2">
                <div className="w-6 h-6 border-2 border-[#00B47A] border-t-transparent rounded-full animate-spin" />
                <p className="text-xs text-[var(--color-text-secondary)] font-semibold">Retrieving cross-check structures...</p>
              </div>
            ) : audits.length === 0 ? (
              <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-12 text-center max-w-sm mx-auto shadow-sm">
                <ShieldAlert size={36} className="mx-auto mb-3 text-[var(--color-text-muted)] opacity-60" />
                <h3 className="text-xs font-bold uppercase tracking-wider">No Audits Pending</h3>
                <p className="text-[var(--color-text-secondary)] text-xs mt-1 leading-relaxed">
                  There are no scheduled audits currently active on the verification hub.
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {audits.map(audit => (
                  <Link 
                    key={audit.id} 
                    href={`/dashboard/properties/${audit.asset_id}`}
                    className="bg-[var(--color-surface)] border border-[var(--color-border)] p-4 rounded-2xl flex items-center justify-between shadow-sm hover:border-[#00B47A]/30 hover:shadow-md transition-all group cursor-pointer active:scale-[0.99] block"
                  >
                    <div className="flex items-center justify-between w-full">
                      <div className="space-y-1 max-w-[70%]">
                        <div className="flex items-center gap-2">
                          <span className="w-2 h-2 rounded-full bg-[#00B47A] shrink-0" />
                          <p className="text-xs font-bold text-[var(--color-text-primary)] truncate group-hover:text-[#00B47A] transition-colors" title={audit.property_name || "Unknown Stove"}>
                            {audit.property_name || `Cookstove ID: ${audit.asset_id.substring(0, 8)}`}
                          </p>
                        </div>
                        
                        <p className="text-[10px] text-[var(--color-text-secondary)] font-semibold truncate">
                          Agent: <span className="text-[var(--color-text-primary)] font-bold">{audit.agent_name || "Unallocated"}</span>
                        </p>

                        <p className="text-[9px] text-[var(--color-text-muted)] font-medium flex items-center gap-1">
                          <Calendar size={11} className="text-[#00B47A]" /> 
                          <span>Allocated: {new Date(audit.created_at).toLocaleDateString()}</span>
                        </p>
                      </div>
                      
                      <div className="flex flex-col items-end gap-1.5 shrink-0">
                        <span className={`px-2 py-0.5 rounded text-[8px] font-extrabold uppercase border tracking-wider shrink-0 ${
                          audit.status === 'completed' 
                            ? 'bg-[#00B47A]/10 text-[#00B47A] border-[#00B47A]/20' 
                            : 'bg-amber-500/10 text-amber-500 border-amber-500/20'
                        }`}>
                          {audit.status}
                        </span>
                        
                        {audit.deadline && (
                          <span className="text-[9px] text-[var(--color-text-muted)] font-mono font-bold">
                            Due: {new Date(audit.deadline).toLocaleDateString()}
                          </span>
                        )}
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            )}

          </div>
        )}

        {/* COMMUNITY SMS VALIDATION TAB */}
        {activeTab === 'community' && (
          <div className="space-y-4 animate-fade-in-up">
            <div className="bg-[var(--color-surface)] p-4.5 rounded-2xl border border-[var(--color-border)] shadow-sm">
              <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-primary)]">SMS & WhatsApp Verification</h3>
              <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
                Inspect double-blind check verification logs sent directly to beneficiary mobile numbers.
              </p>
            </div>
            
            {isLoadingSms ? (
              <div className="flex flex-col items-center justify-center py-16 space-y-2">
                <div className="w-6 h-6 border-2 border-[#00B47A] border-t-transparent rounded-full animate-spin" />
                <p className="text-xs text-[var(--color-text-secondary)] font-semibold">Scanning SMS queue...</p>
              </div>
            ) : smsLogs.length === 0 ? (
              <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-12 text-center max-w-sm mx-auto shadow-sm">
                <MessageSquare size={36} className="mx-auto mb-3 text-[var(--color-text-muted)] opacity-60" />
                <h3 className="text-xs font-bold uppercase tracking-wider">SMS Buffer Idle</h3>
                <p className="text-[var(--color-text-secondary)] text-xs mt-1 leading-relaxed">
                  Waiting for direct recipient SMS responses. Unverified logs will display here immediately.
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-3">
                {smsLogs.map((log) => (
                  <div key={log.id} className="bg-[var(--color-surface)] border border-[var(--color-border)] p-4 rounded-2xl flex items-center justify-between shadow-sm hover:border-[#00B47A]/30 transition-all">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-blue-400 shrink-0" />
                        <p className="text-xs font-bold text-[var(--color-text-primary)]">{log.user_name}</p>
                        <span className="text-[8px] bg-blue-500/10 px-1.5 py-0.5 rounded border border-blue-500/15 text-blue-400 font-extrabold uppercase scale-90">
                          Beneficiary SMS Sync
                        </span>
                      </div>
                      <p className="text-xs text-[var(--color-text-secondary)] font-medium bg-[var(--color-background)] p-3 rounded-xl border border-[var(--color-border)]/50 mt-1 max-w-xl">
                        {log.content}
                      </p>
                    </div>
                    <span className="text-[9px] text-[var(--color-text-muted)] font-mono font-medium">
                      {new Date(log.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* IOT SENSORS TELEMETRY TAB */}
        {activeTab === 'sensors' && (
          <div className="space-y-4 animate-fade-in-up">
            <div className="bg-[var(--color-surface)] p-4.5 rounded-2xl border border-[var(--color-border)] shadow-sm">
              <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-primary)]">Bluetooth & IoT Temperature Sync</h3>
              <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
                Analyze local telemetry logs synchronized directly from cookstove microcontrollers.
              </p>
            </div>
            
            {isLoadingSensors ? (
              <div className="flex flex-col items-center justify-center py-16 space-y-2">
                <div className="w-6 h-6 border-2 border-[#00B47A] border-t-transparent rounded-full animate-spin" />
                <p className="text-xs text-[var(--color-text-secondary)] font-semibold">Tuning Bluetooth telemetry arrays...</p>
              </div>
            ) : sensorDevices.length === 0 ? (
              <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-12 text-center max-w-sm mx-auto shadow-sm">
                <Cpu size={36} className="mx-auto mb-3 text-[var(--color-text-muted)] opacity-60" />
                <h3 className="text-xs font-bold uppercase tracking-wider">IoT Array Idle</h3>
                <p className="text-[var(--color-text-secondary)] text-xs mt-1 leading-relaxed">
                  No active cookstove BLE sync logs detected in this cluster range.
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {sensorDevices.map((dev) => (
                  <div key={dev.device_id} className="bg-[var(--color-surface)] border border-[var(--color-border)] p-4.5 rounded-2xl shadow-sm hover:border-[#00B47A]/30 transition-all flex flex-col justify-between">
                    <div className="space-y-2">
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <div className="p-1.5 bg-[#00B47A]/5 border border-[#00B47A]/10 rounded-lg text-[#00B47A]">
                            <Cpu size={14} />
                          </div>
                          <p className="text-xs font-bold text-[var(--color-text-primary)] font-mono">
                            ESP32: {dev.device_id}
                          </p>
                        </div>
                        <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/15 text-[8px] font-black uppercase tracking-wider">
                          ONLINE
                        </span>
                      </div>
                      
                      <div className="bg-[var(--color-background)] border border-[var(--color-border)]/70 rounded-xl p-3 grid grid-cols-2 gap-2 text-[10px] font-bold text-[var(--color-text-secondary)]">
                        <div>
                          <span className="text-[9px] text-[var(--color-text-muted)] font-extrabold uppercase block tracking-wider mb-0.5">Stove Name</span>
                          <span className="text-[var(--color-text-primary)] truncate block">{dev.property_name || "Unknown"}</span>
                        </div>
                        <div>
                          <span className="text-[9px] text-[var(--color-text-muted)] font-extrabold uppercase block tracking-wider mb-0.5">Readings Sync</span>
                          <span className="text-[var(--color-text-primary)]">{dev.reading_count} logs</span>
                        </div>
                        <div className="mt-1">
                          <span className="text-[9px] text-[var(--color-text-muted)] font-extrabold uppercase block tracking-wider mb-0.5">Latest Temp</span>
                          <span className="text-orange-400 font-extrabold">{dev.last_temperature ? `${dev.last_temperature}°C` : "N/A"}</span>
                        </div>
                        <div className="mt-1">
                          <span className="text-[9px] text-[var(--color-text-muted)] font-extrabold uppercase block tracking-wider mb-0.5">Usage Ratio</span>
                          <span className="text-[#00B47A] font-extrabold">{dev.usage_rate}%</span>
                        </div>
                      </div>
                    </div>
                    <div className="border-t border-[var(--color-border)] pt-2.5 mt-3 flex items-center justify-between text-[9px] text-[var(--color-text-muted)] font-extrabold uppercase tracking-wider">
                      <span>Battery: {dev.last_battery_voltage ? `${dev.last_battery_voltage}V` : "N/A"}</span>
                      <span>Secured BLE Mesh</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

      </div>

    </div>
  );
}

// =============================================================================

// VeriField Nexus — Ground Truth Cross-Verification Page (CIOS Level 5)

// =============================================================================

// Displays pending audit tasks, flagged field submissions, SMS verification,

// and IoT sensor telemetry verification.

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

  Cpu,

  FileText,

  AlertTriangle

} from "lucide-react";

import {

  fetchProperties,

  fetchMyAuditTasks,

  createAuditTask,

  fetchActivities,

  fetchCommunityFeed,

  fetchSensorDevices,

  fetchAgentPerformance,

  type AuditTask

} from "@/lib/api";

import { useToast } from "@/components/Toast";

import { useWorkspace } from "@/context/WorkspaceContext";

import VerificationPipelineStages, { PipelineStage } from "@/components/VerificationPipelineStages";



export default function VerificationsPage() {

  const toast = useToast();

  const { activeSector, activeMethodology, filterProperties, filterAudits, moduleRegistry } = useWorkspace();

  const wsConfig = (activeSector && moduleRegistry?.[activeSector]) ? moduleRegistry[activeSector] : {};

  const [activeTab, setActiveTab] = useState<'audits' | 'community' | 'sensors'>('audits');

  const [selectedStage, setSelectedStage] = useState<PipelineStage | null>(null);

  const [audits, setAudits] = useState<AuditTask[]>([]);

  const [flaggedActivities, setFlaggedActivities] = useState<any[]>([]);

  const [isGenerating, setIsGenerating] = useState(false);

  const [isLoading, setIsLoading] = useState(true);



  // SMS Validation State

  const [smsLogs, setSmsLogs] = useState<any[]>([]);

  const [isLoadingSms, setIsLoadingSms] = useState(false);



  // IoT Sensors State

  const [sensorDevices, setSensorDevices] = useState<any[]>([]);

  const [isLoadingSensors, setIsLoadingSensors] = useState(false);



  // Load audit tasks and flagged activities

  const loadAuditData = async () => {

    setIsLoading(true);

    try {

      const [tasks, activitiesRes] = await Promise.all([

        fetchMyAuditTasks().catch(() => []),

        fetchActivities({ per_page: 100 }).catch(() => ({ activities: [] }))

      ]);



      setAudits(filterAudits(tasks));



      const actsList = Array.isArray(activitiesRes) ? activitiesRes : (activitiesRes?.activities || []);

      const flagged = actsList.filter((a: any) =>

        a.status === "audit" || a.status === "review" || a.trust_status === "AUDIT" || (a.trust_score !== undefined && a.trust_score < 80)

      );

      setFlaggedActivities(flagged);

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

      const [devicesRes, propertiesRes] = await Promise.all([

        fetchSensorDevices(),

        fetchProperties()

      ]);

      const devicesList = devicesRes.devices || [];

      const propertiesList = propertiesRes.properties || [];



      const filteredProps = filterProperties(propertiesList);

      const filteredPropIds = new Set(filteredProps.map(p => p.id));



      const activeDevices = devicesList.filter((dev: any) => filteredPropIds.has(dev.asset_id));

      setSensorDevices(activeDevices);

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

      const propsRes = await fetchProperties();

      if (!propsRes.properties.length) {

        toast.warning("No Assets", "No assets are available to generate audits.");

        return;

      }



      const randomProp = propsRes.properties[Math.floor(Math.random() * propsRes.properties.length)];



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

        agentId = actsRes.activities[0].user_id;

        assignedAgentName = actsRes.activities[0].agent_name || "Active Agent";

      }



      const deadline = new Date();

      deadline.setDate(deadline.getDate() + 7);



      const newAudit = await createAuditTask({

        asset_id: randomProp.id,

        assigned_agent: agentId,

        deadline: deadline.toISOString(),

      });



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



      {/* TITLE SECTION */}

      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[var(--color-border)] pb-4">

        <div>

          <div className="flex items-center gap-2">

            <span className="px-2.5 py-0.5 rounded bg-[var(--color-primary-light)] text-[var(--color-primary)] text-[9px] font-extrabold tracking-wider uppercase border border-[var(--color-primary)]/20">

              {activeMethodology || "All"}

            </span>

            <span className="text-[10px] text-[var(--color-text-secondary)] font-semibold flex items-center gap-1">

              Ground Truth Ledger

            </span>

          </div>

          <h1 className="text-xl font-bold tracking-tight text-[var(--color-text-primary)] mt-1">

            Verification & Audits Hub

          </h1>

          <p className="text-[var(--color-text-secondary)] text-xs mt-0.5">

            Cross-check telemetry, field reports, and independent audit claims for MRV verification.

          </p>

        </div>

      </div>



      {/* VERIFICATION PIPELINE STAGES BAR */}

      <VerificationPipelineStages

        selectedStage={selectedStage}

        onStageChange={setSelectedStage}

      />



      {/* TABS TOOLBAR */}

      <div className="flex bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-1 gap-1 max-w-fit shadow-inner">

        <button

          onClick={() => setActiveTab('audits')}

          className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-bold transition-all uppercase tracking-wider ${

            activeTab === 'audits'

              ? 'bg-[#00B47A] text-white shadow-md'

              : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-background)]/50'

          }`}

        >

          <ShieldAlert size={14} /> Audit Queue

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



      {/* CONTENT BLOCKS */}

      <div className="animation-delay-100 space-y-6">



        {/* AUDITS TAB */}

        {activeTab === 'audits' && (

          <div className="space-y-6">



            {/* 1. FLAGGED SUBMISSIONS PENDING AUDIT (DYNAMIC DB RECORDS) */}

            {flaggedActivities.length > 0 && (

              <div className="bg-[var(--color-surface)] border border-amber-500/30 rounded-2xl p-5 shadow-sm space-y-4">

                <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-3">

                  <div className="flex items-center gap-2.5">

                    <AlertTriangle size={18} className="text-amber-400 shrink-0" />

                    <div>

                      <h3 className="text-sm font-extrabold text-[var(--color-text-primary)] uppercase tracking-wider">

                        Flagged Submissions Pending Audit ({flaggedActivities.length})

                      </h3>

                      <p className="text-xs text-[var(--color-text-secondary)]">

                        Field activities flagged for manual verification by QA Officers or AI anomaly detectors.

                      </p>

                    </div>

                  </div>

                  <span className="text-[10px] font-mono bg-amber-500/20 text-amber-400 px-2.5 py-1 rounded-full font-bold border border-amber-500/30">

                    Action Required

                  </span>

                </div>



                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

                  {flaggedActivities.map((act) => {

                    const actData = act.activity_data || {};

                    const name = actData.stove_id || actData.head_name || act.activity_type?.replace(/_/g, ' ') || "Cookstove Activity";

                    return (

                      <div

                        key={act.id}

                        className="p-4 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] hover:border-amber-500/40 transition-all flex flex-col justify-between gap-3 shadow-xs"

                      >

                        <div className="flex items-start justify-between gap-2">

                          <div>

                            <p className="text-xs font-black text-[var(--color-text-primary)]">{name}</p>

                            <p className="text-[10px] text-[var(--color-text-secondary)] font-mono mt-0.5">

                              ID: {act.id.substring(0, 18)}...

                            </p>

                          </div>

                          <span className="text-[9px] font-mono px-2 py-0.5 rounded bg-amber-500/20 text-amber-400 font-extrabold border border-amber-500/30">

                            {act.trust_score ? `${act.trust_score} REVIEW` : "AUDIT"}

                          </span>

                        </div>



                        <div className="text-[10px] text-[var(--color-text-secondary)] space-y-1">

                          <p>Agent: <strong className="text-[var(--color-text-primary)]">{act.agent_name || "Field Agent"}</strong></p>

                          <p>Captured: <span className="font-mono">{new Date(act.captured_at).toLocaleDateString()}</span></p>

                          {act.latitude && (

                            <p className="font-mono text-blue-400">GPS: {act.latitude.toFixed(5)}, {act.longitude.toFixed(5)}</p>

                          )}

                        </div>



                        <Link

                          href={`/dashboard/activities/${act.id}`}

                          className="w-full py-2 rounded-lg bg-[#00B47A] hover:bg-[#009b68] text-white font-bold text-xs text-center transition-all flex items-center justify-center gap-1.5 shadow-xs"

                        >

                          <span>Review & Audit Sign-Off</span>

                          <ArrowRight size={13} />

                        </Link>

                      </div>

                    );

                  })}

                </div>

              </div>

            )}



            {/* 2. AUTOMATED VERIFICATION TRIGGERS (RANDOM ASSIGNMENTS) */}

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

                          <p className="text-xs font-bold text-[var(--color-text-primary)] truncate group-hover:text-[#00B47A] transition-colors" title={audit.property_name || `Unknown ${wsConfig?.label || "Asset"}`}>

                            {audit.property_name || `${wsConfig?.label || "Asset"} ID: ${audit.asset_id.substring(0, 8)}`}

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

                      </div>

                      <p className="text-[10px] text-[var(--color-text-secondary)] font-mono">{log.phone_number}</p>

                    </div>

                    <span className="text-[9px] font-bold px-2 py-0.5 rounded bg-emerald-500/20 text-[#00B47A]">

                      Confirmed

                    </span>

                  </div>

                ))}

              </div>

            )}

          </div>

        )}



        {/* IOT SENSOR TELEMETRY TAB */}

        {activeTab === 'sensors' && (

          <div className="space-y-4 animate-fade-in-up">

            <div className="bg-[var(--color-surface)] p-4.5 rounded-2xl border border-[var(--color-border)] shadow-sm">

              <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-primary)]">IoT Telemetry Hardware Verification</h3>

              <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">

                Verify active physical sensor BLE signatures and thermal consumption logs.

              </p>

            </div>



            {isLoadingSensors ? (

              <div className="flex flex-col items-center justify-center py-16 space-y-2">

                <div className="w-6 h-6 border-2 border-[#00B47A] border-t-transparent rounded-full animate-spin" />

                <p className="text-xs text-[var(--color-text-secondary)] font-semibold">Scanning IoT gateway signals...</p>

              </div>

            ) : sensorDevices.length === 0 ? (

              <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-12 text-center max-w-sm mx-auto shadow-sm">

                <Cpu size={36} className="mx-auto mb-3 text-[var(--color-text-muted)] opacity-60" />

                <h3 className="text-xs font-bold uppercase tracking-wider">No Active Hardware Sensors</h3>

                <p className="text-[var(--color-text-secondary)] text-xs mt-1 leading-relaxed">

                  No IoT sensors registered for active asset fleet.

                </p>

              </div>

            ) : (

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">

                {sensorDevices.map((dev) => (

                  <div key={dev.id} className="bg-[var(--color-surface)] border border-[var(--color-border)] p-4 rounded-2xl flex items-center justify-between shadow-sm">

                    <div className="space-y-1">

                      <p className="text-xs font-bold text-[var(--color-text-primary)] font-mono">{dev.device_id}</p>

                      <p className="text-[10px] text-[var(--color-text-secondary)]">Battery: {dev.battery_pct}% • Ping: {dev.last_ping}</p>

                    </div>

                    <span className="text-[9px] font-bold px-2 py-0.5 rounded bg-emerald-500/20 text-[#00B47A]">

                      Connected

                    </span>

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

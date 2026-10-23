"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useWorkspace } from "@/context/WorkspaceContext";
import { createActivity, recordSampleCollection, uploadProof } from "@/lib/api";
import { canPerformAction } from "@/lib/roles";
import { CAPTURE_FIELDS, captureQueueKey, projectCaptureSector, validateCapture } from "@/lib/fieldCapture";
import { useToast } from "@/components/Toast";

interface CaptureRecord {
  clientId: string;
  owner: string;
  projectId: string;
  sector: keyof typeof CAPTURE_FIELDS;
  asset: string;
  metric: number;
  latitude: number;
  longitude: number;
  accuracy: number | null;
  capturedAt: string;
  notes: string;
  collector: string;
  condition: string;
  deviation: string;
  photo?: string;
  photoUrl?: string;
  photoHash?: string;
}
const fieldClass = "mt-1 block w-full rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2.5 text-sm text-white focus:border-emerald-500 focus:outline-none";
function readPhoto(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(new Error("Could not read photo."));
    reader.readAsDataURL(file);
  });
}

export default function CapturePage() {
  const { user, isLoading, projects, allowedSectors, activeProject } = useWorkspace();
  const toast = useToast();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  const [projectId, setProjectId] = useState("");
  const [asset, setAsset] = useState("");
  const [metric, setMetric] = useState("");
  const [latitude, setLatitude] = useState<number | null>(null);
  const [longitude, setLongitude] = useState<number | null>(null);
  const [accuracy, setAccuracy] = useState<number | null>(null);
  const [notes, setNotes] = useState("");
  const [condition, setCondition] = useState("GOOD");
  const [deviation, setDeviation] = useState("");
  const [photo, setPhoto] = useState<File | null>(null);
  const [queue, setQueue] = useState<CaptureRecord[]>([]);
  const [online, setOnline] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<{ id: string; status: string } | null>(null);
  const canCapture = canPerformAction("evidence:upload", user?.role);
  const queueKey = user ? captureQueueKey(user.id, user.organization_id) : null;
  const project = projects.find(p => p.id === projectId);
  const sector = projectCaptureSector(project);
  const fields = sector ? CAPTURE_FIELDS[sector] : null;

  useEffect(() => {
    const requested = new URLSearchParams(window.location.search).get("project");
    const selected = requested || activeProject || (projects.length === 1 ? projects[0].id : "");
    if (projects.some(p => p.id === selected)) setProjectId(selected);
  }, [projects, activeProject]);

  useEffect(() => {
    if (!queueKey || !user) return;
    try {
      const saved = JSON.parse(localStorage.getItem(queueKey) || "[]");
      setQueue(Array.isArray(saved) ? saved.filter(r => r.owner === user.id) : []);
    } catch { setError("Saved field records could not be read. They remain in browser storage."); }
  }, [queueKey, user?.id]);

  useEffect(() => {
    const update = () => setOnline(navigator.onLine);
    update();
    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    return () => { window.removeEventListener("online", update); window.removeEventListener("offline", update); };
  }, []);

  function locate() {
    if (!navigator.geolocation) { setError("Location is unavailable on this device. Enter the actual coordinates."); return; }
    navigator.geolocation.getCurrentPosition(position => {
      setLatitude(position.coords.latitude); setLongitude(position.coords.longitude); setAccuracy(position.coords.accuracy); setError("");
    }, () => { setError("Location could not be obtained. Enable location access or enter the actual coordinates."); }, { enableHighAccuracy: true, timeout: 10000 });
  }

  function saveQueue(records: CaptureRecord[]) {
    if (!queueKey) throw new Error("Sign in before saving records.");
    localStorage.setItem(queueKey, JSON.stringify(records));
    setQueue(records);
  }

  async function send(record: CaptureRecord) {
    if (!user || record.owner !== user.id || !canCapture) throw new Error("This record belongs to another account.");
    const currentProject = projects.find(p => p.id === record.projectId);
    const validation = validateCapture(currentProject, allowedSectors, String(record.metric), record.latitude, record.longitude);
    if (validation || projectCaptureSector(currentProject) !== record.sector) throw new Error(validation || "Project sector changed. Review this record before syncing.");
    if (record.photo && !record.photoUrl) {
      const blob = await (await fetch(record.photo)).blob();
      const uploaded = await uploadProof(new File([blob], "field-photo", { type: blob.type }));
      if (!uploaded.image_url) throw new Error("Photo upload failed. The field record has not been submitted.");
      record.photoUrl = uploaded.image_url;
    }
    if (record.sector === "AGRICULTURE_LAND_USE") {
      const response = await recordSampleCollection(record.projectId, record.asset, {
        actual_lat: record.latitude, actual_lon: record.longitude,
        collection_timestamp: record.capturedAt, collector_name: record.collector,
        actual_depth_from_cm: 0, actual_depth_to_cm: record.metric, sample_condition: record.condition,
        deviation_reason: record.deviation || undefined, notes: record.notes || undefined,
        idempotency_key: record.clientId, photo_hash: record.photoHash,
        device_metadata: { gps_accuracy_meters: record.accuracy, photo_url: record.photoUrl },
      });
      return { id: response.id, status: "Collection recorded" };
    }
    const config = CAPTURE_FIELDS[record.sector];
    const response = await createActivity({
      project_id: record.projectId, client_id: record.clientId, activity_type: config.type,
      latitude: record.latitude, longitude: record.longitude, gps_accuracy: record.accuracy,
      captured_at: record.capturedAt, description: record.notes, image_url: record.photoUrl, image_hash: record.photoHash,
      activity_data: { asset_identifier: record.asset, [config.key]: record.metric, sector: record.sector,
        project_id: record.projectId, provisional_field_observation: true, field_data_authority: "PROVISIONAL_OBSERVATION" },
    });
    return { id: response.id, status: response.status || "Submitted" };
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!canCapture || !user) return;
    const validation = validateCapture(project, allowedSectors, metric, latitude, longitude);
    if (validation || !sector) { setError(validation || "Select a project."); return; }
    if (!asset.trim()) { setError(sector === "AGRICULTURE_LAND_USE" ? "Enter the assigned physical sample ID." : "Enter an asset identifier."); return; }
    if (sector === "AGRICULTURE_LAND_USE" && !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(asset.trim())) { setError("Use the assigned physical sample's UUID."); return; }
    setBusy(true); setError("");
    try {
      const photoData = photo ? await readPhoto(photo) : undefined;
      const hash = photo ? Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", await photo.arrayBuffer())), b => b.toString(16).padStart(2, "0")).join("") : undefined;
      const record: CaptureRecord = { clientId: crypto.randomUUID(), owner: user.id, projectId, sector, asset: asset.trim(), metric: Number(metric), latitude: latitude!, longitude: longitude!, accuracy, capturedAt: new Date().toISOString(), notes, collector: user.full_name, condition, deviation, photo: photoData, photoHash: hash };
      if (!navigator.onLine) {
        saveQueue([...queue, record]); setResult({ id: record.clientId, status: "Saved offline — awaiting submission" });
      } else {
        setResult(await send(record));
      }
    } catch (err) { setError(err instanceof Error ? err.message : "Submission failed. Review your record and retry."); }
    finally { setBusy(false); }
  }

  async function sync() {
    if (!online || busy) return;
    setBusy(true); setError("");
    let remaining = [...queue];
    try {
      while (remaining.length) {
        await send(remaining[0]);
        remaining = remaining.slice(1);
        saveQueue(remaining);
      }
      toast.success("Sync complete", "Your field records have been submitted.");
    } catch (err) { setError(err instanceof Error ? err.message : "Sync failed. Remaining records are saved."); }
    finally { setBusy(false); }
  }

  if (!mounted || (isLoading && !user)) return <p className="p-6">Loading field capture…</p>;
  if (!user || !canCapture) return <div className="p-6 space-y-3"><h1 className="text-xl font-semibold">Field capture unavailable</h1><p>Your role does not have permission to submit field records.</p><Link href={user ? "/dashboard" : "/login"}>Return to {user ? "overview" : "sign in"}</Link></div>;

  return <main className="mx-auto max-w-xl p-4 sm:p-6 space-y-6">
    <header className="flex items-center justify-between border-b border-zinc-800 pb-4"><Link href="/dashboard/operations" className="text-sm text-zinc-400">← Field operations</Link><span className="text-xs text-zinc-400">{online ? "Online" : "Offline"}</span></header>
    <div><h1 className="text-2xl font-semibold">Capture field data</h1><p className="mt-1 text-sm text-zinc-400">Record observations for your assigned project.</p></div>
    {!online && <p data-testid="pwa-offline-banner" className="text-sm text-amber-300">Records will be saved on this device until you sync.</p>}
    {queue.length > 0 && <div data-testid="pwa-queue-banner" className="flex justify-between items-center rounded-lg border border-zinc-700 p-3 text-sm"><span>{queue.length} saved offline</span><button data-testid="pwa-sync-button" onClick={sync} disabled={!online || busy} className="text-emerald-400 disabled:opacity-40">Sync records</button></div>}
    {error && <p role="alert" className="rounded-lg border border-red-800 p-3 text-sm text-red-300">{error}</p>}
    {result ? <section className="rounded-xl border border-zinc-700 p-5 space-y-4"><h2 className="text-lg font-semibold">{result.status}</h2><p className="break-all text-sm text-zinc-400">Record: {result.id}</p><button onClick={() => { setResult(null); setAsset(""); setMetric(""); setPhoto(null); setNotes(""); }} className="text-emerald-400 text-sm">Capture another record</button></section> :
      <form onSubmit={submit} className="space-y-5">
        <label className="block text-sm">Project<select required data-testid="pwa-project-select" className={fieldClass} value={projectId} onChange={e => { setProjectId(e.target.value); setAsset(""); setMetric(""); }}><option value="">Select project</option>{projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}</select></label>
        {fields ? <p data-testid="capture-sector" className="text-sm text-emerald-400">{fields.label}</p> : <p className="text-sm text-zinc-400">{projects.length ? "Select a project with a configured sector." : "No assigned projects are available. Contact your project manager."}</p>}
        {fields && <>
          <label className="block text-sm">{sector === "AGRICULTURE_LAND_USE" ? "Physical sample ID" : "Asset identifier"}<input required className={fieldClass} value={asset} onChange={e => setAsset(e.target.value)} /></label>
          <label className="block text-sm">{fields.metric}<input required type="number" min="0.000001" step="any" className={fieldClass} value={metric} onChange={e => setMetric(e.target.value)} /></label>
          {sector === "AGRICULTURE_LAND_USE" && <div className="space-y-4"><label className="block text-sm">Sample condition<select className={fieldClass} value={condition} onChange={e => setCondition(e.target.value)}>{["GOOD", "ACCEPTABLE", "DEGRADED", "COMPACTED"].map(c => <option key={c}>{c}</option>)}</select></label><label className="block text-sm">Location deviation reason<input className={fieldClass} value={deviation} onChange={e => setDeviation(e.target.value)} /></label></div>}
          <fieldset className="rounded-lg border border-zinc-800 p-3"><legend className="px-1 text-sm">Location</legend><button type="button" onClick={locate} className="mb-3 text-sm text-emerald-400">Use current location</button><div className="grid grid-cols-2 gap-3"><label className="text-sm">Latitude<input required type="number" step="any" min="-90" max="90" className={fieldClass} value={latitude ?? ""} onChange={e => { setLatitude(e.target.value === "" ? null : Number(e.target.value)); setAccuracy(null); }} /></label><label className="text-sm">Longitude<input required type="number" step="any" min="-180" max="180" className={fieldClass} value={longitude ?? ""} onChange={e => { setLongitude(e.target.value === "" ? null : Number(e.target.value)); setAccuracy(null); }} /></label></div>{accuracy !== null && <p className="mt-2 text-xs text-zinc-400">GPS accuracy: ±{Math.round(accuracy)} m</p>}</fieldset>
          <label className="block text-sm">Photo (optional)<input type="file" accept="image/jpeg,image/png,image/webp" className={fieldClass} onChange={e => { const f = e.target.files?.[0]; if (f && (f.size > 10 * 1024 * 1024 || !["image/jpeg", "image/png", "image/webp"].includes(f.type))) { setError("Choose a JPG, PNG or WebP photo up to 10 MB."); setPhoto(null); e.target.value = ""; } else setPhoto(f || null); }} /></label>
          <label className="block text-sm">Notes (optional)<textarea className={fieldClass} rows={3} value={notes} onChange={e => setNotes(e.target.value)} /></label>
          <button disabled={busy} className="w-full rounded-lg bg-emerald-600 py-3 text-sm font-semibold text-white disabled:opacity-50">{busy ? "Saving…" : online ? "Submit record" : "Save offline"}</button>
        </>}
      </form>}
  </main>;
}

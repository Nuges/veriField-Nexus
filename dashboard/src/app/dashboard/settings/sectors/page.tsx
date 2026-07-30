"use client";



import { useState, useEffect } from "react";

import { useWorkspace } from "@/context/WorkspaceContext";

import { fetchMethodologyFamilies, addLicensedSector } from "@/lib/api";

import { Plus, ShieldCheck, AlertTriangle, Loader2 } from "lucide-react";



export default function SectorsSettingsPage() {

  const { user, refreshUser } = useWorkspace();

  const [families, setFamilies] = useState<any[]>([]);

  const [selectedSector, setSelectedSector] = useState("");

  const [isLoading, setIsLoading] = useState(false);

  const [error, setError] = useState("");

  const [success, setSuccess] = useState("");



  const isSuperAdmin = user?.role === "SUPER_ADMIN";

  const isOrgAdmin = user?.role === "ORG_ADMIN" || user?.role === "admin";



  useEffect(() => {

    async function loadFamilies() {

      try {

        const fams = await fetchMethodologyFamilies();

        setFamilies(Array.isArray(fams) ? fams : []);

      } catch (err) {

        console.error("Failed to load sectors", err);

      }

    }

    loadFamilies();

  }, []);



  const handleAddSector = async (e: React.FormEvent) => {

    e.preventDefault();

    if (!selectedSector) return;

    if (!user?.organization_id) {

      setError("No organization context found.");

      return;

    }



    setIsLoading(true);

    setError("");

    setSuccess("");



    try {

      await addLicensedSector(user.organization_id, { sector_id: selectedSector });

      setSuccess("Sector capability successfully provisioned to your organization.");

      setSelectedSector("");

      // Refresh user context to reload allowedSectors

      await refreshUser();

    } catch (err: any) {

      setError(err.message || "Failed to provision sector. Please try again.");

    } finally {

      setIsLoading(false);

    }

  };



  if (!isSuperAdmin && !isOrgAdmin) {

    return (

      <div className="p-8">

        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-6 text-red-400 flex items-center gap-4">

          <AlertTriangle size={24} />

          <div>

            <h3 className="font-bold">Access Denied</h3>

            <p className="text-sm">You do not have permission to manage organization sectors.</p>

          </div>

        </div>

      </div>

    );

  }



  // Filter out sectors that the user already has licensed

  const licensedSectorCodes = Array.isArray(user?.licensed_sectors)

    ? user.licensed_sectors.map((s: string) => s.toLowerCase())

    : [user?.sector?.toLowerCase() || ""];



  const availableFamilies = families.filter(fam => !licensedSectorCodes.includes(fam.code?.toLowerCase()));



  return (

    <div className="p-8 max-w-4xl mx-auto animate-fade-in">

      <div className="mb-8">

        <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">Sector Capabilities</h1>

        <p className="text-sm text-[var(--color-text-secondary)] mt-1">

          Manage and provision new MRV sector tracking capabilities for your organization.

        </p>

      </div>



      <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl overflow-hidden mb-8">

        <div className="p-6 border-b border-[var(--color-border)]">

          <h2 className="text-lg font-bold flex items-center gap-2">

            <ShieldCheck className="text-emerald-500" /> Currently Licensed Sectors

          </h2>

        </div>

        <div className="p-6">

          <div className="flex flex-wrap gap-3">

            {licensedSectorCodes.map((code, idx) => (

              <div key={idx} className="bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 px-4 py-2 rounded-xl text-sm font-bold uppercase tracking-wide">

                {code || "Generic"}

              </div>

            ))}

          </div>

        </div>

      </div>



      <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-2xl overflow-hidden">

        <div className="p-6 border-b border-[var(--color-border)]">

          <h2 className="text-lg font-bold flex items-center gap-2">

            <Plus className="text-blue-500" /> Provision New Sector

          </h2>

          <p className="text-sm text-[var(--color-text-secondary)] mt-1">

            Add new tracking capabilities to your workspace. Once provisioned, your field agents can immediately begin onboarding projects in the new sector.

          </p>

        </div>



        <div className="p-6">

          {error && (

            <div className="mb-6 px-4 py-3 rounded-xl text-sm bg-red-500/10 border border-red-500/20 text-red-400 flex items-start gap-2">

              <AlertTriangle size={18} className="mt-0.5 shrink-0" />

              <span>{error}</span>

            </div>

          )}



          {success && (

            <div className="mb-6 px-4 py-3 rounded-xl text-sm bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-start gap-2">

              <ShieldCheck size={18} className="mt-0.5 shrink-0" />

              <span>{success}</span>

            </div>

          )}



          {availableFamilies.length === 0 ? (

            <div className="text-center py-8 text-[var(--color-text-secondary)] bg-[var(--color-surface)] rounded-xl border border-[var(--color-border)] border-dashed">

              Your organization is already licensed for all available sectors!

            </div>

          ) : (

            <form onSubmit={handleAddSector} className="space-y-4">

              <div>

                <label className="text-xs font-bold text-[var(--color-text-secondary)] uppercase tracking-wide mb-2 block">Available Sectors</label>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

                  {availableFamilies.map(fam => (

                    <div

                      key={fam.id}

                      onClick={() => setSelectedSector(fam.id)}

                      className={`cursor-pointer border rounded-xl p-4 transition-all ${selectedSector === fam.id ? "bg-blue-500/10 border-blue-500" : "bg-[var(--color-surface)] border-[var(--color-border)] hover:border-blue-500/50"}`}

                    >

                      <h4 className="font-bold text-[var(--color-text-primary)]">{fam.name}</h4>

                      <p className="text-xs text-[var(--color-text-muted)] mt-1">{fam.description}</p>

                    </div>

                  ))}

                </div>

              </div>



              <div className="pt-4 flex justify-end">

                <button

                  type="submit"

                  disabled={isLoading || !selectedSector}

                  className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white px-6 py-2.5 rounded-xl font-bold text-sm tracking-wide transition-colors flex items-center gap-2 shadow-lg shadow-blue-500/20"

                >

                  {isLoading ? <Loader2 size={16} className="animate-spin" /> : <Plus size={16} />}

                  Provision Sector

                </button>

              </div>

            </form>

          )}

        </div>

      </div>

    </div>

  );

}

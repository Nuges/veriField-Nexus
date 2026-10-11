"use client";



import { useState, useEffect, useMemo } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ShieldCheck, Mail, User, Building, Loader2, Sparkles, MapPin, Activity, ChevronDown } from "lucide-react";
import { createAccessRequest, fetchMethodologies } from "@/lib/api";
import {
  getCanonicalOperatingSectors,
  getCanonicalMethodologiesForSector,
  isMethodologyCompatibleWithSector,
} from "@/lib/sectors";
import { ThemeLogo } from "@/components/common/ThemeLogo";

export default function SignupPage() {
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [orgName, setOrgName] = useState("");
  const [country, setCountry] = useState("Global");
  const [sectorId, setSectorId] = useState("");
  const [methodologyId, setMethodologyId] = useState("");
  const [projectName, setProjectName] = useState("");

  const canonicalSectors = useMemo(() => getCanonicalOperatingSectors(), []);
  const [methodologies, setMethodologies] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const handleSectorChange = async (newSectorId: string) => {
    setSectorId(newSectorId);
    setMethodologyId("");

    if (!newSectorId) {
      setMethodologies([]);
      return;
    }

    // 1. Immediately scope to canonical sector methodologies (fail-closed, 0 latency)
    const canonicalList = getCanonicalMethodologiesForSector(newSectorId);
    setMethodologies(canonicalList);

    // 2. Query backend scoped strictly to this sector to align with server registry
    try {
      const methsRes = await fetchMethodologies(newSectorId).catch(() => []);
      const remoteList = Array.isArray(methsRes) ? methsRes : (methsRes?.modules || []);

      // Filter remote list strictly to authorized methodologies for this sector (zero cross-sector leakage)
      const validRemote = remoteList.filter((m: any) =>
        isMethodologyCompatibleWithSector(newSectorId, m.code || m.id)
      );

      if (validRemote.length > 0) {
        setMethodologies(validRemote);
      }
    } catch (err) {
      console.error("Failed to fetch methodologies for sector:", err);
    }
  };




  const handleSignup = async (e: React.FormEvent) => {

    e.preventDefault();

    if (!fullName || !email || !orgName || !sectorId || !projectName) {

      setError("Please fill out all required fields.");

      return;

    }

    setIsLoading(true);

    setError("");



    try {

      await createAccessRequest({

        full_name: fullName,

        email,

        phone: undefined,

        organization_name: orgName,

        country: country || undefined,

        sector_id: sectorId,

        methodology_id: methodologyId || undefined,

        project_name: projectName,

      });

      setSuccess(true);

    } catch (err: any) {

      setError(err.message || "Failed to submit onboarding request. Please verify details.");

    } finally {

      setIsLoading(false);

    }

  };



  return (

    <div className="min-h-screen bg-[var(--color-background)] flex items-center justify-center px-4 py-12">

      <div className="absolute inset-0 overflow-hidden pointer-events-none">

        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-emerald-500/5 rounded-full blur-3xl" />

        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-blue-500/5 rounded-full blur-3xl" />

      </div>



      <div className="w-full max-w-xl relative animate-fade-in-up">

        {/* Logo */}

        <div className="text-center mb-6 flex flex-col items-center justify-center">

          <ThemeLogo className="h-8 w-auto object-contain mb-2" />

        </div>



        <div className="bg-[var(--color-card)]/80 backdrop-blur-xl border border-[var(--color-border)] rounded-2xl p-8 shadow-2xl">

          <div className="mb-6">

            <h2 className="text-xl font-bold text-[var(--color-text-primary)] mb-2">

              Create Organization

            </h2>

            <p className="text-[var(--color-text-secondary)] text-sm">

              Register your company workspace to generate isolated carbon credit MRV ledgers.

            </p>

          </div>



          {success ? (

            <div className="text-center py-8 space-y-4 animate-fade-in">

              <div className="w-12 h-12 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center mx-auto">

                <ShieldCheck size={28} className="animate-pulse" />

              </div>

              <h3 className="text-sm font-bold text-emerald-400 uppercase tracking-wider">Request Submitted!</h3>

              <p className="text-xs text-[var(--color-text-secondary)]">

                Your onboarding request is pending review by a Super Admin. You will receive an email once approved.

              </p>

            </div>

          ) : (

            <form onSubmit={handleSignup} className="space-y-4">

              {error && (

                <div className="px-4 py-3 rounded-xl text-xs bg-red-500/10 border border-red-500/20 text-red-400">

                  {error}

                </div>

              )}



              <div className="space-y-4">

                <div>

                  <label className="text-sm font-bold text-[var(--color-text-secondary)] mb-1.5 block">Organization Name</label>

                  <div className="relative">

                    <Building size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />

                    <input

                      type="text"

                      value={orgName}

                      onChange={(e) => setOrgName(e.target.value)}

                      placeholder="e.g. Manny Solar"

                      required

                      className="w-full pl-10 pr-4 py-3 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-primary)] text-sm focus:outline-none focus:border-emerald-500 focus:ring-1"

                    />

                  </div>

                </div>



                <div>

                  <label className="text-sm font-bold text-[var(--color-text-secondary)] mb-1.5 block">Full Name</label>

                  <div className="relative">

                    <User size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />

                    <input

                      type="text"

                      value={fullName}

                      onChange={(e) => setFullName(e.target.value)}

                      placeholder="e.g. Dapo Olu"

                      required

                      className="w-full pl-10 pr-4 py-3 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-primary)] text-sm focus:outline-none focus:border-emerald-500 focus:ring-1"

                    />

                  </div>

                </div>



                <div>

                  <label className="text-sm font-bold text-[var(--color-text-secondary)] mb-1.5 block">Email Address</label>

                  <div className="relative">

                    <Mail size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />

                    <input

                      type="email"

                      value={email}

                      onChange={(e) => setEmail(e.target.value)}

                      placeholder="e.g. alex@company.com"

                      required

                      className="w-full pl-10 pr-4 py-3 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-primary)] text-sm focus:outline-none focus:border-emerald-500 focus:ring-1"

                    />

                  </div>

                </div>



                <div>
                  <label htmlFor="primary-operating-sector" className="text-sm font-bold text-[var(--color-text-secondary)] mb-1.5 block">Primary Operating Sector</label>
                  <div className="relative">
                    <Activity size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)] pointer-events-none" />
                    <select
                      id="primary-operating-sector"
                      data-testid="primary-operating-sector-select"
                      aria-label="Primary Operating Sector"
                      value={sectorId}
                      onChange={(e) => handleSectorChange(e.target.value)}
                      required
                      className="w-full pl-10 pr-10 py-3 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-primary)] text-sm focus:outline-none focus:border-emerald-500 focus:ring-1 appearance-none cursor-pointer"
                    >
                      <option value="" disabled>Select a sector...</option>
                      {canonicalSectors.map((sec) => (
                        <option key={sec.code} value={sec.code}>
                          {sec.label}
                        </option>
                      ))}
                    </select>
                    <ChevronDown size={16} className="absolute right-3.5 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)] pointer-events-none" />
                  </div>
                </div>

                <div>
                  <label htmlFor="primary-operating-methodology" className="text-sm font-bold text-[var(--color-text-secondary)] mb-1.5 block">
                    Methodology (Optional Preference)
                  </label>
                  <div className="relative">
                    <select
                      id="primary-operating-methodology"
                      data-testid="methodology-select"
                      aria-label="Methodology (Optional Preference)"
                      value={methodologyId}
                      onChange={(e) => setMethodologyId(e.target.value)}
                      disabled={!sectorId || methodologies.length === 0}
                      className={`w-full pl-4 pr-10 py-3 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-primary)] text-sm focus:outline-none focus:border-emerald-500 focus:ring-1 appearance-none ${
                        !sectorId || methodologies.length === 0 ? "opacity-60 cursor-not-allowed bg-[var(--color-surface-hover)]" : "cursor-pointer"
                      }`}
                    >
                      {!sectorId ? (
                        <option value="">Select a sector first</option>
                      ) : methodologies.length === 0 ? (
                        <option value="">No sector methodologies available</option>
                      ) : (
                        <>
                          <option value="">None / Decide Later at Project Level</option>
                          {methodologies.map((meth) => {
                            const badge = meth.verifieldSupport === "FULL"
                              ? " [Full MRV & Calculations]"
                              : meth.verifieldSupport === "MRV_ONLY"
                              ? " [MRV Evidence & Monitoring]"
                              : meth.verifieldSupport === "CATALOG_ONLY"
                              ? " [Catalog Reference]"
                              : "";
                            return (
                              <option key={meth.id || meth.code} value={meth.id || meth.code}>
                                {meth.code} — {meth.name}{badge}
                              </option>
                            );
                          })}
                        </>
                      )}
                    </select>
                    <ChevronDown size={16} className="absolute right-3.5 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)] pointer-events-none" />
                  </div>
                </div>



                <div>

                  <label className="text-sm font-bold text-[var(--color-text-secondary)] mb-1.5 block">Country of Operations</label>

                  <div className="relative">

                    <MapPin size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />

                    <select

                      value={country}

                      onChange={(e) => setCountry(e.target.value)}

                      className="w-full pl-10 pr-4 py-3 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-primary)] text-sm focus:outline-none focus:border-emerald-500 focus:ring-1 appearance-none"

                    >

                      <option value="Global">Global</option>

                      <option value="Nigeria">Nigeria</option>

                      <option value="Kenya">Kenya</option>

                      <option value="Rwanda">Rwanda</option>

                      <option value="United States">United States</option>

                      <option value="India">India</option>

                      <option value="Brazil">Brazil</option>

                    </select>

                  </div>

                </div>



                <div>

                  <label className="text-sm font-bold text-[var(--color-text-secondary)] mb-1.5 block">First Project Name</label>

                  <div className="relative">

                    <input

                      type="text"

                      value={projectName}

                      onChange={(e) => setProjectName(e.target.value)}

                      placeholder="e.g. Oloibiri Solar Minigrid Phase 1"

                      required

                      className="w-full px-4 py-3 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-primary)] text-sm focus:outline-none focus:border-emerald-500 focus:ring-1"

                    />

                  </div>

                </div>

              </div>



              <div className="pt-4 mt-2">

                <button

                  type="submit"

                  disabled={isLoading}

                  className="w-full py-3 rounded-xl bg-emerald-500 text-white text-sm font-bold hover:bg-emerald-600 transition-colors flex items-center justify-center gap-2 disabled:opacity-50"

                >

                  {isLoading ? <Loader2 size={16} className="animate-spin" /> : "SUBMIT ACCESS REQUEST"}

                </button>

              </div>



              <div className="text-center mt-6">

                <Link href="/login" className="text-xs text-[var(--color-text-secondary)] hover:text-emerald-400 transition-colors">

                  Already have an organization workspace? <strong className="text-emerald-500">Sign In</strong>

                </Link>

              </div>

            </form>

          )}

        </div>

      </div>

    </div>

  );

}

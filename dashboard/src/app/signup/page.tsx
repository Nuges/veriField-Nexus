"use client";



import { useState, useEffect } from "react";

import { useRouter } from "next/navigation";

import Link from "next/link";

import { ShieldCheck, Mail, User, Building, Loader2, Sparkles, MapPin, Activity, ChevronDown } from "lucide-react";

import { createAccessRequest, fetchMethodologyFamilies } from "@/lib/api";
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



  const [families, setFamilies] = useState<any[]>([]);

  const [methodologies, setMethodologies] = useState<any[]>([]);

  const [isLoading, setIsLoading] = useState(false);

  const [error, setError] = useState("");

  const [success, setSuccess] = useState(false);



  const [allMethodologies, setAllMethodologies] = useState<any[]>([]);



  useEffect(() => {

    async function loadData() {

      try {

        const { fetchMethodologyFamilies, fetchMethodologies } = await import("@/lib/api");

        const [famsRes, methsRes] = await Promise.all([

          fetchMethodologyFamilies().catch(() => []),

          fetchMethodologies().catch(() => []),

        ]);



        const filteredFams = Array.isArray(famsRes)

          ? famsRes.filter(f => !["SYS_DEFAULT", "FAM-464d9f"].includes(f.code))

          : [];

        setFamilies(filteredFams);



        const methList = Array.isArray(methsRes) ? methsRes : (methsRes?.modules || []);

        setAllMethodologies(methList);

      } catch (err) {

        console.error("Failed to load signup metadata", err);

      }

    }

    loadData();

  }, []);



  const handleSignup = async (e: React.FormEvent) => {

    e.preventDefault();

    if (!fullName || !email || !orgName || !sectorId || !methodologyId || !projectName) {

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

        methodology_id: methodologyId,

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
                  <label className="text-sm font-bold text-[var(--color-text-secondary)] mb-1.5 block">Primary Operating Sector</label>
                  <div className="relative">
                    <Activity size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)] pointer-events-none" />
                    <select
                      value={sectorId}
                      onChange={(e) => {
                        const newSectorId = e.target.value;
                        setSectorId(newSectorId);
                        setMethodologyId("");

                        const matched = allMethodologies.filter((m: any) =>
                          (m.family && (m.family.id === newSectorId || m.family.code === newSectorId)) ||
                          m.family_id === newSectorId ||
                          m.family_code === newSectorId
                        );

                        // If matched list is not empty use it, otherwise show all active as fallback
                        setMethodologies(matched.length > 0 ? matched : allMethodologies);
                      }}
                      required
                      className="w-full pl-10 pr-10 py-3 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-primary)] text-sm focus:outline-none focus:border-emerald-500 focus:ring-1 appearance-none cursor-pointer"
                    >
                      <option value="" disabled>Select a sector...</option>
                      {families.map((fam) => (
                        <option key={fam.id} value={fam.id}>
                          {fam.name}
                        </option>
                      ))}
                    </select>
                    <ChevronDown size={16} className="absolute right-3.5 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)] pointer-events-none" />
                  </div>
                </div>

                {sectorId && (
                  <div>
                    <label className="text-sm font-bold text-[var(--color-text-secondary)] mb-1.5 block">Methodology</label>
                    <div className="relative">
                      <select
                        value={methodologyId}
                        onChange={(e) => setMethodologyId(e.target.value)}
                        required
                        className="w-full pl-4 pr-10 py-3 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-primary)] text-sm focus:outline-none focus:border-emerald-500 focus:ring-1 appearance-none cursor-pointer"
                      >
                        <option value="" disabled>Select a methodology...</option>
                        {methodologies.map((meth) => (
                          <option key={meth.id} value={meth.id}>
                            {meth.name} ({meth.code})
                          </option>
                        ))}
                      </select>
                      <ChevronDown size={16} className="absolute right-3.5 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)] pointer-events-none" />
                    </div>
                  </div>
                )}



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

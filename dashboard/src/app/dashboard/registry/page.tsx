"use client";
import { useWorkspace } from "@/context/WorkspaceContext";
import RegistryModule from "@/components/dashboard/RegistryModule";

export default function RegistryPage() {
  const { activeProject, changeProject, projects, activeSector } = useWorkspace();
  return <div className="space-y-5 max-w-7xl mx-auto pb-10">
    <div className="flex flex-wrap justify-between gap-3 border-b border-[var(--color-border)] pb-4">
      <div><h1 className="text-xl font-bold">Registry Preparation</h1><p className="text-xs text-[var(--color-text-secondary)] mt-1">Review project requirements and prepare documents for review.</p></div>
      <label className="text-xs flex items-center gap-2">Project
        <select aria-label="Registry project" value={activeProject || ""} onChange={(event) => changeProject(event.target.value || null)} className="p-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] max-w-72">
          <option value="">Select a project</option>{projects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}
        </select>
      </label>
    </div>
    <RegistryModule projectId={activeProject || undefined} sectorCode={activeSector || undefined} />
  </div>;
}

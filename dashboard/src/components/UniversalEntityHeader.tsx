"use client";
import { usePathname } from "next/navigation";
interface SecondaryAction {

  label: string;

  onClick: () => void;

  variant?: "danger" | "neutral";

}



interface UniversalEntityHeaderProps {

  entityType: string;

  entityId: string;

  entityName: string;

  currentStage: number; // 1 to 6

  currentStageName: string;

  ownerRole: string;

  ownerName: string;

  slaText?: string;

  status: string;

  aiConfidence?: number;

  aiRecommendation?: string;

  primaryNextActionLabel: string;

  onPrimaryNextAction: () => void;

  secondaryActions?: SecondaryAction[];

}




const titles: Record<string, string> = {
  projects: "Projects", assets: "Assets", activities: "Field records", agents: "Field performance",
  sensors: "Sensors", methodologies: "Methodologies", analytics: "Reports", carbon: "Carbon ledger",
  verifications: "Verification", people: "People & access", registry: "Registry", monitoring: "Data quality",
};
/** Generic page headers do not imply a verified lifecycle, SLA or AI assessment. */
export default function UniversalEntityHeader(props: UniversalEntityHeaderProps) {
  const pathname = usePathname();
  const key = pathname.split("/")[2];
  return <div className="flex flex-wrap items-center justify-between gap-3 mb-5">
    <h1 className="text-xl font-semibold text-[var(--color-text-primary)]">{titles[key] || props.entityName}</h1>
    <div className="flex flex-wrap gap-2">
      {props.primaryNextActionLabel && <button type="button" onClick={props.onPrimaryNextAction} className="px-3 py-2 rounded-lg bg-emerald-700 text-white text-sm font-medium">{props.primaryNextActionLabel}</button>}
      {props.secondaryActions?.map(action => <button key={action.label} type="button" onClick={action.onClick} className="px-3 py-2 rounded-lg border border-[var(--color-border)] text-sm">{action.label}</button>)}
    </div>
  </div>;
}

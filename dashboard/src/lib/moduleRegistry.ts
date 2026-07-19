import { 
  Leaf, 
  Flame, 
  Zap, 
  Scale, 
  Sprout, 
  Home, 
  Globe, 
  ClipboardCheck, 
  MessageSquare, 
  Cpu,
  LucideIcon
} from "lucide-react";

export interface KPICardDef {
  key: string;
  label: string;
  valueField: string;
  unit: string;
  iconName: string;
  colorTheme: "green" | "amber" | "blue" | "purple" | "emerald";
  description: string;
}

export interface ChartDef {
  key: string;
  title: string;
  type: "area" | "bar" | "line";
  dataKeyX: string;
  dataKeyY: string;
  fillColor: string;
  strokeColor: string;
}

export interface ModuleLabels {
  assetLabel: string;
  assetLabelPlural: string;
  telemetryTitle: string;
  telemetryDesc: string;
  syncTitle: string;
  emptyLogsMsg: string;
  specLabel: string;
  assetTargetLabel: string;
  noLogsText: string;
  propHeading: string;
  propSub: string;
  tabLabel: string;
  tabIconName: string;
  activitiesTitle: string;
  activitiesDesc: string;
}

export interface TableColumnDef {
  header: string;
  accessor: string;
  align?: "left" | "center" | "right";
  format?: "weight" | "percent" | "raw" | "id";
}

export interface FilterOption {
  value: string;
  label: string;
}

export interface ModuleDefinition {
  id: string;
  name: string;
  badge: string;
  methodology: string;
  registryReference: string;
  allowedRoles: string[];
  kpis: KPICardDef[];
  charts: ChartDef[];
  labels: ModuleLabels;
  markerColor: string;
  themeColor: string;
  tableColumns: TableColumnDef[];
  filterOptions: FilterOption[];
}

export function normalizeSector(sec: string): string {
  if (!sec) return "generic";
  const normalized = sec.toLowerCase().trim();
  
  if (normalized.includes("cook") || normalized.includes("stove")) return "cookstove";
  if (normalized.includes("hybrid") || normalized.includes("solar") || normalized.includes("grid")) return "hybrid_energy";
  if (normalized.includes("biochar") || normalized.includes("soil") || normalized.includes("agri")) return "biochar";
  if (normalized.includes("ev") || normalized.includes("mobility") || normalized.includes("transport")) return "ev_mobility";
  
  return normalized;
}

export function mapToWorkspace(record: any): string | null {
  if (!record) return null;

  const normalizeVal = (value?: any) => {
    if (typeof value !== "string") return "";
    return value.toLowerCase().trim();
  };

  const type = normalizeVal(record.property_type || record.activity_type || record.type || record.asset_type || record.sector);
  if (!type) return null;

  if (type.includes("cook") || type.includes("stove") || type === "residential") return "cookstove";
  if (type.includes("hybrid") || type.includes("solar") || type.includes("grid")) return "hybrid_energy";
  if (type.includes("biochar") || type.includes("soil") || type.includes("agri")) return "biochar";
  if (type.includes("ev") || type.includes("mobility") || type.includes("transport")) return "ev_mobility";

  return type;
}

export function getRecordSector(record: any): string {
  if (record && record.sector) {
    return normalizeSector(record.sector);
  }
  return mapToWorkspace(record) || "generic";
}

import type { RiskLevel } from "../types";

export const RISK_LEVELS: RiskLevel[] = [
  "VERY_LOW",
  "LOW",
  "MODERATE",
  "HIGH",
  "CRITICAL",
];

export function riskColor(level: RiskLevel | string): string {
  const map: Record<string, string> = {
    VERY_LOW: "#22c55e",
    LOW: "#eab308",
    MODERATE: "#f97316",
    HIGH: "#ef4444",
    CRITICAL: "#a855f7",
  };
  return map[level] || "#64748b";
}

export function riskTextClass(level: RiskLevel | string): string {
  const map: Record<string, string> = {
    VERY_LOW: "bg-green-100 text-green-700",
    LOW: "bg-yellow-100 text-yellow-700",
    MODERATE: "bg-orange-100 text-orange-700",
    HIGH: "bg-red-100 text-red-700",
    CRITICAL: "bg-purple-100 text-purple-700",
  };
  return map[level] || "bg-slate-100 text-slate-700";
}

export function severityColor(sev: string): string {
  const map: Record<string, string> = {
    low: "bg-green-100 text-green-700",
    medium: "bg-yellow-100 text-yellow-700",
    high: "bg-red-100 text-red-700",
    critical: "bg-purple-100 text-purple-700",
    advisory: "bg-blue-100 text-blue-700",
    watch: "bg-yellow-100 text-yellow-700",
    warning: "bg-red-100 text-red-700",
  };
  return map[sev] || "bg-slate-100 text-slate-700";
}

export function incidentStatusColor(status: string): string {
  const map: Record<string, string> = {
    reported: "bg-slate-100 text-slate-700",
    verified: "bg-blue-100 text-blue-700",
    monitoring: "bg-yellow-100 text-yellow-700",
    response: "bg-orange-100 text-orange-700",
    resolved: "bg-green-100 text-green-700",
  };
  return map[status] || "bg-slate-100 text-slate-700";
}

export function roadStatusColor(status: string): string {
  const map: Record<string, string> = {
    open: "bg-green-100 text-green-700",
    restricted: "bg-yellow-100 text-yellow-700",
    blocked: "bg-red-100 text-red-700",
    severely_blocked: "bg-purple-100 text-purple-700",
    unknown: "bg-slate-100 text-slate-700",
  };
  return map[status] || "bg-slate-100 text-slate-700";
}

export function roadPredictionLevelColor(level: string): string {
  const map: Record<string, string> = {
    low: "bg-green-100 text-green-700",
    moderate: "bg-yellow-100 text-yellow-700",
    high: "bg-red-100 text-red-700",
    critical: "bg-purple-100 text-purple-700",
  };
  return map[level] || "bg-slate-100 text-slate-700";
}

export function priorityColor(cls: string): string {
  const map: Record<string, string> = {
    immediate: "bg-red-600 text-white",
    high: "bg-orange-500 text-white",
    medium: "bg-yellow-500 text-white",
    low: "bg-slate-300 text-slate-700",
  };
  return map[cls] || "bg-slate-300 text-slate-700";
}

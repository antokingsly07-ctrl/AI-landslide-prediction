import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../lib/api";
import type { HealthReport } from "../types";

export default function Health() {
  const { t } = useTranslation();
  const [health, setHealth] = useState<HealthReport | null>(null);

  useEffect(() => {
    api.get("/admin/health").then((r) => setHealth(r.data)).catch(() => setHealth({ status: "degraded", api: "ok", database: "unknown", ml_model: "unknown", weather_provider: "unknown", satellite_provider: "unknown", notification_provider: "unknown", environment: "unknown", components: {} }));
  }, []);

  const ping = (s?: string) =>
    s === "ok" ? "bg-green-100 text-green-700" : s === "degraded" ? "bg-amber-100 text-amber-700" : "bg-red-100 text-red-700";

  const rows: [string, string | undefined][] = [
    ["API", health?.api],
    ["Database", health?.database],
    ["ML Model", health?.ml_model],
    ["Weather Provider", health?.weather_provider],
    ["Satellite Provider", health?.satellite_provider],
    ["Notification Provider", health?.notification_provider],
    ["Environment", health?.environment],
  ];

  return (
    <div className="space-y-4 max-w-3xl">
      <h2 className="text-xl font-semibold">{t("nav.health")}</h2>
      <div className="card">
        <div className="flex items-center gap-2 mb-4">
          <span className={`badge ${health?.status === "ok" ? "bg-green-100 text-green-700" : "bg-amber-100 text-amber-700"}`}>
            {health?.status}
          </span>
          <span className="text-sm text-slate-500">Overall system status</span>
        </div>
        <div className="space-y-3">
          {rows.map(([label, val]) => (
            <div key={label} className="flex items-center justify-between border-b pb-2 last:border-0">
              <span className="text-sm text-slate-600">{label}</span>
              <span className={`badge ${ping(val)} capitalize`}>{val || "unknown"}</span>
            </div>
          ))}
        </div>
      </div>
      {health?.components && (
        <div className="card">
          <h3 className="font-semibold mb-3">Services</h3>
          <div className="space-y-2">
            {Object.entries(health.components).map(([k, v]) => (
              <div key={k} className="flex items-center justify-between">
                <span className="text-sm capitalize">{k.replace(/_/g, " ")}</span>
                <span className={`badge ${ping(v.status)} capitalize`}>{v.status}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

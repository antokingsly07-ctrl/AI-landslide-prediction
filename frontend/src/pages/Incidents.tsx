import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../lib/api";
import type { Incident } from "../types";
import { incidentStatusColor, priorityColor } from "../lib/utils";

export default function Incidents() {
  const { t } = useTranslation();
  const [incidents, setIncidents] = useState<Incident[]>([]);

  useEffect(() => {
    api.get("/incidents").then((r) => setIncidents(r.data)).catch(() => {});
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">{t("nav.incidents")}</h2>
      </div>
      <div className="grid gap-3">
        {incidents.map((i) => (
          <div key={i.id} className="card flex items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="font-semibold capitalize">{i.incident_type}</span>
                <span className={`badge ${incidentStatusColor(i.verification_status)} capitalize`}>
                  {i.verification_status}
                </span>
                <span className="badge bg-slate-100 text-slate-700 capitalize">{i.status}</span>
              </div>
              <p className="text-sm text-slate-600 mt-1">{i.description}</p>
              <div className="text-xs text-slate-500 mt-1">
                {i.reporter_name ? `${i.reporter_name} · ` : ""}
                {new Date(i.reported_at).toLocaleString()}
              </div>
              {i.priority_score !== undefined && (
                <div className="mt-2">
                  <span className={`badge ${priorityColor(i.priority_class || "low")}`}>
                    {i.priority_class?.toUpperCase()} priority · {i.priority_score}
                  </span>
                </div>
              )}
            </div>
            <span className={`text-xs uppercase shrink-0 ${i.severity === "critical" ? "text-red-600" : "text-slate-500"}`}>
              {i.severity}
            </span>
          </div>
        ))}
        {incidents.length === 0 && (
          <div className="card text-center text-slate-500 py-10">No incidents</div>
        )}
      </div>
    </div>
  );
}

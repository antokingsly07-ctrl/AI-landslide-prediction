import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../lib/api";
import { priorityColor } from "../lib/utils";

interface Priority {
  incident_id: string;
  location: string;
  incident_type: string;
  description?: string | null;
  severity: string;
  population_affected: number;
  priority_score: number;
  priority_class: string;
  reasons?: string[];
  status: string;
  responder_notes?: string | null;
  incident_status: string;
}

export default function Emergency() {
  const { t } = useTranslation();
  const [items, setItems] = useState<Priority[]>([]);

  useEffect(() => {
    api
      .get("/dashboard/emergency/priorities")
      .then((r) => setItems(r.data))
      .catch(() => setItems([]));
  }, []);

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">{t("nav.emergency")}</h2>
      <div className="grid gap-3">
        {items.map((it) => (
          <div key={it.incident_id} className="card">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 sm:gap-3">
              <div>
                <div className="font-semibold capitalize">{it.incident_type}</div>
                <div className="text-xs text-slate-500 mt-0.5">{it.location}</div>
              </div>
              <span className={`badge ${priorityColor(it.priority_class)} uppercase self-start sm:self-auto`}>
                {it.priority_class} priority
              </span>
            </div>
            <div className="flex flex-wrap gap-2 mt-2 text-xs">
              <span className="badge bg-slate-100 text-slate-700 capitalize">Severity: {it.severity}</span>
              <span className="badge bg-slate-100 text-slate-700">Pop affected: {it.population_affected}</span>
              <span className="badge bg-slate-100 text-slate-700">Score: {it.priority_score}</span>
              <span className="badge bg-slate-100 text-slate-700 capitalize">Response: {it.status}</span>
            </div>
            {it.reasons && it.reasons.length > 0 && (
              <div className="mt-3 pt-2 border-t border-slate-100">
                <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-400 mb-1.5">
                  Why this priority
                </div>
                <ul className="space-y-1">
                  {it.reasons.map((r, i) => (
                    <li key={i} className="flex items-start gap-1.5 text-xs text-slate-600">
                      <span className="text-slate-400 mt-px">▸</span>
                      <span className="min-w-0">{r}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {it.responder_notes && (
              <p className="text-xs text-slate-500 mt-2 italic">{it.responder_notes}</p>
            )}
          </div>
        ))}
        {items.length === 0 && (
          <div className="card text-center text-slate-500 py-10">No emergency priorities</div>
        )}
      </div>
    </div>
  );
}

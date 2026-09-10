import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../lib/api";
import type { Alert } from "../types";
import { severityColor } from "../lib/utils";

export default function Alerts() {
  const { t } = useTranslation();
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [filter, setFilter] = useState("active");

  useEffect(() => {
    api
      .get("/alerts", { params: filter ? { status: filter } : {} })
      .then((r) => setAlerts(r.data))
      .catch(() => {});
  }, [filter]);

  const acknowledge = async (id: string) => {
    try {
      await api.post(`/alerts/${id}/acknowledge`);
      setAlerts((a) => a.map((x) => (x.id === id ? { ...x, status: "acknowledged" } : x)));
    } catch {
      /* ignore */
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <h2 className="text-xl font-semibold">{t("alert.title")}</h2>
        <select className="input !w-auto" value={filter} onChange={(e) => setFilter(e.target.value)}>
          <option value="active">Active</option>
          <option value="acknowledged">Acknowledged</option>
          <option value="">All</option>
        </select>
      </div>
      <div className="space-y-3">
        {alerts.map((a) => (
          <div key={a.id} className="card">
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-start gap-3">
                <span className={`badge ${severityColor(a.severity)} uppercase`}>{a.severity}</span>
                <div>
                  <div className="font-semibold">{a.title}</div>
                  <p className="text-sm text-slate-600 mt-1">{a.message}</p>
                  {a.cause && (
                    <p className="text-xs text-slate-500 mt-1">
                      <strong>Cause:</strong> {a.cause}
                    </p>
                  )}
                  <div className="flex flex-wrap gap-2 mt-2 text-xs">
                    {a.affected_villages?.length > 0 && (
                      <span className="badge bg-blue-100 text-blue-700">
                        {a.affected_villages.length} villages
                      </span>
                    )}
                    {a.affected_roads?.length > 0 && (
                      <span className="badge bg-blue-100 text-blue-700">
                        {a.affected_roads.length} roads
                      </span>
                    )}
                    {a.risk_level && <span className="badge bg-slate-100 text-slate-700">{a.risk_level}</span>}
                  </div>
                </div>
              </div>
              <div className="text-right shrink-0">
                <div className="text-xs text-slate-500">
                  {new Date(a.triggered_at).toLocaleString()}
                </div>
                <div className="badge mt-1 bg-slate-100 text-slate-700 capitalize">{a.status}</div>
                {a.status === "active" && (
                  <button onClick={() => acknowledge(a.id)} className="btn-secondary !py-1 !px-2 text-xs mt-2">
                    {t("alert.acknowledge")}
                  </button>
                )}
              </div>
            </div>
          </div>
        ))}
        {alerts.length === 0 && (
          <div className="card text-center text-slate-500 py-10">No alerts</div>
        )}
      </div>
    </div>
  );
}
